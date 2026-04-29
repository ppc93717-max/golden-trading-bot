#!/usr/bin/env python3
"""
GOLDEN TRADING NEWS BOT - FINAL VERSION
✅ Real-time news alerts with 5-min pre-alerts
✅ London/NY session briefings
✅ Daily economic calendar at 07:00
✅ Evening report at 21:00
✅ FOMC & high-impact event special coverage
"""

import asyncio
import logging
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from telegram import Bot
from telegram.constants import ParseMode
import feedparser
import schedule
import time
import threading

# ═══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = "8761021544:AAF8PZfLjFoIblvSCkA5gk2cubFI2-Eto0E"
TELEGRAM_CHAT_ID = "7782912937"
GROQ_API_KEY = "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"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK = "mixtral-8x7b-32768"
CHECK_INTERVAL_MINUTES = 15

# ═══════════════════════════════════════════════════════════════
#  NEWS SOURCES - 18 Sources
# ═══════════════════════════════════════════════════════════════
NEWS_SOURCES = [
    {"name": "Reuters Markets",   "url": "https://feeds.reuters.com/reuters/businessNews",        "priority": "HIGH"},
    {"name": "MarketWatch",       "url": "https://feeds.marketwatch.com/marketwatch/marketpulse/","priority": "HIGH"},
    {"name": "FXStreet",          "url": "https://www.fxstreet.com/rss/news",                    "priority": "HIGH"},
    {"name": "ForexLive",         "url": "https://www.forexlive.com/feed/news",                  "priority": "HIGH"},
    {"name": "Investing.com",     "url": "https://www.investing.com/rss/news.rss",               "priority": "HIGH"},
    {"name": "Investing Forex",   "url": "https://www.investing.com/rss/news_285.rss",           "priority": "HIGH"},
    {"name": "Forex Factory",     "url": "https://www.forexfactory.com/news?format=xml",         "priority": "HIGH"},
    {"name": "MyFXBook",          "url": "https://www.myfxbook.com/rss/forex-economic-calendar", "priority": "HIGH"},
    {"name": "Fed Reserve",       "url": "https://www.federalreserve.gov/feeds/press_all.xml",   "priority": "HIGH"},
    {"name": "ECB News",          "url": "https://www.ecb.europa.eu/rss/press.html",             "priority": "HIGH"},
    {"name": "DailyFX",           "url": "https://www.dailyfx.com/feeds/all",                    "priority": "HIGH"},
    {"name": "CNBC Markets",      "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "priority": "MEDIUM"},
    {"name": "Yahoo Finance",     "url": "https://finance.yahoo.com/news/rssindex",              "priority": "MEDIUM"},
    {"name": "Kitco Gold",        "url": "https://www.kitco.com/rss/lo-news.xml",                "priority": "MEDIUM"},
    {"name": "OilPrice.com",      "url": "https://oilprice.com/rss/main",                        "priority": "MEDIUM"},
    {"name": "CoinDesk BTC",      "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",      "priority": "MEDIUM"},
    {"name": "Nasdaq News",       "url": "https://www.nasdaq.com/feed/rssoutbound?category=Markets", "priority": "MEDIUM"},
    {"name": "EIA Energy",        "url": "https://www.eia.gov/rss/press_room.xml",               "priority": "MEDIUM"},
]

# ═══════════════════════════════════════════════════════════════
#  HIGH IMPACT ECONOMIC EVENTS (for 5-min pre-alerts)
# ═══════════════════════════════════════════════════════════════
HIGH_IMPACT_EVENTS = {
    "fomc": {"name": "قرار الفيدرالي الأمريكي (FOMC)", "currency": "USD", "emoji": "🏦🇺🇸"},
    "federal reserve": {"name": "قرار الفيدرالي الأمريكي", "currency": "USD", "emoji": "🏦🇺🇸"},
    "interest rate": {"name": "قرار سعر الفائدة", "currency": "USD", "emoji": "💰"},
    "rate decision": {"name": "قرار سعر الفائدة", "currency": "USD", "emoji": "💰"},
    "nonfarm payroll": {"name": "بيانات الوظائف (NFP)", "currency": "USD", "emoji": "👷🇺🇸"},
    "nfp": {"name": "بيانات الوظائف (NFP)", "currency": "USD", "emoji": "👷🇺🇸"},
    "cpi": {"name": "مؤشر أسعار المستهلكين (CPI)", "currency": "USD", "emoji": "📊"},
    "inflation": {"name": "بيانات التضخم", "currency": "USD", "emoji": "📊"},
    "gdp": {"name": "الناتج المحلي الإجمالي (GDP)", "currency": "USD", "emoji": "📈"},
    "ecb": {"name": "قرار البنك المركزي الأوروبي (ECB)", "currency": "EUR", "emoji": "🏦🇪🇺"},
    "bank of england": {"name": "قرار بنك إنجلترا (BOE)", "currency": "GBP", "emoji": "🏦🇬🇧"},
    "powell": {"name": "خطاب رئيس الفيدرالي باول", "currency": "USD", "emoji": "🎤🇺🇸"},
    "trump": {"name": "تصريح ترامب", "currency": "USD", "emoji": "🇺🇸"},
    "opec": {"name": "قرار أوبك", "currency": "OIL", "emoji": "🛢️"},
}

HIGH_IMPACT_KEYWORDS = [
    "trump", "powell", "yellen", "federal reserve", "fed",
    "lagarde", "ecb", "bank of england", "boe", "bailey",
    "opec", "saudi", "russia", "bessent", "g7", "g20", "imf",
    "interest rate", "rate hike", "rate cut", "inflation", "cpi", "pce",
    "nonfarm payroll", "nfp", "gdp", "unemployment", "jobs report",
    "fomc", "monetary policy", "quantitative",
    "tariff", "trade war", "sanctions", "trade deal", "recession",
    "gold", "oil", "crude", "wti", "brent",
    "bitcoin", "btc", "crypto",
    "dollar", "usd", "euro", "pound", "gbp", "eur", "cad",
    "nasdaq", "s&p", "dow jones", "forex", "fx", "bond", "yield",
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
seen_articles = set()
daily_news_cache = []
sent_pre_alerts = set()  # Track sent pre-alerts


# ═══════════════════════════════════════════════════════════════
#  GROQ API
# ═══════════════════════════════════════════════════════════════
def call_openrouter(prompt: str, max_tokens: int = 1500) -> Optional[str]:
    """Call Groq API - Free & Fast"""
    models = [GROQ_MODEL, GROQ_FALLBACK]
    for model in models:
        try:
            logger.info(f"Calling Groq: {model}")
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.3
                    }
                )
                if response.status_code == 429:
                    logger.warning(f"Rate limit {model}, trying fallback...")
                    time.sleep(2)
                    continue
                if response.status_code != 200:
                    logger.error(f"Groq {response.status_code}: {response.text[:200]}")
                    continue
                data = response.json()
                if "choices" in data and data["choices"]:
                    result = data["choices"][0]["message"]["content"].strip()
                    if result:
                        logger.info(f"Groq success: {model}")
                        return result
        except Exception as e:
            logger.error(f"Groq error {model}: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
#  NEWS FETCHING
# ═══════════════════════════════════════════════════════════════
def is_relevant_news(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(keyword in text for keyword in HIGH_IMPACT_KEYWORDS)


def is_high_impact_event(title: str, summary: str) -> Optional[dict]:
    text = (title + " " + summary).lower()
    for keyword, info in HIGH_IMPACT_EVENTS.items():
        if keyword in text:
            return info
    return None


def fetch_news_from_sources() -> list:
    all_news = []
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:8]:
                article_id = entry.get("id", entry.get("link", ""))
                if article_id in seen_articles:
                    continue
                title = entry.get("title", "")
                summary = re.sub(r'<[^>]+>', '', entry.get("summary", entry.get("description", "")))[:500]
                if is_relevant_news(title, summary):
                    all_news.append({
                        "id": article_id,
                        "source": source["name"],
                        "priority": source["priority"],
                        "title": title,
                        "summary": summary,
                        "link": entry.get("link", ""),
                    })
        except Exception as e:
            logger.error(f"Error fetching {source['name']}: {e}")
    return all_news


# ═══════════════════════════════════════════════════════════════
#  NEWS ANALYSIS
# ═══════════════════════════════════════════════════════════════
def analyze_news(article: dict) -> Optional[dict]:
    prompt = f"""انت محلل مالي خبير متخصص في الفوركس والسلع والمؤشرات. حلل هذا الخبر بدقة:

المصدر: {article['source']}
العنوان: {article['title']}
الملخص: {article['summary']}

اجب بـ JSON فقط بدون اي نص اضافي:
{{
  "sentiment": "POSITIVE or NEGATIVE or NEUTRAL",
  "importance": "HIGH or MEDIUM or LOW",
  "summary_ar": "ملخص الخبر بالعربية في جملة واحدة",
  "markets": {{
    "EURUSD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "GBPUSD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "DXY":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "US100":  {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "US30":   {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "WTI":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "GOLD":   {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "USDCAD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}},
    "BTC":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}}
  }},
  "overall_analysis": "تحليل شامل في 2-3 جمل عربية"
}}"""
    text = call_openrouter(prompt, 1200)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


def analyze_fomc_event(article: dict) -> Optional[dict]:
    """Special analysis for FOMC and high-impact events"""
    prompt = f"""انت محلل مالي خبير. هذا خبر عالي الأهمية جداً — قرار الفيدرالي أو حدث اقتصادي كبير.

المصدر: {article['source']}
العنوان: {article['title']}
التفاصيل: {article['summary']}

قدم تحليلاً شاملاً ودقيقاً. اجب بـ JSON فقط:
{{
  "event_type": "نوع الحدث",
  "result": "نتيجة الحدث بالأرقام اذا متاحة",
  "vs_expected": "مقارنة بالتوقعات — افضل/اسوا/كما متوقع",
  "sentiment": "POSITIVE or NEGATIVE or NEUTRAL",
  "importance": "HIGH",
  "summary_ar": "ملخص تفصيلي للحدث في 2-3 جمل",
  "key_points": ["نقطة مهمة 1", "نقطة مهمة 2", "نقطة مهمة 3"],
  "markets": {{
    "EURUSD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "GBPUSD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "DXY":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "US100":  {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "US30":   {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "WTI":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "GOLD":   {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "USDCAD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}},
    "BTC":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب التفصيلي"}}
  }},
  "overall_analysis": "تحليل شامل ومفصل للحدث وتأثيره الفوري والمتوسط المدى في 3-4 جمل",
  "trading_recommendation": "توصية تداول مباشرة بناءً على هذا الحدث"
}}"""
    text = call_openrouter(prompt, 2000)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


# ═══════════════════════════════════════════════════════════════
#  MESSAGE FORMATTERS
# ═══════════════════════════════════════════════════════════════
def format_news_alert(article: dict, analysis: dict) -> str:
    sentiment = analysis.get("sentiment", "NEUTRAL")
    importance = analysis.get("importance", "MEDIUM")
    s_emoji = {"POSITIVE": "🟢", "NEGATIVE": "🔴", "NEUTRAL": "🟡"}.get(sentiment, "🟡")
    s_text  = {"POSITIVE": "ايجابي ✅", "NEGATIVE": "سلبي ❌", "NEUTRAL": "محايد ⚖️"}.get(sentiment, "محايد")
    i_emoji = {"HIGH": "🔥🔥🔥", "MEDIUM": "⚡⚡", "LOW": "ℹ"}.get(importance, "⚡")
    d_emoji = {"UP": "📈", "DOWN": "📉", "NEUTRAL": "➡️"}
    s_word  = {"STRONG": "قوي", "MODERATE": "متوسط", "WEAK": "ضعيف"}

    markets = analysis.get("markets", {})
    market_lines = ""
    for key, label in [
        ("EURUSD","EUR/USD 🇪🇺"), ("GBPUSD","GBP/USD 🇬🇧"), ("DXY","DXY 💵"),
        ("US100","US100 📊"),    ("US30","US30 🏭"),         ("WTI","WTI Oil 🛢"),
        ("GOLD","GOLD 🥇"),      ("USDCAD","USD/CAD 🇨🇦"),  ("BTC","BTC/USD ₿"),
    ]:
        m  = markets.get(key, {})
        de = d_emoji.get(m.get("direction", "NEUTRAL"), "➡️")
        sw = s_word.get(m.get("strength", "MODERATE"), "متوسط")
        r  = m.get("reason", "")
        market_lines += f"{de} *{label}* — {sw}\n   {r}\n\n"

    return (
        f"🏆 *GOLDEN TRADING NEWS*\n"
        f"{'━'*30}\n"
        f"🚨 *خبر عاجل* {i_emoji}\n"
        f"{'─'*30}\n\n"
        f"📰 *المصدر:* {article['source']}\n"
        f"🕐 {datetime.now(timezone.utc).strftime('%d/%m/%Y  %H:%M')} UTC\n\n"
        f"📌 *العنوان:*\n{article['title']}\n\n"
        f"💡 *الملخص:*\n{analysis.get('summary_ar', '')}\n\n"
        f"{s_emoji} *التوجه:* {s_text}\n"
        f"{'─'*30}\n"
        f"📊 *تأثير الخبر على الأسواق:*\n\n"
        f"{market_lines}"
        f"{'─'*30}\n"
        f"🧠 *التحليل:*\n{analysis.get('overall_analysis', '')}\n\n"
        f"🔗 [قراءة الخبر]({article['link']})\n"
        f"{'━'*30}"
    )


def format_fomc_alert(article: dict, analysis: dict) -> str:
    s_emoji = {"POSITIVE": "🟢", "NEGATIVE": "🔴", "NEUTRAL": "🟡"}.get(analysis.get("sentiment","NEUTRAL"), "🟡")
    d_emoji = {"UP": "📈", "DOWN": "📉", "NEUTRAL": "➡️"}
    s_word  = {"STRONG": "قوي 💪", "MODERATE": "متوسط", "WEAK": "ضعيف"}

    key_points = analysis.get("key_points", [])
    points_text = "\n".join([f"  • {p}" for p in key_points])

    markets = analysis.get("markets", {})
    market_lines = ""
    for key, label in [
        ("EURUSD","EUR/USD 🇪🇺"), ("GBPUSD","GBP/USD 🇬🇧"), ("DXY","DXY 💵"),
        ("US100","US100 📊"),    ("US30","US30 🏭"),         ("WTI","WTI Oil 🛢"),
        ("GOLD","GOLD 🥇"),      ("USDCAD","USD/CAD 🇨🇦"),  ("BTC","BTC/USD ₿"),
    ]:
        m  = markets.get(key, {})
        de = d_emoji.get(m.get("direction", "NEUTRAL"), "➡️")
        sw = s_word.get(m.get("strength", "MODERATE"), "متوسط")
        r  = m.get("reason", "")
        market_lines += f"{de} *{label}* — {sw}\n   {r}\n\n"

    return (
        f"🏆 *GOLDEN TRADING NEWS*\n"
        f"{'━'*30}\n"
        f"🚨🔥 *حدث اقتصادي كبير* 🔥🚨\n"
        f"{'─'*30}\n\n"
        f"🎯 *{analysis.get('event_type', 'حدث مهم')}*\n"
        f"📊 *النتيجة:* {analysis.get('result', 'N/A')}\n"
        f"📌 *مقارنة بالتوقعات:* {analysis.get('vs_expected', '')}\n"
        f"{s_emoji} *التوجه:* {'إيجابي ✅' if analysis.get('sentiment')=='POSITIVE' else 'سلبي ❌' if analysis.get('sentiment')=='NEGATIVE' else 'محايد ⚖️'}\n\n"
        f"💡 *الملخص:*\n{analysis.get('summary_ar', '')}\n\n"
        f"🔑 *النقاط المهمة:*\n{points_text}\n"
        f"{'─'*30}\n"
        f"📊 *تأثير على الأسواق:*\n\n"
        f"{market_lines}"
        f"{'─'*30}\n"
        f"🧠 *التحليل الشامل:*\n{analysis.get('overall_analysis', '')}\n\n"
        f"💼 *توصية التداول:*\n{analysis.get('trading_recommendation', '')}\n\n"
        f"🔗 [قراءة التفاصيل]({article['link']})\n"
        f"{'━'*30}"
    )


def format_pre_alert(event_info: dict, article: dict) -> str:
    return (
        f"🏆 *GOLDEN TRADING NEWS*\n"
        f"{'━'*30}\n"
        f"⚠️ *تنبيه — خبر مهم بعد 5 دقائق!*\n"
        f"{'─'*30}\n\n"
        f"{event_info['emoji']} *{event_info['name']}*\n\n"
        f"💱 *العملة المتأثرة:* {event_info['currency']}\n"
        f"📰 *المصدر:* {article['source']}\n"
        f"🕐 {datetime.now(timezone.utc).strftime('%d/%m/%Y  %H:%M')} UTC\n\n"
        f"📌 {article['title']}\n\n"
        f"⚡ *استعد! سيصلك التحليل الكامل فور صدور الخبر*\n"
        f"{'━'*30}"
    )


# ═══════════════════════════════════════════════════════════════
#  SESSION BRIEFING
# ═══════════════════════════════════════════════════════════════
def generate_session_briefing(session: str) -> Optional[dict]:
    session_ar = "لندن" if session == "LONDON" else "نيويورك"
    prompt = f"""انت محلل مالي خبير. قدم ملخص جلسة {session_ar} الآن مع توصيات واضحة.

اجب بـ JSON فقط:
{{
  "market_mood": "BULLISH or BEARISH or NEUTRAL",
  "key_themes": ["موضوع1", "موضوع2", "موضوع3"],
  "markets": {{
    "EURUSD": {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "GBPUSD": {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "DXY":    {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "US100":  {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "US30":   {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "WTI":    {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "GOLD":   {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "USDCAD": {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}},
    "BTC":    {{"signal": "BUY or SELL or WAIT", "key_level": "مستوى مهم", "reason": "السبب"}}
  }},
  "risk_warning": "تحذير مخاطر مهم",
  "events_to_watch": ["حدث1", "حدث2"]
}}"""
    text = call_openrouter(prompt, 2000)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


def format_session_message(session: str, data: dict) -> str:
    is_london = session == "LONDON"
    header = "🇬🇧 صباح الخير — جلسة لندن" if is_london else "🇺🇸 صباح الخير — جلسة نيويورك"
    mood_emoji = {"BULLISH": "🟢 صاعد", "BEARISH": "🔴 هابط", "NEUTRAL": "🟡 محايد"}.get(data.get("market_mood","NEUTRAL"), "🟡 محايد")
    signal_emoji = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "WAIT": "🟡 WAIT"}
    themes = "\n".join([f"  • {t}" for t in data.get("key_themes", [])])
    events = "\n".join([f"  ⚡ {e}" for e in data.get("events_to_watch", [])])

    markets = data.get("markets", {})
    market_lines = ""
    for key, label in [
        ("EURUSD","EUR/USD 🇪🇺"), ("GBPUSD","GBP/USD 🇬🇧"), ("DXY","DXY 💵"),
        ("US100","US100 📊"),    ("US30","US30 🏭"),         ("WTI","WTI Oil 🛢"),
        ("GOLD","GOLD 🥇"),      ("USDCAD","USD/CAD 🇨🇦"),  ("BTC","BTC/USD ₿"),
    ]:
        m = markets.get(key, {})
        sig = signal_emoji.get(m.get("signal","WAIT"), "🟡 WAIT")
        market_lines += f"\n{sig} *{label}*\n   📍 {m.get('key_level','')}\n   📌 {m.get('reason','')}\n"

    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"{header}\n🕐 {datetime.now(timezone.utc).strftime('%d/%m/%Y  %H:%M')} UTC\n"
        f"{'─'*30}\n\n📊 *مزاج السوق:* {mood_emoji}\n\n"
        f"🎯 *المواضيع الرئيسية:*\n{themes}\n"
        f"{'─'*30}\n💹 *توصيات — BUY / SELL / WAIT:*\n{'─'*30}\n"
        f"{market_lines}\n{'─'*30}\n"
        f"📅 *أحداث يجب مراقبتها:*\n{events}\n\n"
        f"⚠️ *تحذير:*\n{data.get('risk_warning','')}\n{'━'*30}"
    )


