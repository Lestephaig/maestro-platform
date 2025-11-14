from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('performer', 'Исполнитель'),
        ('client', 'Площадка'),
        ('agent', 'Организатор'),
    ]

    email = models.EmailField(unique=True, blank=False, null=False)
    is_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField('Email подтвержден', default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='performer')

    def __str__(self):
        return self.username