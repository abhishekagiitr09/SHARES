import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os

# ------------------------------
# CONFIG
# ------------------------------
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = EMAIL_SENDER

def get_nifty_200_tickers():
    """Dynamically fetches Nifty 200 symbols to increase universe size."""
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    try:
        df_nifty = pd.read_csv(url)
        return [f"{s}.NS" for s in df_nifty['Symbol'].tolist()]
    except Exception as e:
        print(f"Error fetching dynamic list: {e}. Falling back to Nifty 50.")
        # Manual fallback based on trading.txt list
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS"]

# ------------------------------
# SCANNING LOGIC
# ------------------------------
def run_scanner(tickers):
    # Fetch 2y data to ensure SMA200 is valid (Unlike the 3mo in trading.txt)
    print(f"Downloading data for {len(tickers)} stocks...")
    data = yf.download(tickers, period="2y", interval="1d", group_by='ticker', threads=True)
    
    short_term_picks = []
    long_term_picks = []

    for ticker in tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 200: continue

            # Technical Indicators
            df['SMA5'] = df['Close'].rolling(5).mean()
            df['SMA20'] = df['Close'].rolling(20).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            df['SMA200'] = df['Close'].rolling(200).mean()
            
            curr = df.iloc[-1]
            avg_vol = df['Volume'].tail(10).mean()

            # Short Term: Momentum + Volume Spike
            if (curr['SMA5'] > curr['SMA20']) and (curr['Volume'] > avg_vol * 1.5):
                short_term_picks.append(ticker)

            # Long Term: Stage 2 Uptrend[span_1](start_span)[span_1](end_span)
            if (curr['Close'] > curr['SMA50']) and (curr['SMA50'] > curr['SMA200']):
                long_term_picks.append(ticker)
        except:
            continue

    return short_term_picks, long_term_picks

# ------------------------------
# EMAIL TRIGGER
# ------------------------------
def send_email(short_list, long_list):
    body = "📊 Enhanced Stock Scan Report\n\n"
    
    body += "🔴 SHORT-TERM (Momentum & Vol):\n"
    body += "\n".join([f"- {s}" for s in short_list]) if short_list else "No signals found."
    
    body += "\n\n🟢 LONG-TERM (Major Trend):\n"
    body += "\n".join([f"- {s}" for s in long_list]) if long_list else "No signals found."

    msg = MIMEText(body)
    msg["Subject"] = f"Stock Scan Results: {len(short_list) + len(long_list)} Candidates"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            print("✅ Email notification sent.")
    except Exception as e:
        print(f"❌ Email failed: {e}")

# ------------------------------
# MAIN EXECUTION
# ------------------------------
if __name__ == "__main__":
    ticker_list = get_nifty_200_tickers()
    short_results, long_results = run_scanner(ticker_list)
    
    print(f"Short-term candidates: {short_results}")
    print(f"Long-term candidates: {long_results}")
    
    send_email(short_results, long_results)