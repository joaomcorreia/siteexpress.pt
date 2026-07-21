import json
import re

from django.conf import settings


ASSISTANT_INSTRUCTIONS = """
É o assistente da SiteExpress.pt. Responda sempre em português europeu, com um tom natural,
calmo e próximo. Seja curto, claro, honesto e útil. Responda primeiro e apenas ao que a pessoa
perguntou; não transforme cada resposta numa apresentação comercial.

Informação confirmada:
- Página Express: uma página rápida com a informação essencial do negócio; €19,95 por mês + IVA.
- Website completo: várias páginas, com espaço para apresentar melhor a empresa e os diferentes
  serviços; usa WordPress, mas o cliente não precisa de conhecimentos técnicos; €225 + IVA,
  pagamento único para a base apresentada.
- Manutenção opcional: €29,95 por mês + IVA.
- A SiteExpress também prepara materiais impressos; nesta primeira fase destacamos cartões de visita.
- O processo e a automação de impressão ainda estão em desenvolvimento.
- Quando já souber a atividade e pelo menos um serviço concreto, pode propor uma pré-visualização
  visual criada diretamente a partir da conversa. O sistema pede confirmação antes de a abrir.

Regras de conversa:
- Se a mensagem for apenas uma saudação ou conversa casual, responda naturalmente numa frase,
  sem listas de produtos, preços, chamadas à ação ou links.
- O seu âmbito é a SiteExpress, websites, presença online relacionada com estes serviços e
  materiais impressos. Se o pedido não estiver relacionado, explique brevemente o seu âmbito
  e não tente atuar como assistente geral. Perante um risco imediato, pode dar apenas um aviso
  curto de segurança antes de redirecionar a conversa.
- Se pedirem um serviço que a SiteExpress não oferece, diga claramente que esse tipo de serviço
  não está disponível na plataforma e pergunte se precisam de ajuda com outro assunto relacionado
  com a SiteExpress. Não apresente preços SiteExpress só porque a pergunta contém "preço" ou "custa".
- Se a pessoa disser apenas "ok", agradecer ou encerrar o assunto, responda de forma breve e natural.
- Fale na linguagem do cliente. Não comece por termos técnicos como WordPress, CMS, alojamento ou SEO.
  Explique primeiro o resultado: uma página simples ou um site completo com várias páginas.
- Quando o negócio tiver vários serviços diferentes, recomende normalmente o site completo e explique
  que cada serviço importante pode ter o seu próprio título, texto e página. Isso ajuda os clientes a
  perceber a oferta e cria conteúdo mais relevante para pesquisas locais, sem garantir posições no Google.
- Se a pessoa mostrar receio de tecnologia, tempo ou dificuldade, tranquilize-a: basta explicar o negócio
  e o que quer mostrar; a SiteExpress e o assistente ajudam a organizar a estrutura e a preparar os textos.
- Quando a pessoa pedir um exemplo ou uma pré-visualização e já tiver explicado o negócio, diga que pode
  preparar uma proposta visual agora. Nunca diga que o preview só está disponível no botão Começar.
- Nunca diga que já criou, publicou ou mostrou um preview visual quando isso ainda não aconteceu.
- Encaminhe novos visitantes para o botão Começar ou para /pt/onboarding/. Nunca os envie diretamente
  para /pt/onboarding/account-setup/: essa página exige um link privado criado depois do onboarding.
- Só apresente preços quando a pessoa perguntar por preço, custo ou planos.
- Só compare ou enumere várias opções quando a pessoa pedir uma comparação ou não souber qual escolher.
- Só indique o botão Começar ou a página Contactos quando a pessoa mostrar intenção de avançar,
  pedir contacto, ou quando a informação necessária não estiver disponível.
- Evite listas e formatação Markdown quando uma frase simples for suficiente.
- Faça no máximo uma pergunta de cada vez, e apenas quando ajudar a conversa a avançar.
- Não repita apenas a saudação. Se a pessoa voltar a cumprimentar ou enviar apenas "?", ajude a conversa
  a avançar com uma pergunta concreta e curta sobre o negócio ou sobre a página que pretende criar.

Exemplo de abordagem para uma pessoa não técnica com vários serviços:
"Temos duas opções: uma página rápida com a informação essencial e um site mais completo, com várias
páginas. Como tem vários serviços, a segunda opção faz mais sentido: cada serviço pode ter o seu próprio
título e conteúdo, para os clientes perceberem melhor o que faz e em que zona trabalha."

Se a pessoa estiver hesitante, pode responder de forma semelhante a:
"Para si, o processo é simples: diga-me o que quer mostrar e eu ajudo a organizar a estrutura e os textos 😊
Posso já preparar aqui uma primeira proposta com os serviços que mencionou. Quer que avance?"

Não invente descontos, prazos, funcionalidades, fornecedores, stock ou garantias. Não peça dados
sensíveis dentro do chat.
""".strip()


