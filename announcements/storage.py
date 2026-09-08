import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateAnnouncementStorage(FileSystemStorage):
    """Storage outside MEDIA_ROOT, accessible only through authorized views."""

    @property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None


private_announcement_storage = PrivateAnnouncementStorage()
