from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

from .models import BusinessProfile, Partner, WebsiteProject

SERVICE_ICON_CHOICES = [
    ("wrench", _("Wrench")),
    ("car", _("Car")),
    ("shield", _("Shield")),
    ("clock", _("Clock")),
    ("check", _("Check")),
    ("phone", _("Phone")),
    ("spark", _("Spark")),
    ("home", _("Home")),
    ("truck", _("Truck")),
]


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Email"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "email",
                "inputmode": "email",
                "placeholder": "nome@exemplo.pt",
            }
        ),
    )
    password = forms.CharField(
        label=_("Palavra-passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean(self):
        login_value = (self.cleaned_data.get("username") or "").strip()
        if login_value:
            matching_usernames = list(
                get_user_model()
                .objects.filter(email__iexact=login_value)
                .values_list("username", flat=True)[:2]
            )
            if len(matching_usernames) == 1:
                self.cleaned_data["username"] = matching_usernames[0]
        return super().clean()


class BusinessProfileForm(forms.ModelForm):
    preferred_colors = forms.CharField(
        label=_("Preferred colors"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("#0f172a, #e11d48"),
            }
        ),
        help_text=_("Comma-separated color values for the visual direction."),
    )

    class Meta:
        model = BusinessProfile
        fields = [
            "business_name",
            "business_type",
            "address",
            "city",
            "region",
            "country",
            "email",
            "phone",
            "whatsapp",
            "logo",
            "preferred_colors",
            "target_country",
            "target_city",
            "target_region",
            "target_audience",
            "target_language",
        ]
        widgets = {
            "target_audience": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_preferred_colors(self):
        value = self.cleaned_data.get("preferred_colors", "")
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "address",
            "country",
            "target_country",
            "target_city",
            "target_region",
            "target_audience",
            "target_language",
        ):
            self.fields[field_name].required = False

        labels = {
            "business_name": _("Nome do negocio"),
            "business_type": _("O que faz a sua empresa?"),
            "address": _("Morada"),
            "city": _("Cidade ou zona principal"),
            "region": _("Regiao"),
            "country": _("Pais"),
            "email": _("Email"),
            "phone": _("Telefone"),
            "whatsapp": _("WhatsApp"),
            "logo": _("Logotipo"),
            "target_country": _("Pais-alvo"),
            "target_city": _("Cidade-alvo"),
            "target_region": _("Regiao-alvo"),
            "target_audience": _("Publico-alvo"),
            "target_language": _("Idioma principal"),
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label

        self.fields["business_name"].widget.attrs.update(
            {
                "placeholder": _("Ex.: Construções Silva"),
                "autocomplete": "organization",
            }
        )
        self.fields["business_type"].widget.attrs.update(
            {
                "placeholder": _("Ex.: construção, pinturas e manutenção de jardins"),
            }
        )
        self.fields["city"].widget.attrs.update(
            {
                "placeholder": _("Ex.: Santa Maria da Feira"),
                "autocomplete": "address-level2",
            }
        )
        self.fields["email"].widget.attrs.update(
            {
                "placeholder": _("nome@empresa.pt"),
                "autocomplete": "email",
            }
        )
        self.fields["phone"].widget.attrs.update(
            {
                "placeholder": _("Ex.: 912 345 678"),
                "autocomplete": "tel",
            }
        )
        self.fields["whatsapp"].widget.attrs.update(
            {
                "placeholder": _("Se for diferente do telefone"),
                "autocomplete": "tel",
            }
        )

    def clean(self):
        cleaned_data = super().clean()
        city = (cleaned_data.get("city") or "").strip()
        country = (cleaned_data.get("country") or "Portugal").strip()
        region = (cleaned_data.get("region") or "").strip()
        cleaned_data["address"] = (cleaned_data.get("address") or "").strip()
        cleaned_data["country"] = country
        cleaned_data["target_country"] = (
            cleaned_data.get("target_country") or country
        ).strip()
        cleaned_data["target_city"] = (
            cleaned_data.get("target_city") or city
        ).strip()
        cleaned_data["target_region"] = (
            cleaned_data.get("target_region") or region
        ).strip()
        cleaned_data["target_audience"] = (
            cleaned_data.get("target_audience") or ""
        ).strip()
        cleaned_data["target_language"] = (
            cleaned_data.get("target_language") or "pt"
        ).strip()
        return cleaned_data


class WebsiteProjectForm(forms.ModelForm):
    partner_code = forms.CharField(
        label=_("Codigo de parceiro ou recomendacao"),
        required=False,
        help_text=_("Opcional. Preencha apenas se recebeu um codigo de parceiro ou recomendacao."),
    )

    def __init__(self, *args, **kwargs):
        self.partner_locked_code = kwargs.pop("partner_locked_code", "")
        super().__init__(*args, **kwargs)
        self.fields["domain_choice"].required = False
        self.fields["domain_choice"].initial = WebsiteProject.DomainChoice.PREVIEW_ONLY
        self.fields["product_type"].required = True
        self.fields["product_type"].initial = WebsiteProject.ProductType.STARTER_PAGE_MONTHLY
        self.fields["domain_choice"].label = _("Opcao de dominio")
        self.fields["existing_domain"].label = _("Dominio atual")
        self.fields["preferred_domain"].label = _("Dominio pretendido")
        self.fields["alternative_domain_1"].label = _("Dominio alternativo 1")
        self.fields["alternative_domain_2"].label = _("Dominio alternativo 2")
        self.fields["domain_choice"].choices = [
            (WebsiteProject.DomainChoice.ALREADY_HAVE_DOMAIN, _("Ja tenho dominio")),
            (WebsiteProject.DomainChoice.NEED_HELP, _("Preciso de ajuda")),
            (WebsiteProject.DomainChoice.PREVIEW_ONLY, _("Apenas preview")),
        ]
        self.order_fields(
            [
                "product_type",
                "partner_code",
                "domain_choice",
                "existing_domain",
                "preferred_domain",
                "alternative_domain_1",
                "alternative_domain_2",
            ]
        )
        if self.partner_locked_code:
            self.fields["partner_code"].initial = self.partner_locked_code
            self.fields["partner_code"].disabled = True
            self.fields["partner_code"].help_text = _(
                "Codigo aplicado automaticamente por um parceiro SiteExpress."
            )

    class Meta:
        model = WebsiteProject
        fields = [
            "product_type",
            "domain_choice",
            "existing_domain",
            "preferred_domain",
            "alternative_domain_1",
            "alternative_domain_2",
        ]

    def clean_partner_code(self):
        code = (self.cleaned_data.get("partner_code") or self.partner_locked_code or "").strip()
        if not code:
            return ""
        if not Partner.objects.filter(partner_code__iexact=code, status=Partner.Status.ACTIVE).exists():
            raise forms.ValidationError(_("O codigo de parceiro nao e valido ou esta inativo."))
        return code

    def clean(self):
        cleaned_data = super().clean()
        domain_choice = cleaned_data.get("domain_choice") or WebsiteProject.DomainChoice.PREVIEW_ONLY
        cleaned_data["domain_choice"] = domain_choice
        product_type = cleaned_data.get("product_type")
        existing_domain = (cleaned_data.get("existing_domain") or "").strip()
        preferred_domain = (cleaned_data.get("preferred_domain") or "").strip()

        if not product_type:
            self.add_error("product_type", _("Escolha um produto."))

        if domain_choice == WebsiteProject.DomainChoice.ALREADY_HAVE_DOMAIN and not existing_domain:
            self.add_error("existing_domain", _("Enter the domain you already own."))

        if domain_choice == WebsiteProject.DomainChoice.NEED_HELP and not preferred_domain:
            self.add_error("preferred_domain", _("Enter your preferred domain."))

        if domain_choice == WebsiteProject.DomainChoice.PREVIEW_ONLY:
            cleaned_data["existing_domain"] = ""
            cleaned_data["preferred_domain"] = ""
            cleaned_data["alternative_domain_1"] = ""
            cleaned_data["alternative_domain_2"] = ""

        return cleaned_data


class DashboardBusinessInfoForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = [
            "business_name",
            "business_type",
            "city",
            "country",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["business_name"].label = _("Nome do negocio")
        self.fields["business_type"].label = _("Tipo de negocio")
        self.fields["city"].label = _("Cidade")
        self.fields["country"].label = _("Pais")


class DashboardContactDetailsForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = [
            "email",
            "phone",
            "whatsapp",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = _("Email")
        self.fields["phone"].label = _("Telefone")
        self.fields["whatsapp"].label = _("WhatsApp")


class DashboardServicesForm(forms.Form):
    service_count = 6

    def __init__(self, *args, services=None, **kwargs):
        super().__init__(*args, **kwargs)
        services = services or []
        self.service_seed = services
        for index in range(1, self.service_count + 1):
            service = services[index - 1] if index - 1 < len(services) else {}
            self.fields[f"service_{index}_title"] = forms.CharField(
                label=_("Title"),
                required=False,
                initial=service.get("title", ""),
            )
            self.fields[f"service_{index}_short_description"] = forms.CharField(
                label=_("Short description"),
                required=False,
                widget=forms.Textarea(attrs={"rows": 3}),
                initial=service.get("short_description")
                or service.get("description", ""),
            )
            self.fields[f"service_{index}_icon"] = forms.ChoiceField(
                label=_("Icon"),
                required=False,
                choices=SERVICE_ICON_CHOICES,
                initial=service.get("icon", "wrench"),
            )

    def cleaned_services(self, existing_services):
        updated = list(existing_services)
        for index in range(1, self.service_count + 1):
            title = (self.cleaned_data.get(f"service_{index}_title") or "").strip()
            short_description = (
                self.cleaned_data.get(f"service_{index}_short_description") or ""
            ).strip()
            icon = (self.cleaned_data.get(f"service_{index}_icon") or "").strip()
            if not title and not short_description:
                continue

            existing = updated[index - 1] if index - 1 < len(updated) else {}
            slug = (
                existing.get("slug")
                or slugify(existing.get("title", ""))
                or slugify(title)
                or f"service-{index}"
            )
            full_description = existing.get("full_description") or short_description
            service_payload = {
                **existing,
                "title": title or existing.get("title") or slug.replace("-", " ").title(),
                "slug": slug,
                "short_description": short_description,
                "description": short_description,
                "full_description": full_description if full_description else short_description,
                "order": existing.get("order", index),
                "is_active": existing.get("is_active", True),
                "icon": icon or existing.get("icon") or "wrench",
            }
            if index - 1 < len(updated):
                updated[index - 1] = service_payload
            else:
                updated.append(service_payload)
        return updated
