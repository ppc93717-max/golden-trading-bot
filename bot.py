#!/usr/bin/env python3
"""
GOLDEN TRADING NEWS BOT - ULTIMATE VERSION
✅ 18 news sources
✅ Comprehensive keywords for ALL central banks
✅ Pre-alerts 5 min before major events
✅ Special FOMC/BOE/ECB analysis
✅ Daily schedule: Agenda 07:00, London 08:00, NY 14:00, Report 21:00
✅ Smart startup - sends missed reports automatically
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
CHECK_INTERVAL_MINUTES = 10

# ═══════════════════════════════════════════════════════════════
#  18 NEWS SOURCES
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
    {"name": "DailyFX",           "url": "https://www.dailyfx.com/feeds/all",                    "priority": "HIGH"},
    {"name": "Fed Reserve",       "url": "https://www.federalreserve.gov/feeds/press_all.xml",   "priority": "HIGH"},
    {"name": "ECB News",          "url": "https://www.ecb.europa.eu/rss/press.html",             "priority": "HIGH"},
    {"name": "CNBC Markets",      "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "priority": "MEDIUM"},
    {"name": "Yahoo Finance",     "url": "https://finance.yahoo.com/news/rssindex",              "priority": "MEDIUM"},
    {"name": "Kitco Gold",        "url": "https://www.kitco.com/rss/lo-news.xml",                "priority": "MEDIUM"},
    {"name": "OilPrice.com",      "url": "https://oilprice.com/rss/main",                        "priority": "MEDIUM"},
    {"name": "CoinDesk BTC",      "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",      "priority": "MEDIUM"},
    {"name": "Nasdaq News",       "url": "https://www.nasdaq.com/feed/rssoutbound?category=Markets", "priority": "MEDIUM"},
    {"name": "EIA Energy",        "url": "https://www.eia.gov/rss/press_room.xml",               "priority": "MEDIUM"},
    # Trump & Officials monitoring
    {"name": "Trump TruthSocial",  "url": "https://trumpstruth.org/feed",                           "priority": "HIGH"},
    {"name": "Reuters Politics",   "url": "https://feeds.reuters.com/Reuters/PoliticsNews",          "priority": "HIGH"},
    {"name": "Bloomberg Politics", "url": "https://feeds.bloomberg.com/politics/news.rss",           "priority": "HIGH"},
    {"name": "Politico Economy",   "url": "https://rss.politico.com/economy.xml",                   "priority": "HIGH"},
    {"name": "WSJ Economy",        "url": "https://feeds.a.dj.com/rss/RSSEconomics.xml",            "priority": "HIGH"},
]

# ═══════════════════════════════════════════════════════════════
#  HIGH IMPACT EVENTS - Pre-alert triggers
# ═══════════════════════════════════════════════════════════════
HIGH_IMPACT_EVENTS = {
    # US Federal Reserve
    "fomc": {"name": "قرار الفيدرالي الأمريكي (FOMC)", "currency": "USD 🇺🇸", "emoji": "🏦🇺🇸"},
    "federal reserve": {"name": "قرار الفيدرالي الأمريكي", "currency": "USD 🇺🇸", "emoji": "🏦🇺🇸"},
    "fed rate": {"name": "قرار سعر الفائدة الأمريكي", "currency": "USD 🇺🇸", "emoji": "💰🇺🇸"},
    "powell": {"name": "خطاب رئيس الفيدرالي باول", "currency": "USD 🇺🇸", "emoji": "🎤🇺🇸"},
    # ECB
    "ecb rate": {"name": "قرار سعر الفائدة الأوروبي (ECB)", "currency": "EUR 🇪🇺", "emoji": "🏦🇪🇺"},
    "main refinancing rate": {"name": "سعر إعادة التمويل الأوروبي (ECB)", "currency": "EUR 🇪🇺", "emoji": "🏦🇪🇺"},
    "ecb press conference": {"name": "مؤتمر صحفي ECB — لاغارد", "currency": "EUR 🇪🇺", "emoji": "🎤🇪🇺"},
    "lagarde": {"name": "خطاب رئيسة ECB لاغارد", "currency": "EUR 🇪🇺", "emoji": "🎤🇪🇺"},
    "monetary policy statement": {"name": "بيان السياسة النقدية", "currency": "EUR/GBP", "emoji": "📋"},
    # BOE
    "official bank rate": {"name": "قرار سعر الفائدة البريطاني (BOE)", "currency": "GBP 🇬🇧", "emoji": "🏦🇬🇧"},
    "bank of england rate": {"name": "قرار بنك إنجلترا", "currency": "GBP 🇬🇧", "emoji": "🏦🇬🇧"},
    "mpc vote": {"name": "تصويت لجنة السياسة النقدية BOE", "currency": "GBP 🇬🇧", "emoji": "🏦🇬🇧"},
    "boe rate": {"name": "قرار بنك إنجلترا", "currency": "GBP 🇬🇧", "emoji": "🏦🇬🇧"},
    "bailey": {"name": "خطاب محافظ BOE بيلي", "currency": "GBP 🇬🇧", "emoji": "🎤🇬🇧"},
    "monetary policy report": {"name": "تقرير السياسة النقدية BOE", "currency": "GBP 🇬🇧", "emoji": "📋🇬🇧"},
    # US Data
    "nonfarm payroll": {"name": "بيانات الوظائف (NFP) 🔥", "currency": "USD 🇺🇸", "emoji": "👷🇺🇸"},
    "nfp": {"name": "تقرير الوظائف (NFP) 🔥", "currency": "USD 🇺🇸", "emoji": "👷🇺🇸"},
    "cpi": {"name": "مؤشر أسعار المستهلكين (CPI)", "currency": "USD 🇺🇸", "emoji": "📊🇺🇸"},
    "core cpi": {"name": "مؤشر CPI الأساسي", "currency": "USD 🇺🇸", "emoji": "📊🇺🇸"},
    "pce": {"name": "مؤشر PCE للتضخم", "currency": "USD 🇺🇸", "emoji": "📊🇺🇸"},
    "core pce": {"name": "مؤشر PCE الأساسي", "currency": "USD 🇺🇸", "emoji": "📊🇺🇸"},
    "gdp": {"name": "الناتج المحلي الإجمالي (GDP)", "currency": "USD 🇺🇸", "emoji": "📈🇺🇸"},
    "advance gdp": {"name": "أولى بيانات GDP", "currency": "USD 🇺🇸", "emoji": "📈🇺🇸"},
    "unemployment claims": {"name": "طلبات إعانة البطالة", "currency": "USD 🇺🇸", "emoji": "📋🇺🇸"},
    "employment cost": {"name": "مؤشر تكلفة التوظيف", "currency": "USD 🇺🇸", "emoji": "📋🇺🇸"},
    "ism manufacturing": {"name": "مؤشر ISM التصنيعي", "currency": "USD 🇺🇸", "emoji": "🏭🇺🇸"},
    "ism services": {"name": "مؤشر ISM الخدماتي", "currency": "USD 🇺🇸", "emoji": "🏢🇺🇸"},
    "chicago pmi": {"name": "مؤشر PMI شيكاغو", "currency": "USD 🇺🇸", "emoji": "📊🇺🇸"},
    "retail sales": {"name": "بيانات مبيعات التجزئة", "currency": "USD 🇺🇸", "emoji": "🛍️🇺🇸"},
    # EUR Data
    "cpi flash": {"name": "مؤشر CPI الأوروبي الأولي", "currency": "EUR 🇪🇺", "emoji": "📊🇪🇺"},
    "german gdp": {"name": "GDP الألماني", "currency": "EUR 🇪🇺", "emoji": "📈🇩🇪"},
    "german unemployment": {"name": "البطالة الألمانية", "currency": "EUR 🇪🇺", "emoji": "📋🇩🇪"},
    "eurozone gdp": {"name": "GDP منطقة اليورو", "currency": "EUR 🇪🇺", "emoji": "📈🇪🇺"},
    # GBP Data
    "uk cpi": {"name": "مؤشر CPI البريطاني", "currency": "GBP 🇬🇧", "emoji": "📊🇬🇧"},
    "uk gdp": {"name": "GDP البريطاني", "currency": "GBP 🇬🇧", "emoji": "📈🇬🇧"},
    "uk employment": {"name": "بيانات التوظيف البريطانية", "currency": "GBP 🇬🇧", "emoji": "👷🇬🇧"},
    # CAD & OIL
    "canada gdp": {"name": "GDP الكندي", "currency": "CAD 🇨🇦", "emoji": "📈🇨🇦"},
    "crude oil inventories": {"name": "مخزونات النفط الخام", "currency": "OIL 🛢️", "emoji": "🛢️"},
    "opec": {"name": "قرار أوبك", "currency": "OIL 🛢️", "emoji": "🛢️"},
    # Trump & Geopolitics
    "trump": {"name": "تصريح ترامب", "currency": "USD 🇺🇸", "emoji": "🇺🇸"},
    "tariff": {"name": "قرار رسوم جمركية", "currency": "USD 🇺🇸", "emoji": "⚠️🇺🇸"},
    "trade war": {"name": "تطور في الحرب التجارية", "currency": "USD 🇺🇸", "emoji": "⚔️"},
}

# ═══════════════════════════════════════════════════════════════
#  COMPREHENSIVE KEYWORDS
# ═══════════════════════════════════════════════════════════════
HIGH_IMPACT_KEYWORDS = [
    # Central Banks & Officials
    "federal reserve", "fed", "fomc", "powell", "fed rate",
    "ecb", "european central bank", "lagarde", "ecb rate", "main refinancing",
    "bank of england", "boe", "bailey", "mpc", "official bank rate",
    "monetary policy", "monetary policy report", "monetary policy summary",
    "monetary policy statement", "interest rate", "rate decision",
    "rate hike", "rate cut", "basis points", "bps",
    "bank of japan", "boj", "ueda", "bank of canada", "boc",
    "reserve bank", "rba", "snb", "swiss national bank",
    # US Economic Data
    "nonfarm payroll", "nfp", "jobs report", "employment",
    "unemployment", "unemployment claims", "jobless claims",
    "cpi", "core cpi", "inflation", "deflation",
    "pce", "core pce", "personal consumption",
    "gdp", "advance gdp", "gross domestic product",
    "retail sales", "core retail sales",
    "ism manufacturing", "ism services", "pmi",
    "chicago pmi", "empire state", "philly fed",
    "housing starts", "building permits", "existing home sales",
    "consumer confidence", "consumer sentiment", "michigan",
    "durable goods", "factory orders", "trade balance",
    "employment cost", "productivity", "unit labor costs",
    # EUR Economic Data
    "cpi flash", "cpi estimate", "flash gdp", "prelim gdp",
    "german gdp", "german cpi", "german unemployment", "german ifo",
    "eurozone gdp", "eurozone cpi", "eurozone unemployment",
    "eurozone pmi", "eurozone retail", "eurozone inflation",
    "french gdp", "french cpi", "italian gdp",
    "zew", "ifo", "sentix",
    # GBP Economic Data
    "uk cpi", "uk gdp", "uk pmi", "uk employment",
    "uk retail sales", "uk inflation", "uk unemployment",
    "claimant count", "average earnings",
    # Commodities & Markets
    "gold", "xauusd", "silver",
    "oil", "crude oil", "wti", "brent", "opec",
    "crude oil inventories", "eia", "energy",
    "bitcoin", "btc", "crypto", "ethereum",
    "nasdaq", "s&p 500", "sp500", "dow jones", "russell",
    # Geopolitics & Trade
    "trump", "tariff", "trade war", "sanctions", "trade deal",
    "trade deficit", "trade surplus",
    "geopolitical", "war", "conflict", "ceasefire",
    "china", "russia", "ukraine", "middle east",
    "g7", "g20", "imf", "world bank", "bis",
    # FX & General
    "dollar", "usd", "euro", "eur", "pound", "gbp",
    "yen", "jpy", "cad", "aud", "nzd", "chf",
    "forex", "fx", "currency", "exchange rate",
    "bond", "yield", "treasury", "10-year", "2-year",
    "recession", "stagflation", "gdp growth", "economic growth",
    "earnings", "revenue", "profit", "eps",
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
seen_articles = set()
daily_news_cache = []
sent_pre_alerts = set()


# ═══════════════════════════════════════════════════════════════
#  GROQ API
# ═══════════════════════════════════════════════════════════════
def call_openrouter(prompt: str, max_tokens: int = 1500) -> Optional[str]:
    models = [GROQ_MODEL, GROQ_FALLBACK]
    for model in models:
        try:
            logger.info(f"Calling Groq: {model}")
            with httpx.Client(timeout=90) as client:
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
                    time.sleep(3)
                    continue
                if response.status_code != 200:
                    logger.error(f"Groq error {response.status_code}: {response.text[:200]}")
                    continue
                data = response.json()
                if "choices" in data and data["choices"]:
                    result = data["choices"][0]["message"]["content"].strip()
                    if result:
                        logger.info(f"Groq success: {model}")
                        return result
        except Exception as e:
            logger.error(f"Groq error {model}: {e}")
    logger.error("All Groq models failed!")
    return None


def parse_json_response(text: str) -> Optional[dict]:
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)
    except:
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


def is_fomc_or_central_bank(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    triggers = [
        "fomc", "federal reserve rate", "fed rate", "interest rate decision",
        "rate decision", "official bank rate", "main refinancing rate",
        "boe rate", "ecb rate", "bank rate", "powell speaks", "lagarde speaks",
        "bailey speaks", "mpc vote", "nonfarm payroll", "nfp report",
        "cpi report", "inflation report", "gdp report", "advance gdp",
        "monetary policy statement", "monetary policy report",
    ]
    return any(t in text for t in triggers)


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
                summary = re.sub(r'<[^>]+>', '', entry.get("summary", entry.get("description", "")))[:600]
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
#  ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════
MARKETS_JSON = '''{
    "EURUSD": {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "GBPUSD": {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "DXY":    {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "US100":  {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "US30":   {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "WTI":    {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "GOLD":   {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "USDCAD": {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"},
    "BTC":    {"direction": "UP or DOWN or NEUTRAL", "strength": "STRONG or MODERATE or WEAK", "reason": "السبب"}
}'''


def analyze_news(article: dict) -> Optional[dict]:
    prompt = f"""انت محلل مالي خبير متخصص في الفوركس والسلع والمؤشرات. حلل هذا الخبر:

