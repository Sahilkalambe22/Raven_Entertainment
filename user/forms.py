from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import *

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=200, help_text="Required")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class BookingForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    selected_seats = forms.ModelMultipleChoiceField(
        queryset=Seat.objects.none(), widget=forms.CheckboxSelectMultiple
    )

    def _init_(self, *args, **kwargs):
        show = kwargs.pop("show")
        super()._init_(*args, **kwargs)
        self.fields["selected_seats"].queryset = show.seat_set.filter(is_booked=False)

    def clean_selected_seats(self):
        selected_seats = self.cleaned_data["selected_seats"]
        if not selected_seats:
            raise forms.ValidationError("You must select at least one seat.")
        return selected_seats


class ShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = [
            "name",
            "date",
            "seat_price",
            "description",
        ]  # adjust fields as needed


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["phone_number", "address"]
        widgets = {
            "address": forms.TextInput(attrs={"placeholder": "District or Area"}),
        }


# ✅ NEW: Email Update Form
class EmailUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email"]
