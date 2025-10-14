from django import forms
from django.contrib import admin

from .models import Show, UserProfile

# Register UserProfile model
admin.site.register(UserProfile)


# ✅ Custom form for Show model including 'include_balcony'
class AdminShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = [
            "name",
            "slug",
            "description",
            "date",
            "time",
            "seat_price",
            "total_seats",
            "thumbnail",
            "include_balcony",  # ✅ Now visible in admin form
        ]


# ✅ Register Show with custom admin settings
@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    form = AdminShowForm
    list_display = (
        "name",
        "date",
        "time",
        "seat_price",
        "total_seats",
        "include_balcony",  # ✅ Show in the admin list
    )
    prepopulated_fields = {"slug": ("name",)}
