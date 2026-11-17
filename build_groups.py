"""Build data/groups.csv (group, stock_id, stock_name) from the FinMind TaiwanStockInfo snapshot.

Official TWSE/TPEX industries + FinMind thematic categories. A stock can sit in several groups.
Add finer themes in custom_groups.csv (group,stock_id) - they are merged in by build_data.py.
Refresh the snapshot:  curl -o data/stock_info_raw.json 'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo'
"""
import csv, json, re
from collections import defaultdict

DROP = {"電子工業", "化學生技醫療", "其他", "Index", "所有證券", "大盤", "ETF", "ETN", "上櫃ETF", "存託憑證",
        "創新板股票", "創新版股票", "受益證券", "指數投資證券(ETN)", "上櫃指數股票型基金(ETF)"}
ALIAS = {"其他電子類": "其他電子業", "電子通路類": "電子通路業", "數位雲端類": "數位雲端", "居家生活類": "居家生活",
         "綠能環保類": "綠能環保", "運動休閒類": "運動休閒", "觀光事業": "觀光餐旅", "金融業": "金融保險",
         "油電燃氣業": "油電燃氣業"}

raw = json.load(open("data/stock_info_raw.json"))["data"]
members = defaultdict(dict)
for r in raw:
    if r["type"] not in ("twse", "tpex") or not re.fullmatch(r"\d{4}", r["stock_id"]):
        continue
    g = r["industry_category"]
    if g in DROP:
        continue
    g = ALIAS.get(g, g)
    members[g][r["stock_id"]] = r["stock_name"]

with open("data/groups.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["group", "stock_id", "stock_name"])
    for g in sorted(members):
        for sid, name in sorted(members[g].items()):
            w.writerow([g, sid, name])
print({g: len(m) for g, m in sorted(members.items(), key=lambda x: -len(x[1]))})

import os
if not os.path.exists("custom_groups.csv"):
    open("custom_groups.csv", "w", encoding="utf-8").write(
        "# 自訂細分族群：group,stock_id（一檔可屬多群；以 # 開頭為註解）\n"
        "group,stock_id\n"
        "# 範例：AI伺服器,2317\n")
