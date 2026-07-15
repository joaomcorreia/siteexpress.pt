import json

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from django.utils.translation import override

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


class OnboardingFlowTests(TestCase):
    def create_partner(self, **overrides):
        return Partner.objects.create(
            name=overrides.get("name", "Joao Parceiro"),
            company_name=overrides.get("company_name", "Print Partner"),
            email=overrides.get("email", "partner@example.com"),
            phone=overrides.get("phone", "+351930000000"),
            whatsapp_phone=overrides.get("whatsapp_phone", "+351930000000"),
            partner_code=overrides.get("partner_code", "PARCEIRO1"),
            status=overrides.get("status", Partner.Status.ACTIVE),
            default_trial_months=overrides.get("default_trial_months", 1),
            commission_amount=overrides.get("commission_amount", "20.00"),
            commission_currency=overrides.get("commission_currency", "EUR"),
            notes=overrides.get("notes", ""),
        )

    def onboarding_payload(self, **overrides):
        payload = {
            "business_name": "Loja Exemplo",
            "business_type": "Retail",
            "address": "Rua Central 10",
            "city": "Porto",
            "region": "Porto",
            "country": "Portugal",
            "email": "cliente@example.com",
            "phone": "+351910000000",
            "whatsapp": "+351910000000",
            "preferred_colors": "#112233, #445566",
            "target_country": "Portugal",
            "target_city": "Porto",
            "target_region": "Norte",
            "target_audience": "Families and tourists",
            "target_language": "pt",
            "product_type": WebsiteProject.ProductType.STARTER_PAGE_MONTHLY,
        }
        payload.update(overrides)
        return payload

    def create_project_for_user(self, user, **overrides):
        profile = BusinessProfile.objects.create(
            user=user,
            business_name=overrides.get("business_name", "Empresa Teste"),
            business_type=overrides.get("business_type", "Company"),
            address=overrides.get("address", "Rua A"),
            city=overrides.get("city", "Lisboa"),
            region=overrides.get("region", "Lisboa"),
            country=overrides.get("country", "Portugal"),
            email=overrides.get("email", "owner@example.com"),
            phone=overrides.get("phone", "+351911111111"),
            whatsapp=overrides.get("whatsapp", "+351911111111"),
            logo=overrides.get("logo"),
            preferred_colors=overrides.get("preferred_colors", ["#111111"]),
            target_country=overrides.get("target_country", "Portugal"),
            target_city=overrides.get("target_city", "Lisboa"),
            target_region=overrides.get("target_region", "Lisboa"),
            target_audience=overrides.get("target_audience", "Local clients"),
            target_language=overrides.get("target_language", "pt"),
        )
        project = WebsiteProject.objects.create(
            user=user,
            business_profile=profile,
            product_type=overrides.get("product_type", WebsiteProject.ProductType.STARTER_PAGE_MONTHLY),
            price_snapshot=overrides.get("price_snapshot", "19.95"),
            currency=overrides.get("currency", "EUR"),
            billing_type=overrides.get("billing_type", WebsiteProject.BillingType.MONTHLY),
            product_status=overrides.get("product_status", WebsiteProject.ProductStatus.PREVIEW_READY),
            upgrade_status=overrides.get("upgrade_status", WebsiteProject.UpgradeStatus.AVAILABLE),
            plan_interest=overrides.get("plan_interest", WebsiteProject.PlanInterest.STARTER_MONTHLY),
            status=overrides.get("status", WebsiteProject.Status.STARTER_PREVIEW_READY),
            starter_page_enabled=overrides.get("starter_page_enabled", True),
            wordpress_upgrade_available=True,
            partner=overrides.get("partner"),
            partner_code_snapshot=overrides.get("partner_code_snapshot", ""),
            is_partner_trial=overrides.get("is_partner_trial", False),
            trial_source=overrides.get("trial_source", WebsiteProject.TrialSource.NONE),
            domain_choice=overrides.get("domain_choice", WebsiteProject.DomainChoice.PREVIEW_ONLY),
            preferred_domain=overrides.get("preferred_domain", ""),
            existing_domain=overrides.get("existing_domain", ""),
            alternative_domain_1=overrides.get("alternative_domain_1", ""),
            alternative_domain_2=overrides.get("alternative_domain_2", ""),
            trial_months=overrides.get("trial_months", 0),
            trial_started_at=overrides.get("trial_started_at"),
            trial_ends_at=overrides.get("trial_ends_at"),
        )
        GeneratedContent.objects.create(
            project=project,
            language=profile.target_language,
            hero_title=overrides.get("hero_title", f"Hero {profile.business_name}"),
            hero_subtitle="Subtitle",
            intro_text="Intro",
            services_json=overrides.get(
                "services_json",
                [
                    {
                        "title": "Service One",
                        "description": "Short description one",
                        "full_description": "Full description one",
                    },
                    {
                        "title": "Service Two",
                        "description": "Short description two",
                        "full_description": "Full description two",
                    },
                ],
            ),
            about_text="About",
            cta_text="CTA",
            seo_title="SEO",
            seo_description="Description",
        )
        if overrides.get("create_starter_page", True):
            StarterPage.objects.create(project=project, is_preview=True, is_active=True)
        WordPressSiteDraft.objects.create(
            project=project,
            status=overrides.get("wordpress_status", WordPressSiteDraft.Status.WAITING_FOR_UPGRADE),
            notes=overrides.get("wordpress_notes", "Draft ready"),
        )
        if overrides.get("create_partner_referral", False) and project.partner:
            PartnerReferral.objects.create(
                partner=project.partner,
                user=user,
                business_profile=profile,
                project=project,
                customer_name=profile.business_name,
                customer_email=profile.email,
                customer_phone=profile.phone,
                product_type_snapshot=project.product_type,
                trial_months=project.trial_months,
                trial_started_at=project.trial_started_at,
                trial_ends_at=project.trial_ends_at,
                referral_status=overrides.get(
                    "referral_status",
                    PartnerReferral.ReferralStatus.STARTER_TRIAL_ACTIVE,
                ),
                commission_status=overrides.get(
                    "commission_status",
                    PartnerReferral.CommissionStatus.NOT_APPLICABLE,
                ),
                commission_amount=overrides.get("referral_commission_amount", "20.00"),
            )
        return project

    def test_onboarding_page_loads_for_anonymous_user(self):
        response = self.client.get(reverse("onboarding"))
        self.assertEqual(response.status_code, 200)

    def test_language_prefixed_onboarding_routes_work(self):
        with override("en"):
            response = self.client.get("/en/onboarding/")
            self.assertEqual(response.status_code, 200)

        with override("pt"):
            response = self.client.get("/pt/onboarding/")
            self.assertEqual(response.status_code, 200)

    def test_root_redirects_to_portuguese_landing(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/pt/")

    def test_portuguese_public_landing_route_loads(self):
        response = self.client.get("/pt/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O seu negócio online")
        self.assertContains(response, "Página Express")
        self.assertContains(response, "Website Profissional")

    def test_portuguese_public_landing_alias_loads(self):
        response = self.client.get("/pt/siteexpress/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SiteExpress")
        self.assertContains(response, "Ver preços")

    def test_public_landing_main_ctas_point_to_onboarding(self):
        response = self.client.get("/pt/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/pt/onboarding/"', html=False)
        self.assertContains(response, "Começar")
        self.assertContains(response, 'href="/pt/sites-wordpress/"', html=False)
        self.assertContains(response, 'href="/pt/pagina-express/"', html=False)

    def test_public_landing_links_to_real_public_and_legal_pages(self):
        response = self.client.get("/pt/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/pt/impressao/"', html=False)
        self.assertContains(response, 'href="/pt/precos/"', html=False)
        self.assertContains(response, 'href="/pt/politica-de-privacidade/"', html=False)
        self.assertContains(response, 'href="/pt/termos-e-condicoes/"', html=False)

    def test_public_menu_exposes_products_customer_area_and_mobile_navigation(self):
        response = self.client.get("/pt/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/pt/pagina-express/"', html=False)
        self.assertContains(response, 'href="/pt/sites-wordpress/"', html=False)
        self.assertContains(response, 'href="/pt/impressao/cartoes-de-visita/"', html=False)
        self.assertContains(response, 'href="/pt/accounts/login/"', html=False)
        self.assertContains(response, "Área de cliente")
        self.assertContains(response, 'class="mobile-nav"', html=False)

    def test_public_landing_includes_assistant_widget(self):
        response = self.client.get("/pt/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assistente SiteExpress")
        self.assertContains(response, 'fetch("/pt/assistant/chat/"', html=False)
        self.assertContains(response, 'event.key !== "Enter"', html=False)
        self.assertContains(response, "form.requestSubmit()", html=False)

    @override_settings(SITEEXPRESS_ASSISTANT_MODE="demo")
    def test_assistant_demo_chat_creates_usage_records(self):
        response = self.client.post(
            reverse("assistant-chat"),
            data=json.dumps(
                {
                    "message": "Quanto custa um website?",
                    "page_path": "/pt/precos/",
                    "page_title": "Preços",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "demo")
        self.assertIn("€225", payload["reply"])

        conversation = AssistantConversation.objects.get(public_id=payload["conversation_id"])
        self.assertEqual(conversation.turn_count, 1)
        self.assertEqual(conversation.page_path, "/pt/precos/")
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(
            list(conversation.messages.values_list("role", flat=True)),
            [AssistantMessage.Role.USER, AssistantMessage.Role.ASSISTANT],
        )

    @override_settings(SITEEXPRESS_ASSISTANT_MODE="demo")
    def test_assistant_greeting_stays_brief_and_natural(self):
        response = self.client.post(
            reverse("assistant-chat"),
            data=json.dumps({"message": "Olá"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Olá! Como posso ajudar?")

    @override_settings(SITEEXPRESS_ASSISTANT_MODE="demo")
    def test_assistant_chat_continues_existing_conversation(self):
        first = self.client.post(
            reverse("assistant-chat"),
            data=json.dumps({"message": "O que é a Página Express?"}),
            content_type="application/json",
        ).json()
        second_response = self.client.post(
            reverse("assistant-chat"),
            data=json.dumps(
                {
                    "message": "E quanto custa?",
                    "conversation_id": first["conversation_id"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(second_response.status_code, 200)
        conversation = AssistantConversation.objects.get(public_id=first["conversation_id"])
        self.assertEqual(conversation.turn_count, 2)
        self.assertEqual(conversation.messages.count(), 4)

    def test_assistant_chat_rejects_empty_or_invalid_payload(self):
        invalid = self.client.post(
            reverse("assistant-chat"),
            data="not-json",
            content_type="application/json",
        )
        empty = self.client.post(
            reverse("assistant-chat"),
            data=json.dumps({"message": "   "}),
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(empty.status_code, 400)

    def test_assistant_usage_dashboard_is_staff_only_and_shows_totals(self):
        conversation = AssistantConversation.objects.create(
            page_path="/pt/",
            mode=AssistantConversation.Mode.DEMO,
            model="siteexpress-demo",
            turn_count=2,
            last_message_at=timezone.now(),
        )
        AssistantMessage.objects.create(
            conversation=conversation,
            role=AssistantMessage.Role.ASSISTANT,
            content="Resposta de teste",
            mode=AssistantConversation.Mode.DEMO,
            model="siteexpress-demo",
        )
        anonymous_response = self.client.get(reverse("assistant-usage"))
        self.assertEqual(anonymous_response.status_code, 302)

        staff = get_user_model().objects.create_user(
            username="assistant-staff",
            password="secret123",
            is_staff=True,
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("assistant-usage"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Utilização do assistente")
        self.assertContains(response, "Modo de demonstração")
        self.assertContains(response, "/pt/")

    def test_public_product_pages_load_with_unique_content(self):
        expectations = {
            "website-wordpress": "Um website WordPress claro",
            "starter-page": "Comece com uma página útil",
            "how-it-works": "Do negócio ao website",
            "printing": "Materiais físicos que levam clientes",
            "business-cards": "Um cartão simples que continua a trabalhar",
            "contact": "Diga-nos o que o negócio precisa",
        }

        for route_name, expected_copy in expectations.items():
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_copy)
                self.assertContains(response, "https://www.clarity.ms/tag/", html=False)

    def test_pricing_page_uses_current_portuguese_prices(self):
        response = self.client.get(reverse("pricing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "€19,95")
        self.assertContains(response, "€225")
        self.assertContains(response, "€29,95")

    def test_public_legal_pages_load(self):
        expectations = {
            "privacy-policy": "Política de Privacidade",
            "terms": "Termos e Condições",
            "cookie-policy": "Política de Cookies",
        }

        for route_name, heading in expectations.items():
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)

    def test_non_portuguese_public_routes_show_coming_soon_placeholder(self):
        en_response = self.client.get("/en/")
        es_response = self.client.get("/es/")

        self.assertEqual(en_response.status_code, 200)
        self.assertEqual(es_response.status_code, 200)
        self.assertContains(en_response, "Idioma em preparação")
        self.assertContains(es_response, "Idioma em preparação")
        self.assertContains(en_response, 'href="/pt/"', html=False)
        self.assertContains(es_response, 'href="/pt/"', html=False)

    def test_clarity_snippet_is_limited_to_siteexpress_public_pages(self):
        landing_response = self.client.get("/pt/")
        placeholder_response = self.client.get("/en/")
        login_response = self.client.get("/pt/accounts/login/")

        self.assertContains(landing_response, "https://www.clarity.ms/tag/", html=False)
        self.assertContains(landing_response, "x9aurmflrt", html=False)
        self.assertContains(placeholder_response, "https://www.clarity.ms/tag/", html=False)
        self.assertContains(placeholder_response, "x9aurmflrt", html=False)
        self.assertNotContains(login_response, "https://www.clarity.ms/tag/", html=False)
        self.assertNotContains(login_response, "x9aurmflrt", html=False)

    def test_anonymous_onboarding_creates_full_project_records(self):
        response = self.client.post(reverse("onboarding"), data=self.onboarding_payload())

        self.assertRedirects(response, reverse("success"))
        self.assertEqual(BusinessProfile.objects.count(), 1)
        self.assertEqual(WebsiteProject.objects.count(), 1)
        self.assertEqual(GeneratedContent.objects.count(), 1)
        self.assertEqual(StarterPage.objects.count(), 1)
        self.assertEqual(WordPressSiteDraft.objects.count(), 1)

        profile = BusinessProfile.objects.get()
        project = WebsiteProject.objects.get()
        content = GeneratedContent.objects.get()
        starter_page = StarterPage.objects.get()
        wp_draft = WordPressSiteDraft.objects.get()
        user = get_user_model().objects.get()

        self.assertEqual(project.business_profile, profile)
        self.assertEqual(content.project, project)
        self.assertEqual(starter_page.project, project)
        self.assertEqual(wp_draft.project, project)
        self.assertEqual(project.status, WebsiteProject.Status.STARTER_PREVIEW_READY)
        self.assertEqual(wp_draft.status, WordPressSiteDraft.Status.WAITING_FOR_UPGRADE)
        self.assertTrue(starter_page.slug.startswith("loja-exemplo-"))
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())

    @override_settings(DEBUG=True)
    def test_onboarding_success_page_shows_debug_setup_link(self):
        response = self.client.post(reverse("onboarding"), data=self.onboarding_payload(), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Link local para definir a palavra-passe:")
        self.assertContains(response, "/onboarding/account-setup/")

    def test_duplicate_email_submissions_reuse_user_and_create_new_project_records(self):
        first = self.client.post(reverse("onboarding"), data=self.onboarding_payload())
        second = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                business_name="Loja Exemplo 2",
                plan_interest=WebsiteProject.PlanInterest.PREMIUM_BILINGUAL,
            ),
        )

        self.assertRedirects(first, reverse("success"))
        self.assertRedirects(second, reverse("success"))
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(BusinessProfile.objects.count(), 2)
        self.assertEqual(WebsiteProject.objects.count(), 2)
        self.assertEqual(GeneratedContent.objects.count(), 2)
        self.assertEqual(StarterPage.objects.count(), 2)
        self.assertEqual(WordPressSiteDraft.objects.count(), 2)
        self.assertEqual(
            WebsiteProject.objects.filter(user__email="cliente@example.com").count(),
            2,
        )

    def test_need_help_domain_choice_creates_domain_request(self):
        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                domain_choice=WebsiteProject.DomainChoice.NEED_HELP,
                preferred_domain="empresa.pt",
                alternative_domain_1="empresaonline.pt",
                alternative_domain_2="empresaweb.pt",
            ),
        )

        self.assertRedirects(response, reverse("success"))
        domain_request = DomainRequest.objects.get()
        self.assertEqual(domain_request.domain_status, DomainRequest.Status.REQUESTED)
        self.assertEqual(domain_request.requested_domain, "empresa.pt")
        self.assertEqual(domain_request.alternative_domain_1, "empresaonline.pt")

    def test_already_have_domain_creates_waiting_customer_request(self):
        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                domain_choice=WebsiteProject.DomainChoice.ALREADY_HAVE_DOMAIN,
                existing_domain="meudominio.pt",
            ),
        )

        self.assertRedirects(response, reverse("success"))
        domain_request = DomainRequest.objects.get()
        self.assertEqual(domain_request.domain_status, DomainRequest.Status.WAITING_CUSTOMER)
        self.assertEqual(domain_request.requested_domain, "meudominio.pt")

    def test_preview_only_domain_choice_does_not_create_domain_request(self):
        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(domain_choice=WebsiteProject.DomainChoice.PREVIEW_ONLY),
        )

        self.assertRedirects(response, reverse("success"))
        self.assertFalse(DomainRequest.objects.exists())

    def test_onboarding_with_starter_page_monthly_sets_product_fields(self):
        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                product_type=WebsiteProject.ProductType.STARTER_PAGE_MONTHLY,
                domain_choice=WebsiteProject.DomainChoice.NEED_HELP,
                preferred_domain="starterproduto.pt",
            ),
        )

        self.assertRedirects(response, reverse("success"))
        project = WebsiteProject.objects.get()
        self.assertEqual(project.product_type, WebsiteProject.ProductType.STARTER_PAGE_MONTHLY)
        self.assertEqual(project.billing_type, WebsiteProject.BillingType.MONTHLY)
        self.assertEqual(str(project.price_snapshot), "19.95")
        self.assertEqual(project.product_status, WebsiteProject.ProductStatus.PREVIEW_READY)
        self.assertEqual(project.upgrade_status, WebsiteProject.UpgradeStatus.AVAILABLE)
        self.assertTrue(hasattr(project, "starter_page"))

    def test_onboarding_with_full_website_sets_product_fields(self):
        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                product_type=WebsiteProject.ProductType.FULL_WEBSITE_ONETIME,
                domain_choice=WebsiteProject.DomainChoice.PREVIEW_ONLY,
            ),
        )

        self.assertRedirects(response, reverse("success"))
        project = WebsiteProject.objects.get()
        self.assertEqual(project.product_type, WebsiteProject.ProductType.FULL_WEBSITE_ONETIME)
        self.assertEqual(project.billing_type, WebsiteProject.BillingType.ONE_TIME)
        self.assertEqual(str(project.price_snapshot), "225.00")
        self.assertEqual(project.product_status, WebsiteProject.ProductStatus.PREVIEW_READY)
        self.assertEqual(project.upgrade_status, WebsiteProject.UpgradeStatus.NOT_APPLICABLE)
        self.assertEqual(project.status, WebsiteProject.Status.WORDPRESS_DRAFT_READY)
        self.assertFalse(StarterPage.objects.exists())
        self.assertEqual(project.wordpress_draft.status, WordPressSiteDraft.Status.CONTENT_READY)

    def test_valid_partner_code_attaches_partner_to_onboarding(self):
        partner = self.create_partner(partner_code="PRINT123")

        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                partner_code="PRINT123",
                product_type=WebsiteProject.ProductType.FULL_WEBSITE_ONETIME,
            ),
        )

        self.assertRedirects(response, reverse("success"))
        project = WebsiteProject.objects.get()
        referral = PartnerReferral.objects.get()
        self.assertEqual(project.partner, partner)
        self.assertEqual(project.partner_code_snapshot, "PRINT123")
        self.assertEqual(referral.partner, partner)
        self.assertEqual(referral.project, project)

    def test_invalid_partner_code_shows_safe_error(self):
        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(partner_code="INVALIDO"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O codigo de parceiro nao e valido ou esta inativo.")
        self.assertFalse(WebsiteProject.objects.exists())

    def test_partner_starter_monthly_creates_trial_and_referral_record(self):
        partner = self.create_partner(partner_code="TRIAL123", default_trial_months=2)

        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                partner_code="TRIAL123",
                product_type=WebsiteProject.ProductType.STARTER_PAGE_MONTHLY,
            ),
        )

        self.assertRedirects(response, reverse("success"))
        project = WebsiteProject.objects.get()
        referral = PartnerReferral.objects.get()
        self.assertEqual(project.partner, partner)
        self.assertTrue(project.is_partner_trial)
        self.assertEqual(project.trial_source, WebsiteProject.TrialSource.PARTNER)
        self.assertEqual(project.trial_months, 2)
        self.assertIsNotNone(project.trial_started_at)
        self.assertIsNotNone(project.trial_ends_at)
        self.assertEqual(referral.referral_status, PartnerReferral.ReferralStatus.STARTER_TRIAL_ACTIVE)
        self.assertEqual(referral.commission_status, PartnerReferral.CommissionStatus.NOT_APPLICABLE)

    def test_partner_full_website_creates_referral_without_trial(self):
        self.create_partner(partner_code="FULL123")

        response = self.client.post(
            reverse("onboarding"),
            data=self.onboarding_payload(
                partner_code="FULL123",
                product_type=WebsiteProject.ProductType.FULL_WEBSITE_ONETIME,
            ),
        )

        self.assertRedirects(response, reverse("success"))
        project = WebsiteProject.objects.get()
        referral = PartnerReferral.objects.get()
        self.assertFalse(project.is_partner_trial)
        self.assertEqual(project.trial_months, 0)
        self.assertEqual(referral.referral_status, PartnerReferral.ReferralStatus.LEAD_CREATED)
        self.assertEqual(referral.commission_status, PartnerReferral.CommissionStatus.PENDING)

    def test_account_setup_token_page_loads(self):
        self.client.post(reverse("onboarding"), data=self.onboarding_payload())
        user = get_user_model().objects.get(email="cliente@example.com")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(
            reverse("account-setup", kwargs={"uidb64": uidb64, "token": token})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Defina a sua palavra-passe")

    def test_setting_password_activates_user_and_redirects_to_dashboard(self):
        self.client.post(reverse("onboarding"), data=self.onboarding_payload())
        user = get_user_model().objects.get(email="cliente@example.com")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post(
            reverse("account-setup", kwargs={"uidb64": uidb64, "token": token}),
            data={
                "new_password1": "StrongPass123!",
                "new_password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.has_usable_password())

    def test_user_can_log_in_after_password_setup_and_access_dashboard(self):
        self.client.post(reverse("onboarding"), data=self.onboarding_payload())
        user = get_user_model().objects.get(email="cliente@example.com")
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        self.client.post(
            reverse("account-setup", kwargs={"uidb64": uidb64, "token": token}),
            data={
                "new_password1": "StrongPass123!",
                "new_password2": "StrongPass123!",
            },
        )
        self.client.logout()

        login_response = self.client.post(
            reverse("login"),
            data={"username": user.username, "password": "StrongPass123!"},
        )
        dashboard_response = self.client.get(reverse("dashboard"))

        self.assertRedirects(login_response, reverse("dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_partner_onboarding_route_prefills_partner_banner(self):
        partner = self.create_partner(partner_code="URL123", company_name="Partner Route Co")

        response = self.client.get(reverse("partner-onboarding", args=[partner.partner_code]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este pedido foi iniciado atraves de um parceiro SiteExpress.")
        self.assertContains(response, partner.partner_code)

    def test_starter_path_shows_upgrade_option(self):
        user = get_user_model().objects.create_user(username="starter-upgrade", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Starter Upgrade Co",
            email="starterupgrade@example.com",
            product_type=WebsiteProject.ProductType.STARTER_PAGE_MONTHLY,
            billing_type=WebsiteProject.BillingType.MONTHLY,
            product_status=WebsiteProject.ProductStatus.PREVIEW_READY,
            upgrade_status=WebsiteProject.UpgradeStatus.AVAILABLE,
            create_starter_page=True,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Faça upgrade para Website Completo")
        self.assertContains(response, "Pedir upgrade")

    def test_partner_trial_dashboard_text_appears_for_starter_customer(self):
        user = get_user_model().objects.create_user(username="partner-trial-dashboard", password="secret123")
        partner = self.create_partner(partner_code="DASH123", company_name="Trial Partner")
        project = self.create_project_for_user(
            user,
            business_name="Partner Trial Co",
            email="partnertrial@example.com",
            partner=partner,
            partner_code_snapshot=partner.partner_code,
            is_partner_trial=True,
            trial_source=WebsiteProject.TrialSource.PARTNER,
            trial_months=1,
            trial_started_at=timezone.now(),
            trial_ends_at=timezone.now() + timezone.timedelta(days=30),
            create_partner_referral=True,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "A sua Página Express foi iniciada atraves de um Parceiro SiteExpress e continua disponivel para revisao durante o periodo experimental.",
        )
        self.assertContains(response, "O periodo experimental termina em")
        self.assertContains(response, project.partner.company_name)

    def test_full_website_path_does_not_show_starter_upgrade_option(self):
        user = get_user_model().objects.create_user(username="full-no-upgrade", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Full Product Co",
            email="fullproduct@example.com",
            product_type=WebsiteProject.ProductType.FULL_WEBSITE_ONETIME,
            billing_type=WebsiteProject.BillingType.ONE_TIME,
            product_status=WebsiteProject.ProductStatus.PREVIEW_READY,
            upgrade_status=WebsiteProject.UpgradeStatus.NOT_APPLICABLE,
            status=WebsiteProject.Status.WORDPRESS_DRAFT_READY,
            create_starter_page=False,
            starter_page_enabled=False,
            wordpress_status=WordPressSiteDraft.Status.CONTENT_READY,
        )

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Faça upgrade para Website Completo")
        self.assertContains(response, "Website Completo")

    def test_upgrade_request_updates_status(self):
        user = get_user_model().objects.create_user(username="upgrade-request", password="secret123")
        partner = self.create_partner(partner_code="UPGRADE123")
        project = self.create_project_for_user(
            user,
            business_name="Upgrade Request Co",
            email="upgraderequest@example.com",
            product_type=WebsiteProject.ProductType.STARTER_PAGE_MONTHLY,
            billing_type=WebsiteProject.BillingType.MONTHLY,
            product_status=WebsiteProject.ProductStatus.PREVIEW_READY,
            upgrade_status=WebsiteProject.UpgradeStatus.AVAILABLE,
            partner=partner,
            partner_code_snapshot=partner.partner_code,
            is_partner_trial=True,
            trial_source=WebsiteProject.TrialSource.PARTNER,
            trial_months=1,
            trial_started_at=timezone.now(),
            trial_ends_at=timezone.now() + timezone.timedelta(days=30),
            create_starter_page=True,
            create_partner_referral=True,
        )

        self.client.force_login(user)
        response = self.client.post(
            reverse("dashboard"),
            data={"form_type": "upgrade-request"},
        )

        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.upgrade_status, WebsiteProject.UpgradeStatus.REQUESTED)
        self.assertEqual(project.product_status, WebsiteProject.ProductStatus.UPGRADE_REQUESTED)
        self.assertEqual(project.partner_referral.referral_status, PartnerReferral.ReferralStatus.UPGRADE_REQUESTED)
        self.assertEqual(project.partner_referral.commission_status, PartnerReferral.CommissionStatus.PENDING)

    def test_staff_domain_requests_page_loads(self):
        staff = get_user_model().objects.create_user(
            username="domain-staff",
            password="secret123",
            is_staff=True,
        )
        project = self.create_project_for_user(
            staff,
            business_name="Dominio Staff",
            email="dominio@example.com",
        )
        DomainRequest.objects.create(
            user=staff,
            business_profile=project.business_profile,
            project=project,
            requested_domain="dominio.pt",
            preview_subdomain=project.starter_page.slug,
            domain_status=DomainRequest.Status.REQUESTED,
        )

        self.client.force_login(staff)
        response = self.client.get(reverse("domain-requests"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pedidos de Domínio")
        self.assertContains(response, "dominio.pt")

    def test_partner_dashboard_route_works_for_staff(self):
        staff = get_user_model().objects.create_user(
            username="partner-staff",
            password="secret123",
            is_staff=True,
        )
        partner = self.create_partner(partner_code="STAFF123", company_name="Staff Partner Co")
        self.create_project_for_user(
            staff,
            business_name="Partner Lead Co",
            email="partnerlead@example.com",
            partner=partner,
            partner_code_snapshot=partner.partner_code,
            is_partner_trial=True,
            trial_source=WebsiteProject.TrialSource.PARTNER,
            trial_months=1,
            trial_started_at=timezone.now(),
            trial_ends_at=timezone.now() + timezone.timedelta(days=30),
            create_partner_referral=True,
        )

        self.client.force_login(staff)
        response = self.client.get(reverse("partner-dashboard", args=[partner.partner_code]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Partner Co")
        self.assertContains(response, "Copiar link de onboarding")

    def test_language_prefixed_login_routes_work(self):
        with override("en"):
            response = self.client.get("/en/accounts/login/")
            self.assertEqual(response.status_code, 200)

        with override("pt"):
            response = self.client.get("/pt/accounts/login/")
            self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_latest_project_for_logged_in_user(self):
        user = get_user_model().objects.create_user(username="owner", password="secret123")
        older = self.create_project_for_user(
            user,
            business_name="Primeira Empresa",
            email="owner@example.com",
            hero_title="Older Hero",
        )
        newer = self.create_project_for_user(
            user,
            business_name="Segunda Empresa",
            email="owner@example.com",
            hero_title="Newer Hero",
        )

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"].id, newer.id)
        self.assertNotEqual(response.context["project"].id, older.id)
        self.assertEqual(response.context["active_section"], "preview")
        self.assertContains(response, "Newer Hero")
        self.assertContains(response, "Area de preview")
        self.assertContains(response, "Dados do negocio")
        self.assertContains(response, "Logotipo e imagens")
        self.assertContains(response, "iframe")
        self.assertContains(response, "/starter/")

    def test_dashboard_section_defaults_to_preview(self):
        user = get_user_model().objects.create_user(username="dashboard-section-default", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Default Section Co",
            email="sectiondefault@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_section"], "preview")
        self.assertContains(response, "Area de preview")

    def test_dashboard_invalid_section_falls_back_to_preview(self):
        user = get_user_model().objects.create_user(username="dashboard-section-invalid", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Invalid Section Co",
            email="sectioninvalid@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(f"{reverse('dashboard')}?section=invalid&preview=full&variation=modern&layout=wide")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_section"], "preview")
        self.assertEqual(response.context["selected_preview"], "full")
        self.assertEqual(response.context["selected_variation"], "modern")
        self.assertEqual(response.context["selected_layout"], "wide")
        self.assertContains(response, "Area de preview")

    def test_dashboard_supports_device_param(self):
        user = get_user_model().objects.create_user(username="dashboard-device", password="secret123")
        project = self.create_project_for_user(
            user,
            business_name="Device Dashboard",
            email="device@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(f"{reverse('dashboard')}?device=tablet")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_device"], "tablet")
        self.assertContains(response, "device-tablet")
        self.assertContains(
            response,
            f'src="/pt/onboarding/starter/{project.starter_page.slug}/?variation=classic&amp;layout=boxed&amp;embed=1"',
            html=False,
        )

    def test_dashboard_invalid_device_falls_back_to_desktop(self):
        user = get_user_model().objects.create_user(username="dashboard-device-fallback", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Device Fallback",
            email="devicefallback@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(f"{reverse('dashboard')}?device=invalid")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_device"], "desktop")
        self.assertContains(response, "device-desktop")

    def test_dashboard_services_section_shows_services_editor(self):
        user = get_user_model().objects.create_user(username="dashboard-section-services", password="secret123")
        project = self.create_project_for_user(
            user,
            business_name="Services Section Co",
            business_type="Repair services",
            email="sectionservices@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(f"{reverse('dashboard')}?section=services")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_section"], "services")
        self.assertContains(response, "Editor de servicos")
        self.assertContains(response, "Preview da pagina de servicos")
        self.assertContains(response, "Servico 6")
        self.assertContains(response, "Guardar servicos")
        self.assertContains(
            response,
            'src="/pt/onboarding/upgrade/?page=services&amp;variation=classic&amp;layout=boxed&amp;embed=1"',
            html=False,
        )
        self.assertContains(
            response,
            'href="/pt/onboarding/upgrade/?page=service&amp;service=service-one&amp;variation=classic&amp;layout=boxed"',
            html=False,
        )
        self.assertNotContains(
            response,
            f'/pt/onboarding/starter/{project.starter_page.slug}/?variation=classic&amp;layout=boxed&amp;embed=1',
            html=False,
        )

    def test_dashboard_business_section_shows_business_form(self):
        user = get_user_model().objects.create_user(username="dashboard-section-business", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Business Section Co",
            email="sectionbusiness@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(f"{reverse('dashboard')}?section=business")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_section"], "business")
        self.assertContains(response, "Dados do negocio")
        self.assertContains(response, "Guardar dados do negocio")

    def test_dashboard_contact_section_shows_contact_form(self):
        user = get_user_model().objects.create_user(username="dashboard-section-contact", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Contact Section Co",
            email="sectioncontact@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(f"{reverse('dashboard')}?section=contact")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_section"], "contact")
        self.assertContains(response, "Contactos")
        self.assertContains(response, "Guardar contactos")

    def test_owner_can_update_business_information_from_dashboard(self):
        user = get_user_model().objects.create_user(username="dashboard-edit-business", password="secret123")
        project = self.create_project_for_user(
            user,
            business_name="Old Name",
            business_type="Restaurant",
            city="Lisboa",
            country="Portugal",
            email="editbiz@example.com",
        )

        self.client.force_login(user)
        response = self.client.post(
            f"{reverse('dashboard')}?preview=full&variation=modern&layout=wide",
            data={
                "form_type": "business",
                "business-business_name": "New Name",
                "business-business_type": "Beauty salon",
                "business-city": "Porto",
                "business-country": "Spain",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('dashboard')}?section=preview&preview=full&variation=modern&layout=wide&device=desktop",
        )
        project.business_profile.refresh_from_db()
        self.assertEqual(project.business_profile.business_name, "New Name")
        self.assertEqual(project.business_profile.business_type, "Beauty salon")
        self.assertEqual(project.business_profile.city, "Porto")
        self.assertEqual(project.business_profile.country, "Spain")

    def test_owner_can_update_contact_details_from_dashboard(self):
        user = get_user_model().objects.create_user(username="dashboard-edit-contact", password="secret123")
        project = self.create_project_for_user(
            user,
            business_name="Contact Name",
            email="before@example.com",
            phone="+351911111111",
            whatsapp="+351922222222",
        )

        self.client.force_login(user)
        response = self.client.post(
            reverse("dashboard"),
            data={
                "form_type": "contact",
                "contact-email": "after@example.com",
                "contact-phone": "+351933333333",
                "contact-whatsapp": "+351944444444",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('dashboard')}?section=preview&preview=starter&variation=classic&layout=boxed&device=desktop",
        )
        project.business_profile.refresh_from_db()
        self.assertEqual(project.business_profile.email, "after@example.com")
        self.assertEqual(project.business_profile.phone, "+351933333333")
        self.assertEqual(project.business_profile.whatsapp, "+351944444444")

    def test_preview_uses_updated_dashboard_business_profile_data(self):
        user = get_user_model().objects.create_user(username="dashboard-preview-update", password="secret123")
        project = self.create_project_for_user(
            user,
            business_name="Original Studio",
            business_type="Beauty salon",
            city="Lisboa",
            country="Portugal",
            email="previewupdate@example.com",
        )

        self.client.force_login(user)
        self.client.post(
            reverse("dashboard"),
            data={
                "form_type": "business",
                "business-business_name": "Updated Studio",
                "business-business_type": "Beauty salon",
                "business-city": "Coimbra",
                "business-country": "Portugal",
            },
        )
        starter_response = self.client.get(reverse("starter-preview", args=[project.starter_page.slug]))

        self.assertEqual(starter_response.status_code, 200)
        self.assertContains(starter_response, "Updated Studio")
        self.assertContains(starter_response, "Coimbra")

    def test_owner_can_update_service_title_and_description_from_dashboard(self):
        user = get_user_model().objects.create_user(username="dashboard-edit-services", password="secret123")
        project = self.create_project_for_user(
            user,
            business_name="Service Editor Co",
            business_type="Repair services",
            email="serviceeditor@example.com",
        )

        self.client.force_login(user)
        response = self.client.post(
            f"{reverse('dashboard')}?section=services&preview=full&variation=modern&layout=full",
            data={
                "form_type": "services",
                "services-service_1_title": "Rapid diagnostics",
                "services-service_1_icon": "wrench",
                "services-service_1_short_description": "Quick fault finding for urgent local issues.",
                "services-service_2_title": "Maintenance plans",
                "services-service_2_icon": "check",
                "services-service_2_short_description": "Scheduled upkeep for homes and local businesses.",
                "services-service_3_title": "Emergency callouts",
                "services-service_3_icon": "clock",
                "services-service_3_short_description": "Same-day support when problems need immediate attention.",
                "services-service_4_title": "Installation visits",
                "services-service_4_icon": "home",
                "services-service_4_short_description": "Professional setup for new systems and equipment.",
                "services-service_5_title": "Inspection reports",
                "services-service_5_icon": "shield",
                "services-service_5_short_description": "Clear checks with practical next-step guidance.",
                "services-service_6_title": "Area coverage",
                "services-service_6_icon": "truck",
                "services-service_6_short_description": "Regular visits across the main service area.",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('dashboard')}?section=services&preview=full&variation=modern&layout=full&device=desktop",
        )
        project.generated_contents.first().refresh_from_db()
        services_json = project.generated_contents.first().services_json
        self.assertEqual(services_json[0]["title"], "Rapid diagnostics")
        self.assertEqual(
            services_json[0]["description"],
            "Quick fault finding for urgent local issues.",
        )
        self.assertEqual(services_json[0]["slug"], "service-one")
        self.assertEqual(services_json[0]["icon"], "wrench")

    def test_services_section_preserves_variation_and_layout_in_preview_urls(self):
        user = get_user_model().objects.create_user(username="dashboard-services-urls", password="secret123")
        self.create_project_for_user(
            user,
            business_name="Services URL Co",
            business_type="Repair services",
            email="servicesurl@example.com",
        )

        self.client.force_login(user)
        response = self.client.get(
            f"{reverse('dashboard')}?section=services&variation=modern&layout=full"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'src="/pt/onboarding/upgrade/?page=services&amp;variation=modern&amp;layout=full&amp;embed=1"',
            html=False,
        )
        self.assertContains(
            response,
            'href="/pt/onboarding/upgrade/?page=service&amp;service=service-one&amp;variation=modern&amp;layout=full"',
            html=False,
        )
        self.assertContains(response, 'name="services-service_1_icon"', html=False)

    def test_saving_service_icon_updates_services_json(self):
        user = get_user_model().objects.create_user(username="dashboard-save-service-icon", password="secret123")
        project = self.create_project_for_user(
            user,
            business_name="Saved Icon Co",
            business_type="Repair services",
            email="savedicon@example.com",
        )

        self.client.force_login(user)
        response = self.client.post(
            f"{reverse('dashboard')}?section=services&variation=modern&layout=full",
            data={
                "form_type": "services",
                "services-service_1_title": "Rapid diagnostics",
                "services-service_1_icon": "spark",
                "services-service_1_short_description": "Quick checks and safe recommendations.",
                "services-service_2_title": "Service Two",
                "services-service_2_icon": "check",
                "services-service_2_short_description": "Short description two",
                "services-service_3_title": "",
                "services-service_3_icon": "clock",
                "services-service_3_short_description": "",
                "services-service_4_title": "",
                "services-service_4_icon": "home",
                "services-service_4_short_description": "",
                "services-service_5_title": "",
