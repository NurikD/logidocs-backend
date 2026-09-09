"""Ежедневная рассылка push об истекающих путёвках.

Запускать раз в сутки (cron). Идемпотентна в пределах дня: по каждому
документу клиенту уходит не больше одного push за день (last_notified_date).

Клиенту: за 7 дней до конца и дальше каждый день, пока он не нажмёт
«Понятно» в приложении (notification_dismissed).
Диспетчеру: один дайджест в день по всем клиентам в зоне риска —
независимо от того, заглушил ли клиент напоминание у себя.
"""
import os
from datetime import date

from django.core.management.base import BaseCommand

from accounts.models import Document, DeviceToken, User

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:  # пакет не установлен — команда отработает в режиме --dry-run
    firebase_admin = None


def _init_firebase() -> bool:
    """Инициализация Firebase Admin SDK. False — если не настроен."""
    if firebase_admin is None:
        return False
    if firebase_admin._apps:
        return True
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not cred_path or not os.path.exists(cred_path):
        return False
    firebase_admin.initialize_app(credentials.Certificate(cred_path))
    return True


def _client_message(doc: Document, days_left: int) -> tuple[str, str]:
    if days_left < 0:
        return (
            "Путёвка просрочена",
            f"«{doc.title}» истекла {doc.expires_at}. Нужно срочно обновить.",
        )
    if days_left == 0:
        return ("Путёвка истекает сегодня", f"«{doc.title}» действует последний день.")
    return (
        "Путёвка скоро закончится",
        f"«{doc.title}» действует до {doc.expires_at} — осталось {days_left} дн.",
    )


class Command(BaseCommand):
    help = "Отправить push об истекающих и просроченных путёвках"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ничего не отправлять и не сохранять — только показать, что ушло бы",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = date.today()

        firebase_ready = _init_firebase()
        if not firebase_ready and not dry_run:
            self.stdout.write(self.style.WARNING(
                "Firebase не настроен (нет FIREBASE_CREDENTIALS_PATH) — работаю как --dry-run"
            ))
            dry_run = True

        at_risk = [
            d for d in Document.objects
            .filter(kind=Document.Kind.BUSINESS, expires_at__isnull=False)
            .select_related("owner", "vehicle")
            .order_by("expires_at")
            if d.is_expired or d.is_expiring_soon
        ]

        sent = self._notify_clients(at_risk, today, dry_run)
        digest = self._notify_admins(at_risk, dry_run)

        self.stdout.write(self.style.SUCCESS(
            f"В зоне риска: {len(at_risk)}; уведомлений клиентам: {sent}; дайджест диспетчеру: {digest}"
        ))

    def _notify_clients(self, at_risk, today, dry_run) -> int:
        sent = 0
        for doc in at_risk:
            if doc.notification_dismissed or not doc.owner_id:
                continue
            if doc.last_notified_date == today:
                continue

            tokens = list(DeviceToken.objects.filter(user_id=doc.owner_id).values_list("token", flat=True))
            days_left = (doc.expires_at - today).days
            title, body = _client_message(doc, days_left)

            if dry_run:
                self.stdout.write(f"[dry-run] {doc.owner.username}: {title} — {body} ({len(tokens)} устр.)")
            elif tokens:
                self._send(tokens, title, body, {"document_id": str(doc.id)})
                Document.objects.filter(pk=doc.pk).update(last_notified_date=today)
            else:
                # устройств нет — не помечаем как отправленное, догоним когда войдёт
                continue
            sent += 1
        return sent

    def _notify_admins(self, at_risk, dry_run) -> int:
        if not at_risk:
            return 0

        expired = [d for d in at_risk if d.is_expired]
        soon = [d for d in at_risk if not d.is_expired]
        parts = []
        if expired:
            parts.append(f"просрочено: {len(expired)}")
        if soon:
            parts.append(f"истекает: {len(soon)}")
        body = "; ".join(parts)

        names = ", ".join(sorted({d.owner.username for d in at_risk if d.owner_id})[:5])
        if names:
            body = f"{body}. Клиенты: {names}"

        tokens = list(
            DeviceToken.objects.filter(user__is_superuser=True).values_list("token", flat=True)
        )
        if dry_run:
            self.stdout.write(f"[dry-run] диспетчеру: Путёвки клиентов — {body} ({len(tokens)} устр.)")
            return 1
        if not tokens:
            return 0
        self._send(tokens, "Путёвки клиентов", body, {"screen": "expiring"})
        return 1

    def _send(self, tokens, title, body, data):
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data,
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)
        # протухшие токены чистим, чтобы не копить мусор
        for token, result in zip(tokens, response.responses):
            if not result.success:
                DeviceToken.objects.filter(token=token).delete()
