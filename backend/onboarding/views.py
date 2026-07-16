import json
import logging
import re
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.utils import translation
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from .assistant import (
    analyze_assistant_build,
    generate_assistant_reply,
    generate_demo_reply,
    revise_assistant_build,
)
from .forms import (
    BusinessProfileForm,
    DashboardBusinessInfoForm,
    DashboardContactDetailsForm,
    DashboardServicesForm,
    SERVICE_ICON_CHOICES,
    WebsiteProjectForm,
)
from .models import (
    AssistantConversation,
    AssistantMessage,
    AssistantSiteBuild,
    DomainRequest,
    GeneratedContent,
    Partner,
    PartnerReferral,
    StarterPage,
    WebsiteProject,
    WordPressSiteDraft,
)
from .public_pages import LEGAL_PAGES, PRICING_PAGE, PUBLIC_PAGES

logger = logging.getLogger(__name__)

STARTER_FEATURED_LIMIT = 3
STARTER_SERVICES_LIMIT = 6
FULL_FEATURED_LIMIT = 6
SERVICES_HOME_FEATURED_LIMIT = 2
SERVICES_HOME_VISIBLE_LIMIT = 12
RESTAURANT_CLASSIC_STATIC_PREFIX = "siteexpress/demo/restaurant/classic/"
BEAUTY_CLASSIC_STATIC_PREFIX = "siteexpress/demo/beauty/classic/"
SERVICES_CLASSIC_STATIC_PREFIX = "siteexpress/demo/services/classic/"
INSTRUMENT_CLASSIC_STATIC_PREFIX = "siteexpress/demo/instruments/classic/"
CONSTRUCTION_EDITORIAL_STATIC_PREFIX = "siteexpress/demo/construction/editorial-v1/"
FAMILY_DEFAULT_VARIATIONS = {
    "restaurant": "restaurant-classic",
    "beauty": "beauty-classic",
    "services": "services-classic",
}
DEFAULT_VARIATION_MODE = "modern"
DEFAULT_LAYOUT_MODE = "full"
LAYOUT_MODES = {"boxed", "wide", "full"}
DEFAULT_MOTION_MODE = "smooth"
MOTION_MODES = {"minimal", "smooth", "dynamic"}
DEFAULT_DEVICE_MODE = "desktop"
DEVICE_MODES = {"desktop", "tablet", "mobile"}
ASSISTANT_MAX_TURNS_PER_CONVERSATION = 40
DEFAULT_DASHBOARD_SECTION = "preview"
DASHBOARD_SECTIONS = {
    "overview",
    "preview",
    "business",
    "services",
    "images",
    "contact",
    "pages",
    "upgrade",
}
DOMAIN_STATUS_ACTIONS = [
    {"value": DomainRequest.Status.CHECKING, "label": _("Marcar como em verificacao")},
    {"value": DomainRequest.Status.AVAILABLE, "label": _("Marcar como disponivel")},
    {"value": DomainRequest.Status.UNAVAILABLE, "label": _("Marcar como indisponivel")},
    {"value": DomainRequest.Status.WAITING_CUSTOMER, "label": _("Aguardar cliente")},
    {"value": DomainRequest.Status.REGISTERED_MANUAL, "label": _("Marcar como registado manualmente")},
    {"value": DomainRequest.Status.DNS_PENDING, "label": _("Marcar como DNS pendente")},
    {"value": DomainRequest.Status.DNS_CONNECTED, "label": _("Marcar como DNS ligado")},
    {"value": DomainRequest.Status.LIVE, "label": _("Marcar como online")},
    {"value": DomainRequest.Status.CANCELLED, "label": _("Cancelar pedido")},
]
RESTAURANT_KEYWORDS = {
    "restaurant",
    "restaurante",
    "cafe",
    "cafeteria",
    "bistro",
    "bar",
    "pizzeria",
    "takeaway",
    "food",
}
BEAUTY_KEYWORDS = {
    "beauty",
    "beleza",
    "unhas",
    "nails",
    "manicure",
    "pedicure",
    "salão",
    "salao",
    "salon",
    "cabeleireiro",
    "hair",
    "lashes",
    "maquilhagem",
    "makeup",
}
INSTRUMENT_SERVICES_KEYWORDS = {
    "guitar",
    "guitarra",
    "guitarras",
    "instrument repair",
    "instrumento musical",
    "instrumentos musicais",
    "luthier",
    "lutheria",
}
SERVICES_KEYWORDS = {
    "service",
    "services",
    "repair",
    "repairs",
    "mechanic",
    "garage",
    "oficina",
    "limpeza",
    "cleaning",
    "cleaner",
    "painter",
    "painting",
    "pintor",
    "electrician",
    "eletricista",
    "plumber",
    "canalizador",
    "builder",
    "construction",
    "construção",
    "construcao",
    "renovation",
    "renovação",
    "renovacao",
    "locksmith",
    "chaveiro",
    "taxi",
    "transport",
    "transporte",
    "roofing",
    "roof",
    "solar",
    "air conditioning",
    "carpenter",
    "carpentry",
    "carpinteiro",
    "carpintaria",
    "joiner",
    "marceneiro",
    "marcenaria",
    "woodwork",
    "madeira",
    "pedreiro",
    "trolha",
    "obras",
    "remodelações",
    "remodelacoes",
    "jardim",
    "jardinagem",
    *INSTRUMENT_SERVICES_KEYWORDS,
}
AUTO_SERVICES_KEYWORDS = {
    "auto",
    "automóvel",
    "automovel",
    "car repair",
    "garage",
    "mechanic",
    "oficina",
    "repair services",
}
SERVICE_ICON_DEFAULTS = {
    "repairs": "wrench",
    "repair": "wrench",
    "maintenance": "check",
    "emergency support": "clock",
    "installation": "home",
    "inspection": "shield",
    "service area visits": "truck",
}
SERVICE_ICON_LABELS = dict(SERVICE_ICON_CHOICES)
SERVICE_ICON_ORDER_DEFAULTS = [
    "wrench",
    "check",
    "clock",
    "home",
    "shield",
    "truck",
]


def get_restaurant_default_services():
    return [
        {
            "title": _("Chef special"),
            "short_description": _("A signature dish designed to represent the restaurant at a glance."),
            "full_description": _("A plated signature creation that sets the tone for the menu and the dining experience."),
        },
        {
            "title": _("Fresh starters"),
            "short_description": _("Light opening dishes built around seasonal ingredients and shareable plates."),
            "full_description": _("A starter selection focused on freshness, texture, and easy sharing for the table."),
        },
        {
            "title": _("Main dishes"),
            "short_description": _("The core menu selection for lunch and dinner reservations."),
            "full_description": _("A full main-course offering designed for guests who want a complete restaurant experience."),
        },
        {
            "title": _("Desserts and sweets"),
            "short_description": _("A closing menu moment with desserts, sweets, and indulgent extras."),
            "full_description": _("Desserts and sweet pairings that help complete the in-house dining journey."),
        },
        {
            "title": _("Wine and drinks"),
            "short_description": _("Wines, cocktails, and drinks selected to complement the menu."),
            "full_description": _("A beverage selection built to support pairings, aperitifs, and relaxed evenings."),
        },
        {
            "title": _("Group dining"),
            "short_description": _("Menu and table options for birthdays, gatherings, and special occasions."),
            "full_description": _("A dedicated service layer for group bookings, celebrations, and shared dining experiences."),
        },
    ]


def get_beauty_default_services():
    return [
        {
            "title": _("Gel nails"),
            "short_description": _("Long-lasting nails finished with shine, shape, and detail."),
            "full_description": _("A polished gel nail service designed for durability, elegance, and a clean finish."),
        },
        {
            "title": _("Manicure"),
            "short_description": _("Hand and nail care focused on shape, softness, and presentation."),
            "full_description": _("A manicure service that brings together nail care, preparation, and a refined final look."),
        },
        {
            "title": _("Pedicure"),
            "short_description": _("Foot care and finishing designed for comfort and polished results."),
            "full_description": _("A pedicure treatment centered on comfort, care, and a fresh, well-finished presentation."),
        },
        {
            "title": _("Nail art"),
            "short_description": _("Creative designs and visual detail for a more expressive appointment."),
            "full_description": _("A tailored nail art service for clients who want extra design detail, colour, and personality."),
        },
        {
            "title": _("Lashes"),
            "short_description": _("Lash-focused beauty work to enhance definition and everyday confidence."),
            "full_description": _("A lash service built around shape, softness, and a flattering beauty finish."),
        },
        {
            "title": _("Makeup"),
            "short_description": _("Professional beauty styling for events, photos, and special occasions."),
            "full_description": _("A makeup service designed to create a polished result for events, evenings, and celebrations."),
        },
    ]


