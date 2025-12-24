# -*- coding: utf-8 -*-
"""
ベクトルデータベース（ChromaDB）
ニュース記事、リサーチノート、セマンティック検索用の埋め込みを管理
"""
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class VectorDatabase:
    """
    ベクトルデータベース
    ChromaDBを使用したセマンティック検索対応ストレージ
    """

    def __init__(self, db_path: str = None):
        """
        データベースを初期化

        Args:
            db_path: データベースディレクトリのパス
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb is not installed. Run: pip install chromadb")

        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "chroma")

        os.makedirs(db_path, exist_ok=True)
        self.db_path = db_path

        # ChromaDBクライアントを初期化（永続化モード）
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # コレクション定義
        self._init_collections()

    def _init_collections(self):
        """コレクションを初期化"""
        # デフォルトの埋め込み関数を使用（ローカル処理、外部API不要）
        # sentence-transformers のデフォルトモデルを使用
        try:
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        except Exception:
            # フォールバック: 埋め込み関数なしで初期化
            self.embedding_fn = None

        # ニュース記事用コレクション
        self.news_collection = self.client.get_or_create_collection(
            name="news_articles",
            metadata={"description": "Stock-related news articles"},
            embedding_function=self.embedding_fn
        )

        # リサーチノート用コレクション
        self.research_collection = self.client.get_or_create_collection(
            name="research_notes",
            metadata={"description": "AI-generated research notes and analysis"},
            embedding_function=self.embedding_fn
        )

        # 銘柄説明用コレクション
        self.company_collection = self.client.get_or_create_collection(
            name="company_descriptions",
            metadata={"description": "Company business descriptions"},
            embedding_function=self.embedding_fn
        )

    def _generate_id(self, text: str) -> str:
        """テキストからユニークIDを生成"""
        return hashlib.md5(text.encode()).hexdigest()

    # ==================== ニュース ====================

    def add_news(
        self,
        ticker: str,
        title: str,
        content: str,
        url: str = "",
        source: str = "",
        sentiment: str = "neutral",
        metadata: Dict = None
    ) -> str:
        """
        ニュース記事を追加

        Args:
            ticker: 銘柄コード
            title: 記事タイトル
            content: 記事本文
            url: 記事URL
            source: ソース名
            sentiment: センチメント（positive/negative/neutral）
            metadata: 追加メタデータ

        Returns:
            ドキュメントID
        """
        doc_id = self._generate_id(url or title)

        # テキストを結合（埋め込み用）
        full_text = f"{title}\n\n{content}"

        # メタデータを構築
        doc_metadata = {
            "ticker": ticker,
            "title": title,
            "url": url,
            "source": source,
            "sentiment": sentiment,
            "added_at": datetime.now().isoformat(),
            "type": "news"
        }
        if metadata:
            doc_metadata.update(metadata)

        # 既存チェック
        existing = self.news_collection.get(ids=[doc_id])
        if existing and existing["ids"]:
            self.news_collection.update(
                ids=[doc_id],
                documents=[full_text],
                metadatas=[doc_metadata]
            )
        else:
            self.news_collection.add(
                ids=[doc_id],
                documents=[full_text],
                metadatas=[doc_metadata]
            )

        return doc_id

    def search_news(
        self,
        query: str,
        ticker: str = None,
        n_results: int = 10,
        sentiment: str = None
    ) -> List[Dict]:
        """
        ニュースをセマンティック検索

        Args:
            query: 検索クエリ
            ticker: 銘柄コードでフィルタ
            n_results: 取得件数
            sentiment: センチメントでフィルタ

        Returns:
            マッチするニュースリスト
        """
        where = {}
        if ticker:
            where["ticker"] = ticker
        if sentiment:
            where["sentiment"] = sentiment

        results = self.news_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where if where else None
        )

        # 結果を整形
        output = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                item = {
                    "id": doc_id,
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                }
                if results["metadatas"] and results["metadatas"][0]:
                    item.update(results["metadatas"][0][i])
                output.append(item)

        return output

    def get_news_by_ticker(self, ticker: str, limit: int = 20) -> List[Dict]:
        """銘柄のニュースを取得"""
        results = self.news_collection.get(
            where={"ticker": ticker},
            limit=limit
        )

        output = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                item = {
                    "id": doc_id,
                    "content": results["documents"][i] if results["documents"] else "",
                }
                if results["metadatas"]:
                    item.update(results["metadatas"][i])
                output.append(item)

        return output

    # ==================== リサーチノート ====================

    def add_research_note(
        self,
        ticker: str,
        title: str,
        content: str,
        note_type: str = "analysis",
        metadata: Dict = None
    ) -> str:
        """
        リサーチノートを追加

        Args:
            ticker: 銘柄コード
            title: ノートタイトル
            content: ノート内容
            note_type: ノートタイプ（analysis/report/memo）
            metadata: 追加メタデータ

        Returns:
            ドキュメントID
        """
        doc_id = self._generate_id(f"{ticker}_{title}_{datetime.now().isoformat()}")

        full_text = f"{title}\n\n{content}"

        doc_metadata = {
            "ticker": ticker,
            "title": title,
            "note_type": note_type,
            "created_at": datetime.now().isoformat(),
            "type": "research"
        }
        if metadata:
            doc_metadata.update(metadata)

        self.research_collection.add(
            ids=[doc_id],
            documents=[full_text],
            metadatas=[doc_metadata]
        )

        return doc_id

    def search_research(
        self,
        query: str,
        ticker: str = None,
        n_results: int = 10
    ) -> List[Dict]:
        """
        リサーチノートをセマンティック検索

        Args:
            query: 検索クエリ
            ticker: 銘柄コードでフィルタ
            n_results: 取得件数

        Returns:
            マッチするノートリスト
        """
        where = {"ticker": ticker} if ticker else None

        results = self.research_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )

        output = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                item = {
                    "id": doc_id,
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                }
                if results["metadatas"] and results["metadatas"][0]:
                    item.update(results["metadatas"][0][i])
                output.append(item)

        return output

    # ==================== 企業情報 ====================

    def add_company_description(
        self,
        ticker: str,
        name: str,
        description: str,
        sector: str = "",
        industry: str = "",
        metadata: Dict = None
    ) -> str:
        """
        企業説明を追加

        Args:
            ticker: 銘柄コード
            name: 企業名
            description: 事業説明
            sector: セクター
            industry: 業種
            metadata: 追加メタデータ

        Returns:
            ドキュメントID
        """
        doc_id = ticker

        full_text = f"{name}\n\n{description}"

        doc_metadata = {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "updated_at": datetime.now().isoformat(),
            "type": "company"
        }
        if metadata:
            doc_metadata.update(metadata)

        # 既存チェック
        existing = self.company_collection.get(ids=[doc_id])
        if existing and existing["ids"]:
            self.company_collection.update(
                ids=[doc_id],
                documents=[full_text],
                metadatas=[doc_metadata]
            )
        else:
            self.company_collection.add(
                ids=[doc_id],
                documents=[full_text],
                metadatas=[doc_metadata]
            )

        return doc_id

    def search_companies(
        self,
        query: str,
        sector: str = None,
        n_results: int = 10
    ) -> List[Dict]:
        """
        企業をセマンティック検索

        Args:
            query: 検索クエリ（事業内容など）
            sector: セクターでフィルタ
            n_results: 取得件数

        Returns:
            マッチする企業リスト
        """
        where = {"sector": sector} if sector else None

        results = self.company_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )

        output = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                item = {
                    "id": doc_id,
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                }
                if results["metadatas"] and results["metadatas"][0]:
                    item.update(results["metadatas"][0][i])
                output.append(item)

        return output

    def get_company(self, ticker: str) -> Optional[Dict]:
        """企業情報を取得"""
        results = self.company_collection.get(ids=[ticker])

        if results and results["ids"]:
            item = {
                "id": results["ids"][0],
                "content": results["documents"][0] if results["documents"] else "",
            }
            if results["metadatas"]:
                item.update(results["metadatas"][0])
            return item

        return None

    # ==================== 汎用検索 ====================

    def semantic_search(
        self,
        query: str,
        collections: List[str] = None,
        n_results: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        複数コレクションを横断してセマンティック検索

        Args:
            query: 検索クエリ
            collections: 検索対象コレクション（None=すべて）
            n_results: コレクションごとの取得件数

        Returns:
            コレクション別の検索結果
        """
        if collections is None:
            collections = ["news", "research", "company"]

        results = {}

        if "news" in collections:
            results["news"] = self.search_news(query, n_results=n_results)

        if "research" in collections:
            results["research"] = self.search_research(query, n_results=n_results)

        if "company" in collections:
            results["company"] = self.search_companies(query, n_results=n_results)

        return results

    # ==================== ユーティリティ ====================

    def get_stats(self) -> Dict:
        """データベース統計を取得"""
        return {
            "news_count": self.news_collection.count(),
            "research_count": self.research_collection.count(),
            "company_count": self.company_collection.count(),
            "db_path": self.db_path
        }

    def delete_by_ticker(self, ticker: str) -> Dict[str, int]:
        """銘柄に関連するすべてのデータを削除"""
        deleted = {}

        # ニュース
        news = self.news_collection.get(where={"ticker": ticker})
        if news["ids"]:
            self.news_collection.delete(ids=news["ids"])
            deleted["news"] = len(news["ids"])

        # リサーチ
        research = self.research_collection.get(where={"ticker": ticker})
        if research["ids"]:
            self.research_collection.delete(ids=research["ids"])
            deleted["research"] = len(research["ids"])

        # 企業情報
        company = self.company_collection.get(ids=[ticker])
        if company["ids"]:
            self.company_collection.delete(ids=[ticker])
            deleted["company"] = 1

        return deleted

    def clear_all(self):
        """すべてのデータを削除（開発用）"""
        self.client.reset()
        self._init_collections()
