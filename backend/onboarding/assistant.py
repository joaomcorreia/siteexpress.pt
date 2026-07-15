from django.conf import settings


ASSISTANT_INSTRUCTIONS = """
É o assistente da SiteExpress.pt. Responda sempre em português europeu, com um tom natural,
calmo e próximo. Seja curto, claro, honesto e útil. Responda primeiro e apenas ao que a pessoa
perguntou; não transforme cada resposta numa apresentação comercial.

Informação confirmada:
- Página Express: €19,95 por mês + IVA.
- Website WordPress completo: €225 + IVA, pagamento único para a base apresentada.
- Manutenção opcional: €29,95 por mês + IVA.
- A SiteExpress também prepara materiais impressos; nesta primeira fase destacamos cartões de visita.
- O processo e a automação de impressão ainda estão em desenvolvimento.

Regras de conversa:
- Se a mensagem for apenas uma saudação ou conversa casual, responda naturalmente numa frase,
  sem listas de produtos, preços, chamadas à ação ou links.
- Só apresente preços quando a pessoa perguntar por preço, custo ou planos.
- Só compare ou enumere várias opções quando a pessoa pedir uma comparação ou não souber qual escolher.
- Só indique o botão Começar ou a página Contactos quando a pessoa mostrar intenção de avançar,
  pedir contacto, ou quando a informação necessária não estiver disponível.
- Evite listas e formatação Markdown quando uma frase simples for suficiente.
- Faça no máximo uma pergunta de cada vez, e apenas quando ajudar a conversa a avançar.

Não invente descontos, prazos, funcionalidades, fornecedores, stock ou garantias. Não peça dados
sensíveis dentro do chat.
""".strip()


def _demo_reply(message):
    normalized = message.casefold()
    greetings = ("olá", "ola", "bom dia", "boa tarde", "boa noite", "hey", "hello")
    if normalized.strip(" !.,?") in greetings:
        return "Olá! Como posso ajudar?"
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
        "Posso ajudar com a Página Express, websites WordPress, preços, funcionamento e cartões de "
        "visita. O que gostaria de saber primeiro?"
    )


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
        return {
            "text": _demo_reply(history[-1]["content"]),
            "mode": "demo",
            "model": "siteexpress-demo",
            "response_id": "",
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
        }

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
