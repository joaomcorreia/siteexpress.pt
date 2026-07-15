import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class BusinessProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profiles",
        verbose_name=_("User"),
    )
    business_name = models.CharField(max_length=255, verbose_name=_("Business name"))
    business_type = models.CharField(max_length=120, verbose_name=_("Business type"))
    address = models.CharField(max_length=255, verbose_name=_("Address"))
    city = models.CharField(max_length=120, verbose_name=_("City"))
    region = models.CharField(max_length=120, blank=True, verbose_name=_("Region"))
    country = models.CharField(max_length=120, verbose_name=_("Country"))
    email = models.EmailField(verbose_name=_("Email"))
    phone = models.CharField(max_length=30, blank=True, verbose_name=_("Phone"))
    whatsapp = models.CharField(max_length=30, blank=True, verbose_name=_("WhatsApp"))
    logo = models.ImageField(upload_to="logos/", blank=True, null=True, verbose_name=_("Logo"))
    preferred_colors = models.JSONField(default=list, blank=True, verbose_name=_("Preferred colors"))
    target_country = models.CharField(max_length=120, blank=True, verbose_name=_("Target country"))
    target_city = models.CharField(max_length=120, blank=True, verbose_name=_("Target city"))
    target_region = models.CharField(max_length=120, blank=True, verbose_name=_("Target region"))
    target_audience = models.TextField(blank=True, verbose_name=_("Target audience"))
    target_language = models.CharField(max_length=20, default="pt", verbose_name=_("Target language"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Business profile")
        verbose_name_plural = _("Business profiles")

    def __str__(self):
        return self.business_name


class Partner(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        PAUSED = "paused", _("Paused")
        DISABLED = "disabled", _("Disabled")

    name = models.CharField(max_length=255, verbose_name=_("Name"))
    company_name = models.CharField(max_length=255, verbose_name=_("Company name"))
    email = models.EmailField(verbose_name=_("Email"))
    phone = models.CharField(max_length=30, blank=True, verbose_name=_("Phone"))
    whatsapp_phone = models.CharField(max_length=30, blank=True, verbose_name=_("WhatsApp phone"))
    partner_code = models.CharField(max_length=64, unique=True, verbose_name=_("Partner code"))
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_("Status"),
    )
    default_trial_months = models.PositiveIntegerField(default=1, verbose_name=_("Default trial months"))
    commission_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=20.00,
        verbose_name=_("Commission amount"),
    )
    commission_currency = models.CharField(max_length=8, default="EUR", verbose_name=_("Commission currency"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_name", "name"]
        verbose_name = _("Partner")
        verbose_name_plural = _("Partners")

    def __str__(self):
        return f"{self.company_name} ({self.partner_code})"


class WebsiteProject(models.Model):
    class PlanInterest(models.TextChoices):
        STARTER_MONTHLY = "starter_monthly", _("Starter monthly")
        STANDARD_FULL_WEBSITE = "standard_full_website", _("Standard full website")
        PREMIUM_BILINGUAL = "premium_bilingual", _("Premium bilingual")

    class Status(models.TextChoices):
        ONBOARDING_STARTED = "onboarding_started", _("Onboarding started")
        CONTENT_GENERATED = "content_generated", _("Content generated")
        STARTER_PREVIEW_READY = "starter_preview_ready", _("Starter preview ready")
        WORDPRESS_DRAFT_READY = "wordpress_draft_ready", _("WordPress draft ready")
        UPGRADED = "upgraded", _("Upgraded")
        PUBLISHED = "published", _("Published")

    class DomainChoice(models.TextChoices):
        ALREADY_HAVE_DOMAIN = "already_have_domain", _("Already have domain")
        NEED_HELP = "need_help", _("Need help")
        PREVIEW_ONLY = "preview_only", _("Preview only")

    class ProductType(models.TextChoices):
        STARTER_PAGE_MONTHLY = "starter_page_monthly", _("Pagina Express")
        FULL_WEBSITE_ONETIME = "full_website_onetime", _("Website Completo")

    class BillingType(models.TextChoices):
        MONTHLY = "monthly", _("Monthly")
        ONE_TIME = "one_time", _("One time")

    class ProductStatus(models.TextChoices):
        SELECTED = "selected", _("Selected")
        GENERATING = "generating", _("Generating")
        PREVIEW_READY = "preview_ready", _("Preview ready")
        CUSTOMER_REVIEWING = "customer_reviewing", _("Customer reviewing")
        UPGRADE_AVAILABLE = "upgrade_available", _("Upgrade available")
        UPGRADE_REQUESTED = "upgrade_requested", _("Upgrade requested")
        PAYMENT_PENDING = "payment_pending", _("Payment pending")
        PAYMENT_CONFIRMED = "payment_confirmed", _("Payment confirmed")
        PUBLISHING_PENDING = "publishing_pending", _("Publishing pending")
        PUBLISHED = "published", _("Published")
        CANCELLED = "cancelled", _("Cancelled")

    class UpgradeStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", _("Not applicable")
        AVAILABLE = "available", _("Available")
        REQUESTED = "requested", _("Requested")
        IN_PROGRESS = "in_progress", _("In progress")
        COMPLETED = "completed", _("Completed")

    class TrialSource(models.TextChoices):
        NONE = "none", _("None")
        PARTNER = "partner", _("Partner")
        ADMIN = "admin", _("Admin")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="website_projects",
        verbose_name=_("User"),
    )
    business_profile = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name=_("Business profile"),
    )
    plan_interest = models.CharField(
        max_length=32,
        choices=PlanInterest.choices,
        default=PlanInterest.STARTER_MONTHLY,
        verbose_name=_("Plan interest"),
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.ONBOARDING_STARTED,
        verbose_name=_("Status"),
    )
    starter_page_enabled = models.BooleanField(default=True, verbose_name=_("Starter page enabled"))
    wordpress_upgrade_available = models.BooleanField(
        default=True,
        verbose_name=_("WordPress upgrade available"),
    )
    domain_choice = models.CharField(
        max_length=32,
        choices=DomainChoice.choices,
        default=DomainChoice.PREVIEW_ONLY,
        verbose_name=_("Domain choice"),
    )
    existing_domain = models.CharField(max_length=255, blank=True, verbose_name=_("Existing domain"))
    preferred_domain = models.CharField(max_length=255, blank=True, verbose_name=_("Preferred domain"))
    alternative_domain_1 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Alternative domain 1"),
    )
    alternative_domain_2 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Alternative domain 2"),
    )
    product_type = models.CharField(
        max_length=32,
        choices=ProductType.choices,
        default=ProductType.STARTER_PAGE_MONTHLY,
        verbose_name=_("Product type"),
    )
    price_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name=_("Price snapshot"),
    )
    currency = models.CharField(max_length=8, default="EUR", verbose_name=_("Currency"))
    billing_type = models.CharField(
        max_length=16,
        choices=BillingType.choices,
        default=BillingType.MONTHLY,
        verbose_name=_("Billing type"),
    )
    product_status = models.CharField(
        max_length=32,
        choices=ProductStatus.choices,
        default=ProductStatus.SELECTED,
        verbose_name=_("Product status"),
    )
    upgrade_status = models.CharField(
        max_length=32,
        choices=UpgradeStatus.choices,
        default=UpgradeStatus.AVAILABLE,
        verbose_name=_("Upgrade status"),
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.SET_NULL,
        related_name="projects",
        blank=True,
        null=True,
        verbose_name=_("Partner"),
    )
    partner_code_snapshot = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Partner code snapshot"),
    )
    is_partner_trial = models.BooleanField(default=False, verbose_name=_("Is partner trial"))
    trial_source = models.CharField(
        max_length=16,
        choices=TrialSource.choices,
        default=TrialSource.NONE,
        verbose_name=_("Trial source"),
    )
    trial_months = models.PositiveIntegerField(default=0, verbose_name=_("Trial months"))
    trial_started_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Trial started at"))
    trial_ends_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Trial ends at"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Website project")
        verbose_name_plural = _("Website projects")

    def __str__(self):
        return f"{self.business_profile.business_name} ({self.get_plan_interest_display()})"


