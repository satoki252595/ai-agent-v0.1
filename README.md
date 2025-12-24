# 📈 日本株リサーチAIエージェント
## Japan Stock Research AI Agent

プロ投資家向けの日本株特化型AIリサーチプラットフォーム。テクニカル分析、ファンダメンタルズ分析、マクロ経済分析、特許情報収集、アルファ発見機能を搭載した総合投資分析ツールです。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)

---

## ✨ 主な機能

### 📊 個別銘柄分析
- **リアルタイム株価データ取得** - Yahoo Finance経由で日本株データを取得
- **インタラクティブチャート** - ローソク足、出来高、移動平均線
- **詳細な企業情報** - 時価総額、PER、PBR、配当利回り等

### 📈 テクニカル分析
- **トレンド指標**: SMA, EMA, MACD, 一目均衡表, パラボリックSAR
- **オシレーター**: RSI, ストキャスティクス, CCI, ウィリアムズ%R
- **ボラティリティ**: ボリンジャーバンド, ATR, ヒストリカルボラティリティ
- **出来高指標**: OBV, VWAP, MFI, ADL
- **総合シグナル判定**: 買い/売りシグナルの自動生成

### 💰 ファンダメンタルズ分析
- **バリュエーション**: PER, PBR, PSR, EV/EBITDA, PEGレシオ
- **収益性**: ROE, ROA, ROIC, 営業利益率, 純利益率
- **財務健全性**: 自己資本比率, D/E比率, 流動比率
- **成長性**: 売上成長率, 利益成長率
- **DCF法による理論株価算出**
- **同業他社比較**

### 🌍 マクロ経済分析
- **グローバル株価指数**: 日経平均, TOPIX, S&P500, NASDAQ等
- **為替レート**: USD/JPY, EUR/JPY等
- **コモディティ**: 原油, 金, 銀, 銅
- **ボラティリティ指数**: VIX
- **市場レジーム判定**: リスクオン/リスクオフの自動判定
- **セクターローテーション分析**

### 🔍 スクリーニング・アルファ発見
- **バリュー株スクリーニング**: 低PER, 低PBR, 高配当銘柄
- **グロース株スクリーニング**: 高成長率銘柄
- **クオリティ株スクリーニング**: 高収益・健全財務銘柄
- **モメンタム株スクリーニング**: 上昇トレンド銘柄
- **売られすぎ銘柄発見**: 逆張り候補
- **ブレイクアウト候補**: レジスタンス突破間近の銘柄

### 📰 ニュース・センチメント分析
- **企業ニュース収集**: DuckDuckGo経由で最新ニュースを取得
- **センチメント分析**: ポジティブ/ネガティブ/中立の自動判定
- **センチメントスコア**: 100点満点でセンチメントを数値化

### 🔬 特許・技術力分析
- **特許ポートフォリオ分析**: Google Patents経由で特許情報を収集
- **技術分野マッピング**: AI, 半導体, バイオ等の技術領域を分析
- **技術力スコア**: 100点満点で技術力を評価
- **特許ニュース**: 特許関連の最新動向

### 🤖 自律型AIリサーチエージェント
- **自然言語でリサーチ依頼**: 「半導体セクターの見通しを分析して」等
- **自律的な情報収集**: Web検索→記事取得→要約→レポート生成
- **ストリーミング出力**: リアルタイムでレポートを表示
- **投資家向けレポート自動生成**

---

## 🏗️ アーキテクチャ

```
app/
├── main.py              # メインUI（Streamlit）
├── config.py            # 設定・定数
├── modules/
│   ├── stock_data.py    # 株価データ取得
│   ├── technical.py     # テクニカル分析
│   ├── fundamental.py   # ファンダメンタルズ分析
│   ├── macro.py         # マクロ経済分析
│   ├── patent.py        # 特許情報収集
│   ├── alpha.py         # アルファ発見
│   ├── news.py          # ニュース・センチメント
│   └── ai_agent.py      # AIリサーチエージェント
├── utils/
│   └── helpers.py       # ユーティリティ関数
├── requirements.txt
└── Dockerfile
```

---

## 🚀 セットアップ

### Docker Composeで起動（推奨）

```bash
# リポジトリをクローン
git clone <repository-url>
cd ai-agent-v0.1

# Docker Composeで起動
docker-compose up -d

# ブラウザで http://localhost:8501 にアクセス
```

### ローカル環境で起動

```bash
# 仮想環境を作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
cd app
pip install -r requirements.txt

# Ollamaサーバーを起動（別ターミナル）
ollama serve

# モデルをダウンロード
ollama pull nemotron-3-nano

# アプリを起動
streamlit run main.py
```

---

## 📋 必要要件

- **Python**: 3.11+
- **Docker**: 20.10+ (Docker Compose使用時)
- **Ollama**: ローカルLLM推論用
- **GPU**: 推奨（Ollamaのパフォーマンス向上）

---

## 🔧 設定

環境変数またはStreamlit secretsで設定可能:

```bash
OLLAMA_BASE_URL=http://localhost:11435  # Ollama APIエンドポイント
MODEL_NAME=nemotron-3-nano              # 使用するLLMモデル
```

---

## 📦 使用技術

| カテゴリ | 技術 |
|---------|------|
| **UI** | Streamlit, Plotly |
| **LLM** | Ollama, LangChain |
| **データ取得** | yfinance, DuckDuckGo Search |
| **スクレイピング** | Trafilatura |
| **データ分析** | pandas, numpy |
| **コンテナ** | Docker, Docker Compose |

---

## ⚠️ 免責事項

本ツールは情報提供を目的としており、投資助言ではありません。
投資判断は自己責任でお願いいたします。

---

## 📄 ライセンス

MIT License

---

## 🤝 コントリビューション

Issue、Pull Requestは大歓迎です！
