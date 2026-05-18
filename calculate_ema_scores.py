import pandas as pd
import json
import os
from datetime import datetime

# Path to the data folder in ema.dna
DATA_FOLDER = "data/"  # Where copied JSON files are stored
OUTPUT_FOLDER = "data/scores"   # Where results will be saved

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def calculate_ema_from_candles(candles):
    """Calculate EMAs from candle data"""
    if not candles or len(candles) < 200:
        return None, None, None, None
    
    # Extract closing prices
    closes = [c['close'] for c in candles]
    
    # Calculate EMAs using pandas
    close_series = pd.Series(closes)
    ema20 = float(close_series.ewm(span=20).mean().iloc[-1])
    ema50 = float(close_series.ewm(span=50).mean().iloc[-1])
    ema100 = float(close_series.ewm(span=100).mean().iloc[-1])
    ema200 = float(close_series.ewm(span=200).mean().iloc[-1])
    
    return ema20, ema50, ema100, ema200

def calculate_score(latest_close, ema20, ema50, ema100, ema200):
    """Calculate symmetry score based on EMA alignment"""
    # Check if LTP > EMA20 > EMA50 > EMA100 > EMA200
    if latest_close > ema20 > ema50 > ema100 > ema200:
        gaps = [
            latest_close - ema20,
            ema20 - ema50,
            ema50 - ema100,
            ema100 - ema200
        ]
        mean_gap = sum(gaps) / len(gaps)
        
        if mean_gap > 0:
            deviations = [abs(g - mean_gap) for g in gaps]
            max_deviation = max(deviations)
            symmetry_score = max(0, 100 * (1 - (max_deviation / mean_gap)))
        else:
            symmetry_score = 0
    else:
        symmetry_score = 0
    
    return round(symmetry_score, 2)

def process_all_stocks():
    """Process all JSON files in data/processed folder"""
    
    if not os.path.exists(DATA_FOLDER):
        print(f"❌ Data folder not found: {DATA_FOLDER}")
        print("Please run the copy workflow first to get data from shape.dna")
        return
    
    # Get all JSON files
    json_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.json')]
    print(f"📊 Found {len(json_files)} stock files to process")
    
    results = []
    
    for json_file in json_files:
        symbol = json_file.replace('.json', '')
        
        try:
            file_path = os.path.join(DATA_FOLDER, json_file)
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Get candles data
            candles = data.get('candles', [])
            
            if len(candles) < 200:
                print(f"⚠️ {symbol}: Insufficient data ({len(candles)} candles), skipping")
                continue
            
            # Calculate EMAs from candles
            ema20, ema50, ema100, ema200 = calculate_ema_from_candles(candles)
            
            if None in (ema20, ema50, ema100, ema200):
                print(f"⚠️ {symbol}: Could not calculate EMAs, skipping")
                continue
            
            # Get latest price and other data
            latest_close = candles[-1]['close']
            prev_close = candles[-2]['close'] if len(candles) > 1 else latest_close
            change_pct = ((latest_close - prev_close) / prev_close) * 100
            
            latest_high = candles[-1]['high']
            latest_low = candles[-1]['low']
            
            # Calculate score
            score = calculate_score(latest_close, ema20, ema50, ema100, ema200)
            
            # Store results
            stock_data = {
                "symbol": symbol,
                "price": round(latest_close, 2),
                "change": round(change_pct, 2),
                "low": round(latest_low, 2),
                "high": round(latest_high, 2),
                "ema20": round(ema20, 2),
                "ema50": round(ema50, 2),
                "ema100": round(ema100, 2),
                "ema200": round(ema200, 2),
                "score": score,
                "alignment": "Perfect" if latest_close > ema20 > ema50 > ema100 > ema200 else "Partial"
            }
            
            results.append(stock_data)
            print(f"✅ {symbol}: Score={score}, Price={latest_close}, Alignment={stock_data['alignment']}")
            
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Calculate statistics
    if results:
        avg_score = sum(r["score"] for r in results) / len(results)
        bullish = sum(1 for r in results if r["price"] > r["ema200"])
        perfect_alignment = sum(1 for r in results if r["alignment"] == "Perfect")
    else:
        avg_score = bullish = perfect_alignment = 0
    
    # Save individual stock files
    print(f"\n💾 Saving individual stock files...")
    for stock in results:
        stock_file = os.path.join(OUTPUT_FOLDER, f"{stock['symbol']}_ema.json")
        with open(stock_file, 'w') as f:
            json.dump(stock, f, indent=2)
    
    # Save combined results
    final_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_stocks_processed": len(results),
        "statistics": {
            "average_score": round(avg_score, 2),
            "bullish_stocks": bullish,
            "bearish_stocks": len(results) - bullish,
            "perfect_alignment": perfect_alignment,
            "highest_score": results[0]['score'] if results else 0,
            "lowest_score": results[-1]['score'] if results else 0
        },
        "top_10_scores": results[:10],
        "all_stocks": results
    }
    
    combined_file = os.path.join(OUTPUT_FOLDER, "all_results.json")
    with open(combined_file, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    # Also save to root data folder for easy access
    root_result_file = "data/results.json"
    with open(root_result_file, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ EMA CALCULATION COMPLETE!")
    print(f"   Total stocks processed: {len(results)}")
    print(f"   Average score: {round(avg_score, 2)}")
    print(f"   Bullish stocks: {bullish}")
    print(f"   Bearish stocks: {len(results) - bullish}")
    print(f"   Perfect EMA alignment: {perfect_alignment}")
    print(f"   Highest score: {results[0]['symbol']} ({results[0]['score']})" if results else "   No stocks")
    print(f"\n📁 Results saved to:")
    print(f"   - {OUTPUT_FOLDER}/ (individual stock files)")
    print(f"   - {OUTPUT_FOLDER}/all_results.json (combined)")
    print(f"   - data/results.json (root folder)")
    print(f"{'='*60}")

if __name__ == "__main__":
    process_all_stocks()
