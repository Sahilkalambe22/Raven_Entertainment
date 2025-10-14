from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("user/dashboard/", views.user_dashboard, name="user_dashboard"),
    path("admin/", views.admin_dashboard_main, name="admin_dashboard_main"),
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/users/", views.admin_view_users, name="admin_view_users"),
    path(
        "admin/show/<int:show_id>/media/",
        views.admin_show_media_dashboard,
        name="admin_show_media",
    ),
    path(
        "admin/media/<int:media_id>/delete/",
        views.delete_media_file,
        name="delete_media",
    ),
    path(
        "admin/qr-analytics/", views.admin_qr_analytics_view, name="admin_qr_analytics"
    ),
    path(
        "admin/dashboard/home/",
        views.admin_dashboard_content,
        name="admin_dashboard_content",
    ),
    path(
        "admin/upload-media/", views.admin_upload_media_panel, name="admin_upload_media"
    ),
    path("admin/view-bookings/", views.admin_view_bookings, name="admin_view_bookings"),
    path("admin/all-shows/", views.admin_all_shows, name="admin_all_shows"),
    path("qr/scan/<int:show_id>/", views.qr_scan_log, name="qr_scan_log"),
    path("admin/create-show/", views.handle_create_show, name="admin_create_show"),
    path(
        "admin/show/<int:show_id>/scan/",
        views.admin_scan_tickets,
        name="admin_scan_tickets",
    ),
    path("verify-otp/<int:user_id>/", views.verify_email_otp, name="verify_email_otp"),
    path("resend-otp/<int:user_id>/", views.resend_email_otp, name="resend_email_otp"),
    path("forgot-password/", forgot_password_request, name="forgot_password"),
    path(
        "reset-password/otp/<int:user_id>/",
        reset_password_otp,
        name="reset_password_otp",
    ),
    path(
        "admin/manual-booking/<int:show_id>/",
        views.admin_manual_booking,
        name="admin_manual_booking",
    ),
    path("qr/scan/", views.qr_marketing_scan, name="qr_marketing_scan"),
    path(
        "qr/analytics/data/", views.get_qr_marketing_data, name="get_qr_marketing_data"
    ),
    path(
        "admin/qr-campaign-analytics/",
        views.admin_marketing_qr_analytics,
        name="admin_marketing_qr_analytics",
    ),
]
