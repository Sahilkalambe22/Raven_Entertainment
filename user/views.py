import json
import os
from collections import defaultdict
from datetime import date

import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Count
from django.http import (FileResponse, Http404, HttpResponseForbidden,
                         JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.forms import MediaUploadForm
from accounts.models import CustomUser
from user.models import VisitorLog

from .forms import EmailUpdateForm, SignUpForm, UserProfileForm
from .location_utils import get_location_from_ip
from .models import *
from .models import QRScanLog, Show, Ticket
from .qr_utils import generate_ticket_pdf, generate_ticket_qr

# ------------------ Static Pages ------------------ #


def home(request):
    today = date.today()
    shows = Show.objects.filter(date__gte=today).order_by("date")

    # 🌐 Capture IP & Location
    ip = request.META.get("REMOTE_ADDR", "")
    try:
        geo = requests.get(f"http://ip-api.com/json/{ip}").json()
        district = geo.get("city") or geo.get("regionName") or "Unknown"
        VisitorLog.objects.create(ip_address=ip, district=district)
    except:
        pass

    portfolio_items = [
        {
            "image": static(f"assets/img/masonry-portfolio/masonry-portfolio-{i}.jpg"),
            "title": f"Title {i}",
            "description": "Lorem ipsum, dolor sit",
            "filter": f'filter-{["product", "branding", "app"][i % 3]}',
        }
        for i in range(2, 10)
    ]

    return render(
        request,
        "home.html",
        {"shows": shows, "today": today, "portfolio_items": portfolio_items},
    )


def jjv(request):
    return render(request, "jjv.html")


def a1k(request):
    return render(request, "a1k.html")


def payments_page(request):
    return render(request, "payments.html")


# ------------------ Auth Views ------------------ #


def signup_view(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(
            request,
            authenticate(
                username=user.username, password=form.cleaned_data["password1"]
            ),
        )
        return redirect("login")
    return render(request, "signup.html", {"form": form})


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("profile")
    return render(request, "login.html", {"form": form})


# ------------------ Profile & Booking ------------------ #


@never_cache
@login_required
def create_booking(request, show_id):
    show = get_object_or_404(Show, id=show_id)
    if show.date < timezone.now().date():
        return HttpResponseForbidden("❌ Booking for past shows is not allowed.")

    available_seats = Seat.objects.filter(show=show)
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

    recommended_seats = []
    if request.method != "POST":
        stall_rows = [chr(i) for i in range(ord("C"), ord("T") + 1)]
        for row in stall_rows:
            seats = ground_rows.get(row, [])
            center_start = 10
            for offset in range(13):
                left = center_start - offset
                right = center_start + offset
                if any(
                    s.seat_number == f"{row}{left}" and not s.is_booked for s in seats
                ):
                    recommended_seats.append(
                        next(s for s in seats if s.seat_number == f"{row}{left}")
                    )
                if any(
                    s.seat_number == f"{row}{right}" and not s.is_booked for s in seats
                ):
                    recommended_seats.append(
                        next(s for s in seats if s.seat_number == f"{row}{right}")
                    )
                if len(recommended_seats) >= 5:
                    break
            if len(recommended_seats) >= 5:
                break

    if request.method == "POST":
        selected_seat_ids = request.POST.get("selected_seats", "").split(",")
        selected_seat_ids = [sid for sid in selected_seat_ids if sid.strip().isdigit()]
        if selected_seat_ids:
            with transaction.atomic():
                seats_to_book = Seat.objects.select_for_update().filter(
                    id__in=selected_seat_ids, show=show
                )
                if seats_to_book.count() != len(selected_seat_ids) or any(
                    seat.is_booked for seat in seats_to_book
                ):
                    messages.error(
                        request,
                        "⚠️ One or more selected seats are already booked. Please try again.",
                    )
                    return redirect("book_ticket", show_id=show.id)

                Seat.objects.filter(id__in=selected_seat_ids).update(is_booked=True)
                total_price = len(selected_seat_ids) * show.seat_price
                booking = Booking.objects.create(
                    user=request.user,
                    show=show,
                    event_name=show.name,
                    event_date=show.date,
                    number_of_tickets=len(selected_seat_ids),
                    total_price=total_price,
                    payment_status="Confirmed",
                )

                ticket_list = []
                for seat in seats_to_book:
                    ticket = Ticket.objects.create(
                        user=request.user,
                        show=show,
                        seat_number=seat.seat_number,
                        payment_status="confirmed",
                    )
                    generate_ticket_qr(ticket, request)
                    ticket_list.append(ticket)

                # ✅ Link first ticket to the booking for download visibility
                if ticket_list:
                    booking.ticket = ticket_list[0]
                    booking.save()

                # ✅ Generate and email the combined ticket PDF
                pdf_buffer = generate_ticket_pdf(ticket_list, request)
                email = EmailMessage(
                    subject="🎫 Raven Entertainment Ticket Confirmation",
                    body="Attached is your ticket PDF. Thank You for Booking 🎭",
                    to=[request.user.email],
                )
                email.attach("tickets.pdf", pdf_buffer.getvalue(), "application/pdf")
                email.send()

                return redirect("payments", booking_id=booking.id)

    return render(
        request,
        "user/create_booking.html",
        {
            "available_seats": available_seats,
            "ground_rows": dict(ground_rows),
            "balcony_rows": dict(balcony_rows),
            "recommended_seats": recommended_seats,
            "show": show,
        },
    )


@login_required
def payment_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "payments.html", {"booking": booking})


@login_required
def payment_gateway(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if request.method == "POST":
        upi_id = request.POST.get("upi_id")
        amount = booking.total_price

        if upi_id:
            # Optional: Save UPI ID and update status if needed
            booking.upi_id = upi_id
            booking.payment_status = "Initiated"
            booking.save()

            # Create UPI intent URL
            upi_url = (
                f"upi://pay?pa={upi_id}"
                f"&pn=Raven Entertainment"
                f"&am={amount}"
                f"&cu=INR"
            )

            return redirect(upi_url)  # Redirects to the UPI app (on mobile)

    return render(request, "payments.html", {"booking": booking})


# ------------------ API Endpoints ------------------ #


@csrf_exempt
def book_seats(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            Seat.objects.filter(id__in=data.get("seats", [])).update(is_booked=True)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False})


@csrf_exempt
def process_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            if not data.get("upi_id"):
                return JsonResponse({"success": False, "message": "UPI ID missing"})

            booking = Booking.objects.create(
                user=request.user,
                event_name=data.get("event_name", "Default Show"),
                number_of_tickets=int(data.get("number_of_tickets", 1)),
                total_price=float(
                    data.get(
                        "total_price",
                    )
                ),
                payment_status="Paid",
                upi_id=data["upi_id"],
            )
            return JsonResponse({"success": True, "booking_id": booking.id})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})
    return JsonResponse({"success": False, "message": "Invalid request"})


