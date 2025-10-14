from django import forms
from django.contrib.auth.forms import UserCreationForm

from user.models import MediaFile, Show

from .models import CustomUser


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("⚠️ This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = "User"
        if commit:
            user.save()
        return user


class AdminShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = [
            "name",
            "date",
            "time",
            "seat_price",
            "thumbnail",
            "include_balcony",
            "poster",
        ]
        widgets = {
            "time": forms.TimeInput(attrs={"type": "time"}),
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class MediaUploadForm(forms.ModelForm):
    class Meta:
        model = MediaFile
        fields = ["file", "description"]
        widgets = {
            "description": forms.TextInput(
                attrs={"placeholder": "e.g. Poster, Trailer, etc."}
            ),
        }
