from django.urls import path

from . import views


urlpatterns = [
    path("", views.siteexpress_landing_view, name="siteexpress-landing"),
    path("siteexpress/", views.siteexpress_landing_view, name="siteexpress-landing-alias"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("onboarding/parceiro/<str:partner_code>/", views.onboarding_view, name="partner-onboarding"),
    path("onboarding/success/", views.success_view, name="success"),
    path("onboarding/account-setup/<uidb64>/<token>/", views.account_setup_view, name="account-setup"),
    path("onboarding/dashboard/", views.dashboard_view, name="dashboard"),
    path("onboarding/domain-requests/", views.domain_requests_view, name="domain-requests"),
    path("onboarding/partner/<str:partner_code>/dashboard/", views.partner_dashboard_view, name="partner-dashboard"),
    path("onboarding/starter/<slug:slug>/", views.starter_page_preview_view, name="starter-preview"),
    path("onboarding/upgrade/", views.upgrade_placeholder_view, name="upgrade-placeholder"),
]
