# East Africa Stock Tracker

Real-time stock market dashboard for the **Dar es Salaam Stock Exchange (DSE)** and **Nairobi Securities Exchange (NSE)** — updated daily after market close via GitHub Actions.

**[Live Dashboard →](https://nyandajr.github.io/east-africa-stock-tracker)**

---

## Exchanges Covered

| Exchange | Country | Listed Stocks | Currency |
|----------|---------|---------------|----------|
| DSE — Dar es Salaam Stock Exchange | Tanzania | 26 | TZS |
| NSE — Nairobi Securities Exchange | Kenya | 56 | KES |

## Features

- Daily closing prices for all listed stocks
- Technical indicators: MA5, MA20, RSI(14)
- Top gainers & losers per exchange
- 5-day and 20-day price change %
- RSI overbought/oversold alerts
- 60-day index trend charts
- Volume leaders
- Weekly markdown reports (auto-generated every Monday)

## Pipeline

```
MansaMarkets API (free tier — 100 req/day)
        │
   fetch.py          → data/{dse,nse}/prices.csv + latest.json
        │
   indicators.py     → data/{dse,nse}/indicators.json  (MA5, MA20, RSI)
        │
   dashboard.py      → docs/data.json  (GitHub Pages reads this)
        │
   GitHub Actions    → git commit + push (1 commit/market day)
```

## Setup

### 1. Get a MansaMarkets API key
Sign up at [mansamarkets.com/developers](https://www.mansamarkets.com/developers) — free tier gives 100 requests/day.

### 2. Add GitHub secret
Repo Settings → Secrets → Actions → New secret:
- Name: `MANSA_API_KEY`
- Value: your API key

### 3. Enable GitHub Pages
Settings → Pages → Source: `main` branch, `/docs` folder

### 4. Trigger first run
Actions → Market Pipeline → Run workflow

## Local Development

```bash
pip install -r requirements.txt
export MANSA_API_KEY=your_key_here
python scripts/fetch.py
python scripts/indicators.py
python scripts/dashboard.py
python -m http.server 8080 --directory docs
```

## Data Source

[MansaMarkets](https://www.mansamarkets.com) — Africa's most complete market data terminal covering 21 exchanges across 33 countries.
