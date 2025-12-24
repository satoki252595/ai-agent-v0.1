# -*- coding: utf-8 -*-
"""
アルファ発見・スクリーニングモジュール
市場のアルファ（超過収益）を発見するための分析
"""
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import streamlit as st

from utils.helpers import format_ticker, parse_ticker


@dataclass
class AlphaSignal:
    """アルファシグナル"""
    ticker: str
    signal_type: str
    strength: float  # 0-100
    description: str
    factors: Dict


class AlphaFinder:
    """アルファ発見クラス"""

    # 東証プライム市場の主要銘柄（スクリーニング対象）
    UNIVERSE = [
        "7203", "9984", "6758", "9432", "8306", "6861", "6501", "7974", "4063", "6098",
        "6902", "8035", "6367", "4502", "6954", "7267", "8058", "9433", "4503", "6273",
        "8766", "9022", "7751", "6981", "8001", "4568", "6702", "7201", "8411", "3382",
        "6301", "4661", "8031", "2914", "9020", "8802", "6752", "4519", "8316", "6594",
        "5401", "6857", "7269", "8801", "4901", "6326", "7011", "8053", "3407", "4452",
        "6503", "7733", "9021", "2801", "4689", "6479", "9101", "7731", "6762", "8309",
        "7270", "5713", "4543", "6305", "8725", "3099", "6971", "8750", "2502", "4911",
        "7832", "6841", "8267", "8604", "6988", "9602", "4523", "9531", "6473", "2413",
        "3659", "4507", "6146", "9104", "6724", "8591", "9503", "4704", "6753", "7272",
        "7186", "3086", "7912", "1925", "5802", "8354", "6361", "9735", "2768", "8830"
    ]

    def __init__(self):
        self._cache = {}

    @st.cache_data(ttl=3600)
    def get_universe_data(_self, tickers: List[str] = None) -> pd.DataFrame:
        """
        スクリーニング対象銘柄のデータを一括取得
        """
        if tickers is None:
            tickers = _self.UNIVERSE[:50]  # 処理時間短縮のため50銘柄

        data = []
        for ticker in tickers:
            try:
                stock = yf.Ticker(format_ticker(ticker))
                info = stock.info

                if not info.get("regularMarketPrice"):
                    continue

                data.append({
                    "ticker": ticker,
                    "name": info.get("shortName", ""),
                    "sector": info.get("sector", ""),
                    "market_cap": info.get("marketCap", 0),
                    "price": info.get("regularMarketPrice", 0),
                    "per": info.get("trailingPE"),
                    "pbr": info.get("priceToBook"),
                    "roe": info.get("returnOnEquity"),
                    "dividend_yield": info.get("dividendYield"),
                    "revenue_growth": info.get("revenueGrowth"),
                    "earnings_growth": info.get("earningsGrowth"),
                    "operating_margin": info.get("operatingMargins"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "current_ratio": info.get("currentRatio"),
                    "free_cashflow": info.get("freeCashflow"),
                    "beta": info.get("beta"),
                    "52_week_change": info.get("52WeekChange")
                })
            except Exception as e:
                continue

        return pd.DataFrame(data)

    def screen_value_stocks(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        バリュー株スクリーニング
        低PER、低PBR、高配当の割安株を発見
        """
        if df is None:
            df = self.get_universe_data()

        if df.empty:
            return pd.DataFrame()

        # フィルター条件
        conditions = (
            (df["per"].notna()) &
            (df["per"] > 0) &
            (df["per"] < 15) &
            (df["pbr"].notna()) &
            (df["pbr"] < 1.5) &
            (df["dividend_yield"].notna()) &
            (df["dividend_yield"] > 0.02)
        )

        result = df[conditions].copy()

        # バリュースコア計算
        if not result.empty:
            result["value_score"] = (
                (15 - result["per"].clip(upper=15)) / 15 * 40 +
                (1.5 - result["pbr"].clip(upper=1.5)) / 1.5 * 30 +
                result["dividend_yield"].clip(upper=0.05) / 0.05 * 30
            )
            result = result.sort_values("value_score", ascending=False)

        return result

    def screen_growth_stocks(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        グロース株スクリーニング
        高成長率、高ROEの成長株を発見
        """
        if df is None:
            df = self.get_universe_data()

        if df.empty:
            return pd.DataFrame()

        # フィルター条件
        conditions = (
            (df["revenue_growth"].notna()) &
            (df["revenue_growth"] > 0.1) &
            (df["roe"].notna()) &
            (df["roe"] > 0.1) &
            (df["earnings_growth"].notna()) &
            (df["earnings_growth"] > 0)
        )

        result = df[conditions].copy()

        # グロウススコア計算
        if not result.empty:
            result["growth_score"] = (
                result["revenue_growth"].clip(upper=0.5) / 0.5 * 35 +
                result["earnings_growth"].clip(upper=0.5) / 0.5 * 35 +
                result["roe"].clip(upper=0.3) / 0.3 * 30
            )
            result = result.sort_values("growth_score", ascending=False)

        return result

    def screen_quality_stocks(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        クオリティ株スクリーニング
        高収益性、健全な財務の優良株を発見
        """
        if df is None:
            df = self.get_universe_data()

        if df.empty:
            return pd.DataFrame()

        # フィルター条件
        conditions = (
            (df["roe"].notna()) &
            (df["roe"] > 0.1) &
            (df["operating_margin"].notna()) &
            (df["operating_margin"] > 0.1) &
            (df["debt_to_equity"].notna()) &
            (df["debt_to_equity"] < 100) &
            (df["current_ratio"].notna()) &
            (df["current_ratio"] > 1.2)
        )

        result = df[conditions].copy()

        # クオリティスコア計算
        if not result.empty:
            result["quality_score"] = (
                result["roe"].clip(upper=0.3) / 0.3 * 30 +
                result["operating_margin"].clip(upper=0.2) / 0.2 * 30 +
                (150 - result["debt_to_equity"].clip(upper=150)) / 150 * 20 +
                (result["current_ratio"].clip(upper=3) - 1) / 2 * 20
            )
            result = result.sort_values("quality_score", ascending=False)

        return result

    def screen_momentum_stocks(self, tickers: List[str] = None) -> pd.DataFrame:
        """
        モメンタム株スクリーニング
        強いトレンドの銘柄を発見
        """
        if tickers is None:
            tickers = self.UNIVERSE[:30]

        momentum_data = []

        for ticker in tickers:
            try:
                stock = yf.Ticker(format_ticker(ticker))
                hist = stock.history(period="6mo")

                if hist.empty or len(hist) < 20:
                    continue

                close = hist["Close"]

                # モメンタム指標
                return_1m = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) > 21 else 0
                return_3m = (close.iloc[-1] / close.iloc[-63] - 1) * 100 if len(close) > 63 else 0
                return_6m = (close.iloc[-1] / close.iloc[0] - 1) * 100

                # RSI計算
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1]))

                # 移動平均との乖離
                sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else close.mean()
                price_vs_sma = (close.iloc[-1] / sma_50 - 1) * 100

                momentum_data.append({
                    "ticker": ticker,
                    "price": close.iloc[-1],
                    "return_1m": return_1m,
                    "return_3m": return_3m,
                    "return_6m": return_6m,
                    "rsi": rsi,
                    "price_vs_sma50": price_vs_sma
                })

            except Exception:
                continue

        df = pd.DataFrame(momentum_data)

        if df.empty:
            return df

        # モメンタムスコア計算
        df["momentum_score"] = (
            df["return_1m"].clip(-20, 20) / 20 * 30 +
            df["return_3m"].clip(-30, 30) / 30 * 30 +
            (df["rsi"] - 50).clip(-30, 30) / 30 * 20 +
            df["price_vs_sma50"].clip(-20, 20) / 20 * 20
        )

        return df.sort_values("momentum_score", ascending=False)

    def find_oversold_stocks(self, tickers: List[str] = None) -> pd.DataFrame:
        """
        売られすぎ銘柄を発見（逆張り戦略）
        """
        if tickers is None:
            tickers = self.UNIVERSE[:30]

        oversold_data = []

        for ticker in tickers:
            try:
                stock = yf.Ticker(format_ticker(ticker))
                hist = stock.history(period="3mo")
                info = stock.info

                if hist.empty or len(hist) < 20:
                    continue

                close = hist["Close"]

                # RSI
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1]))

                # 52週高値からの下落率
                high_52w = info.get("fiftyTwoWeekHigh", close.max())
                drawdown = (close.iloc[-1] / high_52w - 1) * 100

                # ボリンジャーバンド
                sma_20 = close.rolling(20).mean().iloc[-1]
                std_20 = close.rolling(20).std().iloc[-1]
                bb_lower = sma_20 - 2 * std_20
                bb_position = (close.iloc[-1] - bb_lower) / (4 * std_20) if std_20 > 0 else 0.5

                # 売られすぎ条件チェック
                if rsi < 35 or drawdown < -20 or bb_position < 0.1:
                    oversold_data.append({
                        "ticker": ticker,
                        "name": info.get("shortName", ""),
                        "price": close.iloc[-1],
                        "rsi": rsi,
                        "drawdown_from_52w_high": drawdown,
                        "bb_position": bb_position,
                        "per": info.get("trailingPE"),
                        "pbr": info.get("priceToBook")
                    })

            except Exception:
                continue

        df = pd.DataFrame(oversold_data)

        if not df.empty:
            # 売られすぎスコア（低いほど売られすぎ）
            df["oversold_score"] = (
                (30 - df["rsi"].clip(0, 30)) / 30 * 40 +
                abs(df["drawdown_from_52w_high"].clip(-50, 0)) / 50 * 40 +
                (0.2 - df["bb_position"].clip(0, 0.2)) / 0.2 * 20
            )
            df = df.sort_values("oversold_score", ascending=False)

        return df

    def find_breakout_candidates(self, tickers: List[str] = None) -> pd.DataFrame:
        """
        ブレイクアウト候補銘柄を発見
        """
        if tickers is None:
            tickers = self.UNIVERSE[:30]

        breakout_data = []

        for ticker in tickers:
            try:
                stock = yf.Ticker(format_ticker(ticker))
                hist = stock.history(period="3mo")

                if hist.empty or len(hist) < 20:
                    continue

                close = hist["Close"]
                volume = hist["Volume"]

                # レジスタンスライン（過去の高値）
                resistance = close.iloc[-20:-1].max()
                current_price = close.iloc[-1]

                # 突破判定
                breakout_pct = (current_price / resistance - 1) * 100

                # 出来高増加
                avg_volume = volume.iloc[-20:-1].mean()
                current_volume = volume.iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

                # ブレイクアウト条件：レジスタンス付近で出来高増加
                if -2 < breakout_pct < 5 and volume_ratio > 1.3:
                    breakout_data.append({
                        "ticker": ticker,
                        "price": current_price,
                        "resistance": resistance,
                        "breakout_pct": breakout_pct,
                        "volume_ratio": volume_ratio,
                        "signal": "ブレイクアウト" if breakout_pct > 0 else "ブレイクアウト間近"
                    })

            except Exception:
                continue

        df = pd.DataFrame(breakout_data)

        if not df.empty:
            df["breakout_score"] = (
                df["breakout_pct"].clip(-2, 5) / 5 * 50 +
                (df["volume_ratio"].clip(1, 3) - 1) / 2 * 50
            )
            df = df.sort_values("breakout_score", ascending=False)

        return df

    def calculate_alpha_score(self, ticker: str) -> AlphaSignal:
        """
        銘柄のアルファスコアを総合計算
        """
        try:
            stock = yf.Ticker(format_ticker(ticker))
            info = stock.info
            hist = stock.history(period="1y")

            if hist.empty:
                return AlphaSignal(
                    ticker=ticker,
                    signal_type="データ不足",
                    strength=0,
                    description="株価データが取得できません",
                    factors={}
                )

            factors = {}

            # バリュー要素
            per = info.get("trailingPE")
            pbr = info.get("priceToBook")
            if per and 0 < per < 15:
                factors["value_per"] = 20
            if pbr and 0 < pbr < 1.5:
                factors["value_pbr"] = 15

            # グロース要素
            revenue_growth = info.get("revenueGrowth")
            earnings_growth = info.get("earningsGrowth")
            if revenue_growth and revenue_growth > 0.1:
                factors["growth_revenue"] = 15
            if earnings_growth and earnings_growth > 0.1:
                factors["growth_earnings"] = 15

            # クオリティ要素
            roe = info.get("returnOnEquity")
            operating_margin = info.get("operatingMargins")
            if roe and roe > 0.1:
                factors["quality_roe"] = 15
            if operating_margin and operating_margin > 0.1:
                factors["quality_margin"] = 10

            # モメンタム要素
            close = hist["Close"]
            if len(close) > 63:
                return_3m = (close.iloc[-1] / close.iloc[-63] - 1)
                if return_3m > 0.1:
                    factors["momentum"] = 10

            # 総合スコア
            total_score = sum(factors.values())

            # シグナル判定
            if total_score >= 60:
                signal_type = "強い買い"
            elif total_score >= 40:
                signal_type = "買い"
            elif total_score >= 20:
                signal_type = "中立"
            else:
                signal_type = "様子見"

            description = self._generate_alpha_description(factors, info)

            return AlphaSignal(
                ticker=ticker,
                signal_type=signal_type,
                strength=min(100, total_score),
                description=description,
                factors=factors
            )

        except Exception as e:
            return AlphaSignal(
                ticker=ticker,
                signal_type="エラー",
                strength=0,
                description=str(e),
                factors={}
            )

    def _generate_alpha_description(self, factors: Dict, info: Dict) -> str:
        """
        アルファシグナルの説明を生成
        """
        descriptions = []

        if "value_per" in factors or "value_pbr" in factors:
            per = info.get("trailingPE", "N/A")
            pbr = info.get("priceToBook", "N/A")
            descriptions.append(f"割安感あり（PER: {per:.1f}, PBR: {pbr:.2f}）" if isinstance(per, float) and isinstance(pbr, float) else "割安感あり")

        if "growth_revenue" in factors or "growth_earnings" in factors:
            descriptions.append("高成長を維持")

        if "quality_roe" in factors or "quality_margin" in factors:
            descriptions.append("収益性が高い")

        if "momentum" in factors:
            descriptions.append("上昇トレンド継続中")

        return "。".join(descriptions) if descriptions else "特筆すべき要素なし"

    def get_top_alpha_stocks(self, n: int = 10) -> List[AlphaSignal]:
        """
        アルファスコア上位銘柄を取得
        """
        signals = []

        for ticker in self.UNIVERSE[:50]:
            signal = self.calculate_alpha_score(ticker)
            if signal.strength > 0:
                signals.append(signal)

        # スコア順にソート
        signals.sort(key=lambda x: x.strength, reverse=True)

        return signals[:n]

    def run_comprehensive_screening(self) -> Dict:
        """
        包括的スクリーニングを実行
        """
        df = self.get_universe_data()

        return {
            "value_stocks": self.screen_value_stocks(df).head(10).to_dict('records'),
            "growth_stocks": self.screen_growth_stocks(df).head(10).to_dict('records'),
            "quality_stocks": self.screen_quality_stocks(df).head(10).to_dict('records'),
            "momentum_stocks": self.screen_momentum_stocks().head(10).to_dict('records'),
            "oversold_stocks": self.find_oversold_stocks().head(10).to_dict('records'),
            "breakout_candidates": self.find_breakout_candidates().head(10).to_dict('records'),
            "top_alpha": [
                {
                    "ticker": s.ticker,
                    "signal": s.signal_type,
                    "score": s.strength,
                    "description": s.description
                }
                for s in self.get_top_alpha_stocks(10)
            ]
        }
