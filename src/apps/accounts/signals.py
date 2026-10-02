from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, raw=False, **kwargs):
    # Raw saves come from fixture loading, which brings its own profiles.
    if created and not raw:
        Profile.objects.create(user=instance)
