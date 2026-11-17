# 台股產業族群觀測面板
- `fetch_prices.py` 抓證交所/櫃買收盤價 → `data/prices.db`
- `build_groups.py` 產生族群對照；細分族群請編輯 `custom_groups.csv`
- `build_data.py` 產生 `dist/index.html`（單一檔案，可直接開啟）
- 自動更新：`.github/workflows/update.yml`（GitHub Pages）。部署：建立 repo → 推送 → Settings › Pages › Source 選 GitHub Actions。
