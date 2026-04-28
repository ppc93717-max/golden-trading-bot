#!/usr/bin/env python3
"""
GOLDEN TRADING NEWS BOT
Telegram Bot for Financial News Analysis using OpenRouter AI
Runs 24/7 on Railway.app
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
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = "8761021544:AAF8PZfLjFoIblvSCkA5gk2cubFI2-Eto0E"
TELEGRAM_CHAT_ID = "7782912937"
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"
CHECK_INTERVAL_MINUTES = 15

# ═══════════════════════════════════════════════════════════════
#  NEWS SOURCES (RSS Feeds) - 15 Sources
# ═══════════════════════════════════════════════════════════════
NEWS_SOURCES = [
    # ── HIGH PRIORITY ──────────────────────────────────────────
    {"name": "Reuters Markets",    "url": "https://feeds.reuters.com/reuters/businessNews",                                                           "priority": "HIGH"},
    {"name": "MarketWatch",        "url": "https://feeds.marketwatch.com/marketwatch/marketpulse/",                                                   "priority": "HIGH"},
    {"name": "FXStreet",           "url": "https://www.fxstreet.com/rss/news",                                                                        "priority": "HIGH"},
    {"name": "ForexLive",          "url": "https://www.forexlive.com/feed/news",                                                                      "priority": "HIGH"},
    {"name": "Investing.com",      "url": "https://www.investing.com/rss/news.rss",                                                                   "priority": "HIGH"},
    {"name": "Forex Factory",      "url": "https://www.forexfactory.com/news?format=xml",                                                             "priority": "HIGH"},
    {"name": "MyFXBook News",      "url": "https://www.myfxbook.com/rss/forex-economic-calendar",                                                     "priority": "HIGH"},
    {"name": "Fed Reserve",        "url": "https://www.federalreserve.gov/feeds/press_all.xml",                                                       "priority": "HIGH"},
    {"name": "ECB News",           "url": "https://www.ecb.europa.eu/rss/press.html",                                                                 "priority": "HIGH"},
    # ── MEDIUM PRIORITY ────────────────────────────────────────
    {"name": "CNBC Markets",       "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",                     "priority": "MEDIUM"},
    {"name": "Yahoo Finance",      "url": "https://finance.yahoo.com/news/rssindex",                                                                  "priority": "MEDIUM"},
    {"name": "Kitco Gold",         "url": "https://www.kitco.com/rss/lo-news.xml",                                                                    "priority": "MEDIUM"},
    {"name": "OilPrice.com",       "url": "https://oilprice.com/rss/main",                                                                            "priority": "MEDIUM"},
    {"name": "CoinDesk BTC",       "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",                                                          "priority": "MEDIUM"},
    {"name": "Investing Forex",    "url": "https://www.investing.com/rss/news_285.rss",                                                               "priority": "MEDIUM"},
]

# ═══════════════════════════════════════════════════════════════
#  KEYWORDS TO MONITOR
# ═══════════════════════════════════════════════════════════════
HIGH_IMPACT_KEYWORDS = [
    # Key People & Institutions
    "trump", "powell", "yellen", "federal reserve", "fed",
    "lagarde", "ecb", "bank of england", "boe", "bailey",
    "opec", "saudi", "russia", "bessent", "g7", "g20", "imf", "world bank",
    # Economic Events
    "interest rate", "rate hike", "rate cut", "inflation", "cpi", "pce",
    "nonfarm payroll", "nfp", "gdp", "unemployment", "jobs report",
    "fomc", "monetary policy", "quantitative", "balance sheet",
    "tariff", "trade war", "sanctions", "trade deal", "recession",
    "stagflation", "debt ceiling", "default", "budget",
    # Market Keywords
    "gold", "oil", "crude", "wti", "brent",
    "bitcoin", "btc", "crypto", "ethereum",
    "dollar", "usd", "euro", "pound", "gbp", "eur", "cad",
    "nasdaq", "s&p", "dow jones", "sp500",
    "forex", "fx", "currency", "bond", "yield", "treasury",
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
seen_articles = set()


def is_relevant_news(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(keyword in text for keyword in HIGH_IMPACT_KEYWORDS)


def fetch_news_from_sources() -> list:
    all_news = []
    for source in NEWS_SOURCES:
        try:
            logger.info(f"Fetching: {source['name']}")
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


def analyze_news_with_openrouter(article: dict) -> Optional[dict]:
    prompt = f"""انت محلل مالي خبير في اسواق الفوركس والسلع والمؤشرات. حلل الخبر التالي:

المصدر: {article['source']}
العنوان: {article['title']}
الملخص: {article['summary']}

