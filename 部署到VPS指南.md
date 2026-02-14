# 部署到自購 VPS 指南

伺服器已安裝 Python 與系統依賴後，依下列步驟部署。

---

## 一、前置檢查

確認伺服器已安裝：

```bash
python3 --version   # 建議 3.9+
pip3 --version
```

**系統依賴**（PDF 轉換需 poppler）：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y poppler-utils curl

# 若用 Docker 部署，則需 Docker
docker --version
docker compose version
```

---

## 二、取得程式碼

```bash
cd /opt   # 或你選擇的目錄
sudo git clone https://github.com/你的用戶名/streamlit_ocr_app.git
cd streamlit_ocr_app
```

若程式在本機，可用 `scp` 或 `rsync` 上傳：

```bash
# 在本機執行
scp -r d:\streamlit_ocr_app\* user@你的伺服器IP:/opt/streamlit_ocr_app/
```

---

## 三、安裝 Python 套件

```bash
cd /opt/streamlit_ocr_app

# 建立虛擬環境（建議）
python3 -m venv venv
source venv/bin/activate   # Linux
# Windows: venv\Scripts\activate

# 安裝完整依賴（伺服器版，含 pdf2docx）
pip install -r requirements-server.txt
```

若沒有 `requirements-server.txt`，使用：

```bash
pip install -r requirements.txt
pip install pdf2docx google-cloud-speech   # 補齊
```

---

## 四、設定 Secrets

```bash
mkdir -p .streamlit
nano .streamlit/secrets.toml
```

內容範例：

```toml
GEMINI_API_KEY = "你的Gemini金鑰"

[google_auth]
client_id = "你的Client ID"
client_secret = "你的Client Secret"
redirect_uri = "https://getaiinvoice.com/"

# 若用 LINE 登入
[line_auth]
channel_id = "你的Channel ID"
channel_secret = "你的Channel Secret"
callback_url = "https://getaiinvoice.com/"
```

---

## 五、啟動應用

### 方式 A：直接執行（測試用）

```bash
cd /opt/streamlit_ocr_app
source venv/bin/activate
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

瀏覽器開啟：`http://伺服器IP:8501`

### 方式 B：背景執行（推薦）

```bash
cd /opt/streamlit_ocr_app
nohup streamlit run app.py --server.port=8501 --server.address=0.0.0.0 > streamlit.log 2>&1 &
```

### 方式 C：systemd 服務（開機自啟）

```bash
sudo nano /etc/systemd/system/streamlit-ocr.service
```

內容：

```ini
[Unit]
Description=Streamlit OCR App
After=network.target

[Service]
Type=simple
User=你的用戶名
WorkingDirectory=/opt/streamlit_ocr_app
ExecStart=/opt/streamlit_ocr_app/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
```

啟用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable streamlit-ocr
sudo systemctl start streamlit-ocr
sudo systemctl status streamlit-ocr
```

---

## 六、更新程式碼後重啟

修改程式後，需重新拉取並重啟：

```bash
cd /opt/streamlit_ocr_app   # 或你的專案路徑
git fetch origin && git pull   # 若用 Git
# 或手動上傳 app.py、premium_dark.css、.streamlit/config.toml 等