def show_detail_view(request, slug):
    show = get_object_or_404(Show, slug=slug)
    return render(request, "user/show_detail.html", {"show": show})


def home_view(request):
    today = date.today()
    shows = Show.objects.filter(date__gte=today).order_by("date")
    ongoing_shows = shows.filter(date__gte=today)
    past_shows = shows.filter(date__lt=today)

    context = {
        "shows": shows,
        "ongoing_shows": ongoing_shows,
        "past_shows": past_shows,
        "today": today,
    }
    return render(request, "home.html", context)


@login_required
def edit_booking(request, booking_id):
    if request.user.user_type != "Admin":
        return HttpResponseForbidden("You are not authorized to access this page.")

    booking = get_object_or_404(Booking, id=booking_id)
    all_related_seats = Seat.objects.filter(show=booking.show, booking=booking)

    if request.method == "POST":
        selected_ids = request.POST.getlist("cancel_seats")
        # Set selected seats to booked=True, others to False
        for seat in all_related_seats:
            seat.is_booked = str(seat.id) in selected_ids
            seat.save()

        booking.number_of_tickets = all_related_seats.filter(is_booked=True).count()
        booking.total_price = booking.number_of_tickets * booking.show.seat_price
        booking.save()

        messages.success(request, "Seats updated successfully.")
        return redirect("admin_dashboard")

    return render(
        request,
        "edit_booking.html",
        {
            "booking": booking,
            "seats": all_related_seats,
        },
    )


