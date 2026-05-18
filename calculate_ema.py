import pandas as pd
import json
import os
from datetime import datetime

# Paths
DATA_FOLDER = "data"
OUTPUT_FOLDER = "data/ema_results"

# Create output folder
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def calculate_ema(series, period):
    """Calculate EMA for a series"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_score(latest_close, ema20, ema50, ema100, ema200):
    """Calculate symmetry score based on EMA alignment"""
    # Check if price is above all EMAs in correct order
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
            score = max(0, 100 * (1 - (max_deviation / mean_gap)))
        else:
            score = 0
    else:
        score = 0
    
    return round(score, 2)

def process_all_stocks():
    """Process all .NS.json files in data folder"""
    
    # Get all .NS.json files
    json_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.NS.json')]
    
    if not json_files:
        print(f"❌ No .NS.json files found in {DATA_FOLDER}/")
        return
    
    print(f"📊 Found {len(json_files)} stock files to process")
    print("="*60)
    
    results = []
    failed = 0
    skipped = 0
    
    for i, json_file in enumerate(json_files, 1):
        # Extract symbol name (remove .NS.json)
        symbol = json_file.replace('.NS.json', '')
        
        try:
            file_path = os.path.join(DATA_FOLDER, json_file)
            with open(file_path, 'r') as f:
                candles = json.load(f)
            
            # Check if candles is a list (direct array format)
            if not isinstance(candles, list):
                print(f"[{i}/{len(json_files)}] ⚠️ {symbol}: Invalid format (not a list)")
                skipped += 1
                continue
            
            if len(candles) < 200:
                print(f"[{i}/{len(json_files)}] ⚠️ {symbol}: Only {len(candles)} candles, skipping")
                skipped += 1
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            
            # Ensure columns exist
            required_cols = ['close', 'open', 'high', 'low']
            if not all(col in df.columns for col in required_cols):
                print(f"[{i}/{len(json_files)}] ⚠️ {symbol}: Missing required columns")
                skipped += 1
                continue
            
            # Calculate EMAs
            df['EMA20'] = calculate_ema(df['close'], 20)
            df['EMA50'] = calculate_ema(df['close'], 50)
            df['EMA100'] = calculate_ema(df['close'], 100)
            df['EMA200'] = calculate_ema(df['close'], 200)
            
            # Get latest values
            latest = df.iloc[-1]
            latest_close = latest['close']
            ema20 = latest['EMA20']
            ema50 = latest['EMA50']
            ema100 = latest['EMA100']
            ema200 = latest['EMA200']
            
            # Calculate change
            if len(df) >= 2:
                prev_close = df.iloc[-2]['close']
                change_pct = ((latest_close - prev_close) / prev_close) * 100
            else:
                change_pct = 0
            
            # Get latest high/low
            latest_high = latest['high']
            latest_low = latest['low']
            
            # Calculate score
            score = calculate_score(latest_close, ema20, ema50, ema100, ema200)
            
            # Determine trend and alignment
            if latest_close > ema200:
                trend = "BULLISH"
            elif latest_close < ema200:
                trend = "BEARISH"
            else:
                trend = "NEUTRAL"
            
            if latest_close > ema20 > ema50 > ema100 > ema200:
                alignment = "PERFECT"
            elif latest_close > ema20 and latest_close > ema50:
                alignment = "PARTIAL"
            else:
                alignment = "WEAK"
            
            # Prepare result
            stock_result = {
                "symbol": symbol,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "price": round(latest_close, 2),
                "change_percent": round(change_pct, 2),
                "high": round(latest_high, 2),
                "low": round(latest_low, 2),
                "ema20": round(ema20, 2),
                "ema50": round(ema50, 2),
                "ema100": round(ema100, 2),
                "ema200": round(ema200, 2),
                "score": score,
                "trend": trend,
                "alignment": alignment,
                "candles_count": len(candles)
            }
            
            results.append(stock_result)
            print(f"[{i}/{len(json_files)}] ✅ {symbol}: Score={score}, Price={latest_close}, Trend={trend}")
            
            # Save individual stock JSON
            individual_file = os.path.join(OUTPUT_FOLDER, f"{symbol}.json")
            with open(individual_file, 'w') as f:
                json.dump(stock_result, f, indent=2)
            
        except Exception as e:
            print(f"[{i}/{len(json_files)}] ❌ {symbol}: Error - {e}")
            failed += 1
    
    # Sort results by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Calculate statistics
    if results:
        avg_score = sum(r["score"] for r in results) / len(results)
        bullish_count = sum(1 for r in results if r["trend"] == "BULLISH")
        perfect_count = sum(1 for r in results if r["alignment"] == "PERFECT")
        top_stock = results[0]['symbol']
        top_score = results[0]['score']
    else:
        avg_score = bullish_count = perfect_count = top_score = 0
        top_stock = "N/A"
    
    # Save combined results
    final_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_stocks_found": len(json_files),
        "total_stocks_processed": len(results),
        "skipped_stocks": skipped,
        "failed_stocks": failed,
        "statistics": {
            "average_score": round(avg_score, 2),
            "bullish_stocks": bullish_count,
            "bearish_stocks": len(results) - bullish_count,
            "perfect_alignment": perfect_count,
            "highest_score": top_score,
            "highest_score_stock": top_stock
        },
        "top_10_stocks": results[:10],
        "all_stocks": results
    }
    
    # Save combined JSON
    combined_file = os.path.join(OUTPUT_FOLDER, "all_results.json")
    with open(combined_file, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    # Save to root for easy access
    with open("data/ema_results.json", 'w') as f:
        json.dump(final_data, f, indent=2)
    
    # Save CSV for Excel viewing
    if results:
        df_results = pd.DataFrame(results)
        df_results.to_csv("data/ema_results.csv", index=False)
    
    print("\n" + "="*60)
    print(f"✅ EMA CALCULATION COMPLETE!")
    print(f"   Found: {len(json_files)} files")
    print(f"   Processed: {len(results)} stocks")
    print(f"   Skipped: {skipped}")
    print(f"   Failed: {failed}")
    print(f"   Average Score: {round(avg_score, 2)}")
    print(f"   Bullish Stocks: {bullish_count}")
    print(f"   Bearish Stocks: {len(results) - bullish_count}")
    print(f"   Perfect Alignment: {perfect_count}")
    if results:
        print(f"   Top Stock: {top_stock} (Score: {top_score})")
    print(f"\n📁 Results saved to:")
    print(f"   - {OUTPUT_FOLDER}/ (individual stock JSONs)")
    print(f"   - {OUTPUT_FOLDER}/all_results.json")
    print(f"   - data/ema_results.json")
    print(f"   - data/ema_results.csv")
    print("="*60)

if __name__ == "__main__":
    process_all_stocks()
