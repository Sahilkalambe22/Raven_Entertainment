import re
from collections import defaultdict
from datetime import timedelta

import requests
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import json
from django.core.serializers.json import DjangoJSONEncoder

from accounts.forms import AdminShowForm, MediaUploadForm, SignUpForm
from accounts.models import CustomUser
from user.models import (Booking, MediaFile, QRMarketingScan, QRScanLog, Seat,
                         Show, Ticket)
from user.qr_utils import *

# ------------------ AUTH ------------------ #


def is_admin(user):
    return user.is_authenticated and user.user_type == "Admin"


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.generate_otp()
            user.save()

            from django.conf import settings
            from django.core.mail import send_mail

            send_mail(
                "🎭 Raven Entertainment - Verify Your Email",
                f"Your OTP is: {user.email_otp}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            messages.success(
                request,
                "✅ Account created! Please verify your email with the OTP sent.",
            )
            return redirect("verify_email_otp", user_id=user.id)
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            # ✅ Block login if email is not verified
            if not user.is_email_verified:
                messages.error(
                    request, "❌ Please verify your email before logging in."
                )
                return redirect("login")

            login(request, user)
            return redirect(
                "admin_dashboard" if user.user_type == "Admin" else "user_dashboard"
            )
        else:
            messages.error(request, "❌ Invalid login credentials.")

    else:
        form = AuthenticationForm()

    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


# ------------------ DASHBOARDS ------------------ #
@login_required
def admin_dashboard(request):
    if not request.user.is_authenticated or request.user.user_type != "Admin":
        return HttpResponseForbidden("⛔ Unauthorized")

    shows = Show.objects.all()
    bookings = Booking.objects.all().order_by("-created_at")

    total_revenue = sum(b.total_price for b in bookings if b.payment_status == "Paid")
    revenue_today = sum(
        b.total_price for b in bookings if b.created_at.date() == timezone.now().date()
    )
    revenue_month = sum(
        b.total_price for b in bookings if b.created_at.month == timezone.now().month
    )

    # Build paginated shows with seat data
    enriched_shows = []
    for show in shows:
        total = show.seat_set.count()
        booked = show.seat_set.filter(is_booked=True).count()
        remaining = total - booked

        enriched_shows.append(
            {
                "show": show,
                "total": total,
                "booked": booked,
                "remaining": remaining,
            }
        )

    paginator = Paginator(enriched_shows, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    today = timezone.now().date()

    return render(
        request,
        "accounts/admin_dashboard.html",
        {
            "page_obj": page_obj,  # This now contains enriched show data
            "bookings": bookings,
            "total_revenue": total_revenue,
            "revenue_today": revenue_today,
            "revenue_month": revenue_month,
            "total_bookings": bookings.count(),
            "today": today,
        },
    )


@login_required
def user_dashboard(request):
    if request.user.user_type != "User":
        return HttpResponseForbidden("You are not authorized.")

    bookings = Booking.objects.filter(user=request.user).order_by("-booking_date")

    filter_start_date = request.GET.get("start_date")
    filter_end_date = request.GET.get("end_date")
    filter_status = request.GET.get("status")

    if filter_start_date:
        bookings = bookings.filter(booking_date__date__gte=filter_start_date)
    if filter_end_date:
        bookings = bookings.filter(booking_date__date__lte=filter_end_date)
    if filter_status:
        bookings = bookings.filter(payment_status=filter_status)

    # ✅ Only show shows that are still upcoming — i.e., future datetime
    shows = Show.objects.filter(date__gt=timezone.now()).order_by("date")

    return render(
        request,
        "accounts/user_dashboard.html",
        {
            "user": request.user,
            "bookings": bookings,
            "shows": shows,
            "filter_start_date": filter_start_date,
            "filter_end_date": filter_end_date,
            "filter_status": filter_status,
        },
    )


# ------------------ FORMS ------------------ #


class AdminBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            "user",
            "event_name",
            "event_date",
            "number_of_tickets",
            "total_price",
            "payment_status",
            "upi_id",
        ]

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.all()
        self.fields["payment_status"].initial = "Paid"


# ------------------ ADMIN VIEWS ------------------ #


