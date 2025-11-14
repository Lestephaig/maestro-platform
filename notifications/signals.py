from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from interactions.models import Interaction, InteractionParticipant
from chat.models import Message
from .models import Notification
from .utils import send_notification_email


@receiver(post_save, sender=InteractionParticipant)
def notify_participant_invitation(sender, instance, created, **kwargs):
    """Уведомление при приглашении в проект"""
    if created and instance.status == InteractionParticipant.STATUS_PENDING:
        interaction = instance.interaction
        
        # Определяем роль для отображения
        role_display = instance.get_role_display()
        
        send_notification_email(
            user=instance.user,
            notification_type=Notification.NOTIFICATION_TYPE_PROJECT_INVITATION,
            title=f'Приглашение в проект "{interaction.title}"',
            message=f'Вас пригласили участвовать в проекте "{interaction.title}" в роли {role_display}',
            context={
                'project_title': interaction.title,
                'project_description': interaction.description[:200],
                'role': role_display,
                'inviter_name': interaction.created_by.username,
                'project_url': f'/interactions/{interaction.id}/',
            },
            related_object_id=instance.id,
            related_object_type='interactions.interactionparticipant'
        )


@receiver(pre_save, sender=Interaction)
def notify_project_status_change(sender, instance, **kwargs):
    """Уведомление об изменении статуса проекта"""
    if instance.pk:  # Только для существующих проектов
        try:
            old_instance = Interaction.objects.get(pk=instance.pk)
            old_status = old_instance.status
            new_status = instance.status
            
            # Если статус изменился
            if old_status != new_status:
                # Уведомляем всех участников проекта
                # Используем all() чтобы получить все связи, так как instance еще не сохранен
                participants = list(InteractionParticipant.objects.filter(
                    interaction=instance,
                    status=InteractionParticipant.STATUS_ACCEPTED
                ).select_related('user'))
                
                status_display = instance.get_status_display()
                
                for participant in participants:
                    # Не уведомляем создателя, если он сам изменил статус
                    if participant.user != instance.created_by:
                        send_notification_email(
                            user=participant.user,
                            notification_type=Notification.NOTIFICATION_TYPE_PROJECT_STATUS_CHANGE,
                            title=f'Изменение статуса проекта "{instance.title}"',
                            message=f'Статус проекта "{instance.title}" изменен на "{status_display}"',
                            context={
                                'project_title': instance.title,
                                'old_status': old_instance.get_status_display(),
                                'new_status': status_display,
                                'project_url': f'/interactions/{instance.id}/',
                            },
                            related_object_id=instance.id,
                            related_object_type='interactions.interaction'
                        )
                
                # Уведомление о завершении проекта
                if new_status == Interaction.STATUS_COMPLETED:
                    for participant in participants:
                        send_notification_email(
                            user=participant.user,
                            notification_type=Notification.NOTIFICATION_TYPE_PROJECT_COMPLETION,
                            title=f'Проект "{instance.title}" завершен',
                            message=f'Проект "{instance.title}" был завершен',
                            context={
                                'project_title': instance.title,
                                'project_url': f'/interactions/{instance.id}/',
                            },
                            related_object_id=instance.id,
                            related_object_type='interactions.interaction'
                        )
        except Interaction.DoesNotExist:
            pass


@receiver(post_save, sender=Message)
def schedule_chat_notification(sender, instance, created, **kwargs):
    """Планирует проверку непрочитанного сообщения через 5 минут"""
    if created:
        # Сообщение только что создано, проверка будет выполнена через задачу
        # Это будет обработано через management command или периодическую задачу
        pass