# ═══════════════════════════════════════════════════════════════
#  ECONOMIC CALENDAR
# ═══════════════════════════════════════════════════════════════
def generate_economic_calendar() -> Optional[dict]:
    today = datetime.now(timezone.utc).strftime('%A %d %B %Y')
    prompt = f"""انت محلل مالي خبير. اليوم {today}. قدم الأجندة الاقتصادية الكاملة لهذا اليوم.

اجب بـ JSON فقط:
{{
  "market_overview": "نظرة عامة على اليوم",
  "events": [
    {{
      "time_utc": "وقت UTC",
      "time_morocco": "الوقت بتوقيت المغرب",
      "event": "اسم الحدث",
      "currency": "العملة",
      "importance": "HIGH or MEDIUM or LOW",
      "previous": "القيمة السابقة",
      "forecast": "التوقعات",
      "expected_outcome_ar": "افضل من المتوقع or اسوا من المتوقع or كما متوقع",
      "probability": "70%",
      "markets_impact": {{
        "EURUSD": "UP or DOWN or NEUTRAL",
        "GBPUSD": "UP or DOWN or NEUTRAL",
        "DXY": "UP or DOWN or NEUTRAL",
        "GOLD": "UP or DOWN or NEUTRAL",
        "US100": "UP or DOWN or NEUTRAL"
      }},
      "analysis": "تحليل مختصر"
    }}
  ],
  "most_important_event": "اهم حدث اليوم",
  "day_bias": "RISK_ON or RISK_OFF or NEUTRAL",
  "trading_advice": "نصيحة تداول عامة لهذا اليوم"
}}"""
    text = call_openrouter(prompt, 2500)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


