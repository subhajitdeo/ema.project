import pandas as pd
import yfinance as yf
import json
import time
import os
from datetime import datetime

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Load stock list
stocks = pd.read_csv("scanner/nifty500.csv")

results = []

for symbol in stocks["SYMBOL"]:
    try:
        ticker = symbol + ".NS"
        print(f"Scanning {ticker}")

        data = yf.download(
            ticker,
            period="3y",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if data.empty or len(data) < 200:
            print(f"Insufficient data for {symbol}")
            continue

        close = data["Close"].squeeze()
        low = data["Low"].squeeze()
        high = data["High"].squeeze()

        latest_close = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        change_pct = ((latest_close - prev_close) / prev_close) * 100

        latest_low = float(low.iloc[-1])
        latest_high = float(high.iloc[-1])

        # Calculate EMAs
        ema20 = float(close.ewm(span=20).mean().iloc[-1])
        ema50 = float(close.ewm(span=50).mean().iloc[-1])
        ema100 = float(close.ewm(span=100).mean().iloc[-1])
        ema200 = float(close.ewm(span=200).mean().iloc[-1])

        # ----- Score out of 100 based on sequence + symmetric gaps -----
        # Check if LTP > EMA20 > EMA50 > EMA100 > EMA200
        if latest_close > ema20 > ema50 > ema100 > ema200:
            gaps = [
                latest_close - ema20,
                ema20 - ema50,
                ema50 - ema100,
                ema100 - ema200
            ]
            # All gaps must be positive (already true from sequence)
            mean_gap = sum(gaps) / len(gaps)
            # Symmetry: how close each gap is to mean_gap
            deviations = [abs(g - mean_gap) for g in gaps]
            max_deviation = max(deviations)
            # If max_deviation is 0, perfect symmetry. Else normalize.
            # Score = 100 * (1 - (max_deviation / mean_gap)) but clip to 0-100
            if mean_gap > 0:
                symmetry_score = max(0, 100 * (1 - (max_deviation / mean_gap)))
            else:
                symmetry_score = 0
        else:
            symmetry_score = 0

        score = round(symmetry_score, 2)

        # Store results (no bullish flag)
        results.append({
            "symbol": symbol,
            "price": round(latest_close, 2),
            "change": round(change_pct, 2),
            "low": round(latest_low, 2),
            "high": round(latest_high, 2),
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "ema100": round(ema100, 2),
            "ema200": round(ema200, 2),
            "score": score
        })

        time.sleep(0.7)

    except Exception as e:
        print(f"Failed: {symbol} - {e}")

# Sort by score (higher = better symmetry + alignment)
results.sort(key=lambda x: x["score"], reverse=True)

final_data = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_stocks": len(results),
    "data": results
}

with open("data/results.json", "w") as f:
    json.dump(final_data, f, indent=4)

print(f"Done. {len(results)} stocks saved.")
