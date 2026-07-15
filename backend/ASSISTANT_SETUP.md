# SiteExpress Assistant

The first assistant foundation includes:

- a chat widget on the Portuguese public pages;
- a Django JSON endpoint at `/pt/assistant/chat/`;
- automatic demo mode when no OpenAI API key is available;
- conversation and token usage records;
- a staff-only usage page at `/pt/assistant/usage/`.

## Install and prepare

Run these commands while internet access is available:

```powershell
cd C:\wamp64\www\siteexpress.pt\backend
py -3 -m pip install -r requirements.txt
py -3 manage.py migrate
```

Demo mode works without internet and without an API key.

## Enable OpenAI mode

Never add the API key to Git or paste it into application code. Add it to a local `.env` file
inside `backend` or configure it in the hosting environment:

```text
OPENAI_API_KEY=replace-with-the-private-key
SITEEXPRESS_ASSISTANT_MODE=auto
SITEEXPRESS_ASSISTANT_MODEL=gpt-5.4-mini
DJANGO_SECRET_KEY=replace-with-a-separate-long-random-production-secret
```

With `SITEEXPRESS_ASSISTANT_MODE=auto`, the assistant uses OpenAI when the key is available and
falls back to demo mode when it is not. Set the mode explicitly to `demo` when API calls should
remain disabled.

## Review usage

Sign in with a Django staff account and open:

```text
http://127.0.0.1:8090/pt/assistant/usage/
```

The page shows the last 30 days of conversations, questions, input and output tokens, and an
estimated USD cost based on the configured token rates.
