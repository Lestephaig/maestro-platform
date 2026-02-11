from django.db import models
from accounts.models import User

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField('Наименование площадки', max_length=200)
    address = models.CharField('Адрес площадки', max_length=255, blank=True)
    venue_type = models.CharField('Тип площадки', max_length=120, blank=True)
    hall_capacity = models.PositiveIntegerField('Вместимость зала', null=True, blank=True)
    has_stage = models.BooleanField('Наличие сцены', default=False)
    contact_person = models.CharField('Контактное лицо', max_length=200, blank=True)
    website = models.URLField('Сайт', blank=True)

    stage_size = models.CharField('Размер сцены (Ш×Г×В)', max_length=120, blank=True)
    microphones_count = models.PositiveIntegerField('Микрофоны (кол-во)', null=True, blank=True)
    sound_system = models.CharField('Акустическая система', max_length=200, blank=True)
    mixing_console = models.CharField('Микшерный пульт', max_length=200, blank=True)
    lighting_equipment = models.CharField('Световое оборудование', max_length=200, blank=True)
    video_equipment = models.CharField('Видеооборудование / экраны', max_length=200, blank=True)
    has_internet = models.BooleanField('Интернет', default=False)
    power_supply = models.CharField('Электропитание 220В / 380В', max_length=120, blank=True)
    has_green_rooms = models.BooleanField('Гримерные комнаты', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Client: {self.company_name}"
