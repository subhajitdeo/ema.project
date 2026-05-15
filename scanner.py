"""
NSE Nifty 500 Trend Strength Scanner
Fetches latest Nifty 500 list from yfinance, then downloads bhavcopy data.
"""

import json
import time
import logging
import sys
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from tqdm import tqdm
import yfinance as yf

# ==================== CONFIGURATION ====================
SYMBOLS_FILE = "nifty500.txt"
OUTPUT_FILE = "data/results.json"
YEARS_OF_DATA = 3
REQUEST_DELAY = 0.3
MAX_RETRIES = 3

WEIGHTS = {
    "ema_separation": 0.20,
    "price_distance": 0.25,
    "daily_gain": 0.20,
    "relative_volume": 0.15,
    "momentum": 0.20
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== FETCH COMPLETE NIFTY 500 LIST ====================
def fetch_nifty500_symbols_from_yfinance():
    """Fetch all Nifty 500 symbols using yfinance."""
    try:
        # Fetch NIFTY 500 index constituents from Yahoo Finance
        nifty500 = yf.Ticker("^NSEI")
        # Get the holdings/constituents
        holdings = nifty500.info.get('holdings', [])
        
        if holdings:
            symbols = [h['symbol'].replace('.NS', '') for h in holdings if 'symbol' in h]
            if symbols:
                with open(SYMBOLS_FILE, 'w') as f:
                    f.write("\n".join(symbols))
                logger.info(f"Fetched {len(symbols)} Nifty 500 symbols from yfinance")
                return symbols
        
        # Fallback: known good symbols from NIFTY 50 if constituents fetch fails
        fallback_symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR", "ICICIBANK", "KOTAKBANK",
            "SBIN", "BHARTIARTL", "ITC", "AXISBANK", "LT", "WIPRO", "HCLTECH", "SUNPHARMA",
            "BAJFINANCE", "NTPC", "ONGC", "MARUTI", "TITAN", "ASIANPAINT", "ULTRACEMCO",
            "POWERGRID", "NESTLE", "M&M", "TECHM", "JSWSTEEL", "BAJAJFINSV", "ADANIPORTS",
            "ADANIENT", "BAJAJ-AUTO", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
            "GRASIM", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "INDUSINDBK", "LTIM",
            "MCDOWELL-N", "SBILIFE", "SHREECEM", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "UPL"
        ]
        logger.warning("Could not fetch Nifty 500 symbols, using fallback list of 50 stocks")
        with open(SYMBOLS_FILE, 'w') as f:
            f.write("\n".join(fallback_symbols))
        return fallback_symbols
        
    except Exception as e:
        logger.error(f"Failed to fetch symbols: {e}")
        return []

def load_symbols() -> List[str]:
    """Load symbols from nifty500.txt, fetch from yfinance if missing."""
    if not os.path.exists(SYMBOLS_FILE):
        logger.info("nifty500.txt not found, fetching from yfinance...")
        symbols = fetch_nifty500_symbols_from_yfinance()
        if symbols:
            return symbols
        else:
            # Final fallback: hardcoded NIFTY 50 symbols
            fallback = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR", "ICICIBANK"]
            with open(SYMBOLS_FILE, 'w') as f:
                f.write("\n".join(fallback))
            return fallback
    
    with open(SYMBOLS_FILE, 'r') as f:
        symbols = [line.strip().upper() for line in f if line.strip()]
    logger.info(f"Loaded {len(symbols)} symbols from {SYMBOLS_FILE}")
    return symbols

# ==================== BHAVCOPY DOWNLOADER ====================
def get_all_bhavcopy_dates(years: int = 3):
    """Generate list of dates with bhavcopy files."""
    dates = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Monday=0, Friday=4
            dates.append(current)
        current += timedelta(days=1)
    return dates