@login_required
def admin_user_list(request):
    if request.user.user_type != "Admin":
        return HttpResponseForbidden("You are not authorized.")

    users = CustomUser.objects.exclude(id=request.user.id)

    if request.method == "POST":
        for user in users:
            role = request.POST.get(f"user_type_{user.id}")
            if role in ["User", "Admin"]:
                user.user_type = role
                user.save()
        return redirect("admin_user_list")

    return render(request, "user/admin_manage_users.html", {"users": users})


@require_POST
@login_required
def upload_media(request, show_id):
    show = get_object_or_404(Show, id=show_id)

    if request.method == "POST":
        form = MediaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.show = show
            media.save()
            return redirect(
                "admin_dashboard"
            )  # or wherever you want to go after uploading
        else:
            print(form.errors)  # optional: for debugging in terminal
    return redirect("admin_dashboard")


def verify_qr_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    already_scanned = ticket.is_scanned

    if not already_scanned:
        ticket.is_scanned = True
        ticket.save()

    # Get IP address and location
    ip = request.META.get("REMOTE_ADDR", "")
    location = get_location_from_ip(ip)

    QRScanLog.objects.create(
        ticket=ticket,
        show=ticket.show,
        ip_address=ip,
        city=location["city"],
        region=location["region"],
        district=location["district"],
        postal_code=location["postal"],
    )

    context = {
        "ticket": ticket,
        "already_scanned": already_scanned,
        "valid": True,
    }
    return render(request, "user/qr_validated.html", context)


@user_passes_test(lambda u: u.is_authenticated and u.user_type == "Admin")
def get_visitor_data(request):
    data = (
        VisitorLog.objects.values("district")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return JsonResponse(list(data), safe=False)


@user_passes_test(lambda u: u.is_authenticated and u.user_type == "Admin")
def admin_visitor_analytics(request):
    return render(request, "accounts/partials/visitor_analytics.html")


def download_ticket(request, ticket_id):
    # Step 1: Get the ticket and its related booking
    ticket = Ticket.objects.filter(id=ticket_id, user=request.user).first()
    if not ticket:
        raise Http404("Ticket not found.")

    # Step 2: Find matching booking (to fetch all related tickets)
    booking = (
        Booking.objects.filter(user=request.user, show=ticket.show)
        .order_by("-booking_date")
        .first()
    )
    if not booking:
        raise Http404("Booking not found.")

    # Step 3: Get all tickets for that user + show + date
    all_tickets = Ticket.objects.filter(
        user=request.user,
        show=ticket.show,
        booking_date__date=booking.booking_date.date(),
    )

    if not all_tickets.exists():
        raise Http404("No matching tickets found.")

    # Step 4: Generate PDF if missing
    pdf_path = f"media/tickets/{request.user.id}_{booking.id}_all.pdf"
    if not os.path.exists(pdf_path):
        pdf_buffer = generate_ticket_pdf(list(all_tickets), request)
        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.getvalue())

    return FileResponse(open(pdf_path, "rb"), content_type="application/pdf")


@login_required
def profile_settings(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        p_form = UserProfileForm(request.POST, instance=profile)
        e_form = EmailUpdateForm(request.POST, instance=user)
        pass_form = PasswordChangeForm(user, request.POST)

        has_changes = False

        if p_form.is_valid():
            if p_form.has_changed():
                p_form.save()
                messages.success(request, "📞 Phone and address updated.")
                has_changes = True

        if e_form.is_valid():
            if e_form.has_changed():
                e_form.save()
                messages.success(request, "📧 Email updated.")
                has_changes = True

        password_fields = ["old_password", "new_password1", "new_password2"]
        if any(request.POST.get(f) for f in password_fields):
            if pass_form.is_valid():
                pass_form.save()
                update_session_auth_hash(request, pass_form.user)
                messages.success(request, "🔒 Password changed successfully.")
                has_changes = True
            else:
                messages.error(
                    request, "❌ Password update failed. Please check the fields."
                )

        if has_changes:
            return redirect("user_dashboard")
        else:
            messages.info(request, "ℹ️ No changes detected.")

    else:
        p_form = UserProfileForm(instance=profile)
        e_form = EmailUpdateForm(instance=user)
        pass_form = PasswordChangeForm(user)

    return render(
        request,
        "user/profile_settings.html",
        {"p_form": p_form, "e_form": e_form, "pass_form": pass_form},
    )