class GeneratedContent(models.Model):
    project = models.ForeignKey(
        WebsiteProject,
        on_delete=models.CASCADE,
        related_name="generated_contents",
        verbose_name=_("Project"),
    )
    language = models.CharField(max_length=20, default="pt", verbose_name=_("Language"))
    hero_title = models.CharField(max_length=255, blank=True, verbose_name=_("Hero title"))
    hero_subtitle = models.CharField(max_length=255, blank=True, verbose_name=_("Hero subtitle"))
    intro_text = models.TextField(blank=True, verbose_name=_("Intro text"))
    services_json = models.JSONField(default=list, blank=True, verbose_name=_("Services"))
    about_text = models.TextField(blank=True, verbose_name=_("About text"))
    cta_text = models.CharField(max_length=255, blank=True, verbose_name=_("Call to action text"))
    seo_title = models.CharField(max_length=255, blank=True, verbose_name=_("SEO title"))
    seo_description = models.TextField(blank=True, verbose_name=_("SEO description"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Generated content")
        verbose_name_plural = _("Generated content")

    def __str__(self):
        return f"{self.project} [{self.language}]"


class StarterPage(models.Model):
    project = models.OneToOneField(
        WebsiteProject,
        on_delete=models.CASCADE,
        related_name="starter_page",
        verbose_name=_("Project"),
    )
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_("Slug"))
    is_preview = models.BooleanField(default=True, verbose_name=_("Is preview"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Starter page")
        verbose_name_plural = _("Starter pages")

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):
        if not self.slug and self.project_id:
            base_slug = slugify(self.project.business_profile.business_name) or "starter-page"
            self.slug = f"{base_slug}-{self.project_id}"
        super().save(*args, **kwargs)


class WordPressSiteDraft(models.Model):
    class Status(models.TextChoices):
        DRAFT_PENDING = "draft_pending", _("Draft pending")
        CONTENT_READY = "content_ready", _("Content ready")
        WAITING_FOR_UPGRADE = "waiting_for_upgrade", _("Waiting for upgrade")
        READY_TO_PUBLISH = "ready_to_publish", _("Ready to publish")
        PUBLISHED = "published", _("Published")

    project = models.OneToOneField(
        WebsiteProject,
        on_delete=models.CASCADE,
        related_name="wordpress_draft",
        verbose_name=_("Project"),
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.WAITING_FOR_UPGRADE,
        verbose_name=_("Status"),
    )
    wp_site_url = models.URLField(blank=True, verbose_name=_("WordPress site URL"))
    wp_admin_url = models.URLField(blank=True, verbose_name=_("WordPress admin URL"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("WordPress site draft")
        verbose_name_plural = _("WordPress site drafts")

    def __str__(self):
        return f"{self.project} [{self.get_status_display()}]"


class DomainRequest(models.Model):
    class Status(models.TextChoices):
        NOT_REQUESTED = "not_requested", _("Not requested")
        REQUESTED = "requested", _("Requested")
        CHECKING = "checking", _("Checking")
        AVAILABLE = "available", _("Available")
        UNAVAILABLE = "unavailable", _("Unavailable")
        WAITING_CUSTOMER = "waiting_customer", _("Waiting customer")
        REGISTERED_MANUAL = "registered_manual", _("Registered manually")
        DNS_PENDING = "dns_pending", _("DNS pending")
        DNS_CONNECTED = "dns_connected", _("DNS connected")
        LIVE = "live", _("Live")
        CANCELLED = "cancelled", _("Cancelled")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="domain_requests",
        blank=True,
        null=True,
        verbose_name=_("User"),
    )
    business_profile = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="domain_requests",
        blank=True,
        null=True,
        verbose_name=_("Business profile"),
    )
    project = models.OneToOneField(
        WebsiteProject,
        on_delete=models.CASCADE,
        related_name="domain_request",
        blank=True,
        null=True,
        verbose_name=_("Project"),
    )
    requested_domain = models.CharField(max_length=255, blank=True, verbose_name=_("Requested domain"))
    alternative_domain_1 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Alternative domain 1"),
    )
    alternative_domain_2 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Alternative domain 2"),
    )
    preview_subdomain = models.CharField(max_length=255, blank=True, verbose_name=_("Preview subdomain"))
    domain_status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NOT_REQUESTED,
        verbose_name=_("Domain status"),
    )
    registrar = models.CharField(max_length=255, blank=True, verbose_name=_("Registrar"))
    registrant_name = models.CharField(max_length=255, blank=True, verbose_name=_("Registrant name"))
    registrant_vat_or_nif = models.CharField(
        max_length=80,
        blank=True,
        verbose_name=_("Registrant VAT or NIF"),
    )
    registrant_address = models.TextField(blank=True, verbose_name=_("Registrant address"))
    registrant_email = models.EmailField(blank=True, verbose_name=_("Registrant email"))
    registrant_phone = models.CharField(max_length=50, blank=True, verbose_name=_("Registrant phone"))
    public_note = models.TextField(blank=True, verbose_name=_("Public note"))
    admin_note = models.TextField(blank=True, verbose_name=_("Admin note"))
    registered_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Registered at"))
    dns_connected_at = models.DateTimeField(blank=True, null=True, verbose_name=_("DNS connected at"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Domain request")
        verbose_name_plural = _("Domain requests")

    def __str__(self):
        return self.requested_domain or self.preview_subdomain or str(self.project or self.business_profile or self.user)


class PartnerReferral(models.Model):
    class ReferralStatus(models.TextChoices):
        LEAD_CREATED = "lead_created", _("Lead created")
        STARTER_TRIAL_ACTIVE = "starter_trial_active", _("Starter trial active")
        TRIAL_ENDING_SOON = "trial_ending_soon", _("Trial ending soon")
        TRIAL_EXPIRED = "trial_expired", _("Trial expired")
        STARTER_PAID = "starter_paid", _("Starter paid")
        UPGRADE_REQUESTED = "upgrade_requested", _("Upgrade requested")
        FULL_WEBSITE_PAID = "full_website_paid", _("Full website paid")
        CANCELLED = "cancelled", _("Cancelled")

    class CommissionStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", _("Not applicable")
        PENDING = "pending", _("Pending")
        AVAILABLE = "available", _("Available")
        REQUESTED = "requested", _("Requested")
        PAID = "paid", _("Paid")
        REJECTED = "rejected", _("Rejected")

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name="referrals",
        verbose_name=_("Partner"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="partner_referrals",
        blank=True,
        null=True,
        verbose_name=_("User"),
    )
    business_profile = models.ForeignKey(
        BusinessProfile,
        on_delete=models.SET_NULL,
        related_name="partner_referrals",
        blank=True,
        null=True,
        verbose_name=_("Business profile"),
    )
    project = models.OneToOneField(
        WebsiteProject,
        on_delete=models.SET_NULL,
        related_name="partner_referral",
        blank=True,
        null=True,
        verbose_name=_("Project"),
    )
    customer_name = models.CharField(max_length=255, blank=True, verbose_name=_("Customer name"))
    customer_email = models.EmailField(blank=True, verbose_name=_("Customer email"))
    customer_phone = models.CharField(max_length=50, blank=True, verbose_name=_("Customer phone"))
    product_type_snapshot = models.CharField(max_length=32, blank=True, verbose_name=_("Product type snapshot"))
    trial_months = models.PositiveIntegerField(default=0, verbose_name=_("Trial months"))
    trial_started_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Trial started at"))
    trial_ends_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Trial ends at"))
    referral_status = models.CharField(
        max_length=32,
        choices=ReferralStatus.choices,
        default=ReferralStatus.LEAD_CREATED,
        verbose_name=_("Referral status"),
    )
    commission_status = models.CharField(
        max_length=32,
        choices=CommissionStatus.choices,
        default=CommissionStatus.NOT_APPLICABLE,
        verbose_name=_("Commission status"),
    )
    commission_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name=_("Commission amount"),
    )
    commission_available_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Commission available at"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Partner referral")
        verbose_name_plural = _("Partner referrals")

    def __str__(self):
        return self.customer_name or self.customer_email or str(self.partner)


