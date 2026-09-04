import time

from django.core.management.base import BaseCommand

from notifications.deliveries import process_pending_deliveries


class Command(BaseCommand):
    help = 'Отправляет ожидающие внешние уведомления из надёжной очереди БД'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--watch', action='store_true')
        parser.add_argument('--poll-interval', type=float, default=5)

    def handle(self, *args, **options):
        limit = max(1, options['limit'])
        poll_interval = max(0.1, options['poll_interval'])
        try:
            while True:
                result = process_pending_deliveries(limit=limit)
                if not options['watch']:
                    self.stdout.write(self.style.SUCCESS(
                        f"Обработано: {result['processed']}; отправлено: {result['sent']}"
                    ))
                    return
                if result['processed'] == 0:
                    time.sleep(poll_interval)
        except KeyboardInterrupt:
            self.stdout.write('Worker остановлен')
