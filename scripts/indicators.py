import csv
import json
import os
from collections import defaultdict

def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def load_prices(exchange_code):
    path = f"data/{exchange_code.lower()}/prices.csv"
    if not os.path.exists(path):
        return {}
    by_ticker = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            t = row.get("ticker", "")
            p = safe_float(row.get("price"))
            if t and p is not None:
                by_ticker[t].append({
                    "date":       row.get("date", ""),
                    "name":       row.get("name", ""),
                    "price":      p,
                    "change_pct": safe_float(row.get("change_pct")),
                    "volume":     safe_float(row.get("volume")),
                    "market_cap": safe_float(row.get("market_cap")),
                    "open":       safe_float(row.get("open")),
                    "high":       safe_float(row.get("high")),
                    "low":        safe_float(row.get("low")),
                })
    # sort by date
    for t in by_ticker:
        by_ticker[t].sort(key=lambda x: x["date"])
    return by_ticker

def moving_average(prices, window):
    if len(prices) < window:
        return None
    return round(sum(prices[-window:]) / window, 4)

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    gains  = gains[-period:]
    losses = losses[-period:]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def pct_change(prices, days):
    if len(prices) < days + 1:
        return None
    old = prices[-(days + 1)]
    new = prices[-1]
    if old == 0:
        return None
    return round((new - old) / old * 100, 2)

def compute_indicators(exchange_code):
    by_ticker = load_prices(exchange_code)
    results = {}

    for ticker, history in by_ticker.items():
        prices = [h["price"] for h in history]
        latest = history[-1]

        results[ticker] = {
            "ticker":      ticker,
            "name":        latest["name"],
            "exchange":    exchange_code,
            "price":       latest["price"],
            "change_pct":  latest["change_pct"],
            "volume":      latest["volume"],
            "market_cap":  latest["market_cap"],
            "open":        latest["open"],
            "high":        latest["high"],
            "low":         latest["low"],
            "date":        latest["date"],
            "ma5":         moving_average(prices, 5),
            "ma20":        moving_average(prices, 20),
            "rsi14":       rsi(prices, 14),
            "chg_5d":      pct_change(prices, 5),
            "chg_20d":     pct_change(prices, 20),
            "data_points": len(prices),
            "price_history": [{"date": h["date"], "price": h["price"]} for h in history[-30:]],
        }

    return results

def load_index_history(exchange_code):
    path = "data/indices.csv"
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            if row.get("exchange") == exchange_code:
                v = safe_float(row.get("value"))
                if v:
                    rows.append({"date": row["date"], "value": v,
                                 "change_pct": safe_float(row.get("change_pct")),
                                 "market_cap": safe_float(row.get("market_cap"))})
    return sorted(rows, key=lambda x: x["date"])[-60:]

def main():
    for exchange_code in ("DSE", "NSE"):
        indicators = compute_indicators(exchange_code)
        index_hist  = load_index_history(exchange_code)

        out = {"exchange": exchange_code, "stocks": indicators, "index_history": index_hist}
        path = f"data/{exchange_code.lower()}/indicators.json"
        with open(path, "w") as f:
            json.dump(out, f, indent=2)

        n = len(indicators)
        print(f"[indicators] {exchange_code}: {n} stocks processed")

if __name__ == "__main__":
    main()
