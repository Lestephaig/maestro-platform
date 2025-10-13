from django.db import models
from accounts.models import User

class PerformerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='performer_profile')
    full_name = models.CharField(max_length=200)
    voice_type = models.CharField(max_length=100, blank=True)
    repertoire = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    photo_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Performer: {self.full_name}"