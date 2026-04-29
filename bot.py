#!/usr/bin/env python3
"""
GOLDEN TRADING NEWS BOT - FULL VERSION
✅ Real-time news alerts
✅ London Open briefing (08:00 UTC)
✅ New York Open briefing (13:00 UTC)
✅ Daily evening report (21:00 UTC)
"""

import asyncio
import logging
import json
import re
from datetime import datetime, timezone
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

MARKETS = ["EURUSD", "GBPUSD", "DXY", "US100", "US30", "WTI", "GOLD", "USDCAD", "BTC"]

# ═══════════════════════════════════════════════════════════════
NEWS_SOURCES = [
    {"name": "Reuters Markets",   "url": "https://feeds.reuters.com/reuters/businessNews",        "priority": "HIGH"},
    {"name": "MarketWatch",       "url": "https://feeds.marketwatch.com/marketwatch/marketpulse/","priority": "HIGH"},
    {"name": "FXStreet",          "url": "https://www.fxstreet.com/rss/news",                    "priority": "HIGH"},
    {"name": "ForexLive",         "url": "https://www.forexlive.com/feed/news",                  "priority": "HIGH"},
    {"name": "Investing.com",     "url": "https://www.investing.com/rss/news.rss",               "priority": "HIGH"},
    {"name": "Forex Factory",     "url": "https://www.forexfactory.com/news?format=xml",         "priority": "HIGH"},
    {"name": "MyFXBook",          "url": "https://www.myfxbook.com/rss/forex-economic-calendar", "priority": "HIGH"},
    {"name": "Fed Reserve",       "url": "https://www.federalreserve.gov/feeds/press_all.xml",   "priority": "HIGH"},
    {"name": "ECB News",          "url": "https://www.ecb.europa.eu/rss/press.html",             "priority": "HIGH"},
    {"name": "CNBC Markets",      "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "priority": "MEDIUM"},
    {"name": "Yahoo Finance",     "url": "https://finance.yahoo.com/news/rssindex",              "priority": "MEDIUM"},
    {"name": "Kitco Gold",        "url": "https://www.kitco.com/rss/lo-news.xml",                "priority": "MEDIUM"},
    {"name": "OilPrice.com",      "url": "https://oilprice.com/rss/main",                        "priority": "MEDIUM"},
    {"name": "CoinDesk BTC",      "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",      "priority": "MEDIUM"},
    {"name": "Investing Forex",   "url": "https://www.investing.com/rss/news_285.rss",           "priority": "MEDIUM"},
]

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
daily_news_cache = []  # Store today's news for evening report


def call_openrouter(prompt: str, max_tokens: int = 1500) -> Optional[str]:
    """Call Groq API - Free & Fast"""
    models = [GROQ_MODEL, GROQ_FALLBACK]
    for model in models:
        try:
            logger.info(f"Trying Groq model: {model}")
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.3
                    }
                )
                logger.info(f"Groq status: {response.status_code}")
                if response.status_code != 200:
                    logger.warning(f"Groq {model} returned {response.status_code}, trying next...")
                    continue
                data = response.json()
                if "choices" in data and data["choices"]:
                    result = data["choices"][0]["message"]["content"].strip()
                    if result:
                        logger.info(f"Groq success with: {model}")
                        return result
        except Exception as e:
            logger.error(f"Groq error with {model}: {e}")
    logger.error("All Groq models failed!")
    return None


