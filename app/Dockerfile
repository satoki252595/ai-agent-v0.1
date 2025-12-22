FROM python:3.11-slim

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体のコピー
COPY . .

# Streamlitのポートを公開
EXPOSE 8501

# 起動コマンド
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0"]
