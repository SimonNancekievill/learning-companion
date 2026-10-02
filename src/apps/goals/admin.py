from django.contrib import admin

from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["title", "owner__username"]
