"""Build dist/index.html: embed prices + groups into template.html.  Usage: python build_data.py"""
import csv, json, sqlite3, os

con = sqlite3.connect("data/prices.db")
dates = [r[0] for r in con.execute("select distinct date from px order by date")]
di = {d: i for i, d in enumerate(dates)}
taiex = dict(con.execute("select date, close from idx"))

groups = {}
for path in ("data/groups.csv", "custom_groups.csv"):
    if not os.path.exists(path):
        continue
    lines = [l for l in open(path, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    for r in csv.DictReader(lines):
        groups.setdefault(r["group"].strip(), [])
        sid = r["stock_id"].strip()
        if sid not in groups[r["group"].strip()]:
            groups[r["group"].strip()].append(sid)

used = {s for m in groups.values() for s in m}
stocks = {}
for d, code, name, mkt, close in con.execute("select date, code, name, mkt, close from px order by date"):
    if code not in used:
        continue
    s = stocks.setdefault(code, {"n": name, "m": mkt, "c": [None] * len(dates)})
    s["n"] = name
    s["c"][di[d]] = close

groups = {g: [c for c in m if c in stocks] for g, m in groups.items()}
groups = {g: m for g, m in groups.items() if m}
data = {"dates": dates, "taiex": [taiex.get(d) for d in dates], "stocks": stocks, "groups": groups}

os.makedirs("dist", exist_ok=True)
html = open("template.html", encoding="utf-8").read().replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
open("dist/index.html", "w", encoding="utf-8").write(html)
print(f"{len(dates)} days {dates[0]}..{dates[-1]}, {len(stocks)} stocks, {len(groups)} groups -> dist/index.html ({len(html)//1024} KB)")
