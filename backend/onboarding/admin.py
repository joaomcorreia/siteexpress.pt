from django.contrib import admin

from .models import (
    AssistantConversation,
    AssistantMessage,
    BusinessProfile,
    DomainRequest,
    GeneratedContent,
    Partner,
    PartnerReferral,
    StarterPage,
    WebsiteProject,
    WordPressSiteDraft,
)


class AssistantMessageInline(admin.TabularInline):
    model = AssistantMessage
    extra = 0
    fields = ("role", "content", "mode", "model", "input_tokens", "output_tokens", "created_at")
    readonly_fields = fields
    can_delete = False


@admin.register(AssistantConversation)
class AssistantConversationAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "mode",
        "model",
        "turn_count",
        "input_tokens",
        "output_tokens",
        "page_path",
        "last_message_at",
    )
    list_filter = ("mode", "model", "created_at")
    search_fields = ("public_id", "page_path", "page_title", "messages__content")
    readonly_fields = ("public_id", "created_at", "updated_at", "last_message_at")
    inlines = (AssistantMessageInline,)


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "mode", "model", "input_tokens", "output_tokens", "created_at")
    list_filter = ("role", "mode", "model", "created_at")
    search_fields = ("conversation__public_id", "content", "response_id")
    readonly_fields = ("created_at",)


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ("business_name", "business_type", "city", "country", "target_language", "user")
    search_fields = ("business_name", "email", "city", "country")


@admin.register(WebsiteProject)
class WebsiteProjectAdmin(admin.ModelAdmin):
    list_display = (
        "business_profile",
        "product_type",
        "price_snapshot",
        "billing_type",
        "product_status",
        "upgrade_status",
        "partner",
        "is_partner_trial",
        "trial_source",
        "status",
        "domain_choice",
        "starter_page_enabled",
        "wordpress_upgrade_available",
    )
    list_filter = (
        "product_type",
        "billing_type",
        "product_status",
        "upgrade_status",
        "partner",
        "is_partner_trial",
        "trial_source",
        "status",
        "domain_choice",
        "starter_page_enabled",
        "wordpress_upgrade_available",
    )
    search_fields = ("business_profile__business_name", "business_profile__email", "partner_code_snapshot")


@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ("project", "language", "hero_title", "updated_at")
    search_fields = ("hero_title", "seo_title", "project__business_profile__business_name")


@admin.register(StarterPage)
class StarterPageAdmin(admin.ModelAdmin):
    list_display = ("slug", "project", "is_preview", "is_active")
    list_filter = ("is_preview", "is_active")


@admin.register(WordPressSiteDraft)
class WordPressSiteDraftAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "wp_site_url", "updated_at")
    list_filter = ("status",)


@admin.register(DomainRequest)
class DomainRequestAdmin(admin.ModelAdmin):
    list_display = ("requested_domain", "business_profile", "domain_status", "registrar", "updated_at")
    list_filter = ("domain_status", "registrar")
    search_fields = (
        "requested_domain",
        "alternative_domain_1",
        "alternative_domain_2",
        "business_profile__business_name",
        "business_profile__email",
    )


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "name",
        "partner_code",
        "status",
        "default_trial_months",
        "commission_amount",
    )
    list_filter = ("status", "commission_currency", "default_trial_months")
    search_fields = ("company_name", "name", "partner_code", "email", "phone", "whatsapp_phone")


@admin.register(PartnerReferral)
class PartnerReferralAdmin(admin.ModelAdmin):
    list_display = (
        "partner",
        "customer_name",
        "customer_email",
        "product_type_snapshot",
        "referral_status",
        "commission_status",
        "commission_amount",
        "created_at",
    )
    list_filter = ("partner", "referral_status", "commission_status", "product_type_snapshot")
    search_fields = ("customer_name", "customer_email", "customer_phone", "partner__company_name", "partner__partner_code")
