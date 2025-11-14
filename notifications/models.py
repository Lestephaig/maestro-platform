from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """Модель для отслеживания отправленных уведомлений"""
    
    NOTIFICATION_TYPE_CHAT_MESSAGE = 'chat_message'
    NOTIFICATION_TYPE_PROJECT_INVITATION = 'project_invitation'
    NOTIFICATION_TYPE_PROJECT_STATUS_CHANGE = 'project_status_change'
    NOTIFICATION_TYPE_PROJECT_COMPLETION = 'project_completion'
    
    NOTIFICATION_TYPE_CHOICES = [
        (NOTIFICATION_TYPE_CHAT_MESSAGE, 'Новое сообщение в чате'),
        (NOTIFICATION_TYPE_PROJECT_INVITATION, 'Приглашение в проект'),
        (NOTIFICATION_TYPE_PROJECT_STATUS_CHANGE, 'Изменение статуса проекта'),
        (NOTIFICATION_TYPE_PROJECT_COMPLETION, 'Завершение проекта'),
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