def format_economic_calendar(data: dict) -> str:
    imp_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}
    d_emoji = {"UP": "📈", "DOWN": "📉", "NEUTRAL": "➡️"}
    bias_text = {"RISK_ON": "🟢 شهية مخاطرة", "RISK_OFF": "🔴 نفور مخاطرة", "NEUTRAL": "🟡 محايد"}.get(data.get("day_bias","NEUTRAL"), "🟡")

    events_text = ""
    for event in data.get("events", []):
        imp = imp_emoji.get(event.get("importance","LOW"), "⚪")
        impacts = event.get("markets_impact", {})
        impact_line = " ".join([f"{d_emoji.get(v,'➡️')}{k}" for k,v in impacts.items()])
        events_text += (
            f"\n{'─'*28}\n"
            f"{imp} *{event.get('event','')}*\n"
            f"🕐 {event.get('time_morocco','')} (المغرب)\n"
            f"💱 {event.get('currency','')} | السابق: `{event.get('previous','N/A')}` | المتوقع: `{event.get('forecast','N/A')}`\n"
            f"📌 التوقع: {event.get('expected_outcome_ar','')} | {event.get('probability','')}\n"
            f"📊 {impact_line}\n"
            f"💡 {event.get('analysis','')}\n"
        )

    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"📅 *الأجندة الاقتصادية اليومية*\n"
        f"🗓 {datetime.now(timezone.utc).strftime('%d/%m/%Y')} | 07:00 صباحاً (المغرب)\n"
        f"{'─'*30}\n\n"
        f"📌 *نظرة عامة:*\n{data.get('market_overview','')}\n\n"
        f"🎯 *أهم حدث اليوم:* {data.get('most_important_event','')}\n"
        f"🌡 *مزاج السوق المتوقع:* {bias_text}\n"
        f"{'─'*30}\n⏰ *الأحداث الاقتصادية:*"
        f"{events_text}\n"
        f"{'─'*30}\n"
        f"💼 *نصيحة اليوم:*\n{data.get('trading_advice','')}\n"
        f"{'━'*30}"
    )