class AssistantConversation(models.Model):
    class Mode(models.TextChoices):
        DEMO = "demo", _("Demo")
        OPENAI = "openai", _("OpenAI")

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assistant_conversations",
        blank=True,
        null=True,
        verbose_name=_("User"),
    )
    page_path = models.CharField(max_length=500, blank=True, verbose_name=_("Page path"))
    page_title = models.CharField(max_length=255, blank=True, verbose_name=_("Page title"))
    model = models.CharField(max_length=100, blank=True, verbose_name=_("Model"))
    mode = models.CharField(
        max_length=16,
        choices=Mode.choices,
        default=Mode.DEMO,
        verbose_name=_("Mode"),
    )
    turn_count = models.PositiveIntegerField(default=0, verbose_name=_("Turns"))
    input_tokens = models.PositiveBigIntegerField(default=0, verbose_name=_("Input tokens"))
    cached_input_tokens = models.PositiveBigIntegerField(default=0, verbose_name=_("Cached input tokens"))
    output_tokens = models.PositiveBigIntegerField(default=0, verbose_name=_("Output tokens"))
    last_message_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Last message at"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        verbose_name = _("Assistant conversation")
        verbose_name_plural = _("Assistant conversations")

    def __str__(self):
        return f"{self.public_id} ({self.turn_count})"


class AssistantMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", _("User")
        ASSISTANT = "assistant", _("Assistant")

    conversation = models.ForeignKey(
        AssistantConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Conversation"),
    )
    role = models.CharField(max_length=16, choices=Role.choices, verbose_name=_("Role"))
    content = models.TextField(verbose_name=_("Content"))
    response_id = models.CharField(max_length=255, blank=True, verbose_name=_("Response ID"))
    model = models.CharField(max_length=100, blank=True, verbose_name=_("Model"))
    mode = models.CharField(
        max_length=16,
        choices=AssistantConversation.Mode.choices,
        default=AssistantConversation.Mode.DEMO,
        verbose_name=_("Mode"),
    )
    input_tokens = models.PositiveBigIntegerField(default=0, verbose_name=_("Input tokens"))
    cached_input_tokens = models.PositiveBigIntegerField(default=0, verbose_name=_("Cached input tokens"))
    output_tokens = models.PositiveBigIntegerField(default=0, verbose_name=_("Output tokens"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = _("Assistant message")
        verbose_name_plural = _("Assistant messages")

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:60]}"
