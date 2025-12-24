# -*- coding: utf-8 -*-
"""
データローダー
Yahoo Financeから銘柄データを取得してDBに格納
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import List, Dict
import yfinance as yf

from database.stock_db import StockDatabase
from database.vector_db import VectorDatabase


# 主要日本株銘柄リスト（東証プライム）
DEFAULT_TICKERS = [
    # 自動車
    "7203",  # トヨタ自動車
    "7267",  # ホンダ
    "7201",  # 日産自動車
    "7269",  # スズキ

    # 電機・精密
    "6758",  # ソニーG
    "6861",  # キーエンス
    "6501",  # 日立製作所
    "6702",  # 富士通
    "6752",  # パナソニック
    "6954",  # ファナック

    # 通信・IT
    "9432",  # NTT
    "9433",  # KDDI
    "9984",  # ソフトバンクG
    "4689",  # ZHD

    # 金融
    "8306",  # 三菱UFJ
    "8316",  # 三井住友FG
    "8411",  # みずほFG
    "8766",  # 東京海上

    # 商社
    "8058",  # 三菱商事
    "8031",  # 三井物産
    "8001",  # 伊藤忠商事

    # 医薬品
    "4502",  # 武田薬品
    "4503",  # アステラス製薬
    "4568",  # 第一三共

    # 素材・化学
    "4063",  # 信越化学
    "4452",  # 花王

    # その他
    "6098",  # リクルートHD
    "7974",  # 任天堂
    "9020",  # JR東日本
]


def format_ticker(code: str) -> str:
    """銘柄コードを東証形式に変換"""
    code = str(code).strip()
    if not code.endswith(".T"):
        return f"{code}.T"
    return code


def load_stock_data(
    tickers: List[str] = None,
    stock_db: StockDatabase = None,
    vector_db: VectorDatabase = None,
    verbose: bool = True
) -> Dict:
    """
    銘柄データをDBにロード

    Args:
        tickers: 銘柄コードリスト（デフォルト: 主要30銘柄）
        stock_db: 構造化DB（None=新規作成）
        vector_db: ベクトルDB（None=新規作成）
        verbose: 進捗表示

    Returns:
        ロード結果
    """
    if tickers is None:
        tickers = DEFAULT_TICKERS

    if stock_db is None:
        stock_db = StockDatabase()

    if vector_db is None:
        try:
            vector_db = VectorDatabase()
        except ImportError:
            vector_db = None
            if verbose:
                print("ChromaDB not available, skipping vector storage")

    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }

    for i, ticker in enumerate(tickers):
        if verbose:
            print(f"[{i+1}/{len(tickers)}] Loading {ticker}...")

        try:
            # Yahoo Financeからデータ取得
            yf_ticker = format_ticker(ticker)
            stock = yf.Ticker(yf_ticker)
            info = stock.info

            if not info.get("regularMarketPrice") and not info.get("currentPrice"):
                if verbose:
                    print(f"  ⚠ No data available for {ticker}")
                results["skipped"].append(ticker)
                continue

            # 基本情報を抽出
            stock_data = {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "currency": info.get("currency", "JPY"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
                "previous_close": info.get("previousClose", 0),
                "open": info.get("open", 0),
                "day_high": info.get("dayHigh", 0),
                "day_low": info.get("dayLow", 0),
                "volume": info.get("volume", 0),
                "avg_volume": info.get("averageVolume", 0),
                "week_52_high": info.get("fiftyTwoWeekHigh", 0),
                "week_52_low": info.get("fiftyTwoWeekLow", 0),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "dividend_yield": info.get("dividendYield", 0),
                "dividend_rate": info.get("dividendRate", 0),
                "payout_ratio": info.get("payoutRatio"),
                "beta": info.get("beta"),
                "eps": info.get("trailingEps"),
                "book_value": info.get("bookValue"),
                "revenue": info.get("totalRevenue", 0),
                "gross_profit": info.get("grossProfits", 0),
                "operating_margin": info.get("operatingMargins"),
                "profit_margin": info.get("profitMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "free_cashflow": info.get("freeCashflow", 0),
                "description": info.get("longBusinessSummary", "")
            }

            # 構造化DBに保存
            stock_db.upsert_stock(ticker, stock_data)

            # ファンダメンタルズを保存
            fundamental_data = {
                "pe_ratio": stock_data["pe_ratio"],
                "pb_ratio": stock_data["pb_ratio"],
                "ps_ratio": stock_data["ps_ratio"],
                "roe": stock_data["roe"],
                "roa": stock_data["roa"],
                "operating_margin": stock_data["operating_margin"],
                "profit_margin": stock_data["profit_margin"],
                "dividend_yield": stock_data["dividend_yield"],
                "debt_to_equity": stock_data["debt_to_equity"],
                "current_ratio": stock_data["current_ratio"],
                "revenue": stock_data["revenue"],
                "free_cashflow": stock_data["free_cashflow"]
            }
            stock_db.save_fundamentals(ticker, fundamental_data)

            # 価格履歴を取得・保存
            hist = stock.history(period="3mo")
            if not hist.empty:
                prices = []
                for date, row in hist.iterrows():
                    prices.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"])
                    })
                stock_db.save_prices(ticker, prices)

            # ベクトルDBに企業情報を保存
            if vector_db and stock_data.get("description"):
                vector_db.add_company_description(
                    ticker=ticker,
                    name=stock_data["name"],
                    description=stock_data["description"],
                    sector=stock_data["sector"],
                    industry=stock_data["industry"]
                )

            results["success"].append(ticker)
            if verbose:
                print(f"  ✓ {stock_data['name']} loaded")

        except Exception as e:
            results["failed"].append({"ticker": ticker, "error": str(e)})
            if verbose:
                print(f"  ✗ Error: {e}")

    return results


def load_news_data(
    tickers: List[str] = None,
    stock_db: StockDatabase = None,
    vector_db: VectorDatabase = None,
    verbose: bool = True
) -> Dict:
    """
    銘柄のニュースをDBにロード
    """
    from modules.news import NewsAnalyzer

    if tickers is None:
        tickers = DEFAULT_TICKERS[:10]  # 最初の10銘柄のみ

    if stock_db is None:
        stock_db = StockDatabase()

    news_analyzer = NewsAnalyzer()
    results = {"success": 0, "failed": 0}

    for ticker in tickers:
        try:
            # 銘柄情報を取得
            stock_info = stock_db.get_stock(ticker)
            company_name = stock_info.get("name", ticker) if stock_info else ticker

            if verbose:
                print(f"Fetching news for {ticker} ({company_name})...")

            # ニュースを取得
            news_list = news_analyzer.search_company_news(company_name, max_results=5)

            # 構造化DBに保存
            for article in news_list:
                news_data = {
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "snippet": article.snippet,
                    "sentiment": article.sentiment
                }
                stock_db.save_news(ticker, [news_data])

                # ベクトルDBにも保存
                if vector_db:
                    vector_db.add_news(
                        ticker=ticker,
                        title=article.title,
                        content=article.snippet,
                        url=article.url,
                        source=article.source,
                        sentiment=article.sentiment
                    )

            results["success"] += len(news_list)
            if verbose:
                print(f"  ✓ {len(news_list)} articles saved")

        except Exception as e:
            results["failed"] += 1
            if verbose:
                print(f"  ✗ Error: {e}")

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("日本株データローダー")
    print("=" * 60)
    print()

    # データベース初期化
    print("Initializing databases...")
    stock_db = StockDatabase()

    try:
        vector_db = VectorDatabase()
        print("  ✓ StockDB (TinyDB) initialized")
        print("  ✓ VectorDB (ChromaDB) initialized")
    except ImportError as e:
        vector_db = None
        print("  ✓ StockDB (TinyDB) initialized")
        print(f"  ⚠ VectorDB skipped: {e}")

    print()

    # 銘柄データをロード
    print("Loading stock data...")
    print("-" * 40)
    results = load_stock_data(
        tickers=DEFAULT_TICKERS,
        stock_db=stock_db,
        vector_db=vector_db,
        verbose=True
    )

    print()
    print("-" * 40)
    print(f"Results: {len(results['success'])} success, "
          f"{len(results['failed'])} failed, "
          f"{len(results['skipped'])} skipped")

    # 統計表示
    print()
    print("Database Statistics:")
    print("-" * 40)
    stats = stock_db.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    if vector_db:
        print()
        vector_stats = vector_db.get_stats()
        for key, value in vector_stats.items():
            print(f"  {key}: {value}")

    print()
    print("✓ Data loading complete!")