@user_passes_test(is_admin)
def handle_create_show(request):
    if request.method == "POST":
        form = AdminShowForm(request.POST, request.FILES)
        if form.is_valid():
            show = form.save()  # All seat and QR logic is handled inside Show.save()
            messages.success(request, "✅ Show created successfully.")
            return redirect("admin_dashboard")
        else:
            messages.error(request, "❌ Invalid form: " + str(form.errors))
    else:
        form = AdminShowForm()

    return render(request, "accounts/partials/create_show.html", {"form": form})


@login_required
def admin_show_media_dashboard(request, show_id):
    if request.user.user_type != "Admin":
        return redirect("user_dashboard")

    show = get_object_or_404(Show, id=show_id)
    media_form = MediaUploadForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and media_form.is_valid():
        media = media_form.save(commit=False)
        media.show = show
        media.save()
        return redirect("admin_show_media", show_id=show.id)

    bookings = Booking.objects.filter(event_name=show.name, event_date=show.date)
    media_files = show.media_files.all()

    return render(
        request,
        "accounts/admin_show_media.html",
        {
            "show": show,
            "form": media_form,
            "media_files": media_files,
            "bookings": bookings,
        },
    )


@login_required
def delete_media_file(request, media_id):
    if request.user.user_type != "Admin":
        return redirect("user_dashboard")

    media = get_object_or_404(MediaFile, id=media_id)
    media.show.id

    # Delete file from media storage (only if the file exists)
    if media.file and media.file.name:
        media.file.delete(save=False)

    # Delete DB entry
    media.delete()

    messages.success(request, "✅ Media file deleted successfully.")
    return redirect(
        "admin_dashboard"
    )  # or use: redirect('admin_show_media', show_id=show_id)


def is_admin(user):
    return user.is_authenticated and user.is_staff


# ✅ Sidebar content: Create Show (dynamic)
@user_passes_test(is_admin)
def admin_create_show(request):
    return render(request, "accounts/partials/create_show.html")


# ✅ Sidebar content: QR Analytics (dynamic)
@user_passes_test(is_admin)
def admin_qr_analytics_view(request):
    from django.db.models import Count, Q

    from user.models import Ticket

    raw_stats = Ticket.objects.values("show__name").annotate(
        total_booked=Count("id"), total_scanned=Count("id", filter=Q(is_scanned=True))
    )

    # Pre-calculate percentage in Python
    show_stats = []
    for row in raw_stats:
        booked = row["total_booked"]
        scanned = row["total_scanned"]
        percentage = (scanned / booked * 100) if booked > 0 else 0
        row["attendance_percentage"] = round(percentage, 2)
        show_stats.append(row)

    return render(
        request,
        "accounts/partials/qr_analytics_content.html",
        {
            "scan_data": show_stats,
            "scan_data_json": json.dumps(show_stats, cls=DjangoJSONEncoder),  # 👈 added
        },
    )


# ✅ Sidebar content: Default dashboard welcome screen (dynamic)
@user_passes_test(is_admin)
def admin_dashboard_content(request):
    return render(request, "accounts/partials/dashboard_home.html")


# ✅ Page route: Full admin dashboard page (with sidebar layout)
@user_passes_test(is_admin)
def admin_dashboard_main(request):
    return render(request, "accounts/admin_dashboard.html")


@user_passes_test(is_admin)
def admin_create_booking(request):
    users = CustomUser.objects.filter(user_type="User")
    shows = Show.objects.all().order_by("-date")

    return render(
        request,
        "accounts/partials/create_booking.html",
        {
            "users": users,
            "shows": shows,
        },
    )


@user_passes_test(is_admin)
def admin_view_users(request):
    users = CustomUser.objects.all()  # includes both user_type='User' and 'Admin'
    return render(request, "accounts/partials/view_users.html", {"users": users})


@user_passes_test(is_admin)
def admin_upload_media_panel(request):
    shows = Show.objects.all().order_by("-date")
    return render(request, "accounts/partials/upload_media.html", {"shows": shows})


@user_passes_test(is_admin)
def admin_view_bookings(request):
    shows = Show.objects.annotate(
        total_tickets=Sum("bookings__number_of_tickets"),
        total_price=Sum("bookings__total_price"),
    ).order_by("-date")

    return render(request, "accounts/partials/view_bookings.html", {"shows": shows})


