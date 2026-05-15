# NSE Nifty 500 Trend Strength Scanner

Professional stock scanner that ranks Nifty 500 stocks by EMA trend strength. Generates JSON data via Python, displays interactive dashboard on GitHub Pages.

## Features
- **EMA Alignment:** Price > EMA20 > EMA50 > EMA100 > EMA200
- **Trend Score:** Combines separation %, price distance, daily gain, relative volume, momentum
- **Glassmorphism Dashboard:** Dark UI with search, sort, filter
- **Manual GitHub Actions:** Run scanner after market close with one click
- **No backend/database:** Pure static frontend + precomputed JSON

## Setup Instructions

### 1. Upload to GitHub
```bash
git init
git add .
git commit -m "Initial scanner"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/nse-ema-scanner.git
git push -u origin main
