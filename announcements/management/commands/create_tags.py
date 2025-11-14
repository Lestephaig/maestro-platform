from django.core.management.base import BaseCommand
from django.utils.text import slugify
from announcements.models import Tag
from performers.models import PerformerProfile


class Command(BaseCommand):
    help = 'Создает теги по типам голоса и инструментам'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Удалить существующие теги и создать заново',
        )

    def handle(self, *args, **options):
        # Типы голоса
        voice_types = PerformerProfile.DEFAULT_VOICE_TYPES
        
        # Инструменты
        instruments = PerformerProfile.DEFAULT_INSTRUMENTS
        
        # Если указан флаг --force, удаляем все существующие теги
        if options['force']:
            Tag.objects.all().delete()
            self.stdout.write(self.style.WARNING('Все существующие теги удалены.'))
        
        created_count = 0
        skipped_count = 0
        
        # Создаем теги для типов голоса
        self.stdout.write('Создание тегов для типов голоса...')
        for voice_type in voice_types:
            slug = slugify(voice_type, allow_unicode=False)
            if not slug:  # Если slug пустой, используем транслитерацию
                # Простая транслитерация для основных случаев
                translit_map = {
                    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
                    '-': '-', ' ': '-'
                }
                slug = ''.join(translit_map.get(c.lower(), c.lower() if c.isalnum() else '-') for c in voice_type)
                slug = '-'.join(filter(None, slug.split('-')))
            
            tag, created = Tag.objects.get_or_create(
                slug=slug,
                defaults={'name': voice_type}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  [OK] Создан тег: {voice_type} (slug: {slug})'))
            else:
                # Обновляем имя и slug, если они изменились
                if tag.name != voice_type or tag.slug != slug:
                    tag.name = voice_type
                    tag.slug = slug
                    tag.save()
                    self.stdout.write(self.style.WARNING(f'  [UPD] Обновлен тег: {voice_type}'))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f'  [-] Тег уже существует: {voice_type}'))
        
        # Создаем теги для инструментов
        self.stdout.write('\nСоздание тегов для инструментов...')
        for instrument in instruments:
            slug = slugify(instrument, allow_unicode=False)
            if not slug:  # Если slug пустой, используем транслитерацию
                # Простая транслитерация для основных случаев
                translit_map = {
                    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
                    '-': '-', ' ': '-'
                }
                slug = ''.join(translit_map.get(c.lower(), c.lower() if c.isalnum() else '-') for c in instrument)
                slug = '-'.join(filter(None, slug.split('-')))
            
            tag, created = Tag.objects.get_or_create(
                slug=slug,
                defaults={'name': instrument}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  [OK] Создан тег: {instrument} (slug: {slug})'))
            else:
                # Обновляем имя и slug, если они изменились
                if tag.name != instrument or tag.slug != slug:
                    tag.name = instrument
                    tag.slug = slug
                    tag.save()
                    self.stdout.write(self.style.WARNING(f'  [UPD] Обновлен тег: {instrument}'))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f'  [-] Тег уже существует: {instrument}'))
        
        total_tags = Tag.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nГотово! Создано новых тегов: {created_count}, пропущено: {skipped_count}, всего тегов в БД: {total_tags}'
        ))