def get_services_default_services(project=None):
    business_type = ""
    if project and getattr(project, "business_profile", None):
        business_type = (project.business_profile.business_type or "").casefold()

    if any(keyword in business_type for keyword in INSTRUMENT_SERVICES_KEYWORDS):
        return [
            {
                "title": "Reparação e afinação",
                "short_description": "Diagnóstico, reparação e afinação de guitarras para recuperar conforto, som e fiabilidade.",
                "full_description": "Avaliação do instrumento, identificação do problema e execução dos ajustes ou reparações acordados.",
                "icon": "wrench",
            },
            {
                "title": "Personalização",
                "short_description": "Alterações visuais e funcionais para adaptar o instrumento ao estilo de cada músico.",
                "full_description": "Personalização planeada de acordo com o instrumento, o resultado pretendido e a compatibilidade dos componentes.",
                "icon": "spark",
            },
            {
                "title": "Manutenção preventiva",
                "short_description": "Limpeza, verificação e pequenos ajustes para manter a guitarra pronta a tocar.",
                "full_description": "Manutenção regular de peças, afinação e pontos de desgaste para prevenir problemas maiores.",
                "icon": "check",
            },
            {
                "title": "Eletrónica e componentes",
                "short_description": "Verificação e substituição de captadores, ligações, potenciómetros e outros componentes.",
                "full_description": "Intervenções em componentes eletrónicos e acessórios, após confirmação da solução adequada.",
                "icon": "shield",
            },
            {
                "title": "Guitarras e equipamento",
                "short_description": "Apoio na escolha de guitarras, acessórios e equipamento disponível.",
                "full_description": "Informação clara sobre instrumentos e equipamento para ajudar cada cliente a escolher com confiança.",
                "icon": "home",
            },
            {
                "title": "Avaliação e orçamento",
                "short_description": "Primeiro contacto para analisar o instrumento e explicar os próximos passos.",
                "full_description": "Avaliação inicial do trabalho necessário antes de avançar com reparações ou personalizações.",
                "icon": "clock",
            },
        ]

    if any(
        keyword in business_type
        for keyword in (
            "carpenter",
            "carpentry",
            "carpinteiro",
            "carpintaria",
            "joiner",
            "marceneiro",
            "marcenaria",
            "woodwork",
            "madeira",
        )
    ):
        return [
            {
                "title": "Carpintaria por medida",
                "short_description": "Soluções em madeira adaptadas ao espaço, ao estilo e às necessidades de cada cliente.",
                "full_description": "Planeamento e execução de trabalhos de carpintaria por medida, com atenção ao acabamento e à utilização diária.",
                "icon": "wrench",
            },
            {
                "title": "Móveis e armários",
                "short_description": "Móveis, roupeiros e arrumação pensados para aproveitar melhor cada espaço.",
                "full_description": "Criação e montagem de móveis e armários com medidas, organização e acabamentos definidos para cada projeto.",
                "icon": "home",
            },
            {
                "title": "Portas e acabamentos",
                "short_description": "Montagem e afinação de portas, rodapés, painéis e outros acabamentos em madeira.",
                "full_description": "Trabalhos de instalação e acabamento para melhorar a funcionalidade e o aspeto de divisões interiores.",
                "icon": "check",
            },
            {
                "title": "Reparações de madeira",
                "short_description": "Recuperação de peças, móveis e elementos de carpintaria danificados ou desgastados.",
                "full_description": "Avaliação e reparação de elementos em madeira sempre que seja possível recuperar a peça existente.",
                "icon": "wrench",
            },
            {
                "title": "Montagem no local",
                "short_description": "Deslocação e montagem cuidada na casa, loja ou espaço do cliente.",
                "full_description": "Serviço de montagem no local com preparação, ajuste e verificação final do trabalho realizado.",
                "icon": "truck",
            },
            {
                "title": "Avaliação e orçamento",
                "short_description": "Análise do trabalho pretendido e preparação de uma proposta clara antes de começar.",
                "full_description": "Primeiro contacto para compreender medidas, materiais, prioridades e próximos passos do projeto.",
                "icon": "shield",
            },
        ]

    if any(
        keyword in business_type
        for keyword in (
            "builder",
            "construction",
            "construção",
            "construcao",
            "pedreiro",
            "trolha",
            "obras",
            "remodel",
        )
    ):
        return [
            {
                "title": "Obras e remodelações",
                "short_description": "Intervenções em casas e espaços comerciais, de pequenos trabalhos a remodelações completas.",
                "full_description": "Preparação e execução de obras e remodelações com um plano claro para cada fase do trabalho.",
                "icon": "home",
            },
            {
                "title": "Alvenaria e construção",
                "short_description": "Trabalhos de construção, paredes, rebocos e correções necessárias no imóvel.",
                "full_description": "Serviços de alvenaria e construção adaptados às condições e objetivos de cada espaço.",
                "icon": "wrench",
            },
            {
                "title": "Pinturas interiores e exteriores",
                "short_description": "Preparação e pintura de casas, quartos, fachadas e outros espaços.",
                "full_description": "Proteção das áreas, preparação das superfícies e aplicação de pintura com acabamento cuidado.",
                "icon": "spark",
            },
            {
                "title": "Reparações rápidas",
                "short_description": "Resolução de pequenos problemas antes que se transformem em obras maiores.",
                "full_description": "Visita ao local para identificar e executar reparações práticas dentro do âmbito combinado.",
                "icon": "clock",
            },
            {
                "title": "Jardins e exteriores",
                "short_description": "Apoio em manutenção de jardins e melhoria das zonas exteriores da propriedade.",
                "full_description": "Trabalhos exteriores definidos de acordo com o espaço, a época e a manutenção pretendida.",
                "icon": "check",
            },
            {
                "title": "Visita e orçamento",
                "short_description": "Avaliação do local e preparação de uma proposta antes do início dos trabalhos.",
                "full_description": "Primeiro contacto para compreender o serviço, visitar o espaço e combinar os próximos passos.",
                "icon": "truck",
            },
        ]

    return [
        {
            "title": "Reparações",
            "short_description": "Ajuda prática para avarias, danos e problemas comuns do dia a dia.",
            "full_description": "Um serviço de reparação orientado para resolver o problema com clareza e trabalho cuidado.",
            "icon": "wrench",
        },
        {
            "title": "Manutenção",
            "short_description": "Acompanhamento regular para manter equipamentos, imóveis ou sistemas em boas condições.",
            "full_description": "Manutenção pensada para prevenir problemas e prolongar a utilização do que já existe.",
            "icon": "check",
        },
        {
            "title": "Apoio urgente",
            "short_description": "Resposta a situações que precisam de atenção rápida, mediante disponibilidade.",
            "full_description": "Apoio para clientes que precisam de uma resposta rápida e de uma visita de serviço fiável.",
            "icon": "clock",
        },
        {
            "title": "Instalação",
            "short_description": "Montagem e preparação profissional de novos equipamentos ou elementos.",
            "full_description": "Um serviço de instalação com preparação clara, execução cuidada e verificação final.",
            "icon": "home",
        },
        {
            "title": "Avaliação",
            "short_description": "Verificação inicial para perceber o problema e definir os próximos passos.",
            "full_description": "Uma avaliação que ajuda a clarificar o estado atual, o trabalho necessário e as prioridades.",
            "icon": "shield",
        },
        {
            "title": "Deslocações na zona",
            "short_description": "Visitas no local dentro da área principal de serviço e localidades próximas.",
            "full_description": "Deslocações combinadas para avaliar ou executar o serviço diretamente no local do cliente.",
            "icon": "truck",
        },
    ]


def should_expand_services_defaults(raw_services, default_services):
    if not raw_services:
        return True
    if len(raw_services) >= len(default_services):
        return False

    placeholder_titles = {
        "main service",
        "target market",
        "service one",
        "service two",
        "serviço principal",
        "servico principal",
        "atendimento local",
    }
    normalized_titles = {
        (service.get("title") or "").strip().lower()
        for service in raw_services
        if isinstance(service, dict)
    }
    return bool(normalized_titles) and normalized_titles.issubset(placeholder_titles)


def get_default_services_for_project(project):
    variant_context = get_project_variant_context(project)
    if variant_context["is_restaurant_template"]:
        return get_restaurant_default_services()
    if variant_context["is_beauty_template"]:
        return get_beauty_default_services()
    if variant_context["is_services_template"]:
        return get_services_default_services(project)
    return [
        {
            "title": _("Main service"),
            "short_description": _("A clear summary of the main offer."),
            "full_description": _("A fuller explanation of the main offer."),
        },
        {
            "title": _("Secondary service"),
            "short_description": _("Another key service for the project preview."),
            "full_description": _("Another key service for the project preview."),
        },
    ]


def get_service_editor_seed(project, content):
    raw_existing_services = list(content.services_json or []) if content else []
    existing_services = []
    for index, service in enumerate(raw_existing_services, start=1):
        title = service.get("title") or str(_("Service %(number)s") % {"number": index})
        short_description = service.get("short_description") or service.get("description") or ""
        existing_services.append(
            {
                **service,
                "title": title,
                "slug": service.get("slug") or slugify(title) or f"service-{index}",
                "short_description": short_description,
                "description": short_description,
                "full_description": service.get("full_description") or short_description,
                "order": service.get("order", index),
                "is_active": service.get("is_active", True),
                "icon": service.get("icon") or get_service_icon(service.get("title") or title, index),
            }
        )
    default_services = get_default_services_for_project(project)
    seeded_services = list(existing_services)
    index = len(seeded_services)
    while len(seeded_services) < DashboardServicesForm.service_count:
        fallback = default_services[index] if index < len(default_services) else default_services[-1]
        seeded_services.append(
            {
                "title": str(fallback["title"]),
                "slug": slugify(str(fallback["title"])) or f"service-{len(seeded_services) + 1}",
                "short_description": str(fallback["short_description"]),
                "description": str(fallback["short_description"]),
                "full_description": str(fallback["full_description"]),
                "order": len(seeded_services) + 1,
                "is_active": True,
                "icon": fallback.get("icon") or get_service_icon(str(fallback["title"]), len(seeded_services) + 1),
            }
        )
        index += 1
    return seeded_services


def get_service_icon(title, index):
    normalized_title = (title or "").strip().lower()
    for candidate, icon in SERVICE_ICON_DEFAULTS.items():
        if candidate in normalized_title:
            return icon
    if index - 1 < len(SERVICE_ICON_ORDER_DEFAULTS):
        return SERVICE_ICON_ORDER_DEFAULTS[index - 1]
    return "wrench"


def get_service_editor_cards(services, variation, layout, motion=DEFAULT_MOTION_MODE):
    cards = []
    for index, service in enumerate(services[: DashboardServicesForm.service_count], start=1):
        detail_url = ""
        slug = service.get("slug", "")
        if slug:
            detail_url = build_url_with_query(
                reverse("upgrade-placeholder"),
                page="service",
                service=slug,
                variation=variation,
                layout=layout,
                motion=motion,
            )
        cards.append(
            {
                "number": index,
                "slug": slug,
                "detail_url": detail_url,
            }
        )
    return cards


def build_service_editor_rows(services_form, services_editor_cards):
    if not services_form:
        return []

    rows = []
    for card in services_editor_cards:
        number = card["number"]
        rows.append(
            {
                **card,
                "title_field": services_form[f"service_{number}_title"],
                "short_description_field": services_form[f"service_{number}_short_description"],
                "icon_field": services_form[f"service_{number}_icon"],
            }
        )
    return rows


def build_placeholder_content(profile):
    business_name = profile.business_name
    business_type = profile.business_type
    city = profile.target_city or profile.city
    language = profile.target_language or "pt"

    return {
        "language": language,
        "hero_title": _("%(business_name)s — serviços em %(city)s") % {
            "business_name": business_name,
            "city": city,
        },
        "hero_subtitle": _("%(business_type)s com atendimento local, contacto direto e informação clara.") % {
            "business_type": business_type,
        },
        "intro_text": _(
            "Conheça os serviços de %(business_name)s em %(city)s e peça mais informações sem complicações."
        )
        % {
            "business_name": business_name,
            "city": city,
        },
        "services_json": [
            {
                "title": str(_("Serviço principal")),
                "description": business_type,
                "icon": "wrench",
            },
            {
                "title": str(_("Atendimento local")),
                "description": profile.target_audience
                or str(_("Disponível em %(city)s e localidades próximas.") % {"city": city}),
                "icon": "check",
            },
        ],
        "about_text": _(
            "A %(business_name)s apresenta os seus serviços com proximidade, comunicação simples e atenção ao trabalho realizado."
        )
        % {
            "business_name": business_name,
        },
        "cta_text": _("Peça informações sobre o seu projeto"),
        "seo_title": _("%(business_name)s | %(business_type)s in %(city)s")
        % {
            "business_name": business_name,
            "business_type": business_type,
            "city": city,
        },
        "seo_description": _(
            "Conheça os serviços de %(business_name)s e peça informações."
        )
        % {
            "business_name": business_name,
        },
    }


