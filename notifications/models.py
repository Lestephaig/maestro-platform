from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse


class Notification(models.Model):
    """Модель для отслеживания отправленных уведомлений"""
    
    NOTIFICATION_TYPE_CHAT_MESSAGE = 'chat_message'
    NOTIFICATION_TYPE_PROJECT_INVITATION = 'project_invitation'
    NOTIFICATION_TYPE_PROJECT_STATUS_CHANGE = 'project_status_change'
    NOTIFICATION_TYPE_PROJECT_COMPLETION = 'project_completion'
    NOTIFICATION_TYPE_ANNOUNCEMENT_TAG_MATCH = 'announcement_tag_match'
    
    NOTIFICATION_TYPE_CHOICES = [
        (NOTIFICATION_TYPE_CHAT_MESSAGE, 'Новое сообщение в чате'),
        (NOTIFICATION_TYPE_PROJECT_INVITATION, 'Приглашение в проект'),
        (NOTIFICATION_TYPE_PROJECT_STATUS_CHANGE, 'Изменение статуса проекта'),
        (NOTIFICATION_TYPE_PROJECT_COMPLETION, 'Завершение проекта'),
        (NOTIFICATION_TYPE_ANNOUNCEMENT_TAG_MATCH, 'Новые подходящие объявления'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Пользователь'
    )
    notification_type = models.CharField(
        'Тип уведомления',
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES
    )
    title = models.CharField('Заголовок', max_length=255)
    message = models.TextField('Сообщение')
    related_object_id = models.PositiveIntegerField('ID связанного объекта', null=True, blank=True)
    related_object_type = models.CharField('Тип связанного объекта', max_length=50, blank=True)
    sent_at = models.DateTimeField('Отправлено', auto_now_add=True)
    is_sent = models.BooleanField('Отправлено', default=False)
    email_sent = models.BooleanField('Email отправлен', default=False)
    in_app_sent = models.BooleanField('В приложении доступно', default=True)
    is_read = models.BooleanField('Прочитано', default=False)
    read_at = models.DateTimeField('Прочитано в', null=True, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        indexes = [
            models.Index(fields=['user', 'notification_type', 'is_sent']),
            models.Index(fields=['related_object_type', 'related_object_id']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} для {self.user.username}"

    def mark_read(self):
        if self.is_read:
            return
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])

    def get_related_url(self):
        if self.related_object_type == 'interactions.interaction' and self.related_object_id:
            return reverse('interactions:detail', args=[self.related_object_id])
        if self.related_object_type == 'announcements.announcement' and self.related_object_id:
            return reverse('announcements:detail', args=[self.related_object_id])
        return None


class NotificationPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='Пользователь',
    )
    notification_type = models.CharField(
        'Тип уведомления',
        max_length=50,
        choices=Notification.NOTIFICATION_TYPE_CHOICES,
    )
    in_app_enabled = models.BooleanField('В приложении', default=True)
    email_enabled = models.BooleanField('Email', default=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Настройка уведомлений'
        verbose_name_plural = 'Настройки уведомлений'
        unique_together = ('user', 'notification_type')
        indexes = [
            models.Index(fields=['user', 'notification_type']),
        ]

    def __str__(self):
        return f'{self.user}: {self.get_notification_type_display()}'

    @classmethod
    def get_or_create_for(cls, user, notification_type):
        preference, _ = cls.objects.get_or_create(
            user=user,
            notification_type=notification_type,
            defaults={'in_app_enabled': True, 'email_enabled': True},
        )
        return preference