def _demo_reply(message):
    normalized = message.casefold()
    cleaned = normalized.strip(" !.,?")
    greetings = ("olá", "ola", "bom dia", "boa tarde", "boa noite", "hey", "hello")
    if cleaned in greetings:
        salutation = (
            cleaned.capitalize()
            if cleaned in ("bom dia", "boa tarde", "boa noite")
            else "Olá"
        )
        return f"{salutation}! Sou o assistente da SiteExpress. Em que posso ajudar?"
    acknowledgements = (
        "ok",
        "okay",
        "obrigado",
        "obrigada",
        "perfeito",
        "entendido",
        "está bem",
        "esta bem",
    )
    if cleaned in acknowledgements:
        return "Combinado. Estou por aqui se precisar."
    out_of_scope_terms = (
        "carro",
        "automóvel",
        "automovel",
        "travão",
        "travao",
        "travões",
        "travoes",
        "oficina",
        "mecânico",
        "mecanico",
        "motor",
        "pneu",
        "quilómetro",
        "quilometro",
        "km/h",
        "kms",
    )
    if any(term in normalized for term in out_of_scope_terms):
        return (
            "Esse tipo de serviço não está disponível na plataforma SiteExpress. "
            "Precisa de ajuda com algum dos nossos serviços?"
        )
    if any(term in normalized for term in ("preço", "preco", "custa", "valor", "plano")):
        return (
            "A Página Express custa €19,95/mês + IVA. O Website WordPress completo começa em "
            "€225 + IVA. A manutenção opcional custa €29,95/mês + IVA. Quer comparar as duas opções?"
        )
    if any(term in normalized for term in ("cartão", "cartao", "impress", "visita")):
        return (
            "A área de impressão começa pelos cartões de visita. Ainda estamos a preparar o fluxo "
            "de encomenda, mas já pode consultar a página Impressão e pedir contacto à equipa."
        )
    if any(term in normalized for term in ("wordpress", "website", "site completo")):
        return (
            "O Website WordPress é a opção mais completa: páginas essenciais, serviços, contactos, "
            "formulário e uma base preparada para crescer. O preço inicial é €225 + IVA."
        )
    if any(term in normalized for term in ("página express", "pagina express", "mensal")):
        return (
            "A Página Express é a opção rápida para apresentar o negócio, serviços e contactos. "
            "Custa €19,95/mês + IVA e pode evoluir mais tarde."
        )
    if any(term in normalized for term in ("contact", "falar", "telefon", "email")):
        return (
            "Pode usar a página Contactos para falar com a equipa SiteExpress. Evite enviar dados "
            "sensíveis diretamente neste chat."
        )
    return (
        "Sou o assistente da SiteExpress e posso ajudar com websites, Página Express, preços e "
        "materiais impressos. Tem alguma dúvida sobre estes serviços?"
    )


def generate_demo_reply(message, model="siteexpress-demo"):
    return {
        "text": _demo_reply(message),
        "mode": "demo",
        "model": model,
        "response_id": "",
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
    }


def _usage_value(usage, field, default=0):
    value = getattr(usage, field, default) if usage else default
    return value or default