@user_passes_test(is_admin)
def admin_all_shows(request):
    all_shows = Show.objects.prefetch_related("media_files").order_by("-date")
    enriched_shows = []
    timezone.now().date()

    for show in all_shows:
        # ✅ Explicit filtering for reliable seat counts
        total = Seat.objects.filter(show=show).count()
        booked = Seat.objects.filter(show=show, is_booked=True).count()
        remaining = total - booked
        media = show.media_files.all()

        enriched_shows.append(
            {
                "show": show,
                "total": total,
                "booked": booked,
                "remaining": remaining,
                "media": media,
            }
        )

    return render(
        request, "accounts/partials/all_shows.html", {"shows": enriched_shows}
    )


def qr_scan_log(request, show_id):
    ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
    district = "Unknown"

    try:
        geo = requests.get(f"http://ip-api.com/json/{ip}").json()
        district = geo.get("city") or geo.get("regionName") or "Unknown"
    except:
        pass

    QRScanLog.objects.create(show_id=show_id, district=district)
    return redirect("show_detail", slug=Show.objects.get(id=show_id).slug)


from django.contrib.auth.decorators import login_required, user_passes_test


@login_required
@user_passes_test(lambda u: u.user_type == "Admin")
def admin_scan_tickets(request, show_id):
    show = get_object_or_404(Show, id=show_id)
    message = ""
    ticket = None

    if request.method == "POST":
        raw_input = request.POST.get("ticket_id", "").strip()
        match = re.search(r"/qr/(\d+)/?$", raw_input)
        ticket_id = match.group(1) if match else raw_input

        try:
            ticket = Ticket.objects.get(id=ticket_id, show=show)
            if ticket.is_scanned:
                message = "⚠️ Ticket already scanned!"
            else:
                ticket.is_scanned = True
                ticket.save()

                # Save basic scan log
                QRScanLog.objects.create(
                    ticket=ticket,
                    show=show,
                    ip_address=request.META.get("REMOTE_ADDR", ""),
                    city="N/A",
                    region="N/A",
                    district="N/A",
                    postal_code="000000",
                    scanned_at=timezone.now(),
                )
                message = "✅ Ticket scanned successfully!"
        except Ticket.DoesNotExist:
            message = "❌ Invalid ticket!"

    return render(
        request,
        "accounts/scan_tickets.html",
        {"show": show, "ticket": ticket, "message": message},
    )