# ═══════════════════════════════════════════════════════════════
#  EVENING REPORT
# ═══════════════════════════════════════════════════════════════
def generate_daily_report() -> Optional[dict]:
    news_summary = ""
    if daily_news_cache:
        news_summary = "أخبار اليوم:\n" + "\n".join([f"- {n['title']}" for n in daily_news_cache[-15:]])

    prompt = f"""انت محلل مالي خبير. قدم التقرير اليومي الشامل لنهاية اليوم.

{news_summary}

اجب بـ JSON فقط:
{{
  "day_summary": "ملخص اليوم في 3-4 جمل",
  "top_story": "أهم خبر اثر على الأسواق",
  "markets_performance": {{
    "EURUSD": {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "GBPUSD": {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "DXY":    {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "US100":  {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "US30":   {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "WTI":    {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "GOLD":   {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "USDCAD": {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "BTC":    {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}}
  }},
  "tomorrow_events": ["حدث مهم غداً 1", "حدث مهم غداً 2"],
  "overall_outlook": "نظرة عامة على الغد"
}}"""
    text = call_openrouter(prompt, 2500)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


def format_daily_report(data: dict) -> str:
    sig_emoji = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "WAIT": "🟡 WAIT"}
    markets = data.get("markets_performance", {})
    market_lines = ""
    for key, label in [
        ("EURUSD","EUR/USD 🇪🇺"), ("GBPUSD","GBP/USD 🇬🇧"), ("DXY","DXY 💵"),
        ("US100","US100 📊"),    ("US30","US30 🏭"),         ("WTI","WTI Oil 🛢"),
        ("GOLD","GOLD 🥇"),      ("USDCAD","USD/CAD 🇨🇦"),  ("BTC","BTC/USD ₿"),
    ]:
        m = markets.get(key, {})
        sig = sig_emoji.get(m.get("signal_tomorrow","WAIT"), "🟡 WAIT")
        market_lines += f"\n*{label}*\n   📈 اليوم: {m.get('performance','')}\n   {sig} غداً: {m.get('outlook','')}\n"

    events = "\n".join([f"  ⚡ {e}" for e in data.get("tomorrow_events",[])])
    date_str = datetime.now(timezone.utc).strftime('%d/%m/%Y')
    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"📋 *التقرير اليومي الشامل*\n📅 {date_str}\n"
        f"{'─'*30}\n\n📰 *ملخص اليوم:*\n{data.get('day_summary','')}\n\n"
        f"🔥 *أبرز خبر اليوم:*\n{data.get('top_story','')}\n"
        f"{'─'*30}\n📊 *أداء الأسواق وتوقعات الغد:*\n{'─'*30}\n"
        f"{market_lines}\n{'─'*30}\n"
        f"📅 *أحداث مهمة غداً:*\n{events}\n\n"
        f"🔭 *النظرة العامة:*\n{data.get('overall_outlook','')}\n"
        f"{'━'*30}\n_تقرير GOLDEN TRADING NEWS — {date_str}_"
    )