def download_bhavcopy_for_date(date_obj):
    """Download bhavcopy CSV for a specific date from NSE."""
    try:
        date_str = date_obj.strftime("%d%m%Y")
        url = f"https://archives.nseindia.com/content/historical/EQUITIES/{date_obj.year}/{date_obj.strftime('%b').upper()}/cm{date_str}bhav.csv.zip"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open("temp.zip", "wb") as f:
                f.write(response.content)
            df = pd.read_csv("temp.zip")
            os.remove("temp.zip")
            return df
        return None
    except Exception as e:
        return None

def fetch_stock_data(symbol: str) -> Optional[pd.DataFrame]:
    """Fetch daily data by downloading bhavcopy files."""
    dates = get_all_bhavcopy_dates(YEARS_OF_DATA)
    all_data = []
    
    for date in tqdm(dates, desc=f"Downloading bhavcopy for {symbol}", leave=False):
        df = download_bhavcopy_for_date(date)
        if df is not None:
            stock_row = df[df['SYMBOL'] == symbol]
            if not stock_row.empty:
                row = stock_row.iloc[0]
                all_data.append({
                    'Date': date,
                    'Open': row['OPEN'],
                    'High': row['HIGH'],
                    'Low': row['LOW'],
                    'Close': row['CLOSE'],
                    'Volume': row['TOTTRDQTY']
                })
        time.sleep(0.2)
    
    if not all_data:
        return None
    
    final_df = pd.DataFrame(all_data)
    final_df.set_index('Date', inplace=True)
    final_df.sort_index(inplace=True)
    
    if len(final_df) < 200:
        logger.warning(f"{symbol}: Only {len(final_df)} days, need 200+")
        return None
    
    return final_df

