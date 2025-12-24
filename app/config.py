# -*- coding: utf-8 -*-
"""
日本株リサーチAIエージェント - 設定ファイル
Japan Stock Research AI Agent - Configuration
"""
import streamlit as st

# --- LLM設定 ---
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")
LLM_TEMPERATURE = 0.3

# --- 日本株設定 ---
# 東証プライム市場の主要銘柄サフィックス
JP_STOCK_SUFFIX = ".T"  # 東証
JP_STOCK_SUFFIX_ALT = ".JP"  # 代替

# 主要指数
INDICES = {
    "nikkei225": "^N225",
    "topix": "^TPX",
    "mothers": "^JPN-M",
    "jasdaq": "^JSD"
}

# セクター分類（東証33業種）
SECTORS = {
    "水産・農林業": 1,
    "鉱業": 2,
    "建設業": 3,
    "食料品": 4,
    "繊維製品": 5,
    "パルプ・紙": 6,
    "化学": 7,
    "医薬品": 8,
    "石油・石炭製品": 9,
    "ゴム製品": 10,
    "ガラス・土石製品": 11,
    "鉄鋼": 12,
    "非鉄金属": 13,
    "金属製品": 14,
    "機械": 15,
    "電気機器": 16,
    "輸送用機器": 17,
    "精密機器": 18,
    "その他製品": 19,
    "電気・ガス業": 20,
    "陸運業": 21,
    "海運業": 22,
    "空運業": 23,
    "倉庫・運輸関連業": 24,
    "情報・通信業": 25,
    "卸売業": 26,
    "小売業": 27,
    "銀行業": 28,
    "証券、商品先物取引業": 29,
    "保険業": 30,
    "その他金融業": 31,
    "不動産業": 32,
    "サービス業": 33
}

# テクニカル指標デフォルト設定
TECHNICAL_CONFIG = {
    "sma_periods": [5, 25, 75, 200],  # 移動平均線期間
    "ema_periods": [12, 26],  # 指数移動平均
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2,
    "atr_period": 14,
    "stoch_k": 14,
    "stoch_d": 3,
    "adx_period": 14
}

# ファンダメンタル指標の基準値（スクリーニング用）
FUNDAMENTAL_THRESHOLDS = {
    "per_low": 0,
    "per_high": 30,
    "pbr_low": 0,
    "pbr_high": 3,
    "roe_min": 8,  # %
    "dividend_yield_min": 2,  # %
    "debt_equity_max": 150,  # %
    "current_ratio_min": 100,  # %
    "operating_margin_min": 5  # %
}

# 監視対象の主要銘柄（例）
WATCHLIST_DEFAULT = [
    "7203",  # トヨタ
    "9984",  # ソフトバンクG
    "6758",  # ソニー
    "9432",  # NTT
    "8306",  # 三菱UFJ
    "6861",  # キーエンス
    "6501",  # 日立
    "7974",  # 任天堂
    "4063",  # 信越化学
    "6098",  # リクルート
]

# ニュースソース
NEWS_SOURCES = [
    "reuters.com",
    "nikkei.com",
    "bloomberg.co.jp",
    "kabutan.jp",
    "minkabu.jp",
    "toyokeizai.net",
    "diamond.jp"
]

# マクロ経済指標
MACRO_INDICATORS = {
    "japan_10y_yield": "^TNX",  # 日本10年国債利回り（代替）
    "usdjpy": "USDJPY=X",
    "eurjpy": "EURJPY=X",
    "crude_oil": "CL=F",
    "gold": "GC=F",
    "vix": "^VIX"
}

# API設定
API_RETRY_COUNT = 3
API_RETRY_DELAY = 2  # 秒
REQUEST_TIMEOUT = 30  # 秒

# キャッシュ設定
CACHE_TTL_PRICE = 300  # 株価キャッシュ: 5分
CACHE_TTL_FUNDAMENTAL = 86400  # ファンダメンタル: 1日
CACHE_TTL_NEWS = 1800  # ニュース: 30分