# ═══════════════════════════════════════════════════════════════
#  TELEGRAM
# ═══════════════════════════════════════════════════════════════
async def send_telegram_message(message: str):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for chunk in chunks:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=chunk,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Telegram error: {e}")


# ═══════════════════════════════════════════════════════════════
#  MAIN TASKS
# ═══════════════════════════════════════════════════════════════
async def check_and_send_news():
    logger.info("Checking for new trading news...")
    articles = fetch_news_from_sources()
    new_count = 0
    for article in articles[:5]:
        if article["id"] in seen_articles:
            continue

        # Check if this is a high-impact event that needs pre-alert
        event_info = is_high_impact_event(article["title"], article["summary"])
        pre_alert_key = article["id"] + "_pre"

        if event_info and pre_alert_key not in sent_pre_alerts:
            pre_msg = format_pre_alert(event_info, article)
            await send_telegram_message(pre_msg)
            sent_pre_alerts.add(pre_alert_key)
            await asyncio.sleep(2)

        # Decide analysis type
        is_fomc = any(k in (article["title"] + article["summary"]).lower()
                     for k in ["fomc", "federal reserve", "interest rate", "rate decision", "powell", "nfp", "nonfarm", "cpi"])

        if is_fomc:
            analysis = analyze_fomc_event(article)
            if analysis:
                message = format_fomc_alert(article, analysis)
                await send_telegram_message(message)
                daily_news_cache.append(article)
                new_count += 1
        else:
            analysis = analyze_news(article)
            if analysis and analysis.get("importance") in ["HIGH", "MEDIUM"]:
                message = format_news_alert(article, analysis)
                await send_telegram_message(message)
                daily_news_cache.append(article)
                new_count += 1

        seen_articles.add(article["id"])
        await asyncio.sleep(3)

    logger.info(f"News check done — Sent {new_count} alerts")