pkill -f "streamlit run app.py"   # 停止舊進程
source venv/bin/activate
nohup streamlit run app.py --server.port=8501 --server.address=0.0.0.0 > streamlit.log 2>&1 &
```

若用 systemd：`sudo systemctl restart streamlit-ocr`

---

## 七、Nginx 反向代理（HTTPS）

1. **安裝 Nginx 與 Certbot**

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

2. **新增站點**

```bash
sudo nano /etc/nginx/sites-available/streamlit-ocr
```

內容：

```nginx
server {
    listen 80;
    server_name getaiinvoice.com www.getaiinvoice.com;

    # 隱私權政策（獨立 URL，供 Google OAuth 品牌驗證）
    location = /privacy {
        alias /opt/streamlit_ocr_app/static/privacy.html;
        default_type text/html;
        add_header Cache-Control "public, max-age=3600";
    }

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

3. **加入 /privacy 靜態頁面（若尚未加入）**

若你已有舊版 Nginx 設定，只需在 `location /` **之前**插入以下區塊：

```nginx
    # 隱私權政策（獨立 URL，供 Google OAuth 品牌驗證）
    location = /privacy {
        alias /opt/streamlit_ocr_app/static/privacy.html;
        default_type text/html;
        add_header Cache-Control "public, max-age=3600";
    }

```

完整結構應為：

```
server {
    listen 80;
    server_name getaiinvoice.com www.getaiinvoice.com;

    location = /privacy { ... }   ← 加在這裡，在 location / 之前

    location / {
        proxy_pass http://127.0.0.1:8501;
        ...
    }
}
```

修改後執行 `sudo nginx -t` 檢查語法，再 `sudo systemctl reload nginx` 重新載入。

4. **啟用並申請 SSL**

```bash
sudo ln -s /etc/nginx/sites-available/streamlit-ocr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d getaiinvoice.com -d www.getaiinvoice.com
```

> **若使用 Google / LINE 登入**：請在 Google Cloud Console、LINE Developers 後台，將「授權重導 URI」設為 `https://getaiinvoice.com/`（與 secrets.toml 一致）。
>
> **Google OAuth 品牌驗證**：首頁填 `https://getaiinvoice.com/`，隱私權政策填 `https://getaiinvoice.com/privacy`（需先在 Google Search Console 驗證網域擁有權）。

5. **防火牆**

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## 八、Docker 部署（替代方案）

若偏好 Docker：

```bash
cd /opt/streamlit_ocr_app

# 修改 Dockerfile 使用完整依賴（或複製 requirements-server.txt 為 requirements.txt）
# 建置並啟動
docker compose -f docker-compose.prod.yml up -d --build

# 查看日誌
docker compose -f docker-compose.prod.yml logs -f
```

---

## 九、更新部署

```bash
cd /opt/streamlit_ocr_app
git pull
source venv/bin/activate
pip install -r requirements-server.txt --upgrade

# 若用 systemd
sudo systemctl restart streamlit-ocr

# 若用 Docker
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 十、常見問題

### Nginx 錯誤：`location directive is not allowed here`

**原因**：Certbot 修改後會產生兩個 `server` 區塊（80 與 443），`location` 必須放在 `server { }` 內部，且路徑要正確。

**解法**：在 VPS 上執行 `sudo nano /etc/nginx/sites-available/streamlit-ocr`，確認結構如下（**路徑請依實際專案位置修改**，例如 `/root/streamlit-ocr-app`）：

```nginx
# HTTP：導向 HTTPS
server {
    listen 80;
    server_name getaiinvoice.com www.getaiinvoice.com;
    return 301 https://$host$request_uri;
}

# HTTPS：主要服務
server {
    listen 443 ssl;
    server_name getaiinvoice.com www.getaiinvoice.com;

    # SSL（由 certbot 自動加入，勿刪）
    ssl_certificate /etc/letsencrypt/live/getaiinvoice.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/getaiinvoice.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # 隱私權政策（獨立 URL）
    location = /privacy {
        root /root/streamlit-ocr-app/static;
        try_files /privacy.html =404;
        default_type text/html;
        add_header Cache-Control "public, max-age=3600";
    }

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

**注意**：若 certbot 已跑過，SSL 那幾行可能已存在，只需在 `listen 443 ssl` 的 `server` 區塊內、`location /` 之前加入 `location = /privacy` 即可。專案路徑若不同（如 `/opt/streamlit_ocr_app`），請改 `alias` 路徑。

修改後執行：
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 僅 port 80 有監聽、443 沒有

表示 SSL 尚未設定，請執行：
```bash
sudo certbot --nginx -d getaiinvoice.com -d www.getaiinvoice.com
```

---

| 問題 | 解法 |
|------|------|
| 502 Bad Gateway | 確認 Streamlit 已啟動：`curl http://localhost:8501/_stcore/health` |
| PDF 轉圖片失敗 | 安裝 poppler：`sudo apt install poppler-utils` |
| 資料重啟後消失 | 確認 `data/`、`invoice_images/` 在專案目錄，非臨時路徑 |
| 無法外網訪問 | 檢查防火牆、Nginx、域名 DNS |
