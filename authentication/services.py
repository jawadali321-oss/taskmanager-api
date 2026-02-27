from django.core.mail import send_mail
from django.conf import settings
from .models import OTP
import threading

def send_otp_email(user):
    """Generate OTP and send to user's email"""
    OTP.objects.filter(user=user, is_used=False).update(is_used=True)
    code = OTP.generate_code()
    OTP.objects.create(user=user, code=code)
    
    def send():
        try:
            send_mail(
                subject='Your Verification OTP - Task Manager',
                message=f'Hi {user.username},\n\nYour OTP code is: {code}\n\nThis code expires in 10 minutes.\n\nDo not share this code with anyone.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email sending failed: {e}")
    
    threading.Thread(target=send).start()
    return code

def verify_otp(user, code):
    """Verify OTP code for a user. Returns (success, message)"""
    otp = OTP.objects.filter(user=user, code=code, is_used=False).order_by('-created_at').first()
    if not otp:
        return False, "Invalid OTP code."
    if otp.is_expired():
        return False, "OTP has expired. Please request a new one."
    otp.is_used = True
    otp.save()
    return True, "OTP verified successfully."
