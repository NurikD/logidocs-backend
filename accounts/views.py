from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.contrib.auth.hashers import check_password
from .serializers import LoginSerializer, ChangePasswordSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = ChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user: User = request.user
        if not check_password(s.validated_data["old_password"], user.password):
            return Response({"detail": "Неверный старый пароль"}, status=400)
        user.set_password(s.validated_data["new_password"])
        user.must_change_pw = False
        user.save(update_fields=["password", "must_change_pw"])
        return Response({"ok": True})
