import os
import time
import schedule
import yfinance as yf
from datetime import datetime
from twilio.rest import Client

# Load environment variables
ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
TO_NUMBER = os.getenv("TO_NUMBER")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Portfolio example (should be loaded from CSV ideally)
portfolio = {
    "NVDA": {"buy_price_nis": 590.0, "usd_at_buy": 3.72},
    "AAPL": {"buy_price_nis": 520.0, "usd_at_buy": 3.68}
}

ALERT_THRESHOLDS = [3, 6, 9, 12]
notified_today = {}

def fetch_usd_ils():
    try:
        fx = yf.Ticker("USDILS=X")
        return fx.history(period="1d")["Close"].iloc[-1]
    except:
        return 3.7  # fallback

def build_message(ticker, change, current_price_nis, nominal_gain, real_gain, sp500_diff):
    return f"""
🚨 *שינוי חריג בתיק ההשקעות* 🚨

📍 *מניה:* {ticker}
⬆️ *שינוי יומי:* {change:.2f}%

💰 *מחיר קנייה:* ₪{portfolio[ticker]['buy_price_nis']:.2f}
💸 *מחיר נוכחי:* ₪{current_price_nis:.2f}
📈 *תשואה נומינלית:* {nominal_gain:.2%}
📉 *תשואה ריאלית:* {real_gain:.2%}

📊 *יחס ל-S&P 500:* {sp500_diff:.2f}%
"""

def send_whatsapp(msg):
    message = client.messages.create(
        body=msg,
        from_=TWILIO_NUMBER,
        to=TO_NUMBER
    )
    print(f"Message sent: {message.sid}")

def check_portfolio():
    global notified_today
    usd_now = fetch_usd_ils()
    sp500 = yf.Ticker("^GSPC").history(period="1d")["Close"].pct_change().iloc[-1] * 100

    for ticker in portfolio:
        try:
            data = yf.Ticker(ticker).history(period="1d")
            current_usd = data["Close"].iloc[-1]
            change = data["Close"].pct_change().iloc[-1] * 100
            current_nis = current_usd * usd_now
            buy_nis = portfolio[ticker]["buy_price_nis"]
            usd_buy = portfolio[ticker]["usd_at_buy"]
            nominal_gain = (current_nis - buy_nis) / buy_nis
            real_gain = ((current_usd * usd_now) - buy_nis) / buy_nis
            abs_change = abs(change)

            # Handle threshold logic
            last_notified = notified_today.get(ticker, -1)
            for threshold in ALERT_THRESHOLDS:
                if abs_change >= threshold and threshold > last_notified:
                    msg = build_message(ticker, change, current_nis, nominal_gain, real_gain, change - sp500)
                    send_whatsapp(msg)
                    notified_today[ticker] = threshold
                    break
        except Exception as e:
            print(f"Error with {ticker}: {e}")

# Schedule every hour
schedule.every().hour.do(check_portfolio)
check_portfolio()  # run immediately

# Keep alive
while True:
    schedule.run_pending()
    time.sleep(60)
