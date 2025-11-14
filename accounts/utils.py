from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


def generate_email_verification_token(user):
    """Генерирует токен для подтверждения email"""
    return default_token_generator.make_token(user)


def send_verification_email(user, request):
    """Отправляет email с ссылкой для подтверждения"""
    token = generate_email_verification_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Создаем ссылку подтверждения
    verification_url = request.build_absolute_uri(
        f'/accounts/verify-email/{uid}/{token}/'
    )
    
    # Тема письма
    subject = 'Подтверждение email адреса - Maestro Platform'
    
    # Текст письма
    message = render_to_string('accounts/emails/email_verification.txt', {
        'user': user,
        'verification_url': verification_url,
    })
    
    # HTML версия письма
    html_message = render_to_string('accounts/emails/email_verification.html', {
        'user': user,
        'verification_url': verification_url,
    })
    
    # Отправляем email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def verify_email_token(uidb64, token):
    """Проверяет токен и подтверждает email"""
    from .models import User
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None
    
    if default_token_generator.check_token(user, token):
        user.is_email_verified = True
        user.save()
        return user
    
    return None

