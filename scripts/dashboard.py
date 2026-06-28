import json
import os
import csv
from datetime import datetime, timezone

def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)

def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def top_movers(stocks, n=5):
    with_pct = [(t, s) for t, s in stocks.items() if s.get("change_pct") is not None]
    gainers = sorted(with_pct, key=lambda x: x[1]["change_pct"], reverse=True)[:n]
    losers  = sorted(with_pct, key=lambda x: x[1]["change_pct"])[:n]
    return (
        [{"ticker": t, **s} for t, s in gainers],
        [{"ticker": t, **s} for t, s in losers],
    )

def volume_leaders(stocks, n=5):
    with_vol = [(t, s) for t, s in stocks.items() if s.get("volume")]
    leaders  = sorted(with_vol, key=lambda x: x[1]["volume"], reverse=True)[:n]
    return [{"ticker": t, **s} for t, s in leaders]

def rsi_alerts(stocks):
    alerts = []
    for ticker, s in stocks.items():
        rsi = s.get("rsi14")
        if rsi is None:
            continue
        if rsi >= 70:
            alerts.append({"ticker": ticker, "name": s.get("name",""), "rsi": rsi,
                           "signal": "overbought", "exchange": s.get("exchange","")})
        elif rsi <= 30:
            alerts.append({"ticker": ticker, "name": s.get("name",""), "rsi": rsi,
                           "signal": "oversold", "exchange": s.get("exchange","")})
    return alerts

def latest_index(exchange_code):
    path = "data/indices.csv"
    if not os.path.exists(path):
        return {}
    latest = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            if row.get("exchange") == exchange_code:
                latest = row
    return latest

def main():
    os.makedirs("docs", exist_ok=True)

    dse_ind = load_json("data/dse/indicators.json", {"stocks": {}, "index_history": []})
    nse_ind = load_json("data/nse/indicators.json", {"stocks": {}, "index_history": []})

    dse_stocks = dse_ind.get("stocks", {})
    nse_stocks = nse_ind.get("stocks", {})

    dse_gainers, dse_losers = top_movers(dse_stocks)
    nse_gainers, nse_losers = top_movers(nse_stocks)

    dse_index = latest_index("DSE")
    nse_index = latest_index("NSE")

    all_stocks = {**dse_stocks, **nse_stocks}
    alerts = rsi_alerts(all_stocks)

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "exchanges": {
            "DSE": {
                "name":        "Dar es Salaam Stock Exchange",
                "country":     "Tanzania",
                "currency":    "TZS",
                "index_value": safe_float(dse_index.get("value")),
                "index_change_pct": safe_float(dse_index.get("change_pct")),
                "market_cap":  safe_float(dse_index.get("market_cap")),
                "stock_count": len(dse_stocks),
                "gainers":     dse_gainers,
                "losers":      dse_losers,
                "volume_leaders": volume_leaders(dse_stocks),
                "index_history":  dse_ind.get("index_history", []),
                "all_stocks":  list(dse_stocks.values()),
            },
            "NSE": {
                "name":        "Nairobi Securities Exchange",
                "country":     "Kenya",
                "currency":    "KES",
                "index_value": safe_float(nse_index.get("value")),
                "index_change_pct": safe_float(nse_index.get("change_pct")),
                "market_cap":  safe_float(nse_index.get("market_cap")),
                "stock_count": len(nse_stocks),
                "gainers":     nse_gainers,
                "losers":      nse_losers,
                "volume_leaders": volume_leaders(nse_stocks),
                "index_history":  nse_ind.get("index_history", []),
                "all_stocks":  list(nse_stocks.values()),
            },
        },
        "rsi_alerts": alerts,
        "total_stocks": len(all_stocks),
    }

    with open("docs/data.json", "w") as f:
        json.dump(data, f)

    with open("status.json", "w") as f:
        json.dump({"status": "running", "last_run": data["updated_at"],
                   "total_stocks": len(all_stocks),
                   "dse_stocks": len(dse_stocks), "nse_stocks": len(nse_stocks)}, f, indent=2)

    print(f"[dashboard] Generated docs/data.json — DSE: {len(dse_stocks)} stocks, NSE: {len(nse_stocks)} stocks")

if __name__ == "__main__":
    main()