def get_or_create_project_user(request, email, business_name):
    if request.user.is_authenticated:
        return request.user

    User = get_user_model()
    normalized_email = (email or "").strip().lower()
    username_base = normalized_email or business_name.strip().lower().replace(" ", "-")
    username = username_base
    counter = 1

    existing_by_email = User.objects.filter(email__iexact=normalized_email).first() if normalized_email else None
    if existing_by_email:
        return existing_by_email

    while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{username_base}-{counter}"

    user = User.objects.create_user(
        username=username,
        email=normalized_email,
        is_active=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password", "is_active"])
    return user


def get_latest_project_for_user(user):
    return (
        WebsiteProject.objects.select_related(
            "business_profile",
            "starter_page",
            "wordpress_draft",
            "domain_request",
        )
        .prefetch_related("generated_contents")
        .filter(user=user)
        .order_by("-created_at", "-id")
        .first()
    )


def get_project_preview_subdomain(project):
    if not project:
        return ""
    starter_page = getattr(project, "starter_page", None)
    if starter_page and starter_page.slug:
        return starter_page.slug
    return ""


def sync_domain_request_for_project(project):
    if not project:
        return None

    domain_choice = project.domain_choice
    if domain_choice == WebsiteProject.DomainChoice.PREVIEW_ONLY:
        return None

    requested_domain = (
        project.preferred_domain
        if domain_choice == WebsiteProject.DomainChoice.NEED_HELP
        else project.existing_domain
    )
    domain_status = (
        DomainRequest.Status.REQUESTED
        if domain_choice == WebsiteProject.DomainChoice.NEED_HELP
        else DomainRequest.Status.WAITING_CUSTOMER
    )

    domain_request, _ = DomainRequest.objects.update_or_create(
        project=project,
        defaults={
            "user": project.user,
            "business_profile": project.business_profile,
            "requested_domain": requested_domain,
            "alternative_domain_1": project.alternative_domain_1,
            "alternative_domain_2": project.alternative_domain_2,
            "preview_subdomain": get_project_preview_subdomain(project),
            "domain_status": domain_status,
            "registrant_email": project.business_profile.email,
            "registrant_phone": project.business_profile.phone or project.business_profile.whatsapp,
            "registrant_name": project.business_profile.business_name,
        },
    )
    return domain_request


def get_active_partner_by_code(partner_code):
    code = (partner_code or "").strip()
    if not code:
        return None
    return Partner.objects.filter(
        partner_code__iexact=code,
        status=Partner.Status.ACTIVE,
    ).first()


def calculate_trial_end_date(started_at, trial_months):
    if not started_at or trial_months <= 0:
        return None
    return started_at + timedelta(days=30 * trial_months)


def apply_partner_to_project(project, partner):
    if not partner:
        project.partner = None
        project.partner_code_snapshot = ""
        project.is_partner_trial = False
        project.trial_source = WebsiteProject.TrialSource.NONE
        project.trial_months = 0
        project.trial_started_at = None
        project.trial_ends_at = None
        return

    project.partner = partner
    project.partner_code_snapshot = partner.partner_code
    if project.product_type == WebsiteProject.ProductType.STARTER_PAGE_MONTHLY:
        trial_months = max(partner.default_trial_months, 1)
        trial_started_at = timezone.now()
        project.is_partner_trial = True
        project.trial_source = WebsiteProject.TrialSource.PARTNER
        project.trial_months = trial_months
        project.trial_started_at = trial_started_at
        project.trial_ends_at = calculate_trial_end_date(trial_started_at, trial_months)
    else:
        project.is_partner_trial = False
        project.trial_source = WebsiteProject.TrialSource.NONE
        project.trial_months = 0
        project.trial_started_at = None
        project.trial_ends_at = None


def configure_project_product(project):
    if project.product_type == WebsiteProject.ProductType.FULL_WEBSITE_ONETIME:
        project.plan_interest = WebsiteProject.PlanInterest.STANDARD_FULL_WEBSITE
        project.billing_type = WebsiteProject.BillingType.ONE_TIME
        project.price_snapshot = Decimal("225.00")
        project.currency = "EUR"
        project.product_status = WebsiteProject.ProductStatus.PREVIEW_READY
        project.upgrade_status = WebsiteProject.UpgradeStatus.NOT_APPLICABLE
        project.status = WebsiteProject.Status.WORDPRESS_DRAFT_READY
        project.starter_page_enabled = False
        project.wordpress_upgrade_available = True
    else:
        project.plan_interest = WebsiteProject.PlanInterest.STARTER_MONTHLY
        project.billing_type = WebsiteProject.BillingType.MONTHLY
        project.price_snapshot = Decimal("19.95")
        project.currency = "EUR"
        project.product_status = WebsiteProject.ProductStatus.PREVIEW_READY
        project.upgrade_status = WebsiteProject.UpgradeStatus.AVAILABLE
        project.status = WebsiteProject.Status.STARTER_PREVIEW_READY
        project.starter_page_enabled = True
        project.wordpress_upgrade_available = True


def get_partner_referral_status(project):
    now = timezone.now()
    if project.product_status == WebsiteProject.ProductStatus.CANCELLED:
        return PartnerReferral.ReferralStatus.CANCELLED
    if project.product_type == WebsiteProject.ProductType.FULL_WEBSITE_ONETIME:
        if project.product_status == WebsiteProject.ProductStatus.PAYMENT_CONFIRMED:
            return PartnerReferral.ReferralStatus.FULL_WEBSITE_PAID
        return PartnerReferral.ReferralStatus.LEAD_CREATED
    if (
        project.upgrade_status == WebsiteProject.UpgradeStatus.REQUESTED
        or project.product_status == WebsiteProject.ProductStatus.UPGRADE_REQUESTED
    ):
        return PartnerReferral.ReferralStatus.UPGRADE_REQUESTED
    if project.is_partner_trial:
        if project.trial_ends_at and project.trial_ends_at < now:
            return PartnerReferral.ReferralStatus.TRIAL_EXPIRED
        if project.trial_ends_at and project.trial_ends_at <= now + timedelta(days=7):
            return PartnerReferral.ReferralStatus.TRIAL_ENDING_SOON
        return PartnerReferral.ReferralStatus.STARTER_TRIAL_ACTIVE
    return PartnerReferral.ReferralStatus.STARTER_PAID


def get_partner_commission_state(project, existing_referral=None):
    locked_statuses = {
        PartnerReferral.CommissionStatus.REQUESTED,
        PartnerReferral.CommissionStatus.PAID,
        PartnerReferral.CommissionStatus.REJECTED,
    }
    current_status = existing_referral.commission_status if existing_referral else None
    current_available_at = existing_referral.commission_available_at if existing_referral else None
    if current_status in locked_statuses:
        return current_status, current_available_at
    if project.product_status == WebsiteProject.ProductStatus.CANCELLED:
        return PartnerReferral.CommissionStatus.NOT_APPLICABLE, None
    if project.product_type == WebsiteProject.ProductType.FULL_WEBSITE_ONETIME:
        if project.product_status == WebsiteProject.ProductStatus.PAYMENT_CONFIRMED:
            return (
                PartnerReferral.CommissionStatus.AVAILABLE,
                current_available_at or timezone.now(),
            )
        return PartnerReferral.CommissionStatus.PENDING, current_available_at
    if (
        project.upgrade_status == WebsiteProject.UpgradeStatus.REQUESTED
        or project.product_status == WebsiteProject.ProductStatus.UPGRADE_REQUESTED
    ):
        return PartnerReferral.CommissionStatus.PENDING, current_available_at
    return PartnerReferral.CommissionStatus.NOT_APPLICABLE, None


def sync_partner_referral_for_project(project):
    partner = project.partner
    if not partner:
        return None

    existing_referral = getattr(project, "partner_referral", None)
    referral_status = get_partner_referral_status(project)
    commission_status, commission_available_at = get_partner_commission_state(
        project,
        existing_referral=existing_referral,
    )
    customer_name = project.business_profile.business_name
    customer_phone = project.business_profile.phone or project.business_profile.whatsapp
    defaults = {
        "partner": partner,
        "user": project.user,
        "business_profile": project.business_profile,
        "customer_name": customer_name,
        "customer_email": project.business_profile.email or project.user.email,
        "customer_phone": customer_phone,
        "product_type_snapshot": project.product_type,
        "trial_months": project.trial_months,
        "trial_started_at": project.trial_started_at,
        "trial_ends_at": project.trial_ends_at,
        "referral_status": referral_status,
        "commission_status": commission_status,
        "commission_amount": partner.commission_amount,
        "commission_available_at": commission_available_at,
    }
    referral, _ = PartnerReferral.objects.update_or_create(
        project=project,
        defaults=defaults,
    )
    return referral


def ensure_product_records(project, business_profile):
    placeholder_content = build_placeholder_content(business_profile)
    GeneratedContent.objects.create(project=project, **placeholder_content)

    if project.product_type == WebsiteProject.ProductType.STARTER_PAGE_MONTHLY:
        StarterPage.objects.create(project=project, is_preview=True, is_active=True)
        WordPressSiteDraft.objects.create(
            project=project,
            status=WordPressSiteDraft.Status.WAITING_FOR_UPGRADE,
            notes=_("Rascunho WordPress preparado para futuro upgrade. A ligacao real ao WordPress ainda nao esta ativa."),
        )
    else:
        WordPressSiteDraft.objects.create(
            project=project,
            status=WordPressSiteDraft.Status.CONTENT_READY,
            notes=_("Rascunho WordPress preparado a partir dos dados do onboarding. A ligacao real ao WordPress ainda nao esta ativa."),
        )


def ensure_wordpress_draft_for_project(project):
    if getattr(project, "wordpress_draft", None):
        return project.wordpress_draft
    return WordPressSiteDraft.objects.create(
        project=project,
        status=WordPressSiteDraft.Status.WAITING_FOR_UPGRADE,
        notes=_("Pedido de upgrade recebido. Preparacao WordPress pendente."),
    )


def build_product_summary(project):
    if not project:
        return {}

    status_labels = {
        WebsiteProject.ProductStatus.SELECTED: "Selecionado",
        WebsiteProject.ProductStatus.GENERATING: "Em preparacao",
        WebsiteProject.ProductStatus.PREVIEW_READY: "Preview pronto",
        WebsiteProject.ProductStatus.CUSTOMER_REVIEWING: "Em revisao pelo cliente",
        WebsiteProject.ProductStatus.UPGRADE_AVAILABLE: "Upgrade disponivel",
        WebsiteProject.ProductStatus.UPGRADE_REQUESTED: "Pedido de upgrade",
        WebsiteProject.ProductStatus.PAYMENT_PENDING: "Pagamento pendente",
        WebsiteProject.ProductStatus.PAYMENT_CONFIRMED: "Pagamento confirmado",
        WebsiteProject.ProductStatus.PUBLISHING_PENDING: "Publicacao pendente",
        WebsiteProject.ProductStatus.PUBLISHED: "Publicado",
        WebsiteProject.ProductStatus.CANCELLED: "Cancelado",
    }
    billing_labels = {
        WebsiteProject.BillingType.MONTHLY: "Mensal",
        WebsiteProject.BillingType.ONE_TIME: "Pagamento unico",
    }

    if project.product_type == WebsiteProject.ProductType.FULL_WEBSITE_ONETIME:
        return {
            "title_pt": "Website Completo",
            "description_pt": "Um website WordPress completo, com mais paginas, melhor estrutura e preparado para crescer.",
            "price_pt": "€225 + IVA",
            "status_pt": status_labels.get(project.product_status, project.get_product_status_display()),
            "review_note_pt": "A area de revisao do cliente fica preparada enquanto a ponte WordPress real nao estiver ligada.",
            "show_upgrade_card": False,
            "preview_label_pt": "Preview completo",
            "billing_pt": billing_labels.get(project.billing_type, project.get_billing_type_display()),
        }

    return {
        "title_pt": "Página Express",
        "description_pt": "Uma pagina rapida para comecar, ideal para ter presenca online e partilhar com clientes.",
        "price_pt": "€19,95/mês + IVA",
        "status_pt": status_labels.get(project.product_status, project.get_product_status_display()),
        "review_note_pt": "A pagina express ja usa o fluxo atual de Starter Page e pode evoluir para um website completo.",
        "show_upgrade_card": True,
        "preview_label_pt": "Preview da pagina express",
        "billing_pt": billing_labels.get(project.billing_type, project.get_billing_type_display()),
    }


def build_partner_trial_summary(project):
    if not project or not project.partner or not project.is_partner_trial:
        return {}

    status_pt = "Periodo experimental ativo"
    now = timezone.now()
    if project.trial_ends_at and project.trial_ends_at < now:
        status_pt = "Periodo experimental expirado"
    elif project.trial_ends_at and project.trial_ends_at <= now + timedelta(days=7):
        status_pt = "Periodo experimental a terminar"

    return {
        "show": True,
        "status_pt": status_pt,
        "partner_name": project.partner.company_name or project.partner.name,
        "trial_end_label_pt": (
            project.trial_ends_at.strftime("%d/%m/%Y")
            if project.trial_ends_at
            else ""
        ),
    }


def get_domain_status_badge(domain_request):
    if not domain_request:
        return {
            "label": _("Apenas preview"),
            "status": WebsiteProject.DomainChoice.PREVIEW_ONLY,
            "message_pt": "Ainda nao existe um pedido de dominio para este projeto. Pode continuar a usar o preview enquanto decide o dominio final.",
        }

    status_messages = {
        DomainRequest.Status.NOT_REQUESTED: ("Sem pedido de domínio", "Ainda nao existe um pedido de dominio para este projeto."),
        DomainRequest.Status.REQUESTED: "Recebemos o seu pedido de dominio e vamos analisar as opcoes.",
        DomainRequest.Status.CHECKING: "Estamos a verificar a disponibilidade do dominio pedido.",
        DomainRequest.Status.AVAILABLE: "Boas noticias: o dominio parece estar disponivel.",
        DomainRequest.Status.UNAVAILABLE: "O dominio pedido nao esta disponivel. Vamos precisar de uma alternativa.",
        DomainRequest.Status.WAITING_CUSTOMER: "Estamos a aguardar informacao sua para continuar com o dominio.",
        DomainRequest.Status.REGISTERED_MANUAL: "O dominio ja foi registado manualmente pela equipa.",
        DomainRequest.Status.DNS_PENDING: "O dominio foi preparado e estamos a aguardar a configuracao DNS.",
        DomainRequest.Status.DNS_CONNECTED: "O DNS ja esta ligado. Falta apenas a propagacao final.",
        DomainRequest.Status.LIVE: "O dominio ja esta ligado e o site esta online.",
        DomainRequest.Status.CANCELLED: "O pedido de dominio foi cancelado.",
    }
    status_labels = {
        DomainRequest.Status.REQUESTED: "Pedido recebido",
        DomainRequest.Status.CHECKING: "Em verificacao",
        DomainRequest.Status.AVAILABLE: "Disponivel",
        DomainRequest.Status.UNAVAILABLE: "Indisponivel",
        DomainRequest.Status.WAITING_CUSTOMER: "A aguardar cliente",
        DomainRequest.Status.REGISTERED_MANUAL: "Registado manualmente",
        DomainRequest.Status.DNS_PENDING: "DNS pendente",
        DomainRequest.Status.DNS_CONNECTED: "DNS ligado",
        DomainRequest.Status.LIVE: "Online",
        DomainRequest.Status.CANCELLED: "Cancelado",
        DomainRequest.Status.NOT_REQUESTED: "Sem pedido de domínio",
    }
    return {
        "label": status_labels.get(domain_request.domain_status, domain_request.get_domain_status_display()),
        "status": domain_request.domain_status,
        "message_pt": status_messages.get(
            domain_request.domain_status,
            "Estado de dominio atualizado.",
        )[1] if isinstance(status_messages.get(domain_request.domain_status), tuple) else status_messages.get(
            domain_request.domain_status,
            "Estado de dominio atualizado.",
        ),
    }


def build_domain_dns_placeholder(domain_request):
    target = domain_request.preview_subdomain or "preview-pendente"
    return "\n".join(
        [
            f"Dominio pedido: {domain_request.requested_domain or '-'}",
            f"Preview subdominio: {target}",
            "A @ -> [IP do servidor por confirmar]",
            "CNAME www -> @",
        ]
    )


def get_domain_request_cards():
    domain_requests = (
        DomainRequest.objects.select_related("user", "business_profile", "project", "project__wordpress_draft")
        .order_by("-created_at")
    )
    cards = []
    for domain_request in domain_requests:
        project = domain_request.project
        profile = domain_request.business_profile
        user = domain_request.user
        customer_name = (
            user.get_full_name().strip()
            if user and user.get_full_name().strip()
            else (profile.business_name if profile else (user.username if user else ""))
        )
        cards.append(
            {
                "object": domain_request,
                "business_name": profile.business_name if profile else "",
                "customer_name": customer_name,
                "customer_email": (profile.email if profile else "") or (user.email if user else ""),
                "customer_phone": profile.phone if profile else "",
                "customer_whatsapp": profile.whatsapp if profile else "",
                "preview_subdomain": domain_request.preview_subdomain,
                "project_status": project.get_status_display() if project else "",
                "wordpress_status": (
                    project.wordpress_draft.get_status_display()
                    if project and getattr(project, "wordpress_draft", None)
                    else ""
                ),
                "copy_customer_details": "\n".join(
                    [
                        f"Negocio: {profile.business_name if profile else '-'}",
                        f"Cliente: {customer_name or '-'}",
                        f"Email: {((profile.email if profile else '') or (user.email if user else '')) or '-'}",
                        f"Telefone: {(profile.phone if profile else '') or '-'}",
                        f"WhatsApp: {(profile.whatsapp if profile else '') or '-'}",
                    ]
                ),
                "copy_dns_records": build_domain_dns_placeholder(domain_request),
            }
        )
    return cards


def get_partner_dashboard_cards(partner, request):
    referrals = (
        PartnerReferral.objects.select_related("business_profile", "project", "project__business_profile")
        .filter(partner=partner)
        .order_by("-created_at")
    )
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    available_referrals = referrals.filter(
        commission_status=PartnerReferral.CommissionStatus.AVAILABLE
    )
    available_total = available_referrals.aggregate(total=Sum("commission_amount")).get("total") or Decimal("0.00")
    onboarding_link = request.build_absolute_uri(
        reverse("partner-onboarding", args=[partner.partner_code])
    )
    recent_referrals = []
    for referral in referrals[:12]:
        project = referral.project
        recent_referrals.append(
            {
                "object": referral,
                "business_name": (
                    referral.business_profile.business_name
                    if referral.business_profile
                    else referral.customer_name
                ),
                "product_label": (
                    project.get_product_type_display()
                    if project
                    else referral.get_product_type_snapshot_display()
                    if hasattr(referral, "get_product_type_snapshot_display")
                    else referral.product_type_snapshot
                ),
                "upgrade_status": project.get_upgrade_status_display() if project else "-",
                "trial_end_date": referral.trial_ends_at,
            }
        )
    return {
        "referrals": referrals,
        "referrals_this_month": referrals.filter(created_at__gte=month_start).count(),
        "active_trial_pages": referrals.filter(
            referral_status__in=[
                PartnerReferral.ReferralStatus.STARTER_TRIAL_ACTIVE,
                PartnerReferral.ReferralStatus.TRIAL_ENDING_SOON,
            ]
        ).count(),
        "upgrade_requests": referrals.filter(
            referral_status=PartnerReferral.ReferralStatus.UPGRADE_REQUESTED
        ).count(),
        "full_website_paid": referrals.filter(
            referral_status=PartnerReferral.ReferralStatus.FULL_WEBSITE_PAID
        ).count(),
        "commission_available_total": available_total,
        "commission_available_count": available_referrals.count(),
        "commission_requested_count": referrals.filter(
            commission_status=PartnerReferral.CommissionStatus.REQUESTED
        ).count(),
        "commission_paid_count": referrals.filter(
            commission_status=PartnerReferral.CommissionStatus.PAID
        ).count(),
        "recent_referrals": recent_referrals,
        "onboarding_link": onboarding_link,
    }


def get_project_brand_context(project):
    variant_context = get_project_variant_context(project)
    if variant_context["is_beauty_template"]:
        default_primary, default_secondary, default_accent = (
            "#c45b8d",
            "#33242d",
            "#f8e9f1",
        )
    elif variant_context["is_instrument_template"]:
        default_primary, default_secondary, default_accent = (
            "#b88a3b",
            "#21150f",
            "#f2e5cb",
        )
    elif variant_context["is_construction_template"]:
        default_primary, default_secondary, default_accent = (
            "#f2a000",
            "#101827",
            "#fff0d1",
        )
    elif variant_context["is_restaurant_template"]:
        default_primary, default_secondary, default_accent = (
            "#9b4937",
            "#251713",
            "#f3dfcf",
        )
    elif variant_context["is_services_template"]:
        default_primary, default_secondary, default_accent = (
            "#c95a10",
            "#172033",
            "#fff0e5",
        )
    else:
        default_primary, default_secondary, default_accent = (
            "#8f1f1f",
            "#172033",
            "#f3e8d8",
        )
    colors = project.business_profile.preferred_colors or []
    primary = colors[0] if len(colors) > 0 else default_primary
    secondary = colors[1] if len(colors) > 1 else default_secondary
    accent = colors[2] if len(colors) > 2 else default_accent
    return {
        "brand_primary": primary,
        "brand_secondary": secondary,
        "brand_accent": accent,
        "uses_custom_brand_colors": bool(colors),
    }


def get_project_variant_context(project):
    business_type = (project.business_profile.business_type or "").strip().lower()
    service_location = (
        project.business_profile.city
        or project.business_profile.region
        or project.business_profile.country
        or "Portugal"
    )
    is_restaurant = any(keyword in business_type for keyword in RESTAURANT_KEYWORDS)
    is_beauty = not is_restaurant and any(keyword in business_type for keyword in BEAUTY_KEYWORDS)
    is_services = (
        not is_restaurant
        and not is_beauty
        and any(keyword in business_type for keyword in SERVICES_KEYWORDS)
    )
    is_instrument = is_services and any(
        keyword in business_type for keyword in INSTRUMENT_SERVICES_KEYWORDS
    )
    is_carpentry = is_services and any(
        keyword in business_type
        for keyword in (
            "carpenter",
            "carpentry",
            "carpinteiro",
            "carpintaria",
            "joiner",
            "marceneiro",
            "marcenaria",
            "woodwork",
            "madeira",
        )
    )
    is_construction = is_services and any(
        keyword in business_type
        for keyword in (
            "builder",
            "construction",
            "construção",
            "construcao",
            "pedreiro",
            "trolha",
            "obras",
            "remodel",
        )
    )
    template_family = "restaurant" if is_restaurant else "beauty" if is_beauty else "services" if is_services else ""
    demo_images = {}
    if template_family == "restaurant":
        demo_images = get_restaurant_classic_image_map()
    elif template_family == "beauty":
        demo_images = get_beauty_classic_image_map()
    elif template_family == "services" and is_instrument:
        demo_images = get_instrument_classic_image_map()
    elif template_family == "services" and is_construction:
        demo_images = get_construction_editorial_image_map()
    elif template_family == "services" and any(
        keyword in business_type for keyword in AUTO_SERVICES_KEYWORDS
    ):
        demo_images = get_services_classic_image_map()
    services_hero_title = f"Serviços de confiança em {service_location}"
    services_hero_subtitle = (
        "Trabalho rápido, claro e profissional para clientes locais que procuram ajuda fiável e comunicação direta."
    )
    services_intro_title = "Ajuda clara para trabalhos locais e necessidades de serviço contínuas"
    services_intro_text = (
        f"Serviço claro, comunicação fiável e apoio prático para clientes em {service_location}."
    )
    if is_instrument:
        services_hero_title = f"Reparação e personalização de guitarras em {service_location}"
        services_hero_subtitle = (
            "Afinação, manutenção, personalização e equipamento para músicos que querem tirar mais do seu instrumento."
        )
        services_intro_title = "Cuidado técnico para cada instrumento"
        services_intro_text = (
            "Cada guitarra é avaliada antes do trabalho para identificar o problema e explicar a solução com clareza."
        )
    elif is_carpentry:
        services_hero_title = f"Trabalhos de carpintaria em {service_location} e arredores"
        services_hero_subtitle = (
            "Soluções em madeira, montagem, reparações e trabalhos por medida com atenção a cada acabamento."
        )
        services_intro_title = "Carpintaria pensada para o seu espaço"
        services_intro_text = (
            "Cada trabalho começa por perceber as medidas, o uso pretendido e o acabamento que melhor se adapta ao cliente."
        )
    elif is_construction:
        services_hero_title = f"Obras e remodelações em {service_location} e arredores"
        services_hero_subtitle = (
            "Construção, pinturas, reparações e melhorias exteriores com acompanhamento simples e direto."
        )
        services_intro_title = "Do pequeno arranjo à remodelação"
        services_intro_text = (
            "O trabalho é avaliado no local para combinar prioridades, materiais e os próximos passos antes de começar."
        )
    industry_preset_label = "Geral"
    if is_restaurant:
        industry_preset_label = "Restauração"
    elif is_beauty:
        industry_preset_label = "Beleza e bem-estar"
    elif is_instrument:
        industry_preset_label = "Instrumentos e música"
    elif is_construction:
        industry_preset_label = "Obras e remodelações"
    elif is_carpentry:
        industry_preset_label = "Serviços locais"
    elif is_services:
        industry_preset_label = "Serviços locais"

    context = {
        "template_family": template_family,
        "is_restaurant_template": is_restaurant,
        "is_beauty_template": is_beauty,
        "is_services_template": is_services,
        "is_instrument_template": is_instrument,
        "is_carpentry_template": is_carpentry,
        "is_construction_template": is_construction,
        "services_hero_title": services_hero_title,
        "services_hero_subtitle": services_hero_subtitle,
        "services_intro_title": services_intro_title,
        "services_intro_text": services_intro_text,
        "industry_preset_label": industry_preset_label,
        "demo_images": demo_images,
    }
    context["restaurant_images"] = demo_images if is_restaurant else {}
    context["beauty_images"] = demo_images if is_beauty else {}
    context["services_images"] = demo_images if is_services else {}
    return context


def get_preview_variation(request, project):
    base_context = get_project_variant_context(project)
    template_family = base_context["template_family"]
    if not template_family:
        return "", get_variation_mode(request)

    requested = (request.GET.get("variation") or "").strip().lower()
    variation_mode = requested if requested in {"classic", "modern"} else DEFAULT_VARIATION_MODE
    return f"{template_family}-{variation_mode}", variation_mode


def get_layout_mode(request):
    requested = (request.GET.get("layout") or "").strip().lower()
    if requested not in LAYOUT_MODES:
        return DEFAULT_LAYOUT_MODE
    return requested


def get_variation_mode(request):
    requested = (request.GET.get("variation") or "").strip().lower()
    return requested if requested in {"classic", "modern"} else DEFAULT_VARIATION_MODE


def get_motion_mode(request):
    requested = (request.GET.get("motion") or "").strip().lower()
    return requested if requested in MOTION_MODES else DEFAULT_MOTION_MODE


def get_dashboard_section(request):
    requested = (request.GET.get("section") or "").strip().lower()
    if requested not in DASHBOARD_SECTIONS:
        return DEFAULT_DASHBOARD_SECTION
    return requested


def get_device_mode(request):
    requested = (request.GET.get("device") or "").strip().lower()
    if requested not in DEVICE_MODES:
        return DEFAULT_DEVICE_MODE
    return requested


def build_url_with_query(path, **params):
    filtered = {key: value for key, value in params.items() if value not in (None, "", [])}
    query = urlencode(filtered)
    return f"{path}?{query}" if query else path


def get_restaurant_classic_image_map():
    return {
        "hero": f"{RESTAURANT_CLASSIC_STATIC_PREFIX}hero.jpg",
        "featured": [
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}featured-1.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}featured-2.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}featured-3.jpg",
        ],
        "menu": [
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}menu-1.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}menu-2.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}menu-3.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}menu-4.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}menu-5.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}menu-6.jpg",
        ],
        "about": f"{RESTAURANT_CLASSIC_STATIC_PREFIX}about.jpg",
        "cta": f"{RESTAURANT_CLASSIC_STATIC_PREFIX}cta.jpg",
        "location": f"{RESTAURANT_CLASSIC_STATIC_PREFIX}location.jpg",
        "gallery": [
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}gallery-1.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}gallery-2.jpg",
            f"{RESTAURANT_CLASSIC_STATIC_PREFIX}gallery-3.jpg",
        ],
    }


