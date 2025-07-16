import schedule
import time

def check_portfolio():
    print("🔍 Running investment agent task...")
    # כאן תריץ את כל הלוגיקה שלך:
    # - בדיקת תיק השקעות
    # - חישוב תשואות
    # - שליחת הודעה לוואטסאפ אם צריך
    # (כרגע לצורך דוגמה – רק print)

# תזמון: כל שעה
schedule.every().hour.do(check_portfolio)

# הרצה ראשונית מיידית (אם רוצים לבדוק)
check_portfolio()

# 🔁 לולאה תמידית – חובה כדי שRender לא יסגור את השירות
while True:
    schedule.run_pending()
    time.sleep(60)
