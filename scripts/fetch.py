import requests
import json
import csv
import os
from datetime import datetime, timezone

BASE_URL = "https://www.mansaapi.com/api/v1"
EXCHANGES = {
    "DSE": {"name": "Dar es Salaam Stock Exchange", "country": "Tanzania", "currency": "TZS"},
    "NSE": {"name": "Nairobi Securities Exchange",  "country": "Kenya",    "currency": "KES"},
}

PRICES_FIELDNAMES = [
    "date", "exchange", "ticker", "name", "price", "change", "change_pct",
    "volume", "market_cap", "open", "high", "low",
]

def get_headers():
    api_key = os.environ.get("MANSA_API_KEY", "")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

def fetch_exchange(exchange_code):
    url = f"{BASE_URL}/markets/exchanges/{exchange_code}/stocks"
    r = requests.get(url, headers=get_headers(), timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_index(exchange_code):
    url = f"{BASE_URL}/markets/exchanges/{exchange_code}/indices"
    try:
        r = requests.get(url, headers=get_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[fetch] Index for {exchange_code} failed: {e}")
        return {}

def parse_stocks(raw, exchange_code):
    stocks = raw if isinstance(raw, list) else raw.get("data", raw.get("stocks", []))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for s in stocks:
        rows.append({
            "date":       today,
            "exchange":   exchange_code,
            "ticker":     s.get("ticker", s.get("symbol", "")),
            "name":       s.get("name", s.get("company", "")),
            "price":      s.get("price", s.get("close", "")),
            "change":     s.get("change", ""),
            "change_pct": s.get("change_pct", s.get("changePercent", s.get("pct_change", ""))),
            "volume":     s.get("volume", ""),
            "market_cap": s.get("market_cap", s.get("marketCap", "")),
            "open":       s.get("open", ""),
            "high":       s.get("high", ""),
            "low":        s.get("low", ""),
        })
    return rows

def append_prices(exchange_code, rows):
    path = f"data/{exchange_code.lower()}/prices.csv"
    file_exists = os.path.exists(path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Read existing to avoid duplicate dates
    existing_dates = set()
    if file_exists:
        with open(path) as f:
            for row in csv.DictReader(f):
                existing_dates.add(row.get("date", ""))

    if today in existing_dates:
        print(f"[fetch] {exchange_code} already has data for {today} — skipping append")
        return

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PRICES_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

def append_index(exchange_code, index_data):
    path = "data/indices.csv"
    file_exists = os.path.exists(path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    existing_dates_ex = set()
    if file_exists:
        with open(path) as f:
            for row in csv.DictReader(f):
                if row.get("exchange") == exchange_code:
                    existing_dates_ex.add(row.get("date", ""))

    if today in existing_dates_ex:
        return

    indices = index_data if isinstance(index_data, list) else index_data.get("data", [index_data])
    fieldnames = ["date", "exchange", "index_name", "value", "change", "change_pct", "market_cap"]

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for idx in indices[:1]:
            writer.writerow({
                "date":       today,
                "exchange":   exchange_code,
                "index_name": idx.get("name", idx.get("index", f"{exchange_code} ALL SHARE")),
                "value":      idx.get("value", idx.get("close", "")),
                "change":     idx.get("change", ""),
                "change_pct": idx.get("change_pct", idx.get("changePercent", "")),
                "market_cap": idx.get("market_cap", idx.get("marketCap", "")),
            })

def main():
    for exchange_code, info in EXCHANGES.items():
        print(f"\n[fetch] {info['name']} ({exchange_code})")
        try:
            raw = fetch_exchange(exchange_code)
            rows = parse_stocks(raw, exchange_code)
            append_prices(exchange_code, rows)

            os.makedirs(f"data/{exchange_code.lower()}", exist_ok=True)
            with open(f"data/{exchange_code.lower()}/latest.json", "w") as f:
                json.dump({"exchange": exchange_code, "fetched_at": datetime.now(timezone.utc).isoformat(),
                           "stocks": rows}, f, indent=2)

            print(f"[fetch] {exchange_code}: {len(rows)} stocks saved")
        except Exception as e:
            print(f"[fetch] {exchange_code} FAILED: {e}")

        try:
            index_data = fetch_index(exchange_code)
            append_index(exchange_code, index_data)
        except Exception as e:
            print(f"[fetch] {exchange_code} index FAILED: {e}")

if __name__ == "__main__":
    main()
