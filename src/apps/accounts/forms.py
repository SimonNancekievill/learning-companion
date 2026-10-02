from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Profile, User


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User


class ProfileForm(forms.ModelForm):
    focus_areas = forms.CharField(
        required=False, help_text="Comma-separated, for example: Django, SQL"
    )

    class Meta:
        model = Profile
        fields = ["name", "cohort", "focus_areas"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["focus_areas"] = ", ".join(self.instance.focus_areas or [])

    def clean_focus_areas(self):
        # Trimming, de-duplication and limits are the model's job (Profile.clean).
        pieces = self.cleaned_data["focus_areas"].split(",")
        return [piece for piece in pieces if piece.strip()]
