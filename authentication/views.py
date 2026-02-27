from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, OTPVerifySerializer, LoginSerializer, ResendOTPSerializer
from .services import send_otp_email, verify_otp


def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            try:
                send_otp_email(user)
            except Exception as e:
                user.delete()
                return Response({'error': f'Failed to send OTP email: {str(e)}'}, status=500)
            return Response({
                'message': f'Registration successful! OTP sent to {user.email}. Please verify to activate your account.'
            }, status=201)
        return Response(serializer.errors, status=400)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)

        success, message = verify_otp(user, code)
        if not success:
            return Response({'error': message}, status=400)

        user.is_active = True
        user.save()

        tokens = get_tokens(user)
        return Response({
            'message': 'Account verified successfully!',
            'tokens': tokens,
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            user = User.objects.get(email=serializer.validated_data['email'])
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)

        if user.is_active:
            return Response({'error': 'Account already verified.'}, status=400)

        try:
            send_otp_email(user)
        except Exception as e:
            return Response({'error': f'Failed to send OTP: {str(e)}'}, status=500)

        return Response({'message': f'New OTP sent to {user.email}.'})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )

        if not user:
            return Response({'error': 'Invalid username or password.'}, status=401)

        if not user.is_active:
            return Response({'error': 'Account not verified. Please verify your OTP first.'}, status=403)

        tokens = get_tokens(user)
        return Response({
            'message': 'Login successful!',
            'tokens': tokens,
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'Refresh token required.'}, status=400)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully.'})
        except Exception:
            return Response({'error': 'Invalid token.'}, status=400)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined,
        })
