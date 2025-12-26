# -*- coding: utf-8 -*-
"""
ファンダメンタルズ分析モジュール
財務諸表分析、バリュエーション、成長性分析
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yfinance as yf


def format_ticker(code: str) -> str:
    """銘柄コードを正規化"""
    code = str(code).strip().upper()
    if code.endswith('.T') or code.endswith('.JP'):
        return code
    if code.isdigit():
        return f"{code}.T"
    return code


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """安全な除算"""
    if denominator is None or denominator == 0:
        return default
    try:
        return numerator / denominator
    except (ValueError, TypeError):
        return default


def format_number(value: float, decimals: int = 2) -> str:
    """数値をフォーマット"""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """パーセンテージ表示"""
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


@dataclass
class FundamentalScore:
    """ファンダメンタルスコア"""
    category: str
    score: float  # 0-100
    grade: str  # A, B, C, D, F
    details: Dict


class FundamentalAnalyzer:
    """ファンダメンタルズ分析クラス"""

    def __init__(self, ticker: str):
        self.ticker = format_ticker(ticker)
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
        self._cache = {}

    def get_valuation_metrics(self) -> Dict:
        """
        バリュエーション指標を取得
        """
        return {
            "per": self.info.get("trailingPE", None),
            "forward_per": self.info.get("forwardPE", None),
            "pbr": self.info.get("priceToBook", None),
            "psr": self.info.get("priceToSalesTrailing12Months", None),
            "ev_ebitda": self.info.get("enterpriseToEbitda", None),
            "ev_revenue": self.info.get("enterpriseToRevenue", None),
            "peg_ratio": self.info.get("pegRatio", None),
            "market_cap": self.info.get("marketCap", None),
            "enterprise_value": self.info.get("enterpriseValue", None)
        }

    def get_profitability_metrics(self) -> Dict:
        """
        収益性指標を取得
        """
        return {
            "gross_margin": self.info.get("grossMargins", None),
            "operating_margin": self.info.get("operatingMargins", None),
            "profit_margin": self.info.get("profitMargins", None),
            "roe": self.info.get("returnOnEquity", None),
            "roa": self.info.get("returnOnAssets", None),
            "roic": self._calculate_roic(),
            "eps": self.info.get("trailingEps", None),
            "forward_eps": self.info.get("forwardEps", None)
        }

    def get_financial_health_metrics(self) -> Dict:
        """
        財務健全性指標を取得
        """
        return {
            "current_ratio": self.info.get("currentRatio", None),
            "quick_ratio": self.info.get("quickRatio", None),
            "debt_to_equity": self.info.get("debtToEquity", None),
            "total_debt": self.info.get("totalDebt", None),
            "total_cash": self.info.get("totalCash", None),
            "free_cashflow": self.info.get("freeCashflow", None),
            "operating_cashflow": self.info.get("operatingCashflow", None),
            "interest_coverage": self._calculate_interest_coverage()
        }

    def get_growth_metrics(self) -> Dict:
        """
        成長性指標を取得
        """
        return {
            "revenue_growth": self.info.get("revenueGrowth", None),
            "earnings_growth": self.info.get("earningsGrowth", None),
            "earnings_quarterly_growth": self.info.get("earningsQuarterlyGrowth", None),
            "revenue_per_share": self.info.get("revenuePerShare", None),
            "five_year_avg_dividend_yield": self.info.get("fiveYearAvgDividendYield", None)
        }

    def get_dividend_metrics(self) -> Dict:
        """
        配当関連指標を取得
        """
        return {
            "dividend_rate": self.info.get("dividendRate", None),
            "dividend_yield": self.info.get("dividendYield", None),
            "payout_ratio": self.info.get("payoutRatio", None),
            "ex_dividend_date": self.info.get("exDividendDate", None),
            "trailing_annual_dividend_rate": self.info.get("trailingAnnualDividendRate", None),
            "trailing_annual_dividend_yield": self.info.get("trailingAnnualDividendYield", None)
        }

    def _calculate_roic(self) -> Optional[float]:
        """
        ROIC（投下資本利益率）を計算
        """
        nopat = self.info.get("operatingIncome", 0) * 0.7  # 税引後営業利益（簡易計算）
        total_debt = self.info.get("totalDebt", 0)
        total_equity = self.info.get("totalStockholderEquity", 0) or self.info.get("bookValue", 0) * self.info.get("sharesOutstanding", 1)
        invested_capital = total_debt + total_equity

        if invested_capital > 0:
            return nopat / invested_capital
        return None

    def _calculate_interest_coverage(self) -> Optional[float]:
        """
        インタレストカバレッジレシオを計算
        """
        ebit = self.info.get("ebitda", 0) - self.info.get("depreciation", 0)
        interest_expense = self.info.get("interestExpense", None)
        if interest_expense and interest_expense != 0:
            return abs(ebit / interest_expense)
        return None

    def get_financial_statements(self) -> Dict:
        """
        財務諸表を取得
        """
        return {
            "income_statement": self._format_statement(self.stock.financials),
            "balance_sheet": self._format_statement(self.stock.balance_sheet),
            "cashflow": self._format_statement(self.stock.cashflow),
            "quarterly_income": self._format_statement(self.stock.quarterly_financials),
            "quarterly_balance": self._format_statement(self.stock.quarterly_balance_sheet),
            "quarterly_cashflow": self._format_statement(self.stock.quarterly_cashflow)
        }

    def _format_statement(self, df: pd.DataFrame) -> Dict:
        """財務諸表をDict形式に変換"""
        if df is None or df.empty:
            return {}
        df_copy = df.copy()
        df_copy.columns = [str(col.date()) if hasattr(col, 'date') else str(col) for col in df_copy.columns]
        return df_copy.to_dict()

    def analyze_income_statement(self) -> Dict:
        """
        損益計算書の分析
        """
        try:
            income = self.stock.financials
            if income.empty:
                return {"error": "No income statement data available"}

            # 最新2期間のデータを取得
            latest = income.iloc[:, 0]
            previous = income.iloc[:, 1] if income.shape[1] > 1 else None

            result = {
                "total_revenue": latest.get("Total Revenue", None),
                "gross_profit": latest.get("Gross Profit", None),
                "operating_income": latest.get("Operating Income", None),
                "net_income": latest.get("Net Income", None),
                "ebitda": latest.get("EBITDA", None)
            }

            # 前年比成長率を計算
            if previous is not None:
                result["revenue_growth_yoy"] = safe_divide(
                    latest.get("Total Revenue", 0) - previous.get("Total Revenue", 0),
                    previous.get("Total Revenue", 1)
                )
                result["net_income_growth_yoy"] = safe_divide(
                    latest.get("Net Income", 0) - previous.get("Net Income", 0),
                    abs(previous.get("Net Income", 1))
                )

            return result
        except Exception as e:
            return {"error": str(e)}

    def analyze_balance_sheet(self) -> Dict:
        """
        貸借対照表の分析
        """
        try:
            balance = self.stock.balance_sheet
            if balance.empty:
                return {"error": "No balance sheet data available"}

            latest = balance.iloc[:, 0]

            total_assets = latest.get("Total Assets", 0)
            total_liabilities = latest.get("Total Liabilities Net Minority Interest", 0) or latest.get("Total Liab", 0)
            total_equity = latest.get("Total Stockholder Equity", 0) or latest.get("Stockholders Equity", 0)

            return {
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "current_assets": latest.get("Total Current Assets", None),
                "current_liabilities": latest.get("Total Current Liabilities", None),
                "cash_and_equivalents": latest.get("Cash And Cash Equivalents", None),
                "total_debt": latest.get("Total Debt", None),
                "net_debt": latest.get("Net Debt", None),
                "inventory": latest.get("Inventory", None),
                "accounts_receivable": latest.get("Net Receivables", None),
                "accounts_payable": latest.get("Accounts Payable", None),
                "retained_earnings": latest.get("Retained Earnings", None),
                "equity_ratio": safe_divide(total_equity, total_assets) if total_assets else None,
                "debt_ratio": safe_divide(total_liabilities, total_assets) if total_assets else None
            }
        except Exception as e:
            return {"error": str(e)}

    def analyze_cashflow(self) -> Dict:
        """
        キャッシュフロー計算書の分析
        """
        try:
            cashflow = self.stock.cashflow
            if cashflow.empty:
                return {"error": "No cashflow data available"}

            latest = cashflow.iloc[:, 0]

            operating_cf = latest.get("Total Cash From Operating Activities", 0) or latest.get("Operating Cash Flow", 0)
            investing_cf = latest.get("Total Cashflows From Investing Activities", 0) or latest.get("Investing Cash Flow", 0)
            financing_cf = latest.get("Total Cash From Financing Activities", 0) or latest.get("Financing Cash Flow", 0)
            capex = latest.get("Capital Expenditures", 0) or latest.get("Capital Expenditure", 0)

            free_cashflow = operating_cf + capex if capex < 0 else operating_cf - abs(capex)

            return {
                "operating_cashflow": operating_cf,
                "investing_cashflow": investing_cf,
                "financing_cashflow": financing_cf,
                "free_cashflow": free_cashflow,
                "capex": capex,
                "dividends_paid": latest.get("Dividends Paid", None),
                "stock_repurchase": latest.get("Repurchase Of Stock", None),
                "net_change_in_cash": latest.get("Change In Cash", None),
                "fcf_margin": safe_divide(free_cashflow, self.info.get("totalRevenue", 1))
            }
        except Exception as e:
            return {"error": str(e)}

    def calculate_intrinsic_value_dcf(
        self,
        growth_rate: float = 0.05,
        discount_rate: float = 0.10,
        terminal_growth: float = 0.02,
        projection_years: int = 5
    ) -> Dict:
        """
        DCF法による理論株価算出
        """
        try:
            fcf = self.info.get("freeCashflow", 0)
            shares_outstanding = self.info.get("sharesOutstanding", 1)

            if fcf <= 0:
                return {"error": "Negative or zero free cash flow", "intrinsic_value": None}

            # 将来FCFを予測
            projected_fcf = []
            current_fcf = fcf

            for year in range(1, projection_years + 1):
                current_fcf *= (1 + growth_rate)
                discounted_fcf = current_fcf / ((1 + discount_rate) ** year)
                projected_fcf.append({
                    "year": year,
                    "fcf": current_fcf,
                    "discounted_fcf": discounted_fcf
                })

            # ターミナルバリュー
            terminal_value = (current_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
            discounted_terminal = terminal_value / ((1 + discount_rate) ** projection_years)

            # 企業価値
            total_pv_fcf = sum(p["discounted_fcf"] for p in projected_fcf)
            enterprise_value = total_pv_fcf + discounted_terminal

            # 株式価値
            net_debt = self.info.get("totalDebt", 0) - self.info.get("totalCash", 0)
            equity_value = enterprise_value - net_debt

            intrinsic_value_per_share = equity_value / shares_outstanding
            current_price = self.info.get("currentPrice", 0) or self.info.get("regularMarketPrice", 0)

            upside = ((intrinsic_value_per_share - current_price) / current_price * 100) if current_price else 0

            return {
                "intrinsic_value": intrinsic_value_per_share,
                "current_price": current_price,
                "upside_potential": upside,
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
                "terminal_value": terminal_value,
                "projected_fcf": projected_fcf,
                "assumptions": {
                    "growth_rate": growth_rate,
                    "discount_rate": discount_rate,
                    "terminal_growth": terminal_growth,
                    "projection_years": projection_years
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def calculate_fundamental_score(self) -> FundamentalScore:
        """
        ファンダメンタルスコアを計算（100点満点）
        """
        scores = []
        details = {}

        # バリュエーションスコア（25点）
        valuation = self.get_valuation_metrics()
        val_score = 0
        if valuation.get("per"):
            if 5 <= valuation["per"] <= 15:
                val_score += 10
            elif 15 < valuation["per"] <= 25:
                val_score += 5
        if valuation.get("pbr"):
            if 0.5 <= valuation["pbr"] <= 1.5:
                val_score += 10
            elif 1.5 < valuation["pbr"] <= 3:
                val_score += 5
        if valuation.get("peg_ratio") and valuation["peg_ratio"] < 1:
            val_score += 5
        scores.append(min(val_score, 25))
        details["valuation_score"] = min(val_score, 25)

        # 収益性スコア（25点）
        profitability = self.get_profitability_metrics()
        prof_score = 0
        if profitability.get("roe") and profitability["roe"] > 0.1:
            prof_score += 8
        elif profitability.get("roe") and profitability["roe"] > 0.05:
            prof_score += 4
        if profitability.get("operating_margin") and profitability["operating_margin"] > 0.1:
            prof_score += 8
        elif profitability.get("operating_margin") and profitability["operating_margin"] > 0.05:
            prof_score += 4
        if profitability.get("profit_margin") and profitability["profit_margin"] > 0.05:
            prof_score += 9
        elif profitability.get("profit_margin") and profitability["profit_margin"] > 0:
            prof_score += 4
        scores.append(min(prof_score, 25))
        details["profitability_score"] = min(prof_score, 25)

        # 財務健全性スコア（25点）
        health = self.get_financial_health_metrics()
        health_score = 0
        if health.get("current_ratio") and health["current_ratio"] > 1.5:
            health_score += 8
        elif health.get("current_ratio") and health["current_ratio"] > 1:
            health_score += 4
        if health.get("debt_to_equity") and health["debt_to_equity"] < 100:
            health_score += 8
        elif health.get("debt_to_equity") and health["debt_to_equity"] < 150:
            health_score += 4
        if health.get("free_cashflow") and health["free_cashflow"] > 0:
            health_score += 9
        scores.append(min(health_score, 25))
        details["financial_health_score"] = min(health_score, 25)

        # 成長性スコア（25点）
        growth = self.get_growth_metrics()
        growth_score = 0
        if growth.get("revenue_growth") and growth["revenue_growth"] > 0.1:
            growth_score += 10
        elif growth.get("revenue_growth") and growth["revenue_growth"] > 0:
            growth_score += 5
        if growth.get("earnings_growth") and growth["earnings_growth"] > 0.1:
            growth_score += 10
        elif growth.get("earnings_growth") and growth["earnings_growth"] > 0:
            growth_score += 5
        if growth.get("earnings_quarterly_growth") and growth["earnings_quarterly_growth"] > 0:
            growth_score += 5
        scores.append(min(growth_score, 25))
        details["growth_score"] = min(growth_score, 25)

        total_score = sum(scores)

        # グレード判定
        if total_score >= 80:
            grade = "A"
        elif total_score >= 60:
            grade = "B"
        elif total_score >= 40:
            grade = "C"
        elif total_score >= 20:
            grade = "D"
        else:
            grade = "F"

        return FundamentalScore(
            category="総合",
            score=total_score,
            grade=grade,
            details=details
        )

    def get_peer_comparison(self, peer_tickers: List[str]) -> pd.DataFrame:
        """
        同業他社との比較
        """
        data = []

        # 自社のデータ
        self_data = {
            "ticker": self.ticker.replace(".T", ""),
            "name": self.info.get("shortName", ""),
            "market_cap": self.info.get("marketCap", 0),
            "per": self.info.get("trailingPE", None),
            "pbr": self.info.get("priceToBook", None),
            "roe": self.info.get("returnOnEquity", None),
            "dividend_yield": self.info.get("dividendYield", None),
            "operating_margin": self.info.get("operatingMargins", None)
        }
        data.append(self_data)

        # 同業他社のデータ
        for ticker in peer_tickers:
            peer = yf.Ticker(format_ticker(ticker))
            peer_info = peer.info
            data.append({
                "ticker": ticker,
                "name": peer_info.get("shortName", ""),
                "market_cap": peer_info.get("marketCap", 0),
                "per": peer_info.get("trailingPE", None),
                "pbr": peer_info.get("priceToBook", None),
                "roe": peer_info.get("returnOnEquity", None),
                "dividend_yield": peer_info.get("dividendYield", None),
                "operating_margin": peer_info.get("operatingMargins", None)
            })

        return pd.DataFrame(data)

    def get_analysis_summary(self) -> Dict:
        """
        分析サマリーを取得
        """
        valuation = self.get_valuation_metrics()
        profitability = self.get_profitability_metrics()
        health = self.get_financial_health_metrics()
        growth = self.get_growth_metrics()
        dividend = self.get_dividend_metrics()
        score = self.calculate_fundamental_score()

        return {
            "ticker": self.ticker,
            "name": self.info.get("longName") or self.info.get("shortName", ""),
            "sector": self.info.get("sector", ""),
            "industry": self.info.get("industry", ""),
            "current_price": self.info.get("currentPrice") or self.info.get("regularMarketPrice"),
            "fundamental_score": score.score,
            "fundamental_grade": score.grade,
            "valuation": valuation,
            "profitability": profitability,
            "financial_health": health,
            "growth": growth,
            "dividend": dividend,
            "score_details": score.details
        }