def get_beauty_classic_image_map():
    return {
        "hero": f"{BEAUTY_CLASSIC_STATIC_PREFIX}hero.jpg",
        "featured": [
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}featured-1.jpg",
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}featured-2.jpg",
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}featured-3.jpg",
        ],
        "services": [
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}service-1.jpg",
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}service-2.jpg",
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}service-3.jpg",
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}service-4.jpg",
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}service-5.jpg",
            f"{BEAUTY_CLASSIC_STATIC_PREFIX}service-6.jpg",
        ],
        "about": f"{BEAUTY_CLASSIC_STATIC_PREFIX}about.jpg",
        "cta": f"{BEAUTY_CLASSIC_STATIC_PREFIX}cta.jpg",
        "location": f"{BEAUTY_CLASSIC_STATIC_PREFIX}location.jpg",
    }


def get_services_classic_image_map():
    return {
        "hero": f"{SERVICES_CLASSIC_STATIC_PREFIX}hero.jpg",
        "featured": [
            f"{SERVICES_CLASSIC_STATIC_PREFIX}featured-1.jpg",
            f"{SERVICES_CLASSIC_STATIC_PREFIX}featured-2.jpg",
            f"{SERVICES_CLASSIC_STATIC_PREFIX}featured-3.jpg",
        ],
        "services": [
            f"{SERVICES_CLASSIC_STATIC_PREFIX}service-1.jpg",
            f"{SERVICES_CLASSIC_STATIC_PREFIX}service-2.jpg",
            f"{SERVICES_CLASSIC_STATIC_PREFIX}service-3.jpg",
            f"{SERVICES_CLASSIC_STATIC_PREFIX}service-4.jpg",
            f"{SERVICES_CLASSIC_STATIC_PREFIX}service-5.jpg",
            f"{SERVICES_CLASSIC_STATIC_PREFIX}service-6.jpg",
        ],
        "about": f"{SERVICES_CLASSIC_STATIC_PREFIX}about.jpg",
        "cta": f"{SERVICES_CLASSIC_STATIC_PREFIX}cta.jpg",
        "location": f"{SERVICES_CLASSIC_STATIC_PREFIX}location.jpg",
    }


