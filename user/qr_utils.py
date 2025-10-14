import io
import os
import threading

import qrcode
from django.conf import settings
from django.core.files import File
from django.core.mail import EmailMessage
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Register DejaVu font for ₹ and Unicode support
font_path = os.path.join(settings.BASE_DIR, "static/assets/fonts/DejaVuSans.ttf")
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont("DejaVu", font_path))


def generate_ticket_qr(ticket, request):
    domain = request.get_host()
    scheme = "https" if not settings.DEBUG else "http"
    ticket_url = f"{scheme}://{domain}/qr/{ticket.id}/"

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(ticket_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    logo_path = os.path.join(settings.BASE_DIR, "static/assets/img/RAVEN laser.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((30, 30), Image.LANCZOS)  # smaller logo improves QR visibility
        pos = (
            (qr_img.size[0] - logo.size[0]) // 2,
            (qr_img.size[1] - logo.size[1]) // 2,
        )
        qr_img.paste(logo, pos, mask=logo)

    qr_io = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_file = File(qr_io, name=f"ticket_{ticket.id}.png")
    ticket.qr_code.save(f"ticket_{ticket.id}.png", qr_file)


def generate_ticket_pdf(tickets, request, buyer_name=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    x_margin, y_margin = 20 * mm, 20 * mm
    ticket_width, ticket_height = width - 2 * x_margin, 80 * mm
    vertical_spacing = 15 * mm
    y = height - y_margin

    for ticket in tickets:
        if y - ticket_height < y_margin:
            p.showPage()
            y = height - y_margin

        show = ticket.show

        # Background
        p.setFillColorRGB(0.97, 0.97, 0.97)
        p.roundRect(
            x_margin,
            y - ticket_height,
            ticket_width,
            ticket_height,
            10,
            fill=1,
            stroke=0,
        )

        # Poster
        if show.poster:
            poster_path = os.path.join(settings.MEDIA_ROOT, str(show.poster))
            if os.path.exists(poster_path):
                p.drawImage(
                    ImageReader(poster_path),
                    x_margin + 5,
                    y - ticket_height + 5,
                    width=45 * mm,
                    height=60 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )

        # Ticket details
        text_x = x_margin + 50 * mm
        text_y = y - 10 * mm
        p.setFont("DejaVu", 13)
        p.setFillColorRGB(0.1, 0.1, 0.1)
        p.drawString(text_x, text_y, "🎟️ Raven Entertainment Ticket")

        # 👤 Use buyer_name if provided, else ticket.user.username
        name_to_print = buyer_name or ticket.user.username

        p.setFont("DejaVu", 10)
        p.drawString(text_x, text_y - 14, f"Name: {name_to_print}")
        p.drawString(text_x, text_y - 28, f"Seat: {ticket.seat_number}")
        p.drawString(text_x, text_y - 42, f"Show: {show.name}")
        p.drawString(
            text_x, text_y - 56, f"Time: {show.date.strftime('%d %B %Y %I:%M %p')}"
        )
        p.drawString(text_x, text_y - 70, "📍 Bharat Natya Mandir, Pune")
        p.drawString(text_x, text_y - 84, f"Booking ID: RAVEN{ticket.id:05d}")
        p.drawString(text_x, text_y - 98, "Price: \u20b9" + f"{show.seat_price}")

        # QR Code
        qr_path = os.path.join(settings.MEDIA_ROOT, str(ticket.qr_code))
        if os.path.exists(qr_path):
            p.drawImage(
                qr_path,
                x_margin + ticket_width - 50 * mm,
                y - ticket_height + 15 * mm,
                width=40 * mm,
                height=40 * mm,
            )

        y -= ticket_height + vertical_spacing

    # Footer
    p.setFont("DejaVu", 10)
    p.setFillColorRGB(0.2, 0.2, 0.2)
    p.drawCentredString(
        width / 2,
        15 * mm,
        "Thank you for booking with Raven Entertainment 🎭 | www.ravenentertainment.in",
    )
    p.save()
    buffer.seek(0)
    return buffer


def background_task(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def send_ticket_email(user_email, pdf_buffer):
    email = EmailMessage(
        subject="🎫 Your Raven Entertainment Tickets",
        body="Attached is your ticket(s). See you at the show!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    email.attach("tickets.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()


def send_manual_ticket_email(tickets, user_email, request, buyer_name):
    from .qr_utils import \
        generate_ticket_pdf  # Make sure this is correctly imported

    pdf_buffer = generate_ticket_pdf(tickets, request, buyer_name)

    email = EmailMessage(
        subject="🎫 Your Raven Entertainment Tickets",
        body=f"Dear {buyer_name},\n\nAttached is your ticket(s). Thank you for booking with Raven Entertainment!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    email.attach("tickets.pdf", pdf_buffer.getvalue(), "application/pdf")
    email.send()