المصدر: {article['source']}
العنوان: {article['title']}
الملخص: {article['summary']}

اجب بـ JSON فقط:
{{
  "sentiment": "POSITIVE or NEGATIVE or NEUTRAL",
  "importance": "HIGH or MEDIUM or LOW",
  "summary_ar": "ملخص الخبر بالعربية",
  "markets": {MARKETS_JSON},
  "overall_analysis": "تحليل شامل في 2-3 جمل"
}}"""
    text = call_openrouter(prompt, 1200)
    if not text:
        return None
    return parse_json_response(text)


def analyze_central_bank_event(article: dict) -> Optional[dict]:
    prompt = f"""انت محلل مالي خبير متخصص في قرارات البنوك المركزية والأحداث الاقتصادية الكبرى.

هذا حدث اقتصادي عالي الأهمية جداً — قرار بنك مركزي أو بيانات اقتصادية كبرى.

المصدر: {article['source']}
العنوان: {article['title']}
التفاصيل: {article['summary']}

قدم تحليلاً شاملاً ومفصلاً. اجب بـ JSON فقط:
{{
  "event_type": "نوع الحدث (مثل: قرار BOE / قرار ECB / NFP / GDP)",
  "result": "النتيجة بالأرقام إذا متاحة",
  "vs_expected": "أفضل من المتوقع / أسوأ من المتوقع / كما متوقع",
  "sentiment": "POSITIVE or NEGATIVE or NEUTRAL",
  "summary_ar": "ملخص تفصيلي للحدث في 2-3 جمل",
  "key_points": ["نقطة مهمة 1", "نقطة مهمة 2", "نقطة مهمة 3", "نقطة مهمة 4"],
  "markets": {MARKETS_JSON},
  "overall_analysis": "تحليل شامل ومفصل للحدث وتأثيره الفوري والمتوسط المدى في 3-4 جمل",
  "trading_recommendation": "توصية تداول مباشرة بناءً على هذا الحدث"
}}"""
    text = call_openrouter(prompt, 2000)
    if not text:
        return None
    return parse_json_response(text)


# ═══════════════════════════════════════════════════════════════
#  MESSAGE FORMATTERS
# ═══════════════════════════════════════════════════════════════
D_EMOJI = {"UP": "📈", "DOWN": "📉", "NEUTRAL": "➡️"}
S_WORD = {"STRONG": "قوي 💪", "MODERATE": "متوسط", "WEAK": "ضعيف"}
SIG_EMOJI = {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "WAIT": "🟡 WAIT"}
SENT_EMOJI = {"POSITIVE": "🟢", "NEGATIVE": "🔴", "NEUTRAL": "🟡"}
SENT_TEXT = {"POSITIVE": "إيجابي ✅", "NEGATIVE": "سلبي ❌", "NEUTRAL": "محايد ⚖️"}
IMP_EMOJI = {"HIGH": "🔥🔥🔥", "MEDIUM": "⚡⚡", "LOW": "ℹ️"}

MARKET_LABELS = [
    ("EURUSD","EUR/USD 🇪🇺"), ("GBPUSD","GBP/USD 🇬🇧"), ("DXY","DXY 💵"),
    ("US100","US100 📊"),    ("US30","US30 🏭"),         ("WTI","WTI Oil 🛢"),
    ("GOLD","GOLD 🥇"),      ("USDCAD","USD/CAD 🇨🇦"),  ("BTC","BTC/USD ₿"),
]

def build_market_lines_news(markets: dict) -> str:
    lines = ""
    for key, label in MARKET_LABELS:
        m = markets.get(key, {})
        de = D_EMOJI.get(m.get("direction", "NEUTRAL"), "➡️")
        sw = S_WORD.get(m.get("strength", "MODERATE"), "متوسط")
        r = m.get("reason", "")
        lines += f"{de} *{label}* — {sw}\n   {r}\n\n"
    return lines

def build_market_lines_session(markets: dict) -> str:
    lines = ""
    for key, label in MARKET_LABELS:
        m = markets.get(key, {})
        sig = SIG_EMOJI.get(m.get("signal", "WAIT"), "🟡 WAIT")
        lines += f"\n{sig} *{label}*\n   📍 {m.get('key_level','')}\n   📌 {m.get('reason','')}\n"
    return lines

def build_market_lines_report(markets: dict) -> str:
    lines = ""
    for key, label in MARKET_LABELS:
        m = markets.get(key, {})
        sig = SIG_EMOJI.get(m.get("signal_tomorrow", "WAIT"), "🟡 WAIT")
        lines += f"\n*{label}*\n   📈 اليوم: {m.get('performance','')}\n   {sig} غداً: {m.get('outlook','')}\n"
    return lines

def time_now_str():
    return datetime.now(timezone.utc).strftime('%d/%m/%Y  %H:%M') + " UTC"

def date_str():
    return datetime.now(timezone.utc).strftime('%d/%m/%Y')


def format_pre_alert(event_info: dict, article: dict) -> str:
    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"⚠️ *تنبيه — خبر مهم خلال دقائق!*\n{'─'*30}\n\n"
        f"{event_info['emoji']} *{event_info['name']}*\n\n"
        f"💱 *العملة المتأثرة:* {event_info['currency']}\n"
        f"📰 *المصدر:* {article['source']}\n"
        f"🕐 {time_now_str()}\n\n"
        f"📌 {article['title']}\n\n"
        f"⚡ *استعد! سيصلك التحليل الكامل فور صدور الخبر*\n"
        f"{'━'*30}"
    )


def format_news_alert(article: dict, analysis: dict) -> str:
    sentiment = analysis.get("sentiment", "NEUTRAL")
    importance = analysis.get("importance", "MEDIUM")
    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"🚨 *خبر عاجل* {IMP_EMOJI.get(importance,'⚡')}\n{'─'*30}\n\n"
        f"📰 *المصدر:* {article['source']}\n"
        f"🕐 {time_now_str()}\n\n"
        f"📌 *العنوان:*\n{article['title']}\n\n"
        f"💡 *الملخص:*\n{analysis.get('summary_ar','')}\n\n"
        f"{SENT_EMOJI.get(sentiment,'🟡')} *التوجه:* {SENT_TEXT.get(sentiment,'محايد')}\n"
        f"{'─'*30}\n📊 *تأثير على الأسواق:*\n\n"
        f"{build_market_lines_news(analysis.get('markets',{}))}"
        f"{'─'*30}\n🧠 *التحليل:*\n{analysis.get('overall_analysis','')}\n\n"
        f"🔗 [قراءة الخبر]({article['link']})\n{'━'*30}"
    )


def format_central_bank_alert(article: dict, analysis: dict) -> str:
    sentiment = analysis.get("sentiment", "NEUTRAL")
    key_points = "\n".join([f"  • {p}" for p in analysis.get("key_points", [])])
    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"🚨🔥 *حدث اقتصادي كبير جداً* 🔥🚨\n{'─'*30}\n\n"
        f"🎯 *{analysis.get('event_type','حدث مهم')}*\n"
        f"📊 *النتيجة:* {analysis.get('result','N/A')}\n"
        f"📌 *مقارنة بالتوقعات:* {analysis.get('vs_expected','')}\n"
        f"{SENT_EMOJI.get(sentiment,'🟡')} *التوجه:* {SENT_TEXT.get(sentiment,'محايد')}\n\n"
        f"💡 *الملخص:*\n{analysis.get('summary_ar','')}\n\n"
        f"🔑 *النقاط المهمة:*\n{key_points}\n"
        f"{'─'*30}\n📊 *تأثير على الأسواق:*\n\n"
        f"{build_market_lines_news(analysis.get('markets',{}))}"
        f"{'─'*30}\n🧠 *التحليل الشامل:*\n{analysis.get('overall_analysis','')}\n\n"
        f"💼 *توصية التداول:*\n{analysis.get('trading_recommendation','')}\n\n"
        f"🔗 [قراءة التفاصيل]({article['link']})\n{'━'*30}"
    )


# ═══════════════════════════════════════════════════════════════
#  SESSION BRIEFING
# ═══════════════════════════════════════════════════════════════
def generate_session_briefing(session: str) -> Optional[dict]:
    session_ar = "لندن 🇬🇧" if session == "LONDON" else "نيويورك 🇺🇸"
    prompt = f"""انت محلل مالي خبير. قدم ملخص جلسة {session_ar} الآن مع توصيات واضحة BUY/SELL/WAIT.

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
  "risk_warning": "تحذير مخاطر مهم للجلسة",
  "events_to_watch": ["حدث1", "حدث2", "حدث3"]
}}"""
    text = call_openrouter(prompt, 2000)
    if not text:
        return None
    return parse_json_response(text)


def format_session_message(session: str, data: dict) -> str:
    is_london = session == "LONDON"
    header = "🇬🇧 صباح الخير — جلسة لندن" if is_london else "🇺🇸 جلسة نيويورك"
    mood = {"BULLISH": "🟢 صاعد", "BEARISH": "🔴 هابط", "NEUTRAL": "🟡 محايد"}.get(data.get("market_mood","NEUTRAL"), "🟡 محايد")
    themes = "\n".join([f"  • {t}" for t in data.get("key_themes",[])])
    events = "\n".join([f"  ⚡ {e}" for e in data.get("events_to_watch",[])])
    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"{header}\n🕐 {time_now_str()}\n{'─'*30}\n\n"
        f"📊 *مزاج السوق:* {mood}\n\n"
        f"🎯 *المواضيع الرئيسية:*\n{themes}\n"
        f"{'─'*30}\n💹 *توصيات — BUY / SELL / WAIT:*\n{'─'*30}\n"
        f"{build_market_lines_session(data.get('markets',{}))}\n"
        f"{'─'*30}\n📅 *أحداث يجب مراقبتها:*\n{events}\n\n"
        f"⚠️ *تحذير:*\n{data.get('risk_warning','')}\n{'━'*30}"
    )


# ═══════════════════════════════════════════════════════════════
#  ECONOMIC CALENDAR
# ═══════════════════════════════════════════════════════════════
def fetch_real_calendar_events() -> list:
    """Fetch real economic events from multiple calendar sources"""
    events = []
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Sources that actually work for economic calendar RSS
    calendar_sources = [
        {
            "name": "MyFXBook Calendar",
            "url": "https://www.myfxbook.com/rss/forex-economic-calendar",
        },
        {
            "name": "Investing Economic Calendar", 
            "url": "https://www.investing.com/rss/news_301.rss",
        },
        {
            "name": "FXStreet Calendar",
            "url": "https://www.fxstreet.com/rss/economic-calendar",
        },
        {
            "name": "ForexLive Calendar",
            "url": "https://www.forexlive.com/feed/economic-calendar",
        },
    ]
    
    high_kw = [
        "interest rate", "nfp", "nonfarm payroll", "cpi", "gdp", "fomc",
        "ecb rate", "boe rate", "official bank rate", "main refinancing",
        "fed rate", "pce", "unemployment claims", "inflation report",
        "monetary policy", "rate decision", "powell", "lagarde", "bailey",
    ]
    med_kw = [
        "pmi", "ism", "retail sales", "housing", "consumer confidence",
        "employment", "trade balance", "gdp prelim", "flash gdp",
        "sentix", "zew", "ifo", "jobless claims", "durable goods",
        "chicago pmi", "factory orders", "building permits",
    ]
    
    seen_events = set()
    
    for source in calendar_sources:
        try:
            logger.info(f"Fetching calendar from: {source['name']}")
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                if not title or title in seen_events:
                    continue
                    
                summary = re.sub(r'<[^>]+>', '', 
                    entry.get("summary", entry.get("description", "")))[:300]
                
                t_lower = (title + " " + summary).lower()
                importance = "LOW"
                if any(k in t_lower for k in high_kw):
                    importance = "HIGH"
                elif any(k in t_lower for k in med_kw):
                    importance = "MEDIUM"
                
                if importance in ["HIGH", "MEDIUM"]:
                    seen_events.add(title)
                    events.append({
                        "event": title,
                        "summary": summary,
                        "importance": importance,
                        "source": source["name"],
                        "time_utc": entry.get("published", ""),
                    })
        except Exception as e:
            logger.error(f"Calendar fetch error from {source['name']}: {e}")
    
    logger.info(f"Real calendar: found {len(events)} events total")
    return events


def generate_economic_calendar() -> Optional[dict]:
    today = datetime.now(timezone.utc).strftime('%A %d %B %Y')
    
    # Get real events from Forex Factory
    ff_events = fetch_real_calendar_events()
    ff_text = ""
    if ff_events:
        ff_text = "\n\nأحداث اقتصادية حقيقية مؤكدة اليوم (من MyFXBook/FXStreet/ForexLive):\n"
        for ev in ff_events[:15]:
            ff_text += f"- [{ev['importance']}] {ev['event']}\n"
    else:
        ff_text = "\n\nملاحظة: لم يتم العثور على أحداث اقتصادية مجدولة اليوم من المصادر الحقيقية. قد يكون اليوم هادئاً أو عطلة."
    
    prompt = f"""انت محلل مالي خبير. اليوم {today}.{ff_text}