def get_instrument_classic_image_map():
    return {
        "hero": f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}hero-1.webp",
        "hero_slides": [
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}hero-1.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}hero-2.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}hero-3.webp",
        ],
        "featured": [
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-1.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-3.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-2.webp",
        ],
        "services": [
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-1.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-3.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-4.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-2.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-5.webp",
            f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}service-6.webp",
        ],
        "about": f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}about.webp",
        "cta": f"{INSTRUMENT_CLASSIC_STATIC_PREFIX}hero-2.webp",
    }


def get_construction_editorial_image_map():
    return {
        "hero": f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}hero-1.jpg",
        "hero_slides": [
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}hero-1.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}hero-2.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}hero-3.jpg",
        ],
        "featured": [
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}featured-1.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}featured-2.jpg",
        ],
        "services": [
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}service-1.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}service-2.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}service-3.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}service-4.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}service-5.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}service-6.jpg",
        ],
        "about": f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}about.jpg",
        "portfolio": [
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}portfolio-1.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}portfolio-2.jpg",
            f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}portfolio-3.jpg",
        ],
        "cta": f"{CONSTRUCTION_EDITORIAL_STATIC_PREFIX}hero-2.jpg",
    }


def build_preview_extras(project, services, variant_context):
    hero_slides = []
    slide_images = variant_context.get("demo_images", {}).get("hero_slides", [])
    if slide_images:
        slide_copy = [
            {
                "title": variant_context["services_hero_title"],
                "subtitle": variant_context["services_hero_subtitle"],
            }
        ]
        slide_copy.extend(
            {
                "title": service["title"],
                "subtitle": service["short_description"],
            }
            for service in services[:2]
        )
        while len(slide_copy) < len(slide_images):
            slide_copy.append(
                {
                    "title": variant_context["services_intro_title"],
                    "subtitle": variant_context["services_intro_text"],
                }
            )
        hero_slides = [
            {
                **slide_copy[index],
                "image_path": image_path,
            }
            for index, image_path in enumerate(slide_images)
        ]

    profile = project.business_profile
    location_parts = [
        profile.address,
        profile.city,
        profile.region,
        profile.country,
    ]
    location_query = ", ".join(part.strip() for part in location_parts if part and part.strip())
    if not location_query:
        location_query = "Portugal"
    whatsapp_digits = re.sub(r"\D", "", profile.whatsapp or "")
    return {
        "hero_slides": hero_slides,
        "google_maps_embed_url": f"https://www.google.com/maps?{urlencode({'q': location_query, 'output': 'embed'})}",
        "google_maps_link_url": f"https://www.google.com/maps/search/?{urlencode({'api': 1, 'query': location_query})}",
        "whatsapp_link_url": f"https://wa.me/{whatsapp_digits}" if whatsapp_digits else "",
    }


def normalize_project_services(project, content):
    raw_services = content.services_json if content else []
    normalized = []
    restaurant_defaults = get_restaurant_default_services()
    is_restaurant = get_project_variant_context(project)["is_restaurant_template"]
    is_beauty = get_project_variant_context(project)["is_beauty_template"]
    is_services = get_project_variant_context(project)["is_services_template"]
    beauty_defaults = get_beauty_default_services()
    services_defaults = get_services_default_services(project)
    variant_context = get_project_variant_context(project)
    demo_images = variant_context["demo_images"]
    service_images = demo_images.get("menu", []) if is_restaurant else demo_images.get("services", [])

    if is_services and should_expand_services_defaults(raw_services, services_defaults):
        raw_services = [
            {
                **default_service,
                "title": str(default_service["title"]),
                "short_description": str(default_service["short_description"]),
                "description": str(default_service["short_description"]),
                "full_description": str(default_service["full_description"]),
                "icon": default_service.get("icon") or get_service_icon(str(default_service["title"]), index),
                "order": index,
                "is_active": True,
            }
            for index, default_service in enumerate(services_defaults, start=1)
        ]

    for index, service in enumerate(raw_services, start=1):
        title = (service.get("title") or _("Service %(number)s") % {"number": index}).strip()
        short_description = service.get("short_description") or service.get("description") or _("Service summary pending.")
        full_description = service.get("full_description") or short_description or _("Service detail pending.")
        if is_restaurant and title.lower() in {
            "main service",
            "target market",
            "service one",
            "service two",
        }:
            fallback = restaurant_defaults[index - 1] if index <= len(restaurant_defaults) else restaurant_defaults[-1]
            title = str(fallback["title"])
            short_description = str(fallback["short_description"])
            full_description = str(fallback["full_description"])
        if is_beauty and title.lower() in {
            "main service",
            "target market",
            "service one",
            "service two",
        }:
            fallback = beauty_defaults[index - 1] if index <= len(beauty_defaults) else beauty_defaults[-1]
            title = str(fallback["title"])
            short_description = str(fallback["short_description"])
            full_description = str(fallback["full_description"])
        if is_services and title.lower() in {
            "main service",
            "target market",
            "service one",
            "service two",
            "serviço principal",
            "servico principal",
            "atendimento local",
        }:
            fallback = services_defaults[index - 1] if index <= len(services_defaults) else services_defaults[-1]
            title = str(fallback["title"])
            short_description = str(fallback["short_description"])
            full_description = str(fallback["full_description"])
        slug = service.get("slug") or slugify(title) or f"service-{index}"
        normalized.append(
            {
                "title": title,
                "slug": slug,
                "short_description": short_description,
                "full_description": full_description,
                "icon": service.get("icon") or get_service_icon(title, index),
                "icon_label": str(SERVICE_ICON_LABELS.get(service.get("icon") or get_service_icon(title, index), _("Service icon"))),
                "image_placeholder": service.get("image_placeholder")
                or (
                    _("Food image placeholder")
                    if is_restaurant
                    else _("Beauty image placeholder")
                    if is_beauty
                    else _("Service image placeholder")
                    if is_services
                    else _("Image coming soon")
                ),
                "image_path": (
                    service.get("image_path")
                    or (service_images[index - 1] if index <= len(service_images) else "")
                ),
                "order": service.get("order", index),
                "is_active": service.get("is_active", True),
            }
        )

    normalized.sort(key=lambda item: item["order"])
    return [service for service in normalized if service["is_active"]]


