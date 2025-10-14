from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),  # Home page
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("jjv/", views.jjv, name="jjv"),
    path("a1k/", views.a1k, name="a1k"),
    path("payments/<int:booking_id>/", views.payment_gateway, name="payments"),
    path("accounts/", include("accounts.urls")),
    path("show/<slug:slug>/", views.show_detail_view, name="show_detail"),
    path("admin/manage-users/", views.admin_user_list, name="admin_user_list"),
    path("manage-users/", views.admin_user_list, name="admin_user_list"),
    path("admin/media/upload/<int:show_id>/", views.upload_media, name="upload_media"),
    path("qr/<int:ticket_id>/", views.verify_qr_view, name="verify_qr"),
    path("book/<int:show_id>/", views.create_booking, name="book_ticket"),
    path(
        "dashboard/visitor-analytics/",
        views.admin_visitor_analytics,
        name="admin_visitor_analytics",
    ),
    path(
        "dashboard/get_visitor_data/", views.get_visitor_data, name="get_visitor_data"
    ),
    path(
        "download-ticket/<int:ticket_id>/",
        views.download_ticket,
        name="download_ticket",
    ),
    path("profile/settings/", views.profile_settings, name="profile_settings"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