قدم الأجندة الاقتصادية الكاملة لهذا اليوم بما فيها:
- قرارات البنوك المركزية (Fed/ECB/BOE وغيرها)
- البيانات الاقتصادية المهمة (NFP/CPI/GDP/PMI وغيرها)
- خطابات المسؤولين المهمة

اجب بـ JSON فقط:
{{
  "market_overview": "نظرة عامة على اليوم",
  "events": [
    {{
      "time_utc": "وقت UTC",
      "time_morocco": "الوقت بتوقيت المغرب UTC+1",
      "event": "اسم الحدث",
      "currency": "العملة",
      "importance": "HIGH or MEDIUM or LOW",
      "previous": "القيمة السابقة",
      "forecast": "التوقعات",
      "expected_outcome_ar": "أفضل من المتوقع or أسوأ من المتوقع or كما متوقع",
      "probability": "70%",
      "markets_impact": {{
        "EURUSD": "UP or DOWN or NEUTRAL",
        "GBPUSD": "UP or DOWN or NEUTRAL",
        "DXY": "UP or DOWN or NEUTRAL",
        "GOLD": "UP or DOWN or NEUTRAL",
        "US100": "UP or DOWN or NEUTRAL"
      }},
      "analysis": "تحليل مختصر للحدث"
    }}
  ],
  "most_important_event": "أهم حدث اليوم",
  "day_bias": "RISK_ON or RISK_OFF or NEUTRAL",
  "trading_advice": "نصيحة تداول عامة لهذا اليوم"
}}"""
    text = call_openrouter(prompt, 3000)
    if not text:
        return None
    return parse_json_response(text)


def format_economic_calendar(data: dict) -> str:
    imp_e = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}
    d_e = {"UP": "📈", "DOWN": "📉", "NEUTRAL": "➡️"}
    bias = {"RISK_ON": "🟢 شهية مخاطرة", "RISK_OFF": "🔴 نفور مخاطرة", "NEUTRAL": "🟡 محايد"}.get(data.get("day_bias","NEUTRAL"), "🟡")

    events_text = ""
    for event in data.get("events", []):
        impacts = event.get("markets_impact", {})
        impact_line = " ".join([f"{d_e.get(v,'➡️')}{k}" for k,v in impacts.items()])
        events_text += (
            f"\n{'─'*28}\n"
            f"{imp_e.get(event.get('importance','LOW'),'⚪')} *{event.get('event','')}*\n"
            f"🕐 {event.get('time_morocco','')} (المغرب) | {event.get('time_utc','')} UTC\n"
            f"💱 {event.get('currency','')} | السابق: `{event.get('previous','N/A')}` | المتوقع: `{event.get('forecast','N/A')}`\n"
            f"📌 {event.get('expected_outcome_ar','')} | {event.get('probability','')}\n"
            f"📊 {impact_line}\n"
            f"💡 {event.get('analysis','')}\n"
        )

    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"📅 *الأجندة الاقتصادية اليومية*\n"
        f"🗓 {date_str()} | 07:00 صباحاً (المغرب)\n{'─'*30}\n\n"
        f"📌 *نظرة عامة:*\n{data.get('market_overview','')}\n\n"
        f"🎯 *أهم حدث اليوم:* {data.get('most_important_event','')}\n"
        f"🌡 *مزاج السوق المتوقع:* {bias}\n"
        f"{'─'*30}\n⏰ *الأحداث الاقتصادية:*"
        f"{events_text}\n{'─'*30}\n"
        f"💼 *نصيحة اليوم:*\n{data.get('trading_advice','')}\n{'━'*30}"
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
  "top_story": "أهم خبر أثر على الأسواق اليوم",
  "markets_performance": {{
    "EURUSD": {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "GBPUSD": {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "DXY":    {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "US100":  {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "US30":   {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "WTI":    {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "GOLD":   {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "USDCAD": {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}},
    "BTC":    {{"performance": "أداء اليوم", "signal_tomorrow": "BUY or SELL or WAIT", "outlook": "توقعات الغد"}}
  }},
  "tomorrow_events": ["حدث مهم غداً 1", "حدث مهم غداً 2", "حدث مهم غداً 3"],
  "overall_outlook": "نظرة عامة على الغد والأسبوع القادم"
}}"""
    text = call_openrouter(prompt, 2500)
    if not text:
        return None
    return parse_json_response(text)