def build_plan_render_context(project, services, *, is_full_plan=None):
    if is_full_plan is None:
        is_full_plan = bool(project.wordpress_upgrade_available)
    visible_limit = None if is_full_plan else STARTER_SERVICES_LIMIT
    rendered_services = []
    variant_context = get_project_variant_context(project)
    featured_images = variant_context["demo_images"].get("featured", [])
    is_services_template = variant_context["is_services_template"]

    for index, service in enumerate(services, start=1):
        hidden_by_plan = visible_limit is not None and index > visible_limit
        render_status = "hidden_by_plan" if hidden_by_plan else "visible"
        rendered_services.append(
            {
                **service,
                "render_status": render_status,
                "is_visible": not hidden_by_plan,
            }
        )

    visible_services = [service for service in rendered_services if service["is_visible"]]
    hidden_services = [service for service in rendered_services if not service["is_visible"]]

    if is_services_template:
        homepage_visible_services = (
            visible_services[:SERVICES_HOME_VISIBLE_LIMIT] if is_full_plan else visible_services
        )
        featured_items = homepage_visible_services[:SERVICES_HOME_FEATURED_LIMIT]
        remaining_services = homepage_visible_services[len(featured_items):]
    else:
        if is_full_plan:
            featured_items = visible_services[:FULL_FEATURED_LIMIT]
        else:
            featured_items = visible_services[:STARTER_FEATURED_LIMIT]
        remaining_services = visible_services

    featured_items = [
        {
                **item,
                "featured_image_path": (
                    featured_images[index] if index < len(featured_images) else item.get("image_path", "")
                ),
            }
        for index, item in enumerate(featured_items)
    ]

    return {
        "is_full_plan": is_full_plan,
        "visible_services": visible_services,
        "hidden_services": hidden_services,
        "featured_items": featured_items,
        "featured_services": featured_items,
        "remaining_services": remaining_services,
        "remaining_home_services": remaining_services,
    }


def siteexpress_landing_view(request):
    language_code = (translation.get_language() or settings.LANGUAGE_CODE or "pt")[:2]
    language_links = [
        {"code": "pt", "label": "PT", "url": "/pt/", "active": language_code == "pt"},
        {"code": "es", "label": "ES", "url": "/es/", "active": language_code == "es"},
        {"code": "en", "label": "EN", "url": "/en/", "active": language_code == "en"},
    ]

    if language_code != "pt":
        return render(
            request,
            "onboarding/siteexpress_language_placeholder.html",
            {
                "language_code": language_code,
                "language_links": language_links,
            },
        )

    return render(
        request,
        "onboarding/siteexpress_landing.html",
        {
            "language_code": language_code,
            "language_links": language_links,
        },
    )


def _siteexpress_public_language_context():
    language_code = (translation.get_language() or settings.LANGUAGE_CODE or "pt")[:2]
    return language_code, [
        {"code": "pt", "label": "PT", "url": "/pt/", "active": language_code == "pt"},
        {"code": "es", "label": "ES", "url": "/es/", "active": language_code == "es"},
        {"code": "en", "label": "EN", "url": "/en/", "active": language_code == "en"},
    ]


def _resolve_public_page_routes(page):
    page = deepcopy(page)
    for prefix in ("primary", "secondary", "cta"):
        route = page.get(f"{prefix}_route")
        if route:
            page[f"{prefix}_url"] = reverse(route)
    for offer in page.get("offers", []):
        if offer.get("route"):
            offer["url"] = reverse(offer["route"])
    return page


def public_page_view(request, page_key):
    language_code, language_links = _siteexpress_public_language_context()
    if language_code != "pt":
        return render(
            request,
            "onboarding/siteexpress_language_placeholder.html",
            {"language_code": language_code, "language_links": language_links},
        )

    page = _resolve_public_page_routes(PUBLIC_PAGES[page_key])
    return render(
        request,
        "onboarding/public_page.html",
        {"page": page, "language_code": language_code, "language_links": language_links},
    )


def pricing_view(request):
    language_code, language_links = _siteexpress_public_language_context()
    if language_code != "pt":
        return render(
            request,
            "onboarding/siteexpress_language_placeholder.html",
            {"language_code": language_code, "language_links": language_links},
        )

    page = _resolve_public_page_routes(PRICING_PAGE)
    return render(
        request,
        "onboarding/public_pricing.html",
        {"page": page, "language_code": language_code, "language_links": language_links},
    )


def legal_page_view(request, page_key):
    language_code, language_links = _siteexpress_public_language_context()
    if language_code != "pt":
        return render(
            request,
            "onboarding/siteexpress_language_placeholder.html",
            {"language_code": language_code, "language_links": language_links},
        )

    return render(
        request,
        "onboarding/public_legal.html",
        {
            "page": LEGAL_PAGES[page_key],
            "language_code": language_code,
            "language_links": language_links,
        },
    )


def _assistant_conversation_from_payload(request, payload):
    public_id = (payload.get("conversation_id") or "").strip()
    conversation = None
    if public_id:
        try:
            conversation = AssistantConversation.objects.filter(public_id=public_id).first()
        except (TypeError, ValueError, ValidationError):
            conversation = None

    if conversation is None:
        conversation = AssistantConversation.objects.create(
            user=request.user if request.user.is_authenticated else None,
            page_path=(payload.get("page_path") or "")[:500],
            page_title=(payload.get("page_title") or "")[:255],
            model=settings.SITEEXPRESS_ASSISTANT_MODEL,
        )
    else:
        update_fields = []
        if request.user.is_authenticated and conversation.user_id != request.user.id:
            conversation.user = request.user
            update_fields.append("user")
        page_path = (payload.get("page_path") or "")[:500]
        page_title = (payload.get("page_title") or "")[:255]
        if page_path and conversation.page_path != page_path:
            conversation.page_path = page_path
            update_fields.append("page_path")
        if page_title and conversation.page_title != page_title:
            conversation.page_title = page_title
            update_fields.append("page_title")
        if update_fields:
            update_fields.append("updated_at")
            conversation.save(update_fields=update_fields)
    return conversation


@require_POST
def assistant_chat_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Pedido inválido."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Pedido inválido."}, status=400)

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Escreva uma pergunta antes de enviar."}, status=400)
    if len(message) > settings.SITEEXPRESS_ASSISTANT_MAX_MESSAGE_LENGTH:
        return JsonResponse(
            {"error": f"A mensagem pode ter no máximo {settings.SITEEXPRESS_ASSISTANT_MAX_MESSAGE_LENGTH} caracteres."},
            status=400,
        )

    conversation = _assistant_conversation_from_payload(request, payload)
    if conversation.turn_count >= ASSISTANT_MAX_TURNS_PER_CONVERSATION:
        return JsonResponse(
            {"error": "Esta conversa atingiu o limite. Envie novamente para começar uma conversa nova."},
            status=429,
        )

    AssistantMessage.objects.create(
        conversation=conversation,
        role=AssistantMessage.Role.USER,
        content=message,
        mode=conversation.mode,
        model=conversation.model,
    )

    recent_messages = list(
        conversation.messages.order_by("-created_at", "-id")[
            : settings.SITEEXPRESS_ASSISTANT_MAX_HISTORY_MESSAGES
        ]
    )
    history = [
        {"role": item.role, "content": item.content}
        for item in reversed(recent_messages)
    ]

    pending_build = AssistantSiteBuild.objects.filter(
        conversation=conversation,
        status=AssistantSiteBuild.Status.DRAFT,
    ).first()
    normalized_message = " ".join(message.casefold().strip(" .,!?").split())
    confirmation_words = {
        "sim", "sim pode", "sim por favor", "pode", "pode ser", "quero", "quero ver",
        "mostra", "mostre", "avance", "avança", "vamos ver", "claro",
    }
    preview_terms = ("preview", "pré-visualização", "pre-visualização", "exemplo", "ver o site", "ver a página")
    confirmed_preview = normalized_message in confirmation_words or normalized_message.startswith("sim") or any(
        term in normalized_message for term in preview_terms
    )

    if pending_build and confirmed_preview:
        pending_build.status = AssistantSiteBuild.Status.READY
        pending_build.save(update_fields=["status", "updated_at"])
        result = generate_demo_reply(message, model="siteexpress-preview")
        result["text"] = "Sim. Vou abrir a proposta e construí-la consigo agora 😊"
    else:
        try:
            result = generate_assistant_reply(history)
        except Exception:
            logger.exception("SiteExpress assistant request failed")
            result = generate_demo_reply(message, model="siteexpress-demo-fallback")

    reply = (result.get("text") or "").strip()
    if not reply:
        return JsonResponse(
            {"error": "O assistente não conseguiu preparar uma resposta. Tente novamente."},
            status=503,
        )

    AssistantMessage.objects.create(
        conversation=conversation,
        role=AssistantMessage.Role.ASSISTANT,
        content=reply,
        response_id=result.get("response_id", ""),
        model=result.get("model", ""),
        mode=result.get("mode", AssistantConversation.Mode.DEMO),
        input_tokens=result.get("input_tokens", 0),
        cached_input_tokens=result.get("cached_input_tokens", 0),
        output_tokens=result.get("output_tokens", 0),
    )
    conversation.turn_count += 1
    conversation.mode = result.get("mode", AssistantConversation.Mode.DEMO)
    conversation.model = result.get("model", "")
    conversation.input_tokens += result.get("input_tokens", 0)
    conversation.cached_input_tokens += result.get("cached_input_tokens", 0)
    conversation.output_tokens += result.get("output_tokens", 0)
    conversation.last_message_at = timezone.now()
    conversation.save(
        update_fields=[
            "turn_count",
            "mode",
            "model",
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "last_message_at",
            "updated_at",
        ]
    )

    build_payload = None
    if pending_build and confirmed_preview:
        allowed_builds = request.session.get("assistant_site_builds", [])
        request.session["assistant_site_builds"] = [*allowed_builds[-4:], str(pending_build.public_id)]
        build_payload = {
            "url": reverse("assistant-site-build", args=[pending_build.public_id]),
            "auto_start": True,
        }
    elif not AssistantSiteBuild.objects.filter(conversation=conversation).exists():
        try:
            build_analysis = analyze_assistant_build(
                [*history, {"role": "assistant", "content": reply}]
            )
        except Exception:
            logger.exception("SiteExpress assistant build analysis failed")
            build_analysis = {"ready": False}
        if build_analysis.get("ready"):
            build = AssistantSiteBuild.objects.create(
                conversation=conversation,
                status=(
                    AssistantSiteBuild.Status.READY
                    if confirmed_preview
                    else AssistantSiteBuild.Status.DRAFT
                ),
                category=build_analysis["category"],
                business_name=build_analysis["business_name"],
                business_type=build_analysis["business_type"],
                location=build_analysis["location"],
                content={
                    "headline": build_analysis["headline"],
                    "intro": build_analysis["intro"],
                    "services": build_analysis["services"],
                    "about": build_analysis["about"],
                    "cta": build_analysis["cta"],
                },
            )
            if confirmed_preview:
                allowed_builds = request.session.get("assistant_site_builds", [])
                request.session["assistant_site_builds"] = [*allowed_builds[-4:], str(build.public_id)]
                reply = "Sim. Vou abrir a proposta e construí-la consigo agora 😊"
                last_reply = AssistantMessage.objects.filter(conversation=conversation).order_by("-id").first()
                last_reply.content = reply
                last_reply.save(update_fields=["content"])
                build_payload = {
                    "url": reverse("assistant-site-build", args=[build.public_id]),
                    "auto_start": True,
                }
            else:
                reply = (
                    "Já tenho informação suficiente para preparar uma primeira proposta visual da sua "
                    "Página Express. Quer vê-la a ser construída agora?"
                )
                last_reply = AssistantMessage.objects.filter(conversation=conversation).order_by("-id").first()
                last_reply.content = reply
                last_reply.save(update_fields=["content"])
                build_payload = {"offered": True, "auto_start": False}

    return JsonResponse(
        {
            "reply": reply,
            "conversation_id": str(conversation.public_id),
            "mode": conversation.mode,
            "model": conversation.model,
            "usage": {
                "input_tokens": result.get("input_tokens", 0),
                "cached_input_tokens": result.get("cached_input_tokens", 0),
                "output_tokens": result.get("output_tokens", 0),
            },
            "site_build": build_payload,
        }
    )


