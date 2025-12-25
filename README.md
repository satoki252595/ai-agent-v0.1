# 日本株リサーチAIエージェント

日本株特化型のAIリサーチアシスタント。ローカルLLM（Ollama）とローカルDB（TinyDB + ChromaDB）で完全オフライン動作可能。

## 機能概要

| 機能 | 説明 | 実装 |
|------|------|------|
| **チャットUI** | 自然言語で銘柄分析を依頼 | Streamlit |
| **テクニカル分析** | SMA, MACD, RSI, ボリンジャーバンド等 | pandas |
| **ファンダメンタル** | PER, PBR, ROE, DCF理論株価 | yfinance |
| **マクロ分析** | 日経平均, 為替, 市場レジーム判定 | yfinance |
| **スクリーニング** | バリュー/グロース/高配当銘柄発見 | 独自ロジック |
| **ニュース分析** | センチメント分析付きニュース収集 | DuckDuckGo |
| **特許分析** | 技術力スコア算出 | Google Patents |

## アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit UI                        │
│              （モバイルファースト設計）                │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│               AIエージェント                         │
│         Ollama + nemotron-3-nano                    │
│              (LangChain)                            │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│   TinyDB      │   │   ChromaDB    │
│  (構造化DB)    │   │  (ベクトルDB)  │
│               │   │               │
│ - 銘柄情報     │   │ - 企業説明     │
│ - 価格履歴     │   │ - ニュース     │
│ - 財務データ   │   │ - リサーチ     │
│ - テクニカル   │   │               │
└───────────────┘   └───────────────┘
        │                   │
        └─────────┬─────────┘
                  ▼
        ┌─────────────────┐
        │  yfinance API   │
        │  (Yahoo Finance) │
        └─────────────────┘
```

## データベース

### TinyDB（構造化データ）
- **用途**: 銘柄情報、価格、財務データのキャッシュ
- **形式**: JSON（`app/data/stocks.json`）
- **特徴**: Pure Python、依存なし、高速

### ChromaDB（ベクトルデータ）
- **用途**: セマンティック検索（類似企業、関連ニュース）
- **埋め込み**: BGE-M3（多言語対応、日本語最適化）
- **形式**: `app/data/chroma/`

## セットアップ

```bash
# 依存インストール
cd app
pip install -r requirements.txt

# Ollama起動（別ターミナル）
ollama serve
ollama pull nemotron-3-nano

# アプリ起動
streamlit run main.py
```

## 銘柄データのロード

東証上場全銘柄のデータをDBに格納するには以下を実行：

```bash
cd app

# 全上場銘柄をロード（JPX公式データ使用、約3800銘柄）
python -m database.jpx_loader

# 主要100銘柄のみロード（高速）
python -m database.jpx_loader --major-only

# テスト用：最初の50銘柄のみ
python -m database.jpx_loader --max 50
```

### データソース

| データ | ソース | 更新頻度 |
|--------|--------|----------|
| 銘柄一覧 | [JPX公式](https://www.jpx.co.jp/markets/statistics-equities/misc/01.html) | 月次 |
| 株価・出来高 | Yahoo Finance (yfinance) | リアルタイム |
| 銘柄名 | JPX公式データ（正） | - |

### 処理フロー

```
JPX Excel → フィルタ（ETF等除外）→ yfinance株価取得 → TinyDB保存
```

## 主要ファイル

```
app/
├── main.py                 # チャットUI + DB統合
├── database/
│   ├── stock_db.py         # TinyDBラッパー
│   ├── vector_db.py        # ChromaDB + BGE-M3
│   ├── jpx_loader.py       # JPX公式データ → DB（全銘柄ロード）
│   └── data_loader.py      # 個別銘柄ロード
├── modules/
│   ├── stock_data.py       # 株価データ取得
│   ├── technical.py        # テクニカル分析
│   ├── fundamental.py      # ファンダメンタル分析
│   ├── macro.py            # マクロ経済分析
│   ├── alpha.py            # スクリーニング
│   ├── news.py             # ニュース・センチメント
│   └── ai_agent.py         # LLMエージェント
└── requirements.txt
```

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| UI | Streamlit（モバイルファーストCSS） |
| LLM | Ollama + LangChain |
| 構造化DB | TinyDB |
| ベクトルDB | ChromaDB + BGE-M3 |
| データ | yfinance, pandas |
| 検索 | DuckDuckGo Search |

## 免責事項

本ツールは情報提供目的であり、投資助言ではありません。投資判断は自己責任でお願いします。
