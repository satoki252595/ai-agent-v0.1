# -*- coding: utf-8 -*-
"""
構造化データベース（TinyDB）
銘柄情報、財務データ、価格履歴などの構造化データを管理
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
import json


class StockDatabase:
    """
    日本株データベース
    TinyDBを使用した軽量NoSQLストレージ
    """

    def __init__(self, db_path: str = None):
        """
        データベースを初期化

        Args:
            db_path: データベースファイルのパス（デフォルト: ./data/stocks.json）
        """
        if db_path is None:
            # デフォルトパスを設定
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "stocks.json")

        self.db_path = db_path
        self.db = TinyDB(db_path, storage=CachingMiddleware(JSONStorage))

        # テーブル定義
        self.stocks = self.db.table("stocks")           # 銘柄基本情報
        self.prices = self.db.table("prices")           # 価格履歴
        self.fundamentals = self.db.table("fundamentals")  # ファンダメンタルズ
        self.technicals = self.db.table("technicals")   # テクニカル指標
        self.news = self.db.table("news")               # ニュース
        self.watchlist = self.db.table("watchlist")     # ウォッチリスト

    def close(self):
        """データベースを閉じる"""
        self.db.close()

    # ==================== 銘柄情報 ====================

    def upsert_stock(self, ticker: str, data: Dict) -> int:
        """
        銘柄情報を追加/更新

        Args:
            ticker: 銘柄コード
            data: 銘柄データ

        Returns:
            ドキュメントID
        """
        Stock = Query()
        data["ticker"] = ticker
        data["updated_at"] = datetime.now().isoformat()

        existing = self.stocks.search(Stock.ticker == ticker)
        if existing:
            self.stocks.update(data, Stock.ticker == ticker)
            return existing[0].doc_id
        else:
            return self.stocks.insert(data)

    def get_stock(self, ticker: str) -> Optional[Dict]:
        """
        銘柄情報を取得

        Args:
            ticker: 銘柄コード

        Returns:
            銘柄データ（存在しない場合はNone）
        """
        Stock = Query()
        result = self.stocks.search(Stock.ticker == ticker)
        return result[0] if result else None

    def get_all_stocks(self) -> List[Dict]:
        """すべての銘柄情報を取得"""
        return self.stocks.all()

    def search_stocks(self, **kwargs) -> List[Dict]:
        """
        条件で銘柄を検索

        Args:
            **kwargs: 検索条件（例: sector="Technology", per_lt=15）

        Returns:
            マッチする銘柄リスト
        """
        Stock = Query()
        conditions = []

        for key, value in kwargs.items():
            if key.endswith("_lt"):  # Less than
                field = key[:-3]
                conditions.append(getattr(Stock, field) < value)
            elif key.endswith("_gt"):  # Greater than
                field = key[:-3]
                conditions.append(getattr(Stock, field) > value)
            elif key.endswith("_contains"):  # Contains
                field = key[:-9]
                conditions.append(getattr(Stock, field).search(value))
            else:  # Equals
                conditions.append(getattr(Stock, key) == value)

        if not conditions:
            return self.stocks.all()

        # すべての条件をANDで結合
        query = conditions[0]
        for cond in conditions[1:]:
            query = query & cond

        return self.stocks.search(query)

    def delete_stock(self, ticker: str) -> bool:
        """銘柄を削除"""
        Stock = Query()
        removed = self.stocks.remove(Stock.ticker == ticker)
        return len(removed) > 0

    # ==================== 価格履歴 ====================

    def save_prices(self, ticker: str, prices: List[Dict]) -> int:
        """
        価格履歴を保存

        Args:
            ticker: 銘柄コード
            prices: 価格データのリスト [{"date": "2024-01-01", "open": 100, ...}, ...]

        Returns:
            保存したレコード数
        """
        Price = Query()

        # 既存データを削除
        self.prices.remove(Price.ticker == ticker)

        # 新しいデータを挿入
        records = []
        for price in prices:
            record = {
                "ticker": ticker,
                **price,
                "saved_at": datetime.now().isoformat()
            }
            records.append(record)

        if records:
            self.prices.insert_multiple(records)

        return len(records)

    def get_prices(self, ticker: str, days: int = None) -> List[Dict]:
        """
        価格履歴を取得

        Args:
            ticker: 銘柄コード
            days: 取得する日数（Noneの場合は全件）

        Returns:
            価格データのリスト
        """
        Price = Query()
        results = self.prices.search(Price.ticker == ticker)

        # 日付でソート
        results.sort(key=lambda x: x.get("date", ""), reverse=True)

        if days:
            results = results[:days]

        return results

    # ==================== ファンダメンタルズ ====================

    def save_fundamentals(self, ticker: str, data: Dict) -> int:
        """ファンダメンタルズデータを保存"""
        Fundamental = Query()
        data["ticker"] = ticker
        data["updated_at"] = datetime.now().isoformat()

        existing = self.fundamentals.search(Fundamental.ticker == ticker)
        if existing:
            self.fundamentals.update(data, Fundamental.ticker == ticker)
            return existing[0].doc_id
        else:
            return self.fundamentals.insert(data)

    def get_fundamentals(self, ticker: str) -> Optional[Dict]:
        """ファンダメンタルズデータを取得"""
        Fundamental = Query()
        result = self.fundamentals.search(Fundamental.ticker == ticker)
        return result[0] if result else None

    # ==================== テクニカル指標 ====================

    def save_technicals(self, ticker: str, data: Dict) -> int:
        """テクニカル指標を保存"""
        Technical = Query()
        data["ticker"] = ticker
        data["updated_at"] = datetime.now().isoformat()

        existing = self.technicals.search(Technical.ticker == ticker)
        if existing:
            self.technicals.update(data, Technical.ticker == ticker)
            return existing[0].doc_id
        else:
            return self.technicals.insert(data)

    def get_technicals(self, ticker: str) -> Optional[Dict]:
        """テクニカル指標を取得"""
        Technical = Query()
        result = self.technicals.search(Technical.ticker == ticker)
        return result[0] if result else None

    # ==================== ニュース ====================

    def save_news(self, ticker: str, news_list: List[Dict]) -> int:
        """
        ニュースを保存

        Args:
            ticker: 銘柄コード
            news_list: ニュースリスト

        Returns:
            保存したニュース数
        """
        count = 0
        News = Query()

        for news in news_list:
            # URLで重複チェック
            url = news.get("url", "")
            if url and self.news.search(News.url == url):
                continue

            record = {
                "ticker": ticker,
                **news,
                "saved_at": datetime.now().isoformat()
            }
            self.news.insert(record)
            count += 1

        return count

    def get_news(self, ticker: str = None, limit: int = 20) -> List[Dict]:
        """
        ニュースを取得

        Args:
            ticker: 銘柄コード（Noneの場合は全件）
            limit: 取得件数

        Returns:
            ニュースリスト
        """
        if ticker:
            News = Query()
            results = self.news.search(News.ticker == ticker)
        else:
            results = self.news.all()

        # 日付でソート
        results.sort(key=lambda x: x.get("saved_at", ""), reverse=True)

        return results[:limit]

    # ==================== ウォッチリスト ====================

    def add_to_watchlist(self, ticker: str, note: str = "") -> bool:
        """ウォッチリストに追加"""
        Watchlist = Query()
        if self.watchlist.search(Watchlist.ticker == ticker):
            return False

        self.watchlist.insert({
            "ticker": ticker,
            "note": note,
            "added_at": datetime.now().isoformat()
        })
        return True

    def remove_from_watchlist(self, ticker: str) -> bool:
        """ウォッチリストから削除"""
        Watchlist = Query()
        removed = self.watchlist.remove(Watchlist.ticker == ticker)
        return len(removed) > 0

    def get_watchlist(self) -> List[Dict]:
        """ウォッチリストを取得"""
        return self.watchlist.all()

    # ==================== ユーティリティ ====================

    def get_stats(self) -> Dict:
        """データベース統計を取得"""
        return {
            "stocks_count": len(self.stocks),
            "prices_count": len(self.prices),
            "fundamentals_count": len(self.fundamentals),
            "technicals_count": len(self.technicals),
            "news_count": len(self.news),
            "watchlist_count": len(self.watchlist),
            "db_path": self.db_path
        }

    def is_data_fresh(self, ticker: str, table: str = "stocks", max_age_hours: int = 24) -> bool:
        """
        データが新鮮かどうかを確認

        Args:
            ticker: 銘柄コード
            table: テーブル名
            max_age_hours: 最大許容時間（時間）

        Returns:
            True if fresh, False if stale
        """
        table_obj = getattr(self, table, None)
        if not table_obj:
            return False

        Stock = Query()
        result = table_obj.search(Stock.ticker == ticker)

        if not result:
            return False

        updated_at = result[0].get("updated_at")
        if not updated_at:
            return False

        update_time = datetime.fromisoformat(updated_at)
        age = datetime.now() - update_time
        return age < timedelta(hours=max_age_hours)

    def clear_all(self):
        """すべてのデータを削除（開発用）"""
        self.stocks.truncate()
        self.prices.truncate()
        self.fundamentals.truncate()
        self.technicals.truncate()
        self.news.truncate()
        self.watchlist.truncate()

    def export_to_json(self, filepath: str):
        """データをJSONファイルにエクスポート"""
        data = {
            "stocks": self.stocks.all(),
            "prices": self.prices.all(),
            "fundamentals": self.fundamentals.all(),
            "technicals": self.technicals.all(),
            "news": self.news.all(),
            "watchlist": self.watchlist.all(),
            "exported_at": datetime.now().isoformat()
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_from_json(self, filepath: str):
        """JSONファイルからデータをインポート"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "stocks" in data:
            self.stocks.insert_multiple(data["stocks"])
        if "prices" in data:
            self.prices.insert_multiple(data["prices"])
        if "fundamentals" in data:
            self.fundamentals.insert_multiple(data["fundamentals"])
        if "technicals" in data:
            self.technicals.insert_multiple(data["technicals"])
        if "news" in data:
            self.news.insert_multiple(data["news"])
        if "watchlist" in data:
            self.watchlist.insert_multiple(data["watchlist"])
