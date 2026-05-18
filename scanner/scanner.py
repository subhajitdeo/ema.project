import pandas as pd
import json
import os
from datetime import datetime

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Load stock list
stocks = pd.read_csv("scanner/nifty500.csv")

results = []

# Path to your processed data from calculate.py
PROCESSED_DATA_DIR = "data/processed"

for symbol in stocks["SYMBOL"]:
    try:
        print(f"Scanning {symbol}")
        
        # Read the processed JSON file (created by calculate.py)
        json_path = os.path.join(PROCESSED_DATA_DIR, f"{symbol}.json")
        
        if not os.path.exists(json_path):
            print(f"  No processed data for {symbol}, skipping...")
            continue
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Extract data from the JSON
        candles = data.get('candles', [])
        if len(candles) < 200:
            print(f"  Insufficient candles ({len(candles)}) for {symbol}")
            continue
        
        # Get latest prices
        latest_close = data['latest_price']
        
        # Calculate change from previous day
        if len(candles) >= 2:
            prev_close = candles[-2]['close']
            change_pct = ((latest_close - prev_close) / prev_close) * 100
        else:
            change_pct = 0
        
        # Get latest high/low
        latest_high = candles[-1]['high']
        latest_low = candles[-1]['low']
        
        # Get EMAs from indicators (already calculated in your JSON)
        indicators = data.get('indicators', {})
        
        ema20 = indicators.get('EMA20', {}).get('value', latest_close)
        ema50 = indicators.get('EMA50', {}).get('value', latest_close)
        ema100 = indicators.get('EMA100', {}).get('value', latest_close)
        ema200 = indicators.get('EMA200', {}).get('value', latest_close)
        
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
        
        # Store results
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
        
        print(f"  ✅ {symbol} - Score: {score}, Price: {latest_close}")
        
    except Exception as e:
        print(f"  ❌ Failed: {symbol} - {e}")

# Sort by score (higher = better symmetry + alignment)
results.sort(key=lambda x: x["score"], reverse=True)

final_data = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_stocks": len(results),
    "data": results
}

with open("data/results.json", "w") as f:
    json.dump(final_data, f, indent=4)

print(f"\n✅ Done. {len(results)} stocks analyzed and saved to data/results.json")
