# ReoNa Event Tracker（公開網站原型）

## 目前內容
- 繁體中文響應式活動列表
- 分類篩選、關鍵字搜尋、日期排序
- 使用瀏覽器 localStorage 記錄個人追蹤狀態
- 以官方公告作為初始活動資料
- 官方情報來源入口

## 本版本的重要限制
這是可部署的靜態網站原型，並非已上線網站。`events.json` 目前是人工整理的初始資料。
每日自動追蹤通知已在 ChatGPT 中另行建立，但它不會自動把新資料寫入這個靜態網站。
若要讓所有訪客看到同一份自動更新的活動資料，還需要：
1. 公開網站託管（例如 Cloudflare Pages / Netlify / Vercel）。
2. 排程工作（例如 GitHub Actions / Cloudflare Workers Cron）。
3. 官方來源擷取與資料正規化程式。
4. 資料儲存（Git JSON、Supabase 或其他資料庫）。
5. 去重、來源驗證、日期與售票狀態變更紀錄。
6. 對外公開前確認商標、圖片與網站內容使用規範。

## 本機預覽
在此資料夾執行：
`python -m http.server 8000`
再開啟 `http://localhost:8000`

## 初始資料來源
- https://www.reona-reona.com/
- https://www.sonymusic.co.jp/artist/ReoNa/info/587352
- https://www.reona-reona.com/BEST/
- https://reonafc.com/
- https://www.youtube.com/@ReoNaofficial

## 免責聲明
本網站為非官方粉絲資訊整理工具，與 ReoNa、Sony Music、SACRA MUSIC 或粉絲俱樂部無隸屬關係。
活動時間、售票狀態、延期或取消，請以主辦單位及官方公告為準。
Cloudflare GitHub integration enabled.