async def send_london_briefing():
    logger.info("London briefing...")
    await send_telegram_message("🇬🇧 *جلسة لندن — جاري التحضير...* ⏳")
    data = generate_session_briefing("LONDON")
    if data:
        await send_telegram_message(format_session_message("LONDON", data))
    else:
        await send_telegram_message("⚠️ تعذر تحضير ملخص جلسة لندن.")


async def send_newyork_briefing():
    logger.info("NY briefing...")
    await send_telegram_message("🇺🇸 *جلسة نيويورك — جاري التحضير...* ⏳")
    data = generate_session_briefing("NEWYORK")
    if data:
        await send_telegram_message(format_session_message("NEWYORK", data))
    else:
        await send_telegram_message("⚠️ تعذر تحضير ملخص جلسة نيويورك.")


async def send_economic_calendar():
    logger.info("Economic calendar...")
    await send_telegram_message("📅 *الأجندة الاقتصادية — جاري التحضير...* ⏳")
    data = generate_economic_calendar()
    if data:
        await send_telegram_message(format_economic_calendar(data))
    else:
        await send_telegram_message("⚠️ تعذر تحضير الأجندة الاقتصادية.")


async def send_evening_report():
    logger.info("Evening report...")
    await send_telegram_message("📋 *التقرير اليومي — جاري التحضير...* ⏳")
    data = generate_daily_report()
    if data:
        await send_telegram_message(format_daily_report(data))
        daily_news_cache.clear()
    else:
        await send_telegram_message("⚠️ تعذر تحضير التقرير اليومي.")