اجب بـ JSON فقط بدون اي نص خارجه:
{{
  "sentiment": "POSITIVE or NEGATIVE or NEUTRAL",
  "importance": "HIGH or MEDIUM or LOW",
  "summary_ar": "ملخص الخبر بالعربية في جملة واحدة",
  "markets": {{
    "EURUSD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "GBPUSD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "DXY":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "US100":  {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "US30":   {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "WTI":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "GOLD":   {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "USDCAD": {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}},
    "BTC":    {{"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب باختصار"}}
  }},
  "overall_analysis": "تحليل شامل للخبر وتاثيره على الاسواق في 2-3 جمل عربية"
}}"""

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://golden-trading-news-bot.com",
                    "X-Title": "Golden Trading News Bot"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1200,
                    "temperature": 0.3
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(text)
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return None


def format_telegram_message(article: dict, analysis: dict) -> str:
    sentiment = analysis.get("sentiment", "NEUTRAL")
    importance = analysis.get("importance", "MEDIUM")

    s_emoji = {"POSITIVE": "🟢", "NEGATIVE": "🔴", "NEUTRAL": "🟡"}.get(sentiment, "🟡")
    s_text  = {"POSITIVE": "ايجابي ✅", "NEGATIVE": "سلبي ❌", "NEUTRAL": "محايد ⚖️"}.get(sentiment, "محايد ⚖️")
    i_emoji = {"HIGH": "🔥🔥🔥 عالية", "MEDIUM": "⚡⚡ متوسطة", "LOW": "ℹ منخفضة"}.get(importance, "⚡⚡")
    d_emoji = {"UP": "📈", "DOWN": "📉", "NEUTRAL": "➡️"}
    s_word  = {"STRONG": "قوي 💪", "MODERATE": "متوسط", "WEAK": "ضعيف"}

    markets = analysis.get("markets", {})
    market_lines = ""
    for key, label in [
        ("EURUSD", "EUR/USD 🇪🇺"), ("GBPUSD", "GBP/USD 🇬🇧"), ("DXY",    "DXY 💵"),
        ("US100",  "US100 📊"),    ("US30",   "US30 🏭"),       ("WTI",    "WTI Oil 🛢"),
        ("GOLD",   "GOLD 🥇"),     ("USDCAD", "USD/CAD 🇨🇦"),  ("BTC",    "BTC/USD ₿"),
    ]:
        m  = markets.get(key, {})
        de = d_emoji.get(m.get("direction", "NEUTRAL"), "➡️")
        sw = s_word.get(m.get("strength", "MODERATE"), "متوسط")
        r  = m.get("reason", "")
        market_lines += f"{de} *{label}* — {sw}\n   {r}\n\n"

    msg = (
        f"🏆 *GOLDEN TRADING NEWS*\n"
        f"{'━'*30}\n"
        f"{s_emoji} *خبر عاجل* | {i_emoji}\n"
        f"{'─'*30}\n\n"
        f"📰 *المصدر:* {article['source']}\n"
        f"🕐 *الوقت:* {datetime.now(timezone.utc).strftime('%d/%m/%Y  %H:%M')} UTC\n\n"
        f"📌 *العنوان:*\n{article['title']}\n\n"
        f"💡 *الملخص:*\n{analysis.get('summary_ar', '')}\n\n"
        f"{s_emoji} *التوجه:* {s_text}\n"
        f"{'─'*30}\n"
        f"📊 *تاثير الخبر على الاسواق:*\n"
        f"{'─'*30}\n\n"
        f"{market_lines}"
        f"{'─'*30}\n"
        f"🧠 *التحليل الاساسي:*\n"
        f"{analysis.get('overall_analysis', '')}\n\n"
        f"🔗 [قراءة الخبر كاملاً]({article['link']})\n"
        f"{'━'*30}"
    )
    return msg


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
        logger.info("Message sent to Telegram")
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


async def check_and_send_news():
    logger.info("Checking for new trading news...")
    articles = fetch_news_from_sources()
    logger.info(f"Found {len(articles)} relevant articles")

    new_count = 0
    for article in articles[:5]:
        if article["id"] in seen_articles:
            continue
        logger.info(f"Analyzing: {article['title'][:60]}...")
        analysis = analyze_news_with_openrouter(article)
        if analysis and analysis.get("importance") in ["HIGH", "MEDIUM"]:
            message = format_telegram_message(article, analysis)
            await send_telegram_message(message)
            new_count += 1
            await asyncio.sleep(3)
        seen_articles.add(article["id"])

    logger.info(f"Done — Sent {new_count} alerts")


async def send_startup_message():
    msg = (
        "🏆 *GOLDEN TRADING NEWS*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ البوت يعمل الان 24/7 بنجاح!\n\n"
        "📊 *الاسواق المراقبة:*\n"
        "EUR/USD | GBP/USD | DXY\n"
        "US100 | US30 | WTI Oil\n"
        "GOLD | USD/CAD | BTC/USD\n\n"
        "📰 *مصادر الاخبار (15 مصدر):*\n"
        "Reuters | MarketWatch | FXStreet\n"
        "ForexLive | Forex Factory | MyFXBook\n"
        "Investing.com | CNBC | Yahoo Finance\n"
        "Fed Reserve | ECB | Kitco\n"
        "OilPrice | CoinDesk | Investing Forex\n\n"
        "⏱ فحص الاخبار كل *15 دقيقة*\n"
        "🔥 يُرسل فقط الاخبار المهمة مع تحليل كامل\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Startup message error: {e}")


def run_scheduler():
    def job():
        asyncio.run(check_and_send_news())
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(30)


async def main():
    logger.info("Starting GOLDEN TRADING NEWS BOT 24/7...")
    await send_startup_message()
    await check_and_send_news()
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info(f"Bot running 24/7 — checking every {CHECK_INTERVAL_MINUTES} minutes")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
