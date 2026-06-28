import json
import os
import csv
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta

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

def main():
    now      = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    date_str = now.strftime("%Y-%m-%d")

    dse_ind = load_json("data/dse/indicators.json", {"stocks": {}, "index_history": []})
    nse_ind = load_json("data/nse/indicators.json", {"stocks": {}, "index_history": []})

    lines = [
        f"# East Africa Stock Market — Weekly Report {date_str}",
        f"",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M EAT')}",
        f"",
    ]

    for label, ind, currency in [("DSE — Dar es Salaam", dse_ind, "TZS"),
                                   ("NSE — Nairobi",        nse_ind, "KES")]:
        stocks  = ind.get("stocks", {})
        history = ind.get("index_history", [])

        # Index week change
        week_hist = [h for h in history if h.get("date","") >= week_ago]
        idx_start = week_hist[0]["value"]  if week_hist else None
        idx_end   = week_hist[-1]["value"] if week_hist else None
        idx_chg   = round((idx_end - idx_start) / idx_start * 100, 2) if idx_start and idx_end else None

        lines += [f"## {label}", ""]
        if idx_chg is not None:
            direction = "▲" if idx_chg >= 0 else "▼"
            lines.append(f"**Index weekly change:** {direction} {abs(idx_chg):.2f}%  "
                         f"({idx_start:,.0f} → {idx_end:,.0f})")
            lines.append("")

        # Top gainers
        with_chg = [(t, s) for t, s in stocks.items() if s.get("chg_5d") is not None]
        gainers  = sorted(with_chg, key=lambda x: x[1]["chg_5d"], reverse=True)[:5]
        losers   = sorted(with_chg, key=lambda x: x[1]["chg_5d"])[:5]

        lines += ["**Top Gainers (5-day)**", "",
                  f"| Ticker | Company | Price ({currency}) | 5D Change |",
                  f"|--------|---------|---------|-----------|"]
        for t, s in gainers:
            lines.append(f"| {t} | {s.get('name','')} | {s.get('price','')} | +{s.get('chg_5d','')}% |")

        lines += ["", "**Top Losers (5-day)**", "",
                  f"| Ticker | Company | Price ({currency}) | 5D Change |",
                  f"|--------|---------|---------|-----------|"]
        for t, s in losers:
            lines.append(f"| {t} | {s.get('name','')} | {s.get('price','')} | {s.get('chg_5d','')}% |")

        # RSI alerts
        overbought = [(t, s) for t, s in stocks.items()
                      if s.get("rsi14") and s["rsi14"] >= 70]
        oversold   = [(t, s) for t, s in stocks.items()
                      if s.get("rsi14") and s["rsi14"] <= 30]

        if overbought or oversold:
            lines += ["", "**RSI Alerts**", ""]
            for t, s in overbought:
                lines.append(f"- 🔴 {t} ({s.get('name','')}) — RSI {s['rsi14']:.1f} OVERBOUGHT")
            for t, s in oversold:
                lines.append(f"- 🟢 {t} ({s.get('name','')}) — RSI {s['rsi14']:.1f} OVERSOLD")
        lines.append("")

    os.makedirs("reports/weekly", exist_ok=True)
    path = f"reports/weekly/report_{date_str}.md"
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[weekly_report] Generated {path}")

if __name__ == "__main__":
    main()
