from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('performer', 'Исполнитель'),
        ('client', 'Площадка'),
        ('agent', 'Организатор'),
    ]

    email = models.EmailField(unique=True, blank=False, null=False)
    first_name = models.CharField('Имя', max_length=200, blank=True)
    display_name = models.CharField('Имя пользователя', max_length=150, blank=True, help_text='Отображаемое имя пользователя')
    is_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField('Email подтвержден', default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='performer')

    def __str__(self):
        return self.display_name or self.username or self.email


class TelegramConnection(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_connection',
    )
    telegram_chat_id = models.BigIntegerField(unique=True)
    linked_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Telegram connection for user {self.user_id}'


class TelegramLinkToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_link_tokens',
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'Telegram link token for user {self.user_id}'


class LegalAcceptance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='legal_acceptances')
    document_slug = models.CharField(max_length=80)
    document_title = models.CharField(max_length=255)
    document_version = models.CharField(max_length=40)
    accepted_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'document_slug', 'document_version')
        indexes = [
            models.Index(fields=['user', 'document_slug', 'document_version']),
        ]
        ordering = ['-accepted_at']

    def __str__(self):
        return f'{self.user} accepted {self.document_slug} {self.document_version}'


class CookieConsent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cookie_consents', blank=True, null=True)
    policy_version = models.CharField(max_length=40)
    accepted_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'policy_version']),
        ]
        ordering = ['-accepted_at']

    def __str__(self):
        user_label = self.user_id if self.user_id else 'anonymous'
        return f'{user_label} accepted cookie policy {self.policy_version}'
