# -*- coding: utf-8 -*-
"""
株価データ取得モジュール
日本株の株価データをYahoo Finance経由で取得
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
import streamlit as st

import sys
sys.path.append('..')
from utils.helpers import format_ticker, parse_ticker


class StockDataFetcher:
    """日本株データ取得クラス"""

    def __init__(self):
        self.cache = {}

    @st.cache_data(ttl=300)  # 5分キャッシュ
    def get_stock_info(_self, ticker: str) -> Dict:
        """
        銘柄の基本情報を取得
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)
            info = stock.info

            return {
                "ticker": parse_ticker(ticker),
                "name": info.get("longName") or info.get("shortName", "N/A"),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap", 0),
                "currency": info.get("currency", "JPY"),
                "exchange": info.get("exchange", "JPX"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
                "previous_close": info.get("previousClose", 0),
                "open": info.get("open", 0),
                "day_high": info.get("dayHigh", 0),
                "day_low": info.get("dayLow", 0),
                "volume": info.get("volume", 0),
                "avg_volume": info.get("averageVolume", 0),
                "52_week_high": info.get("fiftyTwoWeekHigh", 0),
                "52_week_low": info.get("fiftyTwoWeekLow", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "forward_pe": info.get("forwardPE", 0),
                "pb_ratio": info.get("priceToBook", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "payout_ratio": info.get("payoutRatio", 0),
                "beta": info.get("beta", 0),
                "eps": info.get("trailingEps", 0),
                "book_value": info.get("bookValue", 0),
                "revenue": info.get("totalRevenue", 0),
                "gross_profit": info.get("grossProfits", 0),
                "operating_margin": info.get("operatingMargins", 0),
                "profit_margin": info.get("profitMargins", 0),
                "roe": info.get("returnOnEquity", 0),
                "roa": info.get("returnOnAssets", 0),
                "debt_to_equity": info.get("debtToEquity", 0),
                "current_ratio": info.get("currentRatio", 0),
                "free_cashflow": info.get("freeCashflow", 0),
                "description": info.get("longBusinessSummary", "")
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    @st.cache_data(ttl=300)
    def get_historical_data(
        _self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        過去の株価データを取得

        Args:
            ticker: 銘柄コード
            period: 期間 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 間隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)
            df = stock.history(period=period, interval=interval)

            if df.empty:
                return pd.DataFrame()

            # カラム名を正規化
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df.index.name = 'date'

            return df
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=300)
    def get_historical_data_range(
        _self,
        ticker: str,
        start_date: str,
        end_date: str = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        指定期間の株価データを取得
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)

            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")

            df = stock.history(start=start_date, end=end_date, interval=interval)

            if df.empty:
                return pd.DataFrame()

            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df.index.name = 'date'

            return df
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    def get_multiple_stocks(self, tickers: List[str], period: str = "1y") -> Dict[str, pd.DataFrame]:
        """
        複数銘柄の株価データを一括取得
        """
        result = {}
        for ticker in tickers:
            df = self.get_historical_data(ticker, period)
            if not df.empty:
                result[ticker] = df
        return result

    @st.cache_data(ttl=60)
    def get_realtime_quote(_self, ticker: str) -> Dict:
        """
        リアルタイム株価を取得（最新の取引データ）
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)

            # 最新の1日データを取得
            df = stock.history(period="1d", interval="1m")

            if df.empty:
                return {"error": "No data available"}

            latest = df.iloc[-1]
            prev_close = stock.info.get("previousClose", 0)
            current_price = latest['Close']

            change = current_price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            return {
                "ticker": parse_ticker(ticker),
                "price": current_price,
                "change": change,
                "change_pct": change_pct,
                "volume": latest['Volume'],
                "high": latest['High'],
                "low": latest['Low'],
                "timestamp": df.index[-1].strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def get_financials(self, ticker: str) -> Dict:
        """
        財務諸表データを取得
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)

            return {
                "income_statement": stock.financials.to_dict() if not stock.financials.empty else {},
                "balance_sheet": stock.balance_sheet.to_dict() if not stock.balance_sheet.empty else {},
                "cashflow": stock.cashflow.to_dict() if not stock.cashflow.empty else {},
                "quarterly_income": stock.quarterly_financials.to_dict() if not stock.quarterly_financials.empty else {},
                "quarterly_balance": stock.quarterly_balance_sheet.to_dict() if not stock.quarterly_balance_sheet.empty else {},
                "quarterly_cashflow": stock.quarterly_cashflow.to_dict() if not stock.quarterly_cashflow.empty else {}
            }
        except Exception as e:
            return {"error": str(e)}

    def get_earnings(self, ticker: str) -> Dict:
        """
        決算・EPS情報を取得
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)

            earnings = stock.earnings_history
            if earnings is not None and not earnings.empty:
                earnings_data = earnings.to_dict('records')
            else:
                earnings_data = []

            return {
                "earnings_history": earnings_data,
                "earnings_dates": stock.earnings_dates.to_dict() if hasattr(stock, 'earnings_dates') and stock.earnings_dates is not None else {}
            }
        except Exception as e:
            return {"error": str(e)}

    def get_dividends(self, ticker: str) -> pd.DataFrame:
        """
        配当履歴を取得
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)
            dividends = stock.dividends

            if dividends.empty:
                return pd.DataFrame()

            df = dividends.reset_index()
            df.columns = ['date', 'dividend']
            return df
        except Exception as e:
            print(f"Error fetching dividends: {e}")
            return pd.DataFrame()

    def get_recommendations(self, ticker: str) -> pd.DataFrame:
        """
        アナリスト推奨を取得
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)
            recs = stock.recommendations

            if recs is None or recs.empty:
                return pd.DataFrame()

            return recs
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return pd.DataFrame()

    def get_holders(self, ticker: str) -> Dict:
        """
        株主情報を取得
        """
        try:
            ticker_formatted = format_ticker(ticker)
            stock = yf.Ticker(ticker_formatted)

            return {
                "major_holders": stock.major_holders.to_dict() if stock.major_holders is not None else {},
                "institutional_holders": stock.institutional_holders.to_dict('records') if stock.institutional_holders is not None else [],
                "mutualfund_holders": stock.mutualfund_holders.to_dict('records') if stock.mutualfund_holders is not None else []
            }
        except Exception as e:
            return {"error": str(e)}

    @st.cache_data(ttl=300)
    def get_index_data(_self, index_symbol: str, period: str = "1y") -> pd.DataFrame:
        """
        株価指数データを取得
        """
        try:
            index = yf.Ticker(index_symbol)
            df = index.history(period=period)

            if df.empty:
                return pd.DataFrame()

            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df.index.name = 'date'

            return df
        except Exception as e:
            print(f"Error fetching index data: {e}")
            return pd.DataFrame()

    def compare_stocks(self, tickers: List[str], period: str = "1y") -> pd.DataFrame:
        """
        複数銘柄の比較（正規化リターン）
        """
        try:
            data = {}
            for ticker in tickers:
                df = self.get_historical_data(ticker, period)
                if not df.empty:
                    # 開始日を100として正規化
                    normalized = (df['close'] / df['close'].iloc[0]) * 100
                    data[parse_ticker(ticker)] = normalized

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error comparing stocks: {e}")
            return pd.DataFrame()