def resend_email_otp(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    # Check if last OTP was generated within 60 seconds
    if user.last_otp_sent and timezone.now() - user.last_otp_sent < timedelta(
        seconds=60
    ):
        messages.error(request, "⏱️ Please wait 1 minute before requesting another OTP.")
        return redirect("verify_email_otp", user_id=user.id)

    # Generate new OTP and send
    user.generate_otp()
    user.last_otp_sent = timezone.now()
    user.save()

    send_mail(
        "🔁 Raven OTP Resend",
        f"Your new OTP is: {user.email_otp}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

    messages.success(request, "🔁 New OTP sent to your email.")
    return redirect("verify_email_otp", user_id=user.id)


# Update verify_email_otp with OTP expiry check


def verify_email_otp(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        # Check if OTP expired
        if user.last_otp_sent and timezone.now() - user.last_otp_sent > timedelta(
            minutes=10
        ):
            messages.error(request, "⏳ OTP has expired. Please request a new one.")
            return redirect("verify_email_otp", user_id=user.id)

        if entered_otp == user.email_otp:
            user.is_email_verified = True
            user.save()
            messages.success(request, "✅ Email verified successfully.")
            login(request, user)
            return redirect(
                "admin_dashboard" if user.user_type == "Admin" else "user_dashboard"
            )
        else:
            messages.error(request, "❌ Invalid OTP. Please try again.")

    return render(request, "accounts/verify_email_otp.html", {"user": user})


def forgot_password_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = CustomUser.objects.filter(email=email).first()
        if user:
            user.generate_otp()
            from django.conf import settings
            from django.core.mail import send_mail

            send_mail(
                "🔐 Raven Entertainment Password Reset OTP",
                f"Your password reset OTP is: {user.email_otp}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            messages.success(request, "✅ OTP sent to your email.")
            return redirect("reset_password_otp", user_id=user.id)
        else:
            messages.error(request, "❌ Email not found.")
    return render(request, "accounts/forgot_password.html")


def reset_password_otp(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == "POST":
        otp = request.POST.get("otp")
        new_password = request.POST.get("new_password")
        if otp == user.email_otp:
            user.password = make_password(new_password)
            user.email_otp = ""  # Clear OTP
            user.save()
            messages.success(
                request, "✅ Password reset successfully. You can now log in."
            )
            return redirect("login")
        else:
            messages.error(request, "❌ Invalid OTP.")
    return render(request, "accounts/reset_password_otp.html", {"user": user})


@user_passes_test(is_admin)
@transaction.atomic
def admin_manual_booking(request, show_id):
    show = get_object_or_404(Show, id=show_id)

    available_seats = Seat.objects.filter(show=show, is_booked=False)
    ground_rows = defaultdict(list)
    balcony_rows = defaultdict(list)

    for seat in available_seats:
        row_label = "".join(filter(str.isalpha, seat.seat_number))
        if len(row_label) >= 2 and row_label.startswith("B"):
            balcony_rows[row_label].append(seat)
        else:
            ground_rows[row_label].append(seat)

    for row_dict in [ground_rows, balcony_rows]:
        for row, seats in row_dict.items():
            row_dict[row] = sorted(
                seats, key=lambda s: int("".join(filter(str.isdigit, s.seat_number)))
            )

    if request.method == "POST":
        buyer_name = request.POST.get("offline_name")
        email_id = request.POST.get("offline_email")
        selected_ids = request.POST.getlist("selected_seats")

        if not buyer_name or not email_id or not selected_ids:
            messages.error(request, "❌ All fields are required.")
            return redirect("admin_manual_booking", show_id=show.id)

        try:
            selected_seats = Seat.objects.select_for_update().filter(
                id__in=selected_ids, show=show
            )
            if selected_seats.count() != len(selected_ids):
                messages.error(
                    request,
                    "⚠️ One or more selected seats are already booked or invalid.",
                )
                return redirect("admin_manual_booking", show_id=show.id)

            tickets = []
            for seat in selected_seats:
                seat.is_booked = True
                seat.save()

                ticket = Ticket.objects.create(
                    show=show,
                    seat_number=seat.seat_number,
                    payment_status="confirmed",
                    user=request.user,  # 👈 fallback admin user (required for FK)
                )
                generate_ticket_qr(ticket, request)
                tickets.append(ticket)

            def send_manual_ticket_email():
                pdf_buffer = generate_ticket_pdf(
                    tickets, request, buyer_name=buyer_name
                )
                send_ticket_email(email_id, pdf_buffer)

            threading.Thread(target=send_manual_ticket_email).start()

            messages.success(
                request, f"✅ {len(tickets)} ticket(s) booked and sent to {email_id}"
            )
            return redirect("admin_manual_booking", show_id=show.id)

        except Exception as e:
            messages.error(request, f"❌ Booking failed: {str(e)}")
            return redirect("admin_manual_booking", show_id=show.id)

    return render(
        request,
        "accounts/manual_booking.html",
        {
            "show": show,
            "ground_rows": dict(ground_rows),
            "balcony_rows": dict(balcony_rows),
        },
    )


def qr_marketing_scan(request):
    identifier = request.GET.get(
        "qr", "unknown"
    )  # 👈 captures ?qr=banner or ?qr=ticket
    ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

    city = region = district = postal = None
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/").json()
        city = response.get("city")
        region = response.get("region")
        district = response.get("district")
        postal = response.get("postal")
    except Exception as e:
        print(f"Geo lookup failed: {e}")

    user_agent = request.META.get("HTTP_USER_AGENT", "")

    QRMarketingScan.objects.create(
        identifier=identifier,
        ip_address=ip,
        city=city,
        region=region,
        district=district,
        postal=postal,
        user_agent=user_agent,
    )

    return redirect("https://www.instagram.com/raven.entertainment")


def admin_marketing_qr_analytics(request):
    return render(request, "accounts/partials/qr_campaign_analytics.html")


def get_qr_marketing_data(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    city = request.GET.get("city")

    scans = QRMarketingScan.objects.all()

    if start_date:
        scans = scans.filter(timestamp__date__gte=start_date)
    if end_date:
        scans = scans.filter(timestamp__date__lte=end_date)
    if city:
        scans = scans.filter(city__iexact=city)

    counts = scans.values("identifier").annotate(count=Count("id"))
    return JsonResponse(list(counts), safe=False)
