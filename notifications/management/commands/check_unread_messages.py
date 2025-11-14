from django.core.management.base import BaseCommand
from notifications.utils import check_unread_chat_messages


class Command(BaseCommand):
    help = 'Проверяет непрочитанные сообщения в чате и отправляет уведомления через 5 минут'

    def handle(self, *args, **options):
        self.stdout.write('Проверка непрочитанных сообщений...')
        check_unread_chat_messages()
        self.stdout.write(self.style.SUCCESS('Проверка завершена'))