def format_daily_report(data: dict) -> str:
    events = "\n".join([f"  ⚡ {e}" for e in data.get("tomorrow_events",[])])
    return (
        f"🏆 *GOLDEN TRADING NEWS*\n{'━'*30}\n"
        f"📋 *التقرير اليومي الشامل*\n📅 {date_str()}\n{'─'*30}\n\n"
        f"📰 *ملخص اليوم:*\n{data.get('day_summary','')}\n\n"
        f"🔥 *أبرز خبر اليوم:*\n{data.get('top_story','')}\n"
        f"{'─'*30}\n📊 *أداء الأسواق وتوقعات الغد:*\n{'─'*30}\n"
        f"{build_market_lines_report(data.get('markets_performance',{}))}\n"
        f"{'─'*30}\n📅 *أحداث مهمة غداً:*\n{events}\n\n"
        f"🔭 *النظرة العامة:*\n{data.get('overall_outlook','')}\n"
        f"{'━'*30}\n_تقرير GOLDEN TRADING NEWS — {date_str()}_"
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
        logger.info("Message sent to Telegram")
    except Exception as e:
        logger.error(f"Telegram error: {e}")


# ═══════════════════════════════════════════════════════════════
#  MAIN TASKS
# ═══════════════════════════════════════════════════════════════
async def check_and_send_news():
    logger.info("Checking for new trading news...")
    articles = fetch_news_from_sources()
    new_count = 0

    for article in articles[:6]:
        if article["id"] in seen_articles:
            continue

        title = article["title"]
        summary = article["summary"]

        # Pre-alert for high impact events
        event_info = is_high_impact_event(title, summary)
        pre_alert_key = article["id"] + "_pre"
        if event_info and pre_alert_key not in sent_pre_alerts:
            pre_msg = format_pre_alert(event_info, article)
            await send_telegram_message(pre_msg)
            sent_pre_alerts.add(pre_alert_key)
            await asyncio.sleep(2)

        # Choose analysis type
        if is_fomc_or_central_bank(title, summary):
            analysis = analyze_central_bank_event(article)
            if analysis:
                msg = format_central_bank_alert(article, analysis)
                await send_telegram_message(msg)
                daily_news_cache.append(article)
                new_count += 1
        else:
            analysis = analyze_news(article)
            if analysis and analysis.get("importance") in ["HIGH", "MEDIUM"]:
                msg = format_news_alert(article, analysis)
                await send_telegram_message(msg)
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
async def run_async_scheduler():
    """Pure async scheduler - no threads, no freezing"""
    logger.info("Async scheduler started")
    
    last_news_check = datetime.now(timezone.utc)
    last_calendar_day = -1
    last_london_day = -1
    last_ny_day = -1
    last_report_day = -1

    while True:
        try:
            now = datetime.now(timezone.utc)
            morocco_hour = (now.hour + 1) % 24
            morocco_minute = now.minute
            today = now.day

            # News check every 10 minutes
            if (now - last_news_check).total_seconds() >= CHECK_INTERVAL_MINUTES * 60:
                last_news_check = now
                await check_and_send_news()

            # 07:00 Morocco = 06:00 UTC — Economic Calendar
            if morocco_hour == 7 and morocco_minute < 10 and last_calendar_day != today:
                last_calendar_day = today
                await send_economic_calendar()

            # 08:00 Morocco = 07:00 UTC — London Briefing
            if morocco_hour == 8 and morocco_minute < 10 and last_london_day != today:
                last_london_day = today
                await send_london_briefing()

            # 14:00 Morocco = 13:00 UTC — NY Briefing
            if morocco_hour == 14 and morocco_minute < 10 and last_ny_day != today:
                last_ny_day = today
                await send_newyork_briefing()

            # 21:00 Morocco = 20:00 UTC — Evening Report
            if morocco_hour == 21 and morocco_minute < 10 and last_report_day != today:
                last_report_day = today
                await send_evening_report()

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(60)  # Check every minute


async def send_startup_message():
    msg = (
        "🏆 *GOLDEN TRADING NEWS — ULTIMATE VERSION*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ البوت يعمل الآن 24/7!\n\n"
        "📅 *الجدول اليومي (بتوقيت المغرب):*\n"
        "⏰ 07:00 — الأجندة الاقتصادية الكاملة\n"
        "🇬🇧 08:00 — ملخص جلسة لندن + BUY/SELL/WAIT\n"
        "🇺🇸 14:00 — ملخص جلسة نيويورك + BUY/SELL/WAIT\n"
        "📋 21:00 — التقرير اليومي الشامل\n\n"
        "🚨 *فوري — تغطية شاملة:*\n"
        "⚠️ تنبيه قبل الأخبار الكبيرة\n"
        "🏦 تحليل خاص: Fed/ECB/BOE/NFP/CPI/GDP\n"
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
    logger.info("Starting GOLDEN TRADING NEWS BOT — ULTIMATE VERSION")
    await send_startup_message()

    # Smart startup — send missed reports based on Morocco time (UTC+1)
    now_utc = datetime.now(timezone.utc)
    morocco_hour = (now_utc.hour + 1) % 24
    logger.info(f"Morocco time: {morocco_hour}:00 — checking missed reports...")

    if morocco_hour >= 7:
        logger.info("Sending missed economic calendar...")
        await send_economic_calendar()
        await asyncio.sleep(5)

    if morocco_hour >= 8:
        logger.info("Sending missed London briefing...")
        await send_london_briefing()
        await asyncio.sleep(5)

    if morocco_hour >= 14:
        logger.info("Sending missed NY briefing...")
        await send_newyork_briefing()
        await asyncio.sleep(5)

    await check_and_send_news()

    # Use pure async scheduler — no threads, no freezing
    logger.info("Bot running 24/7 with async scheduler")
    await run_async_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
