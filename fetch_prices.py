"""Fetch daily close prices (TWSE + TPEX, common stocks) and TAIEX into SQLite.

Usage: python fetch_prices.py [--start 2026-06-01]   (idempotent; skips days already stored)
"""
import argparse, datetime as dt, re, sqlite3, sys, time
import requests

DB = "data/prices.db"
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 tw-sector-dashboard"


def get_json(url, tries=6):
    for i in range(tries):
        try:
            r = S.get(url, timeout=40)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            wait = 3 * (i + 1) if not isinstance(e, ValueError) else 60 * (i + 1)  # non-JSON = rate-limited by TWSE
            print(f"  retry {i+1}/{tries} ({e.__class__.__name__}) in {wait}s", flush=True)
            time.sleep(wait)
    return None


def num(s):
    s = str(s).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def roc_to_iso(s):
    y, m, d = s.split("/")
    return f"{int(y)+1911:04d}-{int(m):02d}-{int(d):02d}"


def init(con):
    con.execute("create table if not exists px(date text, code text, name text, mkt text, close real, primary key(date, code))")
    con.execute("create table if not exists idx(date text primary key, close real)")
    con.commit()


def fetch_index(con, start):
    d = dt.date.fromisoformat(start).replace(day=1)
    today = dt.date.today()
    while d <= today:
        j = get_json(f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={d:%Y%m}01&response=json")
        if j and j.get("stat") == "OK":
            for row in j["data"]:
                v = num(row[4])
                if v:
                    con.execute("insert or replace into idx values(?,?)", (roc_to_iso(row[0]), v))
        con.commit()
        time.sleep(2)
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def fetch_twse(day):
    j = get_json(f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={day:%Y%m%d}&type=ALLBUT0999&response=json")
    out = []
    if not j or j.get("stat") != "OK" or f"{day.year-1911}年{day:%m}月{day:%d}日" not in j["tables"][0].get("title", ""):
        return out
    for t in j.get("tables", []):
        if "每日收盤行情" in t.get("title", ""):
            for r in t["data"]:
                if re.fullmatch(r"\d{4}", r[0]) and num(r[8]):
                    out.append((r[0], r[1].strip(), "twse", num(r[8])))
    return out


def fetch_tpex(day):
    j = get_json(f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={day:%Y/%m/%d}&type=EW&response=json")
    out = []
    if not j or j.get("date") != f"{day:%Y%m%d}":  # guard: API silently returns another day
        return out
    for t in j.get("tables", []):
        if "每日收盤行情" in t.get("title", ""):
            for r in t.get("data", []):
                if re.fullmatch(r"\d{4}", r[0]) and num(r[2]):
                    out.append((r[0], r[1].strip(), "tpex", num(r[2])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-06-01")
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    init(con)
    fetch_index(con, a.start)
    days = [r[0] for r in con.execute("select date from idx where date>=? order by date", (a.start,))]
    have = {r[0] for r in con.execute("select distinct date from px")}
    todo = [d for d in days if d not in have]
    print(f"{len(days)} trading days, {len(todo)} to fetch", flush=True)
    for i, ds in enumerate(todo, 1):
        day = dt.date.fromisoformat(ds)
        rows = fetch_twse(day)
        time.sleep(7)
        rows += fetch_tpex(day)
        time.sleep(3)
        if not any(r[2] == "twse" for r in rows) or not any(r[2] == "tpex" for r in rows):
            print(f"[{i}/{len(todo)}] {ds} incomplete (twse/tpex missing) - skipped", flush=True)
            continue
        con.executemany("insert or replace into px values(?,?,?,?,?)", [(ds, *r) for r in rows])
        con.commit()
        print(f"[{i}/{len(todo)}] {ds} {len(rows)} stocks", flush=True)


if __name__ == "__main__":
    main()