def generate_assistant_reply(history):
    model = settings.SITEEXPRESS_ASSISTANT_MODEL
    configured_mode = settings.SITEEXPRESS_ASSISTANT_MODE
    use_openai = configured_mode == "openai" or (
        configured_mode == "auto" and bool(settings.OPENAI_API_KEY)
    )

    if not use_openai:
        return generate_demo_reply(history[-1]["content"])

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key is not configured.")

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.create(
        model=model,
        instructions=ASSISTANT_INSTRUCTIONS,
        input=history,
        max_output_tokens=350,
        store=False,
    )
    usage = getattr(response, "usage", None)
    input_details = getattr(usage, "input_tokens_details", None) if usage else None
    return {
        "text": (response.output_text or "").strip(),
        "mode": "openai",
        "model": model,
        "response_id": getattr(response, "id", "") or "",
        "input_tokens": _usage_value(usage, "input_tokens"),
        "cached_input_tokens": _usage_value(input_details, "cached_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
    }


BUILD_ANALYSIS_INSTRUCTIONS = """
Analise a conversa para decidir se já existe informação suficiente para criar uma primeira
pré-visualização de uma Página Express. Responda APENAS com JSON válido.

Está pronta quando conhece uma atividade profissional concreta e pelo menos um serviço real.
Não exija nome, email, telefone, morada ou pagamento. A pré-visualização pode usar um nome provisório.

Formato:
{
  "ready": true,
  "business_name": "",
  "business_type": "",
  "category": "construction|beauty|automotive|craft|professional|local_service",
  "location": "",
  "headline": "",
  "intro": "",
  "services": [{"title": "", "description": ""}],
  "about": "",
  "cta": "Pedir orçamento"
}

Use português europeu. Produza 3 ou 4 serviços curtos, sem inventar qualificações, experiência,
preços, garantias, nomes de pessoas ou localizações. Se não estiver pronta, use {"ready": false}.
""".strip()


def _clean_build_analysis(data):
    if not isinstance(data, dict) or not data.get("ready"):
        return {"ready": False}
    business_type = " ".join(str(data.get("business_type") or "").split())[:160]
    services = []
    for item in data.get("services") or []:
        if not isinstance(item, dict):
            continue
        title = " ".join(str(item.get("title") or "").split())[:90]
        description = " ".join(str(item.get("description") or "").split())[:220]
        if title:
            services.append({"title": title, "description": description})
        if len(services) >= 4:
            break
    if not business_type or not services:
        return {"ready": False}
    allowed = {"construction", "beauty", "automotive", "craft", "professional", "local_service"}
    category = str(data.get("category") or "local_service").strip().lower()
    if category not in allowed:
        category = "local_service"
    return {
        "ready": True,
        "business_name": " ".join(str(data.get("business_name") or "").split())[:255],
        "business_type": business_type,
        "category": category,
        "location": " ".join(str(data.get("location") or "").split())[:160],
        "headline": " ".join(str(data.get("headline") or "").split())[:255],
        "intro": " ".join(str(data.get("intro") or "").split())[:500],
        "services": services,
        "about": " ".join(str(data.get("about") or "").split())[:700],
        "cta": " ".join(str(data.get("cta") or "Pedir orçamento").split())[:80],
    }


def analyze_assistant_build(history):
    if not settings.OPENAI_API_KEY or settings.SITEEXPRESS_ASSISTANT_MODE == "demo":
        return {"ready": False}
    from openai import OpenAI

    response = OpenAI(api_key=settings.OPENAI_API_KEY).responses.create(
        model=settings.SITEEXPRESS_ASSISTANT_MODEL,
        instructions=BUILD_ANALYSIS_INSTRUCTIONS,
        input=history,
        max_output_tokens=700,
        store=False,
    )
    raw = (response.output_text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    return _clean_build_analysis(json.loads(raw))


BUILD_REVISION_INSTRUCTIONS = """
Atualize uma pré-visualização de Página Express segundo o pedido do cliente. Responda APENAS com
JSON válido e mantenha exatamente os campos e serviços que o cliente não pediu para alterar.
Não invente preços, garantias, experiência, contactos, qualificações ou localizações.

Formato:
{
  "business_name": "",
  "business_type": "",
  "location": "",
  "headline": "",
  "intro": "",
  "services": [{"title": "", "description": ""}],
  "about": "",
  "cta": ""
}
Use português europeu e texto curto, natural e próprio para uma página comercial.
""".strip()


def revise_assistant_build(build_data, request_text):
    if not settings.OPENAI_API_KEY or settings.SITEEXPRESS_ASSISTANT_MODE == "demo":
        raise RuntimeError("AI site revision is not available.")
    from openai import OpenAI

    response = OpenAI(api_key=settings.OPENAI_API_KEY).responses.create(
        model=settings.SITEEXPRESS_ASSISTANT_MODEL,
        instructions=BUILD_REVISION_INSTRUCTIONS,
        input=(
            "VERSÃO ATUAL:\n"
            f"{json.dumps(build_data, ensure_ascii=False)}\n\n"
            f"ALTERAÇÃO PEDIDA:\n{request_text}"
        ),
        max_output_tokens=900,
        store=False,
    )
    raw = (response.output_text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    return _clean_build_analysis({"ready": True, "category": "local_service", **json.loads(raw)})


COLOR_NAMES = {
    "amarelo": "#f5a623",
    "azul": "#1769aa",
    "azul escuro": "#12324a",
    "verde": "#287a47",
    "vermelho": "#b7221a",
    "laranja": "#e87524",
    "roxo": "#7047a8",
    "rosa": "#c94f7c",
    "preto": "#15191c",
    "cinzento": "#66727a",
    "branco": "#ffffff",
}


def extract_color_revision(request_text):
    """Return a safe palette update for an explicit colour request."""
    normalized = " ".join(str(request_text or "").casefold().split())
    has_colour_language = any(term in normalized for term in ("cor", "cores", "tom", "paleta", "em vez de"))
    has_direct_choice = any(term in normalized for term in ("quero", "prefiro", "mudar para", "trocar para"))
    if not (has_colour_language or has_direct_choice):
        return None
    target_text = normalized.split("em vez de", 1)[0]
    hex_match = re.search(r"#[0-9a-f]{6}\b", target_text)
    if hex_match:
        return {"accent": hex_match.group(0)}
    for name in sorted(COLOR_NAMES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", target_text):
            return {"accent": COLOR_NAMES[name]}
    return None
