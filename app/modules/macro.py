# -*- coding: utf-8 -*-
"""
マクロ経済分析モジュール
日銀政策、為替、金利、グローバル経済指標の分析
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import streamlit as st
from duckduckgo_search import DDGS
import trafilatura


class MacroAnalyzer:
    """マクロ経済分析クラス"""

    # 主要な経済指標シンボル
    INDICATORS = {
        # 為替
        "usdjpy": "USDJPY=X",
        "eurjpy": "EURJPY=X",
        "gbpjpy": "GBPJPY=X",
        "audjpy": "AUDJPY=X",
        "cnypy": "CNYJPY=X",

        # 株価指数
        "nikkei225": "^N225",
        "topix": "^TPX",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dow": "^DJI",
        "dax": "^GDAXI",
        "shanghai": "000001.SS",
        "hang_seng": "^HSI",

        # 金利・債券
        "us_10y": "^TNX",
        "us_2y": "^IRX",

        # コモディティ
        "crude_oil": "CL=F",
        "brent_oil": "BZ=F",
        "gold": "GC=F",
        "silver": "SI=F",
        "copper": "HG=F",
        "natural_gas": "NG=F",

        # VIX
        "vix": "^VIX",
        "vxj": "^VXJ"  # 日経VI
    }

    def __init__(self):
        self._cache = {}

    @st.cache_data(ttl=300)
    def get_indicator_data(_self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """
        経済指標データを取得
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            if df.empty:
                return pd.DataFrame()
            df.columns = [col.lower() for col in df.columns]
            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()

    def get_forex_rates(self) -> Dict:
        """
        主要為替レートを取得
        """
        forex_pairs = ["usdjpy", "eurjpy", "gbpjpy", "audjpy"]
        rates = {}

        for pair in forex_pairs:
            symbol = self.INDICATORS.get(pair)
            if symbol:
                df = self.get_indicator_data(symbol, "5d")
                if not df.empty:
                    latest = df['close'].iloc[-1]
                    prev = df['close'].iloc[-2] if len(df) > 1 else latest
                    rates[pair] = {
                        "rate": latest,
                        "change": latest - prev,
                        "change_pct": ((latest - prev) / prev) * 100 if prev else 0
                    }

        return rates

    def get_global_indices(self) -> Dict:
        """
        グローバル株価指数を取得
        """
        indices = ["nikkei225", "topix", "sp500", "nasdaq", "dow", "shanghai", "hang_seng"]
        result = {}

        for index in indices:
            symbol = self.INDICATORS.get(index)
            if symbol:
                df = self.get_indicator_data(symbol, "5d")
                if not df.empty:
                    latest = df['close'].iloc[-1]
                    prev = df['close'].iloc[-2] if len(df) > 1 else latest
                    result[index] = {
                        "value": latest,
                        "change": latest - prev,
                        "change_pct": ((latest - prev) / prev) * 100 if prev else 0
                    }

        return result

    def get_commodity_prices(self) -> Dict:
        """
        コモディティ価格を取得
        """
        commodities = ["crude_oil", "gold", "silver", "copper", "natural_gas"]
        result = {}

        for commodity in commodities:
            symbol = self.INDICATORS.get(commodity)
            if symbol:
                df = self.get_indicator_data(symbol, "5d")
                if not df.empty:
                    latest = df['close'].iloc[-1]
                    prev = df['close'].iloc[-2] if len(df) > 1 else latest
                    result[commodity] = {
                        "price": latest,
                        "change": latest - prev,
                        "change_pct": ((latest - prev) / prev) * 100 if prev else 0
                    }

        return result

    def get_volatility_indices(self) -> Dict:
        """
        ボラティリティ指数を取得
        """
        result = {}

        for name, symbol in [("vix", "^VIX")]:
            df = self.get_indicator_data(symbol, "5d")
            if not df.empty:
                latest = df['close'].iloc[-1]
                prev = df['close'].iloc[-2] if len(df) > 1 else latest
                result[name] = {
                    "value": latest,
                    "change": latest - prev,
                    "status": "高警戒" if latest > 30 else "警戒" if latest > 20 else "安定"
                }

        return result

    def analyze_correlation(self, ticker: str, period: str = "1y") -> Dict:
        """
        銘柄とマクロ指標の相関分析
        """
        from modules.stock_data import StockDataFetcher

        fetcher = StockDataFetcher()
        stock_data = fetcher.get_historical_data(ticker, period)

        if stock_data.empty:
            return {"error": "No stock data available"}

        correlations = {}
        indicators_to_check = ["usdjpy", "nikkei225", "sp500", "crude_oil", "gold", "vix"]

        for indicator in indicators_to_check:
            symbol = self.INDICATORS.get(indicator)
            if symbol:
                indicator_data = self.get_indicator_data(symbol, period)
                if not indicator_data.empty:
                    # 日付でマージ
                    merged = pd.merge(
                        stock_data['close'].rename('stock'),
                        indicator_data['close'].rename('indicator'),
                        left_index=True,
                        right_index=True,
                        how='inner'
                    )
                    if len(merged) > 20:
                        corr = merged['stock'].corr(merged['indicator'])
                        correlations[indicator] = round(corr, 3)

        return correlations

    def get_market_regime(self) -> Dict:
        """
        市場レジーム（相場環境）を判定
        """
        # VIX取得
        vix_data = self.get_indicator_data("^VIX", "3mo")
        vix_current = vix_data['close'].iloc[-1] if not vix_data.empty else 20
        vix_avg = vix_data['close'].mean() if not vix_data.empty else 20

        # 日経平均のトレンド
        nikkei_data = self.get_indicator_data("^N225", "3mo")
        if not nikkei_data.empty:
            nikkei_return = ((nikkei_data['close'].iloc[-1] / nikkei_data['close'].iloc[0]) - 1) * 100
            nikkei_trend = "上昇" if nikkei_return > 5 else "下落" if nikkei_return < -5 else "横ばい"
        else:
            nikkei_return = 0
            nikkei_trend = "不明"

        # 為替トレンド
        usdjpy_data = self.get_indicator_data("USDJPY=X", "3mo")
        if not usdjpy_data.empty:
            usdjpy_change = ((usdjpy_data['close'].iloc[-1] / usdjpy_data['close'].iloc[0]) - 1) * 100
            yen_trend = "円安" if usdjpy_change > 3 else "円高" if usdjpy_change < -3 else "安定"
        else:
            usdjpy_change = 0
            yen_trend = "不明"

        # 市場レジーム判定
        if vix_current > 30:
            regime = "リスクオフ（高ボラティリティ）"
            risk_level = "高"
        elif vix_current > 20:
            regime = "警戒相場"
            risk_level = "中"
        elif nikkei_trend == "上昇":
            regime = "リスクオン（上昇トレンド）"
            risk_level = "低"
        else:
            regime = "通常相場"
            risk_level = "中"

        return {
            "regime": regime,
            "risk_level": risk_level,
            "vix": {
                "current": vix_current,
                "average": vix_avg,
                "status": "高警戒" if vix_current > 30 else "警戒" if vix_current > 20 else "安定"
            },
            "nikkei": {
                "trend": nikkei_trend,
                "return_3m": nikkei_return
            },
            "forex": {
                "trend": yen_trend,
                "usdjpy_change_3m": usdjpy_change
            }
        }

    def get_sector_rotation_signal(self) -> Dict:
        """
        セクターローテーション分析
        景気サイクルに基づく有望セクターを判定
        """
        regime = self.get_market_regime()

        # 景気サイクルに基づくセクター推奨
        sector_recommendations = {
            "リスクオン（上昇トレンド）": {
                "recommended": ["情報・通信", "電気機器", "精密機器", "サービス"],
                "avoid": ["電気・ガス", "食料品"],
                "reason": "景気拡大期は成長セクターが有利"
            },
            "リスクオフ（高ボラティリティ）": {
                "recommended": ["食料品", "医薬品", "電気・ガス", "陸運"],
                "avoid": ["不動産", "証券", "海運"],
                "reason": "ディフェンシブセクターへの資金シフトが予想される"
            },
            "警戒相場": {
                "recommended": ["医薬品", "食料品", "通信"],
                "avoid": ["不動産", "建設"],
                "reason": "景気敏感セクターは控えめに"
            },
            "通常相場": {
                "recommended": ["機械", "化学", "卸売"],
                "avoid": [],
                "reason": "バランスの取れたポートフォリオが有効"
            }
        }

        current_regime = regime["regime"]
        recommendation = sector_recommendations.get(current_regime, sector_recommendations["通常相場"])

        return {
            "current_regime": current_regime,
            "risk_level": regime["risk_level"],
            "recommended_sectors": recommendation["recommended"],
            "sectors_to_avoid": recommendation["avoid"],
            "reason": recommendation["reason"]
        }

    def search_boj_news(self) -> List[Dict]:
        """
        日銀関連ニュースを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    "日銀 金融政策 site:boj.or.jp OR site:nikkei.com",
                    region='jp-jp',
                    max_results=5
                ))
            return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
        except:
            return []

    def search_economic_news(self, topic: str = "日本経済") -> List[Dict]:
        """
        経済ニュースを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"{topic} 経済指標 最新",
                    region='jp-jp',
                    max_results=5
                ))
            return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
        except:
            return []

    def get_macro_summary(self) -> Dict:
        """
        マクロ経済サマリーを取得
        """
        return {
            "forex": self.get_forex_rates(),
            "indices": self.get_global_indices(),
            "commodities": self.get_commodity_prices(),
            "volatility": self.get_volatility_indices(),
            "market_regime": self.get_market_regime(),
            "sector_rotation": self.get_sector_rotation_signal()
        }

    def analyze_impact_on_stock(self, ticker: str) -> Dict:
        """
        マクロ要因が特定銘柄に与える影響を分析
        """
        from modules.stock_data import StockDataFetcher

        fetcher = StockDataFetcher()
        info = fetcher.get_stock_info(ticker)

        if "error" in info:
            return {"error": info["error"]}

        sector = info.get("sector", "")
        industry = info.get("industry", "")

        correlations = self.analyze_correlation(ticker)
        regime = self.get_market_regime()

        # セクター別の影響分析
        impact_analysis = {
            "ticker": ticker,
            "sector": sector,
            "industry": industry,
            "correlations": correlations,
            "market_regime": regime["regime"],
            "impacts": []
        }

        # 為替影響
        if correlations.get("usdjpy"):
            usdjpy_corr = correlations["usdjpy"]
            if abs(usdjpy_corr) > 0.3:
                if usdjpy_corr > 0:
                    impact_analysis["impacts"].append({
                        "factor": "為替（ドル円）",
                        "correlation": usdjpy_corr,
                        "assessment": "円安でプラス影響、円高でマイナス影響"
                    })
                else:
                    impact_analysis["impacts"].append({
                        "factor": "為替（ドル円）",
                        "correlation": usdjpy_corr,
                        "assessment": "円高でプラス影響、円安でマイナス影響"
                    })

        # 原油価格影響
        if correlations.get("crude_oil"):
            oil_corr = correlations["crude_oil"]
            if abs(oil_corr) > 0.3:
                impact_analysis["impacts"].append({
                    "factor": "原油価格",
                    "correlation": oil_corr,
                    "assessment": f"原油価格と{'正の相関':'負の相関'}（相関係数: {oil_corr}）"
                })

        # VIX影響
        if correlations.get("vix"):
            vix_corr = correlations["vix"]
            impact_analysis["impacts"].append({
                "factor": "市場リスク（VIX）",
                "correlation": vix_corr,
                "assessment": "リスクオフ時に注意が必要" if vix_corr < -0.3 else "市場変動の影響は限定的"
            })

        return impact_analysis
