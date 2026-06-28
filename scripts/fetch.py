import requests
import csv
import json
import os
from datetime import datetime, timezone

# Twelve Data API — free tier: 800 credits/day, 1 credit per symbol
TWELVE_DATA_BASE = "https://api.twelvedata.com"

PRICES_FIELDNAMES = [
    "date", "exchange", "ticker", "name", "price", "change", "change_pct",
    "volume", "market_cap", "open", "high", "low",
]

INDEX_FIELDNAMES = ["date", "exchange", "index_name", "value", "change", "change_pct", "market_cap"]

# All NSE Kenya tickers (70 stocks, confirmed from nse.co.ke listings)
NSE_TICKERS = [
    "ABSA", "ALP", "AMAC", "ARM", "BAMB", "BAT", "BKG", "BOC", "BRIT",
    "CABL", "CARB", "CGEN", "CIC", "COOP", "CRWN", "CTUM", "DCON", "DTK",
    "EABL", "EGAD", "EQTY", "EVRD", "FMLY", "FTGH", "GLD", "HAFR", "HBE",
    "HFCK", "IMH", "JUB", "KAPC", "KCB", "KEGN", "KNRE", "KPC", "KPLC",
    "KQ", "KUKZ", "KURV", "LAPR", "LBTY", "LIMT", "LKL", "MSC", "NBV",
    "NCBA", "NMG", "NSE", "OCH", "PORT", "SASN", "SBIC", "SCAN", "SCBK",
    "SCOM", "SGL", "SKL", "SLAM", "SMER", "SMWF", "TCL", "TOTL", "TPSE",
    "UCHM", "UMME", "UNGA", "WTK", "XPRS",
]


def safe_float(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(",", "").replace("+", "").strip())
    except (ValueError, AttributeError):
        return None


def safe_int(s):
    if not s:
        return 0
    try:
        return int(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def fetch_nse(api_key):
    """Fetch NSE Kenya stocks via Twelve Data batch quote endpoint.
    1 API credit per symbol. 70 symbols = 70 credits (free tier: 800/day).
    """
    print(f"[fetch] NSE — Twelve Data API ({len(NSE_TICKERS)} symbols)")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Batch request: up to 120 symbols per call
    symbols = ",".join(NSE_TICKERS)
    url = f"{TWELVE_DATA_BASE}/quote"
    params = {
        "symbol": symbols,
        "exchange": "NSE",
        "apikey": api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=60)
        print(f"[fetch] NSE HTTP {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[fetch] NSE FAILED: {e}")
        return [], None

    # Batch response: {TICKER: {...}, TICKER: {...}, ...}
    # Single response: {...} (no wrapper)
    if not isinstance(data, dict):
        print(f"[fetch] NSE unexpected response type: {type(data)}")
        return [], None

    # If single ticker, wrap it
    if "symbol" in data:
        data = {data["symbol"]: data}

    stocks = []
    nasi_value = None

    for ticker, q in data.items():
        if not isinstance(q, dict):
            continue
        if q.get("status") == "error":
            continue

        price = safe_float(q.get("close") or q.get("price"))
        if price is None:
            continue

        change_abs = safe_float(q.get("change")) or 0.0
        change_pct = safe_float(q.get("percent_change")) or 0.0

        stocks.append({
            "date": today,
            "exchange": "NSE",
            "ticker": ticker,
            "name": q.get("name", ticker),
            "price": price,
            "change": change_abs,
            "change_pct": change_pct,
            "volume": safe_int(q.get("volume")),
            "market_cap": None,
            "open": safe_float(q.get("open")),
            "high": safe_float(q.get("high")),
            "low": safe_float(q.get("low")),
        })

    print(f"[fetch] NSE: {len(stocks)} stocks")

    index_row = None
    if nasi_value:
        index_row = {
            "date": today, "exchange": "NSE",
            "index_name": "NASI", "value": nasi_value,
            "change": None, "change_pct": None, "market_cap": None,
        }

    return stocks, index_row


def append_prices(exchange_code, rows):
    path = f"data/{exchange_code.lower()}/prices.csv"
    file_exists = os.path.exists(path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    existing_dates = set()
    if file_exists:
        with open(path) as f:
            for row in csv.DictReader(f):
                existing_dates.add(row.get("date", ""))

    if today in existing_dates:
        print(f"[fetch] {exchange_code}: already have data for {today}, skipping")
        return

    os.makedirs(f"data/{exchange_code.lower()}", exist_ok=True)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PRICES_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def append_index(index_row):
    if not index_row:
        return
    path = "data/indices.csv"
    file_exists = os.path.exists(path)
    exchange = index_row["exchange"]
    date = index_row["date"]

    if file_exists:
        with open(path) as f:
            for row in csv.DictReader(f):
                if row.get("exchange") == exchange and row.get("date") == date:
                    return

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(index_row)


def save_latest(exchange_code, rows):
    os.makedirs(f"data/{exchange_code.lower()}", exist_ok=True)
    with open(f"data/{exchange_code.lower()}/latest.json", "w") as f:
        json.dump({
            "exchange": exchange_code,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": len(rows),
            "stocks": rows,
        }, f, indent=2)


def main():
    api_key = os.environ.get("TWELVE_DATA_KEY", "")
    if not api_key:
        print("[fetch] ERROR: TWELVE_DATA_KEY secret not set")
        raise SystemExit(1)

    os.makedirs("data/dse", exist_ok=True)
    os.makedirs("data/nse", exist_ok=True)

    nse_stocks, nse_index = fetch_nse(api_key)
    if nse_stocks:
        append_prices("NSE", nse_stocks)
        save_latest("NSE", nse_stocks)
        append_index(nse_index)

    print(f"\n[fetch] Done — NSE: {len(nse_stocks)}, DSE: 0 (pending source)")


if __name__ == "__main__":
    main()
