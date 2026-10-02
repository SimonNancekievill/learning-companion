from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]

    def get_inline_instances(self, request, obj=None):
        # The post_save signal creates the profile, so it is only edited once the user exists.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)
