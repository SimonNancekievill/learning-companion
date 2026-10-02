from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    pass


MAX_FOCUS_AREAS = 10
MAX_FOCUS_AREA_LENGTH = 30


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    name = models.CharField(max_length=100, blank=True)
    cohort = models.CharField(max_length=50, blank=True)
    focus_areas = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.user.get_username()}'s profile"

    def clean(self):
        # A cleared form field submits None; the field allows blank, so treat it as no tags.
        tags = [] if self.focus_areas is None else self.focus_areas
        if not isinstance(tags, list):
            raise ValidationError({"focus_areas": "Focus areas must be a list of tags."})
        if any(not isinstance(tag, str) or not tag.strip() for tag in tags):
            raise ValidationError({"focus_areas": "Each focus area must be a non-empty text tag."})
        normalised, seen = [], set()
        for tag in (tag.strip() for tag in tags):
            if tag.casefold() not in seen:
                seen.add(tag.casefold())
                normalised.append(tag)
        if len(normalised) > MAX_FOCUS_AREAS:
            raise ValidationError({"focus_areas": f"Use at most {MAX_FOCUS_AREAS} focus areas."})
        if any(len(tag) > MAX_FOCUS_AREA_LENGTH for tag in normalised):
            raise ValidationError(
                {"focus_areas": f"Focus areas can be at most {MAX_FOCUS_AREA_LENGTH} characters."}
            )
        self.focus_areas = normalised
