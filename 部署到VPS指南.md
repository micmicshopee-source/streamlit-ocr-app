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
redirect_uri = "https://你的域名/"

# 若用 LINE 登入
[line_auth]
channel_id = "你的Channel ID"
channel_secret = "你的Channel Secret"
callback_url = "https://你的域名/"
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

## 六、Nginx 反向代理（HTTPS）

1. **安裝 Nginx 與 Certbot**

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

2. **新增站點**

```bash
sudo nano /etc/nginx/sites-available/streamlit-ocr
```

內容（將 `你的域名.com` 改為實際域名）：

```nginx
server {
    listen 80;
    server_name 你的域名.com www.你的域名.com;

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

3. **啟用並申請 SSL**

```bash
sudo ln -s /etc/nginx/sites-available/streamlit-ocr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d 你的域名.com -d www.你的域名.com
```

4. **防火牆**

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## 七、Docker 部署（替代方案）

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

## 八、更新部署

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

## 九、常見問題

| 問題 | 解法 |
|------|------|
| 502 Bad Gateway | 確認 Streamlit 已啟動：`curl http://localhost:8501/_stcore/health` |
| PDF 轉圖片失敗 | 安裝 poppler：`sudo apt install poppler-utils` |
| 資料重啟後消失 | 確認 `data/`、`invoice_images/` 在專案目錄，非臨時路徑 |
| 無法外網訪問 | 檢查防火牆、Nginx、域名 DNS |