def _assistant_build_for_session(request, public_id):
    allowed = {str(item) for item in request.session.get("assistant_site_builds", [])}
    if str(public_id) not in allowed:
        return None
    return AssistantSiteBuild.objects.filter(
        public_id=public_id,
        status=AssistantSiteBuild.Status.READY,
    ).first()


@require_GET
def assistant_site_build_view(request, public_id):
    build = _assistant_build_for_session(request, public_id)
    if build is None:
        return render(request, "onboarding/assistant_build_unavailable.html", status=404)
    return render(
        request,
        "onboarding/assistant_site_build.html",
        {
            "build": build,
            "preview_url": reverse("assistant-site-build-preview", args=[build.public_id]),
        },
    )


@require_GET
def assistant_site_build_preview_view(request, public_id):
    build = _assistant_build_for_session(request, public_id)
    if build is None:
        return render(request, "onboarding/assistant_build_unavailable.html", status=404)
    try:
        stage = max(0, min(int(request.GET.get("stage", 6)), 6))
    except (TypeError, ValueError):
        stage = 6
    return render(
        request,
        "onboarding/assistant_site_build_preview.html",
        {"build": build, "content": build.content or {}, "stage": stage},
    )


@require_POST
def assistant_site_build_revision_view(request, public_id):
    build = _assistant_build_for_session(request, public_id)
    if build is None:
        return JsonResponse({"error": "Esta pré-visualização já não está disponível."}, status=404)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Pedido inválido."}, status=400)
    message = " ".join(str(payload.get("message") or "").split())
    if not message:
        return JsonResponse({"error": "Explique o que gostaria de alterar."}, status=400)
    normalized_message = message.casefold()
    expanded_content_terms = (
        "mais conteúdo", "mais conteudo", "mais informação", "mais informacao",
        "mais detalhes", "mais texto", "dizer mais", "falar mais", "explicar mais",
    )
    if any(term in normalized_message for term in expanded_content_terms):
        return JsonResponse({
            "reply": (
                "Esta é uma primeira pré-visualização, por isso mantive o conteúdo mais curto. "
                "Depois da ativação, o seu assistente poderá ajudar a desenvolver essa parte e "
                "adicionar mais conteúdo consigo."
            ),
            "preview_url": "",
        })
    current = {
        "business_name": build.business_name,
        "business_type": build.business_type,
        "location": build.location,
        **(build.content or {}),
    }
    try:
        revised = revise_assistant_build(current, message)
    except Exception:
        logger.exception("SiteExpress assistant preview revision failed")
        return JsonResponse({"error": "Não consegui aplicar essa alteração. Tente descrevê-la de outra forma."}, status=503)
    build.business_name = revised["business_name"]
    build.business_type = revised["business_type"]
    build.location = revised["location"]
    build.content = {
        "headline": revised["headline"], "intro": revised["intro"],
        "services": revised["services"], "about": revised["about"], "cta": revised["cta"],
    }
    build.save(update_fields=["business_name", "business_type", "location", "content", "updated_at"])
    return JsonResponse({
        "reply": "Alterei apenas o que pediu. Veja agora a nova versão — está mais próxima da sua ideia?",
        "preview_url": f"{reverse('assistant-site-build-preview', args=[build.public_id])}?stage=6",
    })


@staff_member_required
def assistant_usage_view(request):
    since = timezone.now() - timedelta(days=30)
    recent = AssistantConversation.objects.filter(created_at__gte=since)
    totals = recent.aggregate(
        conversations=Count("id"),
        turns=Sum("turn_count"),
        input_tokens=Sum("input_tokens"),
        cached_input_tokens=Sum("cached_input_tokens"),
        output_tokens=Sum("output_tokens"),
    )
    input_tokens = totals["input_tokens"] or 0
    cached_input_tokens = totals["cached_input_tokens"] or 0
    output_tokens = totals["output_tokens"] or 0
    uncached_input_tokens = max(input_tokens - cached_input_tokens, 0)
    estimated_cost = (
        Decimal(uncached_input_tokens) * Decimal(settings.SITEEXPRESS_ASSISTANT_INPUT_USD_PER_MILLION)
        + Decimal(cached_input_tokens)
        * Decimal(settings.SITEEXPRESS_ASSISTANT_CACHED_INPUT_USD_PER_MILLION)
        + Decimal(output_tokens) * Decimal(settings.SITEEXPRESS_ASSISTANT_OUTPUT_USD_PER_MILLION)
    ) / Decimal("1000000")
    configured_mode = settings.SITEEXPRESS_ASSISTANT_MODE
    effective_mode = (
        "openai"
        if configured_mode == "openai" or (configured_mode == "auto" and settings.OPENAI_API_KEY)
        else "demo"
    )
    return render(
        request,
        "onboarding/assistant_usage.html",
        {
            "totals": {
                "conversations": totals["conversations"] or 0,
                "turns": totals["turns"] or 0,
                "input_tokens": input_tokens,
                "cached_input_tokens": cached_input_tokens,
                "output_tokens": output_tokens,
            },
            "estimated_cost": estimated_cost.quantize(Decimal("0.0001")),
            "effective_mode": effective_mode,
            "configured_model": settings.SITEEXPRESS_ASSISTANT_MODEL,
            "api_key_configured": bool(settings.OPENAI_API_KEY),
            "conversations": AssistantConversation.objects.select_related("user")[:50],
        },
    )


def build_account_setup_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    with translation.override(translation.get_language()):
        path = reverse("account-setup", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


def send_account_setup_notice(request, user, setup_link):
    message = _(
        "SiteExpress account setup for %(email)s: %(link)s"
    ) % {
        "email": user.email or user.username,
        "link": setup_link,
    }
    logger.info(message)
    if settings.DEBUG:
        print(message)


def onboarding_view(request, partner_code=None):
    locked_partner = None
    partner_code_locked = ""
    partner_banner = ""
    if partner_code:
        locked_partner = get_object_or_404(
            Partner,
            partner_code__iexact=partner_code,
            status=Partner.Status.ACTIVE,
        )
        partner_code_locked = locked_partner.partner_code
        partner_banner = "Este pedido foi iniciado atraves de um parceiro SiteExpress."

    if request.method == "POST":
        profile_form = BusinessProfileForm(request.POST, request.FILES)
        project_form = WebsiteProjectForm(request.POST, partner_locked_code=partner_code_locked)

        if profile_form.is_valid() and project_form.is_valid():
            with transaction.atomic():
                user = get_or_create_project_user(
                    request,
                    profile_form.cleaned_data["email"],
                    profile_form.cleaned_data["business_name"],
                )

                business_profile = profile_form.save(commit=False)
                business_profile.user = user
                business_profile.save()

                project = project_form.save(commit=False)
                project.user = user
                project.business_profile = business_profile
                partner = locked_partner or get_active_partner_by_code(
                    project_form.cleaned_data.get("partner_code")
                )
                configure_project_product(project)
                apply_partner_to_project(project, partner)
                project.save()

                ensure_product_records(project, business_profile)
                sync_domain_request_for_project(project)
                sync_partner_referral_for_project(project)

            setup_link = build_account_setup_link(request, user)
            send_account_setup_notice(request, user, setup_link)
            request.session["onboarding_setup_email"] = user.email or user.username
            request.session["onboarding_setup_link"] = setup_link if settings.DEBUG else ""
            request.session["onboarding_setup_required"] = not user.has_usable_password()

            return redirect("success")
    else:
        profile_form = BusinessProfileForm(
            initial={
                "target_language": "pt",
                "target_country": "Portugal",
                "country": "Portugal",
            }
        )
        project_form = WebsiteProjectForm(
            initial={
                "product_type": WebsiteProject.ProductType.STARTER_PAGE_MONTHLY,
                "partner_code": partner_code_locked,
            },
            partner_locked_code=partner_code_locked,
        )

    return render(
        request,
        "onboarding/onboarding_form.html",
        {
            "profile_form": profile_form,
            "project_form": project_form,
            "locked_partner": locked_partner,
            "partner_banner": partner_banner,
        },
    )


def success_view(request):
    return render(
        request,
        "onboarding/success.html",
        {
            "setup_email": request.session.get("onboarding_setup_email", ""),
            "setup_link": request.session.get("onboarding_setup_link", ""),
            "setup_required": request.session.get("onboarding_setup_required", True),
            "debug_mode": settings.DEBUG,
        },
    )


def account_setup_entry_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    setup_link = request.session.get("onboarding_setup_link", "")
    if setup_link:
        return redirect(setup_link)
    return render(
        request,
        "onboarding/account_setup_invalid.html",
        {"missing_token": True},
        status=400,
    )


def account_setup_view(request, uidb64, token):
    user = None
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if not user or not default_token_generator.check_token(user, token):
        return render(
            request,
            "onboarding/account_setup_invalid.html",
            status=400,
        )

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])

            authenticated_user = authenticate(
                request,
                username=user.username,
                password=form.cleaned_data["new_password1"],
            )
            if authenticated_user is not None:
                login(request, authenticated_user)
                return redirect("dashboard")
            return redirect("login")
    else:
        form = SetPasswordForm(user)

    return render(
        request,
        "onboarding/account_setup_form.html",
        {
            "form": form,
            "account_email": user.email or user.username,
        },
    )


