# Third-Party Integrations

## Integration Inventory

| Service | Purpose | Auth Method | SDK |
|---------|---------|------------|-----|
| Supabase | PostgreSQL database + auth | Service key (JWT) | `supabase-py` |
| Redis | Cache + Celery broker | URL + password | `redis-py` |
| Qdrant | Vector similarity search | API key | `qdrant-client` |
| Anthropic Claude | LLM explanations + chat | API key | `anthropic` |
| OpenAI GPT | LLM fallback | API key | `openai` |
| Google Gemini | LLM fallback | API key | `google-generativeai` |
| Razorpay | Subscription billing | Key ID + Secret | `razorpay` |
| Telegram Bot API | Push notifications | Bot token | `python-telegram-bot` |
| OpenWeatherMap | Pre-match weather | API key | `aiohttp` (REST) |
| AWS SES | Transactional email | IAM access key | `boto3` |
| Sentry | Error tracking | DSN | `sentry-sdk` |

---

## Anthropic Claude

```python
# llm/providers/anthropic_provider.py
import anthropic

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

async def generate_explanation(prompt: str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
```

**Rate limits:** Respect Anthropic's per-minute token limits. Implement exponential backoff on 429.  
**Fallback:** Switch to OpenAI if 3 consecutive failures.

---

## Razorpay

```python
# backend/services/payment_service.py
import razorpay

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_subscription(plan: str) -> dict:
    plan_id = PLAN_IDS[plan]  # Razorpay plan IDs from dashboard
    return client.subscription.create({
        "plan_id": plan_id,
        "total_count": 12 if plan == "premium_monthly" else 1,
        "quantity": 1,
        "notify_info": {"notify_phone": user.phone, "notify_email": user.email}
    })

def verify_webhook_signature(body: bytes, signature: str) -> bool:
    return razorpay.utility.verify_webhook_signature(
        body.decode(), signature, settings.RAZORPAY_KEY_SECRET
    )
```

**Webhook URL:** `POST /api/v1/payments/webhook`  
**Required events:** `payment.captured`, `subscription.charged`, `subscription.cancelled`

---

## Telegram Bot

```python
# notifications/channels/telegram.py
from telegram import Bot

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

async def send_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return True
    except telegram.error.Forbidden:
        # User blocked the bot
        await mark_telegram_disabled(chat_id)
        return False
    except telegram.error.TelegramError as e:
        log.error("telegram_send_failed", error=str(e), chat_id=chat_id)
        return False
```

Users connect Telegram by starting a chat with `@XithSenseBot` and following the link-account flow.

---

## OpenWeatherMap

```python
# data/sources/weather.py
async def fetch_match_weather(city: str, match_datetime: datetime) -> WeatherContext:
    async with aiohttp.ClientSession() as session:
        url = f"{settings.WEATHER_API_URL}/forecast"
        params = {"q": city, "appid": settings.WEATHER_API_KEY, "units": "metric"}
        async with session.get(url, params=params) as resp:
            data = await resp.json()
    # Find closest forecast to match_datetime
    return WeatherContext(
        temperature=data["list"][0]["main"]["temp"],
        humidity=data["list"][0]["main"]["humidity"],
        wind_speed=data["list"][0]["wind"]["speed"],
        rain_probability=data["list"][0].get("pop", 0.0) * 100
    )
```

**Used for:** Pitch impact estimation (dew probability, rain risk).  
**Cache:** 3-hour TTL per city.  
**Fallback:** Use venue historical averages if API unavailable.

---

## Sentry

```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENV,
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=0.1,      # 10% of requests traced
    profiles_sample_rate=0.05,   # 5% profiled
    release=settings.VERSION,
)
```

**Alert rules in Sentry:**  
- Any unhandled exception → immediate alert  
- Error rate > 1% for 5 min → alert  
- P95 latency > 2s → alert