# ==================== EMA AND METRICS CALCULATION ====================
def calculate_emas(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate EMAs 20, 50, 100, 200."""
    df = df.copy()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

def compute_metrics(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """Extract latest metrics and compute trend indicators."""
    try:
        if df is None or df.empty:
            return None
        
        df = calculate_emas(df)
        latest = df.iloc[-1]
        
        required_cols = ['EMA20', 'EMA50', 'EMA100', 'EMA200']
        if any(pd.isna(latest[col]) for col in required_cols):
            return None
        
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else latest['Close']
        daily_gain_pct = ((latest['Close'] - prev_close) / prev_close) * 100
        
        vol_series = df['Volume'].iloc[-21:-1]
        avg_volume_20 = vol_series.mean() if len(vol_series) >= 10 else latest['Volume']
        rel_volume = latest['Volume'] / avg_volume_20 if avg_volume_20 > 0 else 1.0
        
        ema_sep_pct = ((latest['EMA20'] - latest['EMA200']) / latest['EMA200']) * 100
        price_dist_pct = ((latest['Close'] - latest['EMA20']) / latest['EMA20']) * 100
        
        if len(df) >= 6:
            close_5d_ago = df['Close'].iloc[-6]
            momentum_pct = ((latest['Close'] - close_5d_ago) / close_5d_ago) * 100
        else:
            momentum_pct = daily_gain_pct
        
        is_bullish = (
            latest['Close'] > latest['EMA20'] > latest['EMA50'] > latest['EMA100'] > latest['EMA200']
        )
        
        volume_int = int(latest['Volume']) if not pd.isna(latest['Volume']) else 0
        
        return {
            "symbol": symbol,
            "price": round(latest['Close'], 2),
            "ema20": round(latest['EMA20'], 2),
            "ema50": round(latest['EMA50'], 2),
            "ema100": round(latest['EMA100'], 2),
            "ema200": round(latest['EMA200'], 2),
            "daily_gain_pct": round(daily_gain_pct, 2),
            "volume": volume_int,
            "rel_volume": round(rel_volume, 2),
            "ema_sep_pct": round(ema_sep_pct, 2),
            "price_dist_pct": round(price_dist_pct, 2),
            "momentum_pct": round(momentum_pct, 2),
            "is_bullish_aligned": is_bullish
        }
    except Exception as e:
        logger.error(f"{symbol}: compute_metrics error - {str(e)}")
        return None

def normalize_metric(values: List[float]) -> List[float]:
    """Min-max normalization with outlier clipping."""
    if not values or len(values) < 2:
        return [0.5] * len(values)
    
    series = pd.Series(values)
    lower = series.quantile(0.05)
    upper = series.quantile(0.95)
    
    if upper <= lower:
        return [0.5] * len(values)
    
    normalized = [(v - lower) / (upper - lower) for v in values]
    return [max(0.0, min(1.0, n)) for n in normalized]

def calculate_trend_scores(stocks_data: List[Dict]) -> List[Dict]:
    """Add normalized trend strength score (0-100)."""
    if not stocks_data:
        return []
    
    metrics = {
        "ema_sep_pct": [],
        "price_dist_pct": [],
        "daily_gain_pct": [],
        "rel_volume": [],
        "momentum_pct": []
    }
    
    for stock in stocks_data:
        for key in metrics.keys():
            metrics[key].append(stock.get(key, 0))
    
    normalized_metrics = {}
    for key, values in metrics.items():
        normalized_metrics[key] = normalize_metric(values)
    
    for idx, stock in enumerate(stocks_data):
        score = 0.0
        for metric, weight in WEIGHTS.items():
            score += normalized_metrics[metric][idx] * weight
        
        stock["trend_score"] = round(score * 100, 1)
        
        if stock.get("is_bullish_aligned", False) and stock["trend_score"] >= 60:
            stock["status"] = "Strong Bullish"
            stock["color"] = "green"
        elif stock.get("is_bullish_aligned", False):
            stock["status"] = "Bullish"
            stock["color"] = "green"
        elif stock["trend_score"] >= 50:
            stock["status"] = "Neutral"
            stock["color"] = "yellow"
        else:
            stock["status"] = "Weak"
            stock["color"] = "red"
    
    stocks_data.sort(key=lambda x: x["trend_score"], reverse=True)
    for rank, stock in enumerate(stocks_data, 1):
        stock["rank"] = rank
    
    return stocks_data

def run_scanner():
    """Main execution."""
    start_time = datetime.now()
    logger.info("=== NSE Nifty 500 Trend Strength Scanner (Bhavcopy Direct) ===")
    
    # Load or fetch symbols
    symbols = load_symbols()
    if not symbols:
        logger.error("No symbols loaded. Exiting.")
        sys.exit(1)
    
    all_stocks = []
    failed_symbols = []
    
    for symbol in tqdm(symbols, desc="Scanning stocks"):
        time.sleep(REQUEST_DELAY)
        df = fetch_stock_data(symbol)
        if df is None:
            failed_symbols.append(symbol)
            continue
        
        metrics = compute_metrics(df, symbol)
        if metrics:
            all_stocks.append(metrics)
        else:
            failed_symbols.append(symbol)
    
    logger.info(f"Successfully processed: {len(all_stocks)} stocks")
    logger.info(f"Failed: {len(failed_symbols)} stocks")
    
    if not all_stocks:
        logger.error("No valid stock data. Exiting.")
        sys.exit(1)
    
    ranked_stocks = calculate_trend_scores(all_stocks)
    bullish_count = sum(1 for s in ranked_stocks if s.get("is_bullish_aligned", False))
    
    output = {
        "last_updated": datetime.now().isoformat(),
        "last_updated_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "total_stocks_scanned": len(symbols),
        "successful_stocks": len(ranked_stocks),
        "bullish_count": bullish_count,
        "failed_count": len(failed_symbols),
        "scanner_duration_seconds": round((datetime.now() - start_time).total_seconds(), 1),
        "stocks": ranked_stocks
    }
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Results saved to {OUTPUT_FILE}")
    if ranked_stocks:
        logger.info(f"Top 5 stocks: {[s['symbol'] for s in ranked_stocks[:5]]}")
    
    print("\n" + "="*50)
    print("SCAN COMPLETE")
    print(f"Total scanned: {len(ranked_stocks)}")
    print(f"Bullish aligned: {bullish_count}")
    if ranked_stocks:
        print(f"Avg trend score: {sum(s['trend_score'] for s in ranked_stocks)/len(ranked_stocks):.1f}")
    print("="*50)

if __name__ == "__main__":
    run_scanner()
