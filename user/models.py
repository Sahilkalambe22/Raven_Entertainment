from datetime import date
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", blank=True, null=True
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Post(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Show(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    date = models.DateField()
    time = models.TimeField()
    poster = models.ImageField(upload_to="show_posters/", null=True, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, null=True)
    total_seats = models.IntegerField(default=0)
    seat_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    include_balcony = models.BooleanField(default=True)  # ✅ New field
    qr_code = models.ImageField(upload_to="qrcodes/", blank=True, null=True)

    def save(self, *args, **kwargs):
        from .models import Seat  # Make sure Seat is defined below this class

        # ✅ 1. Generate unique slug
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Show.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # ✅ 2. Save to generate Show ID
        super().save(*args, **kwargs)

        # ✅ 3. Generate QR code
        qr = qrcode.make(f"http://127.0.0.1:8000/qr/scan/{self.id}/")
        buffer = BytesIO()
        qr.save(buffer)
        self.qr_code.save(
            f"{self.slug}_qr.png", ContentFile(buffer.getvalue()), save=False
        )
        super().save(update_fields=["qr_code"])

        # ✅ 4. Auto-generate Bharat Natya Mandir seat layout (only once)
        if not Seat.objects.filter(show=self).exists():
            # Ground Floor: A to T, 26 seats per row
            ground_rows = [chr(i) for i in range(ord("A"), ord("T") + 1)]
            for row in ground_rows:
                for num in range(1, 27):
                    seat_number = f"{row}{num}"
                    is_booked = row in ["A", "B"]  # ✅ A and B rows booked by default
                    Seat.objects.create(
                        show=self, seat_number=seat_number, is_booked=is_booked
                    )

            # Balcony: BA to BO, 22 seats per row (conditionally included)
            if self.include_balcony:
                balcony_rows = [f"B{chr(i)}" for i in range(ord("A"), ord("O") + 1)]
                for row in balcony_rows:
                    for num in range(1, 23):
                        seat_number = f"{row}{num}"
                        Seat.objects.create(
                            show=self, seat_number=seat_number, is_booked=False
                        )

    def __str__(self):
        return self.name


class Seat(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"Seat {self.seat_number} for {self.show.name}"


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    event_name = models.CharField(max_length=200, default="Default Event Name")
    booking_date = models.DateTimeField(auto_now_add=True)
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="bookings")
    event_date = models.DateField(default=date(2025, 1, 1))
    number_of_tickets = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(
        max_length=50,
        choices=[("Pending", "Pending"), ("Paid", "Paid")],
        default="Pending",
    )
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    transaction_screenshot = models.ImageField(
        upload_to="transaction_screenshots/", blank=True, null=True
    )
    upi_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ticket = models.ForeignKey(
        "Ticket", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.event_name} - {self.payment_status}"


class MediaFile(models.Model):
    show = models.ForeignKey(
        "Show", related_name="media_files", on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="show_media/")
    description = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.show.name} - {self.description or self.file.name}"


class Ticket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    show = models.ForeignKey("Show", on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=10)
    booking_date = models.DateTimeField(auto_now_add=True)
    is_scanned = models.BooleanField(default=False)
    qr_code = models.ImageField(upload_to="tickets/qrcodes/", blank=True, null=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("confirmed", "Confirmed")],
        default="confirmed",
    )

    def __str__(self):
        return f"Ticket #{self.id} for {self.user} - Seat {self.seat_number}"


class QRScanLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="qrscanlog")
    ip_address = models.GenericIPAddressField()
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100)  # ✅ Only one district field kept
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.city}, {self.district} @ {self.timestamp}"


class VisitorLog(models.Model):
    ip_address = models.GenericIPAddressField()
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.district} @ {self.timestamp}"


class QRMarketingScan(models.Model):
    identifier = models.CharField(max_length=100)  # e.g., "banner", "ticket", "poster"
    ip_address = models.GenericIPAddressField()
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.identifier} - {self.district} @ {self.timestamp}"
