import requests
from bs4 import BeautifulSoup
import csv
import json
import os
import re
from datetime import datetime, timezone

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

PRICES_FIELDNAMES = [
    "date", "exchange", "ticker", "name", "price", "change", "change_pct",
    "volume", "market_cap", "open", "high", "low",
]

INDEX_FIELDNAMES = ["date", "exchange", "index_name", "value", "change", "change_pct", "market_cap"]


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


def fetch_nse():
    """Scrape NSE stocks and NASI index from afx.kwayisi.org/nse/"""
    print("[fetch] NSE — afx.kwayisi.org/nse/")
    url = "https://afx.kwayisi.org/nse/"
    resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
    print(f"[fetch] NSE HTTP {resp.status_code}, content length {len(resp.text)}")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Parse NASI index — appears as text near the top of the page
    index_row = None
    page_text = soup.get_text(" ", strip=True)
    # Match patterns like "222.42 +3.20 +1.46%"
    m = re.search(r"NASI[^\d]*([\d,]+\.?\d*)\s*([+-][\d.]+)?\s*([+-][\d.]+%)?", page_text)
    if m:
        value = safe_float(m.group(1))
        change = safe_float(m.group(2)) if m.group(2) else None
        change_pct_str = (m.group(3) or "").replace("%", "")
        change_pct = safe_float(change_pct_str) if change_pct_str else None
        if value:
            index_row = {
                "date": today, "exchange": "NSE",
                "index_name": "NASI", "value": value,
                "change": change, "change_pct": change_pct, "market_cap": None,
            }

    # Parse stocks table — columns: Ticker | Company | Volume | Price | Change
    stocks = []
    table = soup.find("table")
    if not table:
        print("[fetch] NSE: no table found — page snippet:")
        print(resp.text[:500])
        return stocks, index_row

    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        ticker = cols[0].get_text(strip=True)
        company = cols[1].get_text(strip=True)
        volume_text = cols[2].get_text(strip=True)
        price_text = cols[3].get_text(strip=True)
        change_text = cols[4].get_text(strip=True) if len(cols) > 4 else ""

        price = safe_float(price_text)
        if not ticker or price is None:
            continue

        volume = safe_int(volume_text)
        change_abs = safe_float(change_text) or 0.0
        prev_price = price - change_abs
        change_pct = round((change_abs / prev_price) * 100, 2) if prev_price and change_abs else 0.0

        stocks.append({
            "date": today, "exchange": "NSE",
            "ticker": ticker, "name": company,
            "price": price, "change": change_abs, "change_pct": change_pct,
            "volume": volume, "market_cap": None, "open": None, "high": None, "low": None,
        })

    print(f"[fetch] NSE: {len(stocks)} stocks")
    return stocks, index_row


def fetch_dse():
    """Scrape DSE stocks from africanfinancials.com"""
    print("[fetch] DSE — africanfinancials.com")
    url = "https://africanfinancials.com/dar-es-salaam-stock-exchange-share-prices/"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    headers = {**BROWSER_HEADERS, "Referer": "https://www.google.com/"}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        print(f"[fetch] DSE HTTP {resp.status_code}, content length {len(resp.text)}")
        resp.raise_for_status()
    except Exception as e:
        print(f"[fetch] DSE FAILED: {e}")
        return [], None

    soup = BeautifulSoup(resp.text, "html.parser")
    stocks = []

    table = soup.find("table")
    if not table:
        print("[fetch] DSE: no table found — page snippet:")
        print(resp.text[:500])
        return stocks, None

    rows = table.find_all("tr")
    # Detect header row to map column positions
    header_cols = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])] if rows else []
    col_idx = {h: i for i, h in enumerate(header_cols)}

    # Fallback column order if headers not found: ticker, name, price, change, change_pct, volume
    t_col  = col_idx.get("ticker", col_idx.get("symbol", col_idx.get("code", 0)))
    n_col  = col_idx.get("name", col_idx.get("company", col_idx.get("security", 1)))
    p_col  = col_idx.get("price", col_idx.get("last", col_idx.get("close", 2)))
    ch_col = col_idx.get("change", 3)
    cp_col = col_idx.get("%change", col_idx.get("change %", col_idx.get("change%", 4)))
    v_col  = col_idx.get("volume", col_idx.get("vol", 5))

    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        def gcol(idx):
            return cols[idx].get_text(strip=True) if idx < len(cols) else ""

        ticker = gcol(t_col)
        company = gcol(n_col)
        price = safe_float(gcol(p_col))

        if not ticker or price is None:
            continue

        stocks.append({
            "date": today, "exchange": "DSE",
            "ticker": ticker, "name": company,
            "price": price,
            "change": safe_float(gcol(ch_col)) or 0.0,
            "change_pct": safe_float(gcol(cp_col)) or 0.0,
            "volume": safe_int(gcol(v_col)),
            "market_cap": None, "open": None, "high": None, "low": None,
        })

    print(f"[fetch] DSE: {len(stocks)} stocks")
    return stocks, None


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
                    return  # already saved

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
    os.makedirs("data/dse", exist_ok=True)
    os.makedirs("data/nse", exist_ok=True)

    nse_stocks, nse_index = fetch_nse()
    if nse_stocks:
        append_prices("NSE", nse_stocks)
        save_latest("NSE", nse_stocks)
        append_index(nse_index)

    dse_stocks, dse_index = fetch_dse()
    if dse_stocks:
        append_prices("DSE", dse_stocks)
        save_latest("DSE", dse_stocks)
        append_index(dse_index)

    print(f"\n[fetch] Done — NSE: {len(nse_stocks)}, DSE: {len(dse_stocks)}")


if __name__ == "__main__":
    main()
