from django.urls import path

from . import views


urlpatterns = [
    path("", views.siteexpress_landing_view, name="siteexpress-landing"),
    path("siteexpress/", views.siteexpress_landing_view, name="siteexpress-landing-alias"),
    path(
        "sites-wordpress/",
        views.public_page_view,
        {"page_key": "wordpress"},
        name="website-wordpress",
    ),
    path(
        "pagina-express/",
        views.public_page_view,
        {"page_key": "starter"},
        name="starter-page",
    ),
    path(
        "como-funciona/",
        views.public_page_view,
        {"page_key": "process"},
        name="how-it-works",
    ),
    path("precos/", views.pricing_view, name="pricing"),
    path(
        "impressao/",
        views.public_page_view,
        {"page_key": "printing"},
        name="printing",
    ),
    path(
        "impressao/cartoes-de-visita/",
        views.public_page_view,
        {"page_key": "business-cards"},
        name="business-cards",
    ),
    path(
        "contactos/",
        views.public_page_view,
        {"page_key": "contact"},
        name="contact",
    ),
    path(
        "assistente-ia/",
        views.public_page_view,
        {"page_key": "ai-assistant"},
        name="ai-assistant",
    ),
    path(
        "politica-de-privacidade/",
        views.legal_page_view,
        {"page_key": "privacy"},
        name="privacy-policy",
    ),
    path(
        "termos-e-condicoes/",
        views.legal_page_view,
        {"page_key": "terms"},
        name="terms",
    ),
    path(
        "politica-de-cookies/",
        views.legal_page_view,
        {"page_key": "cookies"},
        name="cookie-policy",
    ),
    path("assistant/chat/", views.assistant_chat_view, name="assistant-chat"),
    path("assistant/usage/", views.assistant_usage_view, name="assistant-usage"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("onboarding/parceiro/<str:partner_code>/", views.onboarding_view, name="partner-onboarding"),
    path("onboarding/success/", views.success_view, name="success"),
    path("onboarding/account-setup/", views.account_setup_entry_view, name="account-setup-entry"),
    path("onboarding/account-setup/<uidb64>/<token>/", views.account_setup_view, name="account-setup"),
    path("onboarding/dashboard/", views.dashboard_view, name="dashboard"),
    path("onboarding/domain-requests/", views.domain_requests_view, name="domain-requests"),
    path("onboarding/partner/<str:partner_code>/dashboard/", views.partner_dashboard_view, name="partner-dashboard"),
    path("onboarding/starter/<slug:slug>/", views.starter_page_preview_view, name="starter-preview"),
    path("onboarding/upgrade/", views.upgrade_placeholder_view, name="upgrade-placeholder"),
]