# ═══════════════════════════════════════════════════════════════
#  SCHEDULER
# ═══════════════════════════════════════════════════════════════
def run_scheduler():
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(lambda: asyncio.run(check_and_send_news()))
    schedule.every().day.at("06:00").do(lambda: asyncio.run(send_economic_calendar()))   # 07:00 Morocco
    schedule.every().day.at("07:00").do(lambda: asyncio.run(send_london_briefing()))     # 08:00 Morocco
    schedule.every().day.at("13:00").do(lambda: asyncio.run(send_newyork_briefing()))    # 14:00 Morocco
    schedule.every().day.at("20:00").do(lambda: asyncio.run(send_evening_report()))      # 21:00 Morocco
    while True:
        schedule.run_pending()
        time.sleep(30)


async def send_startup_message():
    msg = (
        "🏆 *GOLDEN TRADING NEWS — FINAL VERSION*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ البوت يعمل الآن 24/7!\n\n"
        "📅 *الجدول اليومي (بتوقيت المغرب):*\n"
        "⏰ 07:00 — الأجندة الاقتصادية اليومية\n"
        "🇬🇧 08:00 — ملخص جلسة لندن + BUY/SELL/WAIT\n"
        "🇺🇸 14:00 — ملخص جلسة نيويورك + BUY/SELL/WAIT\n"
        "📋 21:00 — التقرير اليومي الشامل\n\n"
        "🚨 *فوري:*\n"
        "⚠️ تنبيه قبل الأخبار الكبيرة بـ 5 دقائق\n"
        "🔥 تحليل خاص لـ FOMC/NFP/CPI/سعر الفائدة\n"
        "📰 كل خبر مهم مع تحليل كامل\n\n"
        "📊 *الأسواق:* EUR/USD | GBP/USD | DXY\n"
        "US100 | US30 | WTI | GOLD | USD/CAD | BTC\n\n"
        "📰 *المصادر:* 18 مصدر إخباري متخصص\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Startup error: {e}")


async def main():
    logger.info("Starting GOLDEN TRADING NEWS BOT — FINAL VERSION")
    await send_startup_message()
    await check_and_send_news()
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Bot running 24/7")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