@login_required
def dashboard_view(request):
    project = get_latest_project_for_user(request.user)
    content = project.generated_contents.first() if project else None
    domain_request = getattr(project, "domain_request", None) if project else None
    domain_status_badge = get_domain_status_badge(domain_request)
    product_summary = build_product_summary(project)
    partner_trial_summary = build_partner_trial_summary(project)
    variant_context = get_project_variant_context(project) if project else {}
    selected_layout = get_layout_mode(request)
    selected_variation = get_variation_mode(request)
    selected_variation_label = {
        "classic": "Soft Studio",
        "modern": "Editorial Full Width",
    }[selected_variation]
    selected_motion = get_motion_mode(request)
    selected_device = get_device_mode(request)
    active_section = get_dashboard_section(request)
    requested_preview = (request.GET.get("preview") or "").strip().lower()
    preview_was_explicit = requested_preview in {"starter", "full"}
    starter_available = bool(project and getattr(project, "starter_page", None))
    selected_preview = requested_preview if requested_preview in {"starter", "full"} else "starter"
    if selected_preview == "starter" and not starter_available:
        selected_preview = "full"

    starter_preview_url = ""
    full_preview_url = ""
    iframe_preview_url = ""
    services_page_preview_url = ""
    dashboard_query = {
        "section": active_section,
        "preview": selected_preview,
        "variation": selected_variation,
        "layout": selected_layout,
        "motion": selected_motion,
        "device": selected_device,
    }
    dashboard_return_url = build_url_with_query(reverse("dashboard"), **dashboard_query)
    business_form = None
    contact_form = None
    services_form = None
    services_editor_cards = []
    services_editor_rows = []

    if project:
        service_seed = get_service_editor_seed(project, content) if content else []
        services_editor_cards = get_service_editor_cards(
            service_seed,
            selected_variation,
            selected_layout,
            selected_motion,
        )
        if request.method == "POST":
            form_type = (request.POST.get("form_type") or "").strip().lower()
            if form_type == "business":
                business_form = DashboardBusinessInfoForm(
                    request.POST,
                    instance=project.business_profile,
                    prefix="business",
                )
                contact_form = DashboardContactDetailsForm(
                    instance=project.business_profile,
                    prefix="contact",
                )
                services_form = DashboardServicesForm(
                    services=service_seed,
                    prefix="services",
                )
                if business_form.is_valid():
                    business_form.save()
                    return redirect(dashboard_return_url)
            elif form_type == "contact":
                business_form = DashboardBusinessInfoForm(
                    instance=project.business_profile,
                    prefix="business",
                )
                contact_form = DashboardContactDetailsForm(
                    request.POST,
                    instance=project.business_profile,
                    prefix="contact",
                )
                services_form = DashboardServicesForm(
                    services=service_seed,
                    prefix="services",
                )
                if contact_form.is_valid():
                    contact_form.save()
                    return redirect(dashboard_return_url)
            elif form_type == "services" and content:
                business_form = DashboardBusinessInfoForm(
                    instance=project.business_profile,
                    prefix="business",
                )
                contact_form = DashboardContactDetailsForm(
                    instance=project.business_profile,
                    prefix="contact",
                )
                services_form = DashboardServicesForm(
                    request.POST,
                    services=service_seed,
                    prefix="services",
                )
                if services_form.is_valid():
                    content.services_json = services_form.cleaned_services(service_seed)
                    content.save(update_fields=["services_json"])
                    return redirect(dashboard_return_url)
            elif form_type == "upgrade-request":
                project.upgrade_status = WebsiteProject.UpgradeStatus.REQUESTED
                project.product_status = WebsiteProject.ProductStatus.UPGRADE_REQUESTED
                project.status = WebsiteProject.Status.UPGRADED
                project.save(update_fields=["upgrade_status", "product_status", "status", "updated_at"])
                ensure_wordpress_draft_for_project(project)
                sync_partner_referral_for_project(project)
                return redirect(f"{dashboard_return_url}&upgrade_requested=1")

        if business_form is None:
            business_form = DashboardBusinessInfoForm(
                instance=project.business_profile,
                prefix="business",
            )
        if contact_form is None:
            contact_form = DashboardContactDetailsForm(
                instance=project.business_profile,
                prefix="contact",
            )
        if services_form is None and content:
            services_form = DashboardServicesForm(
                services=service_seed,
                prefix="services",
            )
        services_editor_rows = build_service_editor_rows(services_form, services_editor_cards)

    if project:
        full_preview_url = build_url_with_query(
            reverse("upgrade-placeholder"),
            variation=selected_variation,
            layout=selected_layout,
            motion=selected_motion,
        )
        services_page_preview_url = build_url_with_query(
            reverse("upgrade-placeholder"),
            page="services",
            variation=selected_variation,
            layout=selected_layout,
            motion=selected_motion,
            embed=1,
        )
        if starter_available:
            starter_preview_url = build_url_with_query(
                reverse("starter-preview", args=[project.starter_page.slug]),
                variation=selected_variation,
                layout=selected_layout,
                motion=selected_motion,
                embed=1,
            )
        full_preview_url = build_url_with_query(
            reverse("upgrade-placeholder"),
            variation=selected_variation,
            layout=selected_layout,
            motion=selected_motion,
            embed=1,
        )
        if active_section == "services" and not (
            preview_was_explicit and selected_preview == "starter" and starter_preview_url
        ):
            iframe_preview_url = services_page_preview_url
        else:
            iframe_preview_url = (
                starter_preview_url
                if selected_preview == "starter" and starter_preview_url
                else full_preview_url
            )

    dashboard_base_query = {
        "section": active_section,
        "preview": selected_preview,
        "variation": selected_variation,
        "layout": selected_layout,
        "motion": selected_motion,
        "device": selected_device,
    }

    def dashboard_control_url(**overrides):
        return build_url_with_query(
            reverse("dashboard"),
            **{**dashboard_base_query, **overrides},
        )

    dashboard_control_urls = {
        "sections": {
            section: dashboard_control_url(section=section)
            for section in DASHBOARD_SECTIONS
        },
        "preview": {
            "starter": dashboard_control_url(preview="starter"),
            "full": dashboard_control_url(preview="full"),
        },
        "variation": {
            "classic": dashboard_control_url(variation="classic"),
            "modern": dashboard_control_url(variation="modern"),
        },
        "layout": {
            "boxed": dashboard_control_url(layout="boxed"),
            "wide": dashboard_control_url(layout="wide"),
            "full": dashboard_control_url(layout="full"),
        },
        "motion": {
            "minimal": dashboard_control_url(motion="minimal"),
            "smooth": dashboard_control_url(motion="smooth"),
            "dynamic": dashboard_control_url(motion="dynamic"),
        },
        "device": {
            "desktop": dashboard_control_url(device="desktop"),
            "tablet": dashboard_control_url(device="tablet"),
            "mobile": dashboard_control_url(device="mobile"),
        },
    }
    show_product_preview_action = active_section in {"preview", "upgrade"}
    return render(
        request,
        "onboarding/dashboard.html",
        {
            "project": project,
            "content": content,
            "active_section": active_section,
            "selected_preview": selected_preview,
            "selected_variation": selected_variation,
            "selected_variation_label": selected_variation_label,
            "selected_layout": selected_layout,
            "selected_motion": selected_motion,
            "selected_device": selected_device,
            "starter_preview_url": starter_preview_url,
            "full_preview_url": full_preview_url,
            "services_page_preview_url": services_page_preview_url,
            "iframe_preview_url": iframe_preview_url,
            "dashboard_control_urls": dashboard_control_urls,
            "dashboard_return_url": dashboard_return_url,
            "business_form": business_form,
            "contact_form": contact_form,
            "services_form": services_form,
            "services_editor_cards": services_editor_cards,
            "services_editor_rows": services_editor_rows,
            "domain_request": domain_request,
            "domain_status_badge": domain_status_badge,
            "product_summary": product_summary,
            "partner_trial_summary": partner_trial_summary,
            "upgrade_requested_flag": request.GET.get("upgrade_requested") == "1",
            "show_product_preview_action": show_product_preview_action,
            **variant_context,
        },
    )


@staff_member_required
def domain_requests_view(request):
    if request.method == "POST":
        domain_request = get_object_or_404(DomainRequest, pk=request.POST.get("domain_request_id"))
        requested_status = (request.POST.get("domain_status") or "").strip()
        valid_statuses = {choice for choice, _ in DomainRequest.Status.choices}
        if requested_status in valid_statuses:
            domain_request.domain_status = requested_status
            if requested_status == DomainRequest.Status.REGISTERED_MANUAL and not domain_request.registered_at:
                domain_request.registered_at = timezone.now()
            if requested_status == DomainRequest.Status.DNS_CONNECTED and not domain_request.dns_connected_at:
                domain_request.dns_connected_at = timezone.now()
            domain_request.save(
                update_fields=["domain_status", "registered_at", "dns_connected_at", "updated_at"]
            )
        return redirect("domain-requests")

    return render(
        request,
        "onboarding/domain_requests.html",
        {
            "domain_request_cards": get_domain_request_cards(),
            "domain_status_actions": DOMAIN_STATUS_ACTIONS,
        },
    )


@staff_member_required
def partner_dashboard_view(request, partner_code):
    partner = get_object_or_404(Partner, partner_code__iexact=partner_code)
    if request.method == "POST":
        form_type = (request.POST.get("form_type") or "").strip().lower()
        if form_type == "request-payout":
            now = timezone.now()
            PartnerReferral.objects.filter(
                partner=partner,
                commission_status=PartnerReferral.CommissionStatus.AVAILABLE,
            ).update(
                commission_status=PartnerReferral.CommissionStatus.REQUESTED,
                updated_at=now,
            )
            return redirect(f"{reverse('partner-dashboard', args=[partner.partner_code])}?payout_requested=1")

    dashboard_data = get_partner_dashboard_cards(partner, request)
    return render(
        request,
        "onboarding/partner_dashboard.html",
        {
            "partner": partner,
            "payout_requested_flag": request.GET.get("payout_requested") == "1",
            **dashboard_data,
        },
    )


@login_required
def starter_page_preview_view(request, slug):
    project = get_object_or_404(
        WebsiteProject.objects.select_related("business_profile", "starter_page"),
        user=request.user,
        starter_page__slug=slug,
        starter_page__is_active=True,
    )
    content = project.generated_contents.first()
    services = normalize_project_services(project, content)
    plan_context = build_plan_render_context(project, services, is_full_plan=False)
    variant_context = get_project_variant_context(project)
    preview_extras = build_preview_extras(project, services, variant_context)
    preview_variation, variation_mode = get_preview_variation(request, project)
    if settings.DEBUG and variant_context.get("is_services_template"):
        logger.debug(
            "Services starter preview counts project=%s normalized=%s featured=%s remaining=%s",
            project.id,
            len(services),
            len(plan_context.get("featured_services", [])),
            len(plan_context.get("remaining_home_services", [])),
        )
    return render(
        request,
        "onboarding/starter_preview.html",
        {
            "project": project,
            "content": content,
            "services": services,
            "preview_variation": preview_variation,
            "variation_mode": variation_mode,
            "layout_mode": get_layout_mode(request),
            "motion_mode": get_motion_mode(request),
            "embed_mode": request.GET.get("embed") == "1",
            **plan_context,
            **variant_context,
            **preview_extras,
            **get_project_brand_context(project),
        },
    )


@login_required
def upgrade_placeholder_view(request):
    project = get_latest_project_for_user(request.user)
    content = project.generated_contents.first() if project else None
    services = normalize_project_services(project, content) if project and content else []
    plan_context = (
        build_plan_render_context(project, services, is_full_plan=bool(project.wordpress_upgrade_available))
        if project and content
        else {}
    )
    active_page = request.GET.get("page", "home")
    if active_page not in {"home", "services", "service", "about", "contact"}:
        active_page = "home"
    requested_service_slug = request.GET.get("service", "")
    active_service = next((service for service in services if service["slug"] == requested_service_slug), None)
    if active_page == "service" and not active_service:
        active_page = "services"
    full_pages_unlocked = bool(plan_context.get("is_full_plan")) if project else False
    variant_context = get_project_variant_context(project) if project else {}
    preview_extras = build_preview_extras(project, services, variant_context) if project else {}
    preview_variation, variation_mode = get_preview_variation(request, project) if project else ("", "classic")
    if active_page != "home" and not full_pages_unlocked:
        active_page = "home"
    if settings.DEBUG and variant_context.get("is_services_template") and project:
        logger.debug(
            "Services full preview counts project=%s normalized=%s featured=%s remaining=%s",
            project.id,
            len(services),
            len(plan_context.get("featured_services", [])),
            len(plan_context.get("remaining_home_services", [])),
        )
    return render(
        request,
        "onboarding/upgrade_placeholder.html",
        {
            "project": project,
            "content": content,
            "active_page": active_page,
            "services": services,
            "active_service": active_service,
            "full_pages_unlocked": full_pages_unlocked,
            "preview_variation": preview_variation,
            "variation_mode": variation_mode,
            "layout_mode": get_layout_mode(request),
            "motion_mode": get_motion_mode(request),
            "embed_mode": request.GET.get("embed") == "1",
            **plan_context,
            **variant_context,
            **preview_extras,
            **(get_project_brand_context(project) if project else {}),
        },
    )