def is_relevant_news(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(keyword in text for keyword in HIGH_IMPACT_KEYWORDS)


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
    prompt = f"""انت محلل مالي خبير. حلل الخبر التالي:
المصدر: {article['source']}
العنوان: {article['title']}
الملخص: {article['summary']}

اجب بـ JSON فقط:
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
    text = call_groq(prompt)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


# ═══════════════════════════════════════════════════════════════
#  SESSION BRIEFING (London / New York)
# ═══════════════════════════════════════════════════════════════
def generate_session_briefing(session: str) -> str:
    session_ar = "لندن 🇬🇧" if session == "LONDON" else "نيويورك 🇺🇸"
    time_str = "08:00 UTC" if session == "LONDON" else "13:00 UTC"
    
    prompt = f"""انت محلل مالي خبير. قدم ملخص جلسة {session_ar} ({time_str}) الآن.

بناءً على:
- الوضع الاقتصادي الحالي
- آخر قرارات الفيد والمركزي الاوروبي وبنك انجلترا
- اتجاهات الدولار والذهب والنفط
- مخاطر الاسواق الحالية

اجب بـ JSON فقط:
{{
  "session": "{session_ar}",
  "market_mood": "BULLISH or BEARISH or NEUTRAL",
  "mood_ar": "صاعد or هابط or محايد",
  "key_themes": ["موضوع1", "موضوع2", "موضوع3"],
  "markets": {{
    "EURUSD": {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "GBPUSD": {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "DXY":    {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "US100":  {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "US30":   {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "WTI":    {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "GOLD":   {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "USDCAD": {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}},
    "BTC":    {{"signal": "BUY or SELL or WAIT", "bias": "الاتجاه المتوقع", "key_level": "مستوى مهم", "reason": "السبب"}}
  }},
  "risk_warning": "تحذير مخاطر مهم للجلسة",
  "events_to_watch": ["حدث1", "حدث2"]
}}"""
    
    text = call_groq(prompt, max_tokens=2000)
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
    time_now = datetime.now(timezone.utc).strftime('%d/%m/%Y  %H:%M') + " UTC"
    
    mood_emoji = {"BULLISH": "🟢 صاعد", "BEARISH": "🔴 هابط", "NEUTRAL": "🟡 محايد"}.get(
        data.get("market_mood", "NEUTRAL"), "🟡 محايد")
    
    signal_emoji = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "WAIT": "🟡 WAIT"}
    
    themes = data.get("key_themes", [])
    themes_text = "\n".join([f"  • {t}" for t in themes])
    
    markets = data.get("markets", {})
    market_lines = ""
    for key, label in [
        ("EURUSD","EUR/USD 🇪🇺"), ("GBPUSD","GBP/USD 🇬🇧"), ("DXY","DXY 💵"),
        ("US100","US100 📊"),    ("US30","US30 🏭"),         ("WTI","WTI Oil 🛢"),
        ("GOLD","GOLD 🥇"),      ("USDCAD","USD/CAD 🇨🇦"),  ("BTC","BTC/USD ₿"),
    ]:
        m = markets.get(key, {})
        sig = signal_emoji.get(m.get("signal", "WAIT"), "🟡 WAIT")
        bias = m.get("bias", "")
        level = m.get("key_level", "")
        reason = m.get("reason", "")
        market_lines += (
            f"\n{sig} *{label}*\n"
            f"   📍 مستوى مهم: {level}\n"
            f"   📌 {reason}\n"
        )
    
    events = data.get("events_to_watch", [])
    events_text = "\n".join([f"  ⚡ {e}" for e in events])
    
    msg = (
        f"🏆 *GOLDEN TRADING NEWS*\n"
        f"{'━'*30}\n"
        f"{header}\n"
        f"🕐 {time_now}\n"
        f"{'─'*30}\n\n"
        f"📊 *مزاج السوق:* {mood_emoji}\n\n"
        f"🎯 *المواضيع الرئيسية:*\n{themes_text}\n"
        f"{'─'*30}\n"
        f"💹 *توصيات الجلسة — BUY / SELL / WAIT:*\n"
        f"{'─'*30}\n"
        f"{market_lines}\n"
        f"{'─'*30}\n"
        f"📅 *احداث يجب مراقبتها:*\n{events_text}\n\n"
        f"⚠️ *تحذير:*\n{data.get('risk_warning', '')}\n"
        f"{'━'*30}"
    )
    return msg


# ═══════════════════════════════════════════════════════════════
#  DAILY EVENING REPORT
# ═══════════════════════════════════════════════════════════════
def generate_daily_report() -> str:
    news_summary = ""
    if daily_news_cache:
        news_summary = "اخبار اليوم:\n" + "\n".join([
            f"- {n['title']}" for n in daily_news_cache[-15:]
        ])
    
    prompt = f"""انت محلل مالي خبير. قدم التقرير اليومي الشامل لنهاية اليوم.

{news_summary}

اجب بـ JSON فقط:
{{
  "day_summary": "ملخص اليوم في 3-4 جمل عربية",
  "top_story": "اهم خبر اثر على الاسواق اليوم",
  "markets_performance": {{
    "EURUSD": {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "GBPUSD": {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "DXY":    {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "US100":  {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "US30":   {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "WTI":    {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "GOLD":   {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "USDCAD": {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}},
    "BTC":    {{"performance": "وصف اداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "التوقعات للغد"}}
  }},
  "tomorrow_events": ["حدث مهم غدا1", "حدث مهم غدا2", "حدث مهم غدا3"],
  "overall_outlook": "نظرة عامة على الغد والاسبوع القادم"
}}"""
    
    text = call_groq(prompt, max_tokens=2500)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


def format_daily_report(data: dict) -> str:
    signal_emoji = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "WAIT": "🟡 WAIT"}
    time_now = datetime.now(timezone.utc).strftime('%d/%m/%Y')
    
    markets = data.get("markets_performance", {})
    market_lines = ""
    for key, label in [
        ("EURUSD","EUR/USD 🇪🇺"), ("GBPUSD","GBP/USD 🇬🇧"), ("DXY","DXY 💵"),
        ("US100","US100 📊"),    ("US30","US30 🏭"),         ("WTI","WTI Oil 🛢"),
        ("GOLD","GOLD 🥇"),      ("USDCAD","USD/CAD 🇨🇦"),  ("BTC","BTC/USD ₿"),
    ]:
        m = markets.get(key, {})
        sig = signal_emoji.get(m.get("signal_tomorrow", "WAIT"), "🟡 WAIT")
        perf = m.get("performance", "")
        outlook = m.get("outlook", "")
        market_lines += (
            f"\n*{label}*\n"
            f"   📈 اليوم: {perf}\n"
            f"   {sig} غداً: {outlook}\n"
        )
    
    events = data.get("tomorrow_events", [])
    events_text = "\n".join([f"  ⚡ {e}" for e in events])
    
    msg = (
        f"🏆 *GOLDEN TRADING NEWS*\n"
        f"{'━'*30}\n"
        f"📋 *التقرير اليومي الشامل*\n"
        f"📅 {time_now}\n"
        f"{'─'*30}\n\n"
        f"📰 *ملخص اليوم:*\n{data.get('day_summary', '')}\n\n"
        f"🔥 *أبرز خبر اليوم:*\n{data.get('top_story', '')}\n"
        f"{'─'*30}\n"
        f"📊 *أداء الأسواق وتوقعات الغد:*\n"
        f"{'─'*30}\n"
        f"{market_lines}\n"
        f"{'─'*30}\n"
        f"📅 *أحداث مهمة غداً:*\n{events_text}\n\n"
        f"🔭 *النظرة العامة:*\n{data.get('overall_outlook', '')}\n"
        f"{'━'*30}\n"
        f"_تقرير GOLDEN TRADING NEWS — {time_now}_"
    )
    return msg


# ═══════════════════════════════════════════════════════════════
#  NEWS ALERT FORMAT
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
        f"📊 *تاثير الخبر على الاسواق:*\n\n"
        f"{market_lines}"
        f"{'─'*30}\n"
        f"🧠 *التحليل:*\n{analysis.get('overall_analysis', '')}\n\n"
        f"🔗 [قراءة الخبر]({article['link']})\n"
        f"{'━'*30}"
    )


# ═══════════════════════════════════════════════════════════════
#  TELEGRAM SENDER
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
#  SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════
async def check_and_send_news():
    logger.info("Checking for new trading news...")
    articles = fetch_news_from_sources()
    new_count = 0
    for article in articles[:5]:
        if article["id"] in seen_articles:
            continue
        analysis = analyze_news(article)
        if analysis and analysis.get("importance") in ["HIGH", "MEDIUM"]:
            message = format_news_alert(article, analysis)
            await send_telegram_message(message)
            daily_news_cache.append(article)
            new_count += 1
            await asyncio.sleep(3)
        seen_articles.add(article["id"])
    logger.info(f"News check done — Sent {new_count} alerts")


async def send_london_briefing():
    logger.info("Generating London session briefing...")
    await send_telegram_message(
        "🇬🇧 *جلسة لندن — جاري تحضير الملخص...*\n_يرجى الانتظار لحظة_ ⏳"
    )
    data = generate_session_briefing("LONDON")
    if data:
        msg = format_session_message("LONDON", data)
        await send_telegram_message(msg)
    else:
        await send_telegram_message("⚠️ تعذر تحضير ملخص جلسة لندن. يرجى المحاولة لاحقاً.")


async def send_newyork_briefing():
    logger.info("Generating New York session briefing...")
    await send_telegram_message(
        "🇺🇸 *جلسة نيويورك — جاري تحضير الملخص...*\n_يرجى الانتظار لحظة_ ⏳"
    )
    data = generate_session_briefing("NEWYORK")
    if data:
        msg = format_session_message("NEWYORK", data)
        await send_telegram_message(msg)
    else:
        await send_telegram_message("⚠️ تعذر تحضير ملخص جلسة نيويورك.")


async def send_evening_report():
    logger.info("Generating daily evening report...")
    await send_telegram_message(
        "📋 *التقرير اليومي — جاري التحضير...*\n_يرجى الانتظار لحظة_ ⏳"
    )
    data = generate_daily_report()
    if data:
        msg = format_daily_report(data)
        await send_telegram_message(msg)
        daily_news_cache.clear()  # Reset for next day
    else:
        await send_telegram_message("⚠️ تعذر تحضير التقرير اليومي.")



# ═══════════════════════════════════════════════════════════════
#  DAILY ECONOMIC CALENDAR — 07:00 UTC (08:00 Morocco)
# ═══════════════════════════════════════════════════════════════
def generate_economic_calendar() -> Optional[dict]:
    today = datetime.now(timezone.utc).strftime('%A %d %B %Y')
    prompt = f"""انت محلل مالي خبير. اليوم هو {today}.

قدم الاجندة الاقتصادية الكاملة لهذا اليوم — كل الاحداث والبيانات الاقتصادية المقررة اليوم.

اجب بـ JSON فقط:
{{
  "date": "{today}",
  "market_overview": "نظرة عامة على اليوم وما يجب توقعه",
  "events": [
    {{
      "time_utc": "وقت الحدث UTC",
      "time_morocco": "الوقت بتوقيت المغرب",
      "event": "اسم الحدث",
      "currency": "العملة او السوق المتأثر",
      "importance": "HIGH or MEDIUM or LOW",
      "previous": "القيمة السابقة",
      "forecast": "التوقعات",
      "expected_outcome": "BETTER or WORSE or INLINE",
      "expected_outcome_ar": "افضل من المتوقع or اسوا من المتوقع or كما متوقع",
      "probability": "نسبة احتمال الخروج ايجابي مثل 70%",
      "markets_impact": {{
        "EURUSD": "UP or DOWN or NEUTRAL",
        "GBPUSD": "UP or DOWN or NEUTRAL",
        "DXY": "UP or DOWN or NEUTRAL",
        "US100": "UP or DOWN or NEUTRAL",
        "US30": "UP or DOWN or NEUTRAL",
        "WTI": "UP or DOWN or NEUTRAL",
        "GOLD": "UP or DOWN or NEUTRAL",
        "USDCAD": "UP or DOWN or NEUTRAL",
        "BTC": "UP or DOWN or NEUTRAL"
      }},
      "analysis": "تحليل مختصر للحدث وتأثيره المتوقع"
    }}
  ],
  "most_important_event": "اهم حدث اليوم",
  "day_bias": "RISK_ON or RISK_OFF or NEUTRAL",
  "day_bias_ar": "شهية مخاطرة or نفور من المخاطرة or محايد",
  "trading_advice": "نصيحة تداول عامة لهذا اليوم"
}}"""

    text = call_groq(prompt, max_tokens=3000)
    if not text:
        return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)
    except:
        return None


def format_economic_calendar(data: dict) -> str:
    importance_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}
    direction_emoji = {"UP": "📈", "DOWN": "📉", "NEUTRAL": "➡️"}
    outcome_emoji = {"BETTER": "✅", "WORSE": "❌", "INLINE": "⚖️"}
    bias_emoji = {"RISK_ON": "🟢 شهية مخاطرة", "RISK_OFF": "🔴 نفور من المخاطرة", "NEUTRAL": "🟡 محايد"}

    events = data.get("events", [])
    events_text = ""

    for i, event in enumerate(events, 1):
        imp = event.get("importance", "LOW")
        imp_e = importance_emoji.get(imp, "⚪")
        out_e = outcome_emoji.get(event.get("expected_outcome", "INLINE"), "⚖️")
        prob = event.get("probability", "50%")
        
        # Market impacts
        impacts = event.get("markets_impact", {})
        impact_line = ""
        for key, label in [("EURUSD","EUR"), ("GBPUSD","GBP"), ("DXY","DXY"),
                            ("US100","NQ"), ("US30","DJ"), ("WTI","OIL"),
                            ("GOLD","XAU"), ("USDCAD","CAD"), ("BTC","BTC")]:
            d = impacts.get(key, "NEUTRAL")
            de = direction_emoji.get(d, "➡️")
            impact_line += f"{de}{label} "

        events_text += (
            f"\n{'─'*28}\n"
            f"{imp_e} *{event.get('event', '')}*\n"
            f"🕐 {event.get('time_morocco', '')} (المغرب) | {event.get('time_utc', '')} UTC\n"
            f"💱 {event.get('currency', '')}\n"
            f"📊 السابق: `{event.get('previous', 'N/A')}` | المتوقع: `{event.get('forecast', 'N/A')}`\n"
            f"{out_e} التوقع: {event.get('expected_outcome_ar', '')} | احتمال: {prob}\n"
            f"📉 التأثير: {impact_line}\n"
            f"💡 {event.get('analysis', '')}\n"
        )

    bias = data.get("day_bias", "NEUTRAL")
    bias_text = bias_emoji.get(bias, "🟡 محايد")
    time_now = datetime.now(timezone.utc).strftime('%d/%m/%Y')

    msg = (
        f"🏆 *GOLDEN TRADING NEWS*\n"
        f"{'━'*30}\n"
        f"📅 *الأجندة الاقتصادية اليومية*\n"
        f"🗓 {time_now} | 08:00 صباحاً (المغرب)\n"
        f"{'─'*30}\n\n"
        f"📌 *نظرة عامة على اليوم:*\n"
        f"{data.get('market_overview', '')}\n\n"
        f"🎯 *أهم حدث اليوم:* {data.get('most_important_event', '')}\n"
        f"🌡 *مزاج السوق المتوقع:* {bias_text}\n"
        f"{'─'*30}\n"
        f"⏰ *الأحداث الاقتصادية المقررة:*"
        f"{events_text}\n"
        f"{'─'*30}\n"
        f"💼 *نصيحة اليوم:*\n"
        f"{data.get('trading_advice', '')}\n"
        f"{'━'*30}"
    )
    return msg


async def send_economic_calendar():
    logger.info("Generating daily economic calendar...")
    await send_telegram_message(
        "📅 *الأجندة الاقتصادية — جاري التحضير...*\n_يرجى الانتظار لحظة_ ⏳"
    )
    data = generate_economic_calendar()
    if data:
        msg = format_economic_calendar(data)
        await send_telegram_message(msg)
    else:
        await send_telegram_message("⚠️ تعذر تحضير الأجندة الاقتصادية اليوم.")

# ═══════════════════════════════════════════════════════════════
#  SCHEDULER
# ═══════════════════════════════════════════════════════════════
def run_scheduler():
    # News check every 15 minutes
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(
        lambda: asyncio.run(check_and_send_news())
    )
    # 📅 Agenda — 07:00 Morocco = 06:00 UTC
    schedule.every().day.at("06:00").do(
        lambda: asyncio.run(send_economic_calendar())
    )
    # 🇬🇧 London — 08:00 Morocco = 07:00 UTC
    schedule.every().day.at("07:00").do(
        lambda: asyncio.run(send_london_briefing())
    )
    # 🇺🇸 New York — 14:00 Morocco = 13:00 UTC
    schedule.every().day.at("13:00").do(
        lambda: asyncio.run(send_newyork_briefing())
    )
    # 📋 Evening Report — 21:00 Morocco = 20:00 UTC
    schedule.every().day.at("20:00").do(
        lambda: asyncio.run(send_evening_report())
    )
    while True:
        schedule.run_pending()
        time.sleep(30)


async def send_startup_message():
    msg = (
        "🏆 *GOLDEN TRADING NEWS — FULL VERSION*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ البوت يعمل الان 24/7!\n\n"
        "🆕 *الميزات الجديدة:*\n"
        "📅 07:00 صباحاً — الأجندة الاقتصادية + توقعات الأخبار\n"
        "🇬🇧 08:00 صباحاً — ملخص جلسة لندن + BUY/SELL/WAIT\n"
        "🇺🇸 14:00 ظهراً — ملخص جلسة نيويورك + BUY/SELL/WAIT\n"
        "📋 21:00 مساءً — تقرير يومي شامل + توقعات الغد\n"
        "🚨 فور نشر اي خبر مهم — تحليل فوري كامل\n\n"
        "📊 *الاسواق:* EUR/USD | GBP/USD | DXY\n"
        "US100 | US30 | WTI | GOLD | USD/CAD | BTC\n\n"
        "📰 *المصادر:* 15 مصدر إخباري متخصص\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=msg,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Startup error: {e}")


async def main():
    logger.info("Starting GOLDEN TRADING NEWS BOT — FULL VERSION")
    await send_startup_message()
    
    # Send all missed reports immediately on startup
    logger.info("Sending missed daily reports...")
    await send_economic_calendar()
    await asyncio.sleep(3)
    await send_london_briefing()
    await asyncio.sleep(3)
    await check_and_send_news()
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Bot running 24/7")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
