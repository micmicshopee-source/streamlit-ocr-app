FROM python:3.9-slim

WORKDIR /app

# 安裝系統依賴
# - curl: 健康檢查
# - poppler-utils: pdf2image 所需（PDF 轉圖片、PPT）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件（Docker 用完整版 requirements-server.txt）
COPY requirements-server.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

# 複製應用文件
COPY app.py .
COPY pdf_converter.py .
COPY NotoSansTC-Regular.ttf .
COPY premium_dark.css .
COPY templates/ ./templates/
COPY pages/ ./pages/

# 創建數據目錄
RUN mkdir -p /app/data /app/invoice_images

# 設置環境變數
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8501

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 啟動命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
