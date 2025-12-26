# -*- coding: utf-8 -*-
"""
日本株リサーチAIエージェント - 設定ファイル
Japan Stock Research AI Agent - Configuration
"""
import streamlit as st
import os

# --- LLM設定 (Ollama) ---
def get_secret(key, default=""):
    """Streamlit secrets または環境変数から値を取得"""
    return st.secrets.get(key, os.environ.get(key, default))

OLLAMA_URL = get_secret("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = get_secret("MODEL_NAME", "nemotron-3-nano")
LLM_TEMPERATURE = 0.3

# --- 日本株設定 ---
JP_STOCK_SUFFIX = ".T"
JP_STOCK_SUFFIX_ALT = ".JP"

# 主要指数
INDICES = {
    "nikkei225": "^N225",
    "topix": "^TPX",
    "mothers": "^JPN-M",
    "jasdaq": "^JSD"
}

# セクター分類（東証33業種）
SECTORS = {
    "水産・農林業": 1, "鉱業": 2, "建設業": 3, "食料品": 4,
    "繊維製品": 5, "パルプ・紙": 6, "化学": 7, "医薬品": 8,
    "石油・石炭製品": 9, "ゴム製品": 10, "ガラス・土石製品": 11,
    "鉄鋼": 12, "非鉄金属": 13, "金属製品": 14, "機械": 15,
    "電気機器": 16, "輸送用機器": 17, "精密機器": 18,
    "その他製品": 19, "電気・ガス業": 20, "陸運業": 21,
    "海運業": 22, "空運業": 23, "倉庫・運輸関連業": 24,
    "情報・通信業": 25, "卸売業": 26, "小売業": 27,
    "銀行業": 28, "証券、商品先物取引業": 29, "保険業": 30,
    "その他金融業": 31, "不動産業": 32, "サービス業": 33
}

# テクニカル指標デフォルト設定
TECHNICAL_CONFIG = {
    "sma_periods": [5, 25, 75, 200],
    "ema_periods": [12, 26],
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

# ファンダメンタル指標の基準値
FUNDAMENTAL_THRESHOLDS = {
    "per_low": 0, "per_high": 30,
    "pbr_low": 0, "pbr_high": 3,
    "roe_min": 8, "dividend_yield_min": 2,
    "debt_equity_max": 150, "current_ratio_min": 100,
    "operating_margin_min": 5
}

# 監視対象の主要銘柄
WATCHLIST_DEFAULT = [
    "7203", "9984", "6758", "9432", "8306",
    "6861", "6501", "7974", "4063", "6098",
]

# ニュースソース
NEWS_SOURCES = [
    "reuters.com", "nikkei.com", "bloomberg.co.jp",
    "kabutan.jp", "minkabu.jp", "toyokeizai.net", "diamond.jp"
]

# マクロ経済指標
MACRO_INDICATORS = {
    "japan_10y_yield": "^TNX",
    "usdjpy": "USDJPY=X",
    "eurjpy": "EURJPY=X",
    "crude_oil": "CL=F",
    "gold": "GC=F",
    "vix": "^VIX"
}

# API設定
API_RETRY_COUNT = 3
API_RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# キャッシュ設定
CACHE_TTL_PRICE = 300
CACHE_TTL_FUNDAMENTAL = 86400
CACHE_TTL_NEWS = 1800
