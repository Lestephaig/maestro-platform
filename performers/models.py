from django.db import models
from accounts.models import User

class PerformerProfile(models.Model):
    CALENDAR_MODE_CHOICES = [
        ('mark_available', 'Отмечать доступные даты'),
        ('mark_unavailable', 'Отмечать занятые даты'),
    ]

    PERFORMER_TYPE_VOCALIST = 'vocalist'
    PERFORMER_TYPE_INSTRUMENTALIST = 'instrumentalist'
    PERFORMER_TYPE_CHOICES = [
        (PERFORMER_TYPE_VOCALIST, 'Вокалист'),
        (PERFORMER_TYPE_INSTRUMENTALIST, 'Инструменталист'),
    ]

    DEFAULT_VOICE_TYPES = [
        'Сопрано',
        'Меццо-сопрано',
        'Контральто',
        'Тенор',
        'Баритон',
        'Бас',
        'Контртенор',
        'Альт',
    ]

    DEFAULT_INSTRUMENTS = [
        'Скрипка',
        'Альт',
        'Виолончель',
        'Контрабас',
        'Флейта',
        'Гобой',
        'Кларнет',
        'Фагот',
        'Саксофон',
        'Труба',
        'Тромбон',
        'Валторна',
        'Туба',
        'Фортепиано',
        'Орган',
        'Арфа',
        'Гитара',
        'Ударные',
        'Барабаны',
        'Аккордеон',
        'Домра',
        'Балалайка',
        'Баян',
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='performer_profile')
    full_name = models.CharField(max_length=200)
    performer_type = models.CharField(
        max_length=20,
        choices=PERFORMER_TYPE_CHOICES,
        default=PERFORMER_TYPE_VOCALIST,
        help_text='Основная специализация исполнителя'
    )
    voice_type = models.CharField(max_length=100, blank=True)
    instrument = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    education = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    repertoire = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    photo = models.ImageField(upload_to='performers/photos/', blank=True, null=True)
    calendar_mode = models.CharField(
        max_length=20, 
        choices=CALENDAR_MODE_CHOICES, 
        default='mark_unavailable',
        help_text='Режим заполнения календаря'
    )
    is_verified = models.BooleanField(
        default=False,
        help_text='Верифицирован ли профиль артиста'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Обнуляем несоответствующие специализации поля
        if self.performer_type == self.PERFORMER_TYPE_VOCALIST:
            self.instrument = ''
        elif self.performer_type == self.PERFORMER_TYPE_INSTRUMENTALIST:
            self.voice_type = ''

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        if self.user and self.user.is_verified != self.is_verified:
            self.user.is_verified = self.is_verified
            self.user.save(update_fields=['is_verified'])

    @property
    def specialization_display(self):
        if self.performer_type == self.PERFORMER_TYPE_INSTRUMENTALIST and self.instrument:
            return self.instrument
        if self.performer_type == self.PERFORMER_TYPE_VOCALIST and self.voice_type:
            return self.voice_type
        return ''

    def __str__(self):
        specialization = self.specialization_display
        if specialization:
            return f"{self.full_name} ({specialization})"
        return f"Performer: {self.full_name}"


class PerformerAvailability(models.Model):
    STATUS_CHOICES = [
        ('available', 'Доступен'),
        ('unavailable', 'Занят'),
        ('maybe', 'Готов подумать'),
    ]
    
    performer = models.ForeignKey(PerformerProfile, on_delete=models.CASCADE, related_name='availabilities')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True, help_text='Дополнительные заметки')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['performer', 'date']
        ordering = ['date']
    
    def __str__(self):
        return f"{self.performer.full_name} - {self.date} - {self.get_status_display()}"


class PerformerPhoto(models.Model):
    performer = models.ForeignKey(PerformerProfile, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='performers/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"{self.performer.full_name} - Photo {self.id}"


class PerformerVideo(models.Model):
    performer = models.ForeignKey(PerformerProfile, on_delete=models.CASCADE, related_name='videos')
    video_url = models.URLField()
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"{self.performer.full_name} - {self.title or 'Video'}"


class RepertoireItem(models.Model):
    """Отдельное произведение в репертуаре артиста"""
    
    CATEGORY_CHOICES = [
        ('opera', 'Опера'),
        ('operetta', 'Оперетта'),
        ('aria', 'Ария'),
        ('romance', 'Романс'),
        ('song', 'Песня'),
        ('chamber', 'Камерная музыка'),
        ('oratorio', 'Оратория'),
        ('cantata', 'Кантата'),
        ('mass', 'Месса/Реквием'),
        ('lieder', 'Lied'),
        ('other', 'Другое'),
    ]
    
    EPOCH_CHOICES = [
        ('renaissance', 'Ренессанс'),
        ('baroque', 'Барокко'),
        ('classical', 'Классицизм'),
        ('romantic', 'Романтизм'),
        ('modern', 'XX век'),
        ('contemporary', 'XXI век'),
        ('folk', 'Народная музыка'),
    ]
    
    performer = models.ForeignKey(PerformerProfile, on_delete=models.CASCADE, related_name='repertoire_items')
    composer = models.CharField(max_length=200, help_text='Композитор (например: Моцарт В.А., Верди Дж.)')
    work_title = models.CharField(max_length=300, help_text='Название произведения')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    epoch = models.CharField(max_length=50, choices=EPOCH_CHOICES, blank=True)
    role_or_part = models.CharField(max_length=200, blank=True, help_text='Роль, партия или часть произведения')
    year_performed = models.IntegerField(blank=True, null=True, help_text='Год исполнения (опционально)')
    notes = models.TextField(blank=True, help_text='Дополнительные заметки')
    video_link = models.URLField(blank=True, help_text='Ссылка на YouTube или другой видеосервис')
    is_featured = models.BooleanField(default=False, help_text='Выделить как избранное')
    order = models.IntegerField(default=0, help_text='Порядок отображения')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', 'order', 'composer', 'work_title']
        indexes = [
            models.Index(fields=['composer']),
            models.Index(fields=['work_title']),
        ]
    
    def __str__(self):
        role_part = f" ({self.role_or_part})" if self.role_or_part else ""
        return f"{self.composer} - {self.work_title}{role_part}"