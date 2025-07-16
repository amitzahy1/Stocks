import os
import time
import schedule
import yfinance as yf
import requests
from datetime import datetime
from twilio.rest import Client

# ==== ENVIRONMENT VARIABLES ====
ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
TO_NUMBER = os.getenv("TO_NUMBER")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ==== CONFIG ====
ALERT_THRESHOLDS = [3, 6, 9, 12]
notified_today = {}

# ==== PORTFOLIO ====
portfolio = {
    "NVDA": {"buy_price_nis": 590.0, "usd_at_buy": 3.72},
    "AAPL": {"buy_price_nis": 520.0, "usd_at_buy": 3.68},
    "QQQM": {"buy_price_nis": 225.0, "usd_at_buy": 3.75}
}

# ==== FUNCTIONS ====

def fetch_usd_ils():
    fx = yf.Ticker("USDILS=X")
    return fx.history(period="1d")["Close"].iloc[-1]

def get_sentiment_score(ticker):
    url = f"https://newsapi.org/v2/everything?q={ticker}&apiKey=demo"  # החלף ב-API Key משלך
    try:
        response = requests.get(url)
        articles = response.json().get("articles", [])
        positives = [a for a in articles if any(word in a["title"].lower() for word in ["beat", "surge", "gain", "growth"])]
        negatives = [a for a in articles if any(word in a["title"].lower() for word in ["miss", "drop", "loss", "fall"])]
        total = len(articles)
        if total == 0:
            return "ניטרלי"
        score = (len(positives) - len(negatives)) / total
        if score > 0.2:
            return "חיובי"
        elif score < -0.2:
            return "שלילי"
        else:
            return "ניטרלי"
    except:
        return "לא זמין"

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs)).iloc[-1]

def get_technical_analysis(ticker):
    data = yf.Ticker(ticker).history(period="6mo")
    if len(data) < 200:
        return "לא מספיק נתונים לניתוח טכני"
    closes = data["Close"]
    ma50 = closes.rolling(50).mean().iloc[-1]
    ma200 = closes.rolling(200).mean().iloc[-1]
    rsi = compute_rsi(closes)
    current = closes.iloc[-1]
    direction = "⬆️" if current > ma50 else "⬇️"
    return f"{direction} RSI: {rsi:.1f}, MA50: {ma50:.2f}, MA200: {ma200:.2f}"

def fetch_analyst_rating(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get("recommendationKey", "לא זמין")
    except:
        return "לא זמין"

def compare_to_sp500(change):
    sp = yf.Ticker("^GSPC").history(period="1d")
    sp_change = sp["Close"].pct_change().iloc[-1] * 100
    return change - sp_change

def build_message(ticker, change, price_nis, gain_nom, gain_real, sentiment, tech, rating, vs_sp500):
    return f"""
🚨 *שינוי חריג בתיק ההשקעות* 🚨

📍 *מניה:* {ticker}
⬆️ *שינוי יומי:* {change:.2f}%
📈 *תשואה נומינלית:* {gain_nom:.2%}
📉 *תשואה ריאלית:* {gain_real:.2%}
💸 *מחיר נוכחי:* ₪{price_nis:.2f}

🧠 *סנטימנט:* {sentiment}
📊 *ניתוח טכני:* {tech}
🧾 *המלצת אנליסטים:* {rating}
📈 *יחס ל-S&P 500:* {vs_sp500:.2f}%
"""

def send_whatsapp(msg):
    try:
        message = client.messages.create(
            body=msg,
            from_=TWILIO_NUMBER,
            to=TO_NUMBER
        )
        print("הודעה נשלחה ✔️")
    except Exception as e:
        print("שגיאה בשליחה:", e)

# ==== CORE ====
def check_portfolio():
    usd_now = fetch_usd_ils()
    for ticker, info in portfolio.items():
        try:
            data = yf.Ticker(ticker).history(period="1d")
            current_usd = data["Close"].iloc[-1]
            change = data["Close"].pct_change().iloc[-1] * 100
            price_nis = current_usd * usd_now
            gain_nom = (price_nis - info["buy_price_nis"]) / info["buy_price_nis"]
            gain_real = ((current_usd * usd_now) - info["buy_price_nis"]) / info["buy_price_nis"]
            abs_change = abs(change)
            last_notified = notified_today.get(ticker, -1)

            for threshold in ALERT_THRESHOLDS:
                if abs_change >= threshold and threshold > last_notified:
                    sentiment = get_sentiment_score(ticker)
                    tech = get_technical_analysis(ticker)
                    rating = fetch_analyst_rating(ticker)
                    vs_sp500 = compare_to_sp500(change)
                    msg = build_message(ticker, change, price_nis, gain_nom, gain_real, sentiment, tech, rating, vs_sp500)
                    send_whatsapp(msg)
                    notified_today[ticker] = threshold
                    break
        except Exception as e:
            print(f"שגיאה במניה {ticker}: {e}")

# ==== SCHEDULING ====
schedule.every().hour.do(check_portfolio)
check_portfolio()  # run immediately

while True:
    schedule.run_pending()
    time.sleep(60)
