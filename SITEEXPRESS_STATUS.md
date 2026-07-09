# SiteExpress.pt V1 Status

## Dev Environment

- Project root: `C:\wamp64\www\siteexpress.pt`
- Backend path: `C:\wamp64\www\siteexpress.pt\backend`
- Frontend WordPress path: `C:\wamp64\www\siteexpress.pt\frontend`
- Local dev URL: `http://127.0.0.1:8090`

## Current Working Routes

### Public

- `/` -> redirects to `/pt/`
- `/pt/` -> public SiteExpress landing page
- `/pt/siteexpress/` -> landing page alias
- `/en/` -> language placeholder page
- `/es/` -> language placeholder page

### Onboarding and Customer Flow

- `/pt/onboarding/` -> main onboarding form
- `/pt/onboarding/parceiro/PARCEIROV1/` -> partner-assisted onboarding test route
- `/pt/onboarding/success/` -> onboarding success page
- `/pt/onboarding/account-setup/<uid>/<token>/` -> account password setup
- `/pt/onboarding/dashboard/` -> customer dashboard

### Staff / Internal

- `/pt/onboarding/domain-requests/` -> staff domain request page
- `/pt/onboarding/partner/<partner_code>/dashboard/` -> partner dashboard, staff-only in V1

### Preview Routes

- `/pt/onboarding/starter/<slug>/` -> Página Express preview
- `/pt/onboarding/upgrade/` -> Website Completo preview / placeholder flow

## Current Product Paths

### Página Express

- Entry point: `/pt/onboarding/`
- Product label: `Página Express`
- Price: `€9,95/mês + IVA`
- Flow:
  - onboarding
  - starter preview
  - customer dashboard
  - optional upgrade request

### Website Completo

- Entry point: `/pt/onboarding/`
- Product label: `Website Completo`
- Price: `€235 + IVA`
- Flow:
  - onboarding
  - full preview placeholder route
  - customer dashboard
  - manual preparation / follow-up

## Partner Test Code

- Main partner test code: `PARCEIROV1`
- Example onboarding URL: `/pt/onboarding/parceiro/PARCEIROV1/`

## Current Functional Status

- Onboarding works
- Product choice works
- Domain request flow works
- Partner / referral / free trial flow works
- Partner dashboard works
- Public landing page works
- Starter preview and upgrade preview are cleaned for Portuguese demo use

## Known Rough Edges

- No real WordPress frontend bridge yet
- No payment automation yet
- No domain automation yet
- Partner dashboard is still staff-only in V1
- ES and EN are placeholder public language pages only
- Terms / privacy links are still placeholders
- Some seed/generated content may still include English placeholder text depending on test/demo data

## Current Architecture Notes

- Django is the active application layer for:
  - public landing page
  - onboarding
  - customer account setup
  - dashboard
  - domain request tracking
  - partner flow
  - starter / full preview routes
- WordPress frontend is not currently connected as a live publishing bridge
- Domain handling is manual
- Payment handling is manual / not automated

## Tests

- Current onboarding test suite: `83` tests green
- Last known command status:
  - `py -3 manage.py check` -> passing
  - `py -3 manage.py test onboarding` -> passing

## Next Recommended Steps

1. Replace placeholder legal/contact pages with real Django public pages.
2. Add a lightweight public contact / lead capture route if needed for the landing page.
3. Decide the first real WordPress bridge milestone:
   - preview sync only
   - draft handoff only
   - or controlled publish workflow
4. Decide the first payment milestone:
   - manual payment status tracking in Django
   - or later gateway integration
5. Decide the first domain operations milestone:
   - keep manual but improve staff tooling
   - or prepare registrar / DNS abstraction without enabling automation yet
6. Add real partner authentication when partner access should move beyond staff-only V1.
7. Review generated placeholder copy and seed content so demos stay fully Portuguese without mixed sample text.
