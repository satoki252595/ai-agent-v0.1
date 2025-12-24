# -*- coding: utf-8 -*-
"""
ニュース・センチメント分析モジュール
企業ニュース収集と市場センチメント分析
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import trafilatura
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_fixed


@dataclass
class NewsArticle:
    """ニュース記事"""
    title: str
    url: str
    source: str
    snippet: str
    published_date: Optional[str] = None
    sentiment: Optional[str] = None  # "ポジティブ", "ネガティブ", "中立"


class NewsAnalyzer:
    """ニュース・センチメント分析クラス"""

    # センチメント分析用キーワード
    POSITIVE_KEYWORDS = [
        "上昇", "増収", "増益", "過去最高", "好調", "急伸", "上方修正",
        "増配", "自社株買い", "提携", "新製品", "受注", "拡大", "成長",
        "黒字", "回復", "改善", "達成", "突破", "更新", "躍進", "好決算",
        "買い", "上げ", "強い", "期待", "注目", "人気"
    ]

    NEGATIVE_KEYWORDS = [
        "下落", "減収", "減益", "赤字", "損失", "下方修正", "減配",
        "撤退", "縮小", "リストラ", "訴訟", "不正", "問題", "懸念",
        "悪化", "低迷", "苦戦", "失敗", "遅延", "停止", "売り",
        "急落", "暴落", "弱い", "リスク", "警戒"
    ]

    def __init__(self):
        self._cache = {}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def search_company_news(self, company_name: str, max_results: int = 10) -> List[NewsArticle]:
        """
        企業関連ニュースを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"{company_name} 株価 OR 決算 OR 業績",
                    region='jp-jp',
                    safesearch='off',
                    max_results=max_results
                ))

            articles = []
            for r in results:
                sentiment = self._analyze_sentiment(r.get("title", "") + " " + r.get("body", ""))
                articles.append(NewsArticle(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    source=self._extract_source(r.get("href", "")),
                    snippet=r.get("body", ""),
                    sentiment=sentiment
                ))

            return articles
        except Exception as e:
            print(f"News search error: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def search_ticker_news(self, ticker: str, max_results: int = 10) -> List[NewsArticle]:
        """
        銘柄コードでニュースを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"{ticker} 株 決算 OR 業績 OR 株価",
                    region='jp-jp',
                    max_results=max_results
                ))

            articles = []
            for r in results:
                sentiment = self._analyze_sentiment(r.get("title", "") + " " + r.get("body", ""))
                articles.append(NewsArticle(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    source=self._extract_source(r.get("href", "")),
                    snippet=r.get("body", ""),
                    sentiment=sentiment
                ))

            return articles
        except Exception as e:
            print(f"News search error: {e}")
            return []

    def search_sector_news(self, sector: str, max_results: int = 10) -> List[NewsArticle]:
        """
        セクター・業界ニュースを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"{sector} 業界 動向 OR 見通し",
                    region='jp-jp',
                    max_results=max_results
                ))

            articles = []
            for r in results:
                sentiment = self._analyze_sentiment(r.get("title", "") + " " + r.get("body", ""))
                articles.append(NewsArticle(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    source=self._extract_source(r.get("href", "")),
                    snippet=r.get("body", ""),
                    sentiment=sentiment
                ))

            return articles
        except:
            return []

    def search_earnings_news(self, company_name: str) -> List[NewsArticle]:
        """
        決算関連ニュースを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"{company_name} 決算 発表 OR 業績 OR 見通し",
                    region='jp-jp',
                    max_results=5
                ))

            articles = []
            for r in results:
                sentiment = self._analyze_sentiment(r.get("title", "") + " " + r.get("body", ""))
                articles.append(NewsArticle(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    source=self._extract_source(r.get("href", "")),
                    snippet=r.get("body", ""),
                    sentiment=sentiment
                ))

            return articles
        except:
            return []

    def search_market_news(self, max_results: int = 10) -> List[NewsArticle]:
        """
        市場全体のニュースを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    "日経平均 東証 株式市場 本日",
                    region='jp-jp',
                    max_results=max_results
                ))

            articles = []
            for r in results:
                sentiment = self._analyze_sentiment(r.get("title", "") + " " + r.get("body", ""))
                articles.append(NewsArticle(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    source=self._extract_source(r.get("href", "")),
                    snippet=r.get("body", ""),
                    sentiment=sentiment
                ))

            return articles
        except:
            return []

    def _analyze_sentiment(self, text: str) -> str:
        """
        テキストのセンチメントを分析
        """
        text_lower = text.lower()

        positive_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text)
        negative_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text)

        if positive_count > negative_count + 1:
            return "ポジティブ"
        elif negative_count > positive_count + 1:
            return "ネガティブ"
        else:
            return "中立"

    def _extract_source(self, url: str) -> str:
        """
        URLからソース名を抽出
        """
        source_mapping = {
            "nikkei.com": "日経新聞",
            "reuters.com": "ロイター",
            "bloomberg.co.jp": "ブルームバーグ",
            "kabutan.jp": "株探",
            "minkabu.jp": "みんかぶ",
            "toyokeizai.net": "東洋経済",
            "diamond.jp": "ダイヤモンド",
            "shikiho.jp": "四季報",
            "yahoo.co.jp": "Yahoo!ファイナンス",
            "rakuten-sec.co.jp": "楽天証券",
            "sbisec.co.jp": "SBI証券"
        }

        for domain, name in source_mapping.items():
            if domain in url:
                return name

        # ドメイン名を抽出
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return match.group(1) if match else "不明"

    def get_sentiment_score(self, articles: List[NewsArticle]) -> Dict:
        """
        ニュース全体のセンチメントスコアを計算
        """
        if not articles:
            return {
                "score": 50,
                "sentiment": "中立",
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0
            }

        positive = sum(1 for a in articles if a.sentiment == "ポジティブ")
        negative = sum(1 for a in articles if a.sentiment == "ネガティブ")
        neutral = sum(1 for a in articles if a.sentiment == "中立")

        total = len(articles)

        # スコア計算 (0-100)
        score = 50 + ((positive - negative) / total) * 50

        if score >= 65:
            overall_sentiment = "ポジティブ"
        elif score <= 35:
            overall_sentiment = "ネガティブ"
        else:
            overall_sentiment = "中立"

        return {
            "score": round(score, 1),
            "sentiment": overall_sentiment,
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "total_articles": total
        }

    def fetch_article_content(self, url: str) -> str:
        """
        記事の本文を取得
        """
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(downloaded, include_comments=False)
                return content if content else ""
            return ""
        except:
            return ""

    def analyze_company_sentiment(self, ticker: str, company_name: str) -> Dict:
        """
        企業のセンチメント総合分析
        """
        # 複数ソースからニュース収集
        company_news = self.search_company_news(company_name, max_results=5)
        ticker_news = self.search_ticker_news(ticker, max_results=5)
        earnings_news = self.search_earnings_news(company_name)

        # 重複除去
        all_urls = set()
        all_news = []
        for article in company_news + ticker_news + earnings_news:
            if article.url not in all_urls:
                all_urls.add(article.url)
                all_news.append(article)

        # センチメントスコア計算
        sentiment_score = self.get_sentiment_score(all_news)

        # ニュースをセンチメント別に分類
        positive_news = [a for a in all_news if a.sentiment == "ポジティブ"]
        negative_news = [a for a in all_news if a.sentiment == "ネガティブ"]

        return {
            "ticker": ticker,
            "company": company_name,
            "sentiment_score": sentiment_score["score"],
            "overall_sentiment": sentiment_score["sentiment"],
            "positive_count": sentiment_score["positive_count"],
            "negative_count": sentiment_score["negative_count"],
            "neutral_count": sentiment_score["neutral_count"],
            "total_articles": sentiment_score["total_articles"],
            "positive_headlines": [{"title": a.title, "source": a.source} for a in positive_news[:3]],
            "negative_headlines": [{"title": a.title, "source": a.source} for a in negative_news[:3]],
            "all_news": [
                {
                    "title": a.title,
                    "url": a.url,
                    "source": a.source,
                    "snippet": a.snippet,
                    "sentiment": a.sentiment
                }
                for a in all_news[:10]
            ]
        }

    def get_market_sentiment(self) -> Dict:
        """
        市場全体のセンチメントを分析
        """
        market_news = self.search_market_news(max_results=15)
        sentiment_score = self.get_sentiment_score(market_news)

        return {
            "market_sentiment_score": sentiment_score["score"],
            "market_sentiment": sentiment_score["sentiment"],
            "summary": self._generate_market_summary(market_news, sentiment_score),
            "top_news": [
                {
                    "title": a.title,
                    "source": a.source,
                    "sentiment": a.sentiment
                }
                for a in market_news[:5]
            ]
        }

    def _generate_market_summary(self, news: List[NewsArticle], score: Dict) -> str:
        """
        市場センチメントのサマリーを生成
        """
        sentiment = score["sentiment"]

        if sentiment == "ポジティブ":
            return "市場センチメントは楽観的。投資家心理は改善傾向にあります。"
        elif sentiment == "ネガティブ":
            return "市場センチメントは慎重。リスク回避姿勢が見られます。"
        else:
            return "市場センチメントは中立。方向感を模索する展開です。"

    def search_analyst_reports(self, company_name: str) -> List[Dict]:
        """
        アナリストレポート・レーティングを検索
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    f"{company_name} アナリスト レーティング OR 目標株価",
                    region='jp-jp',
                    max_results=5
                ))

            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                }
                for r in results
            ]
        except:
            return []

    def get_comprehensive_news_analysis(self, ticker: str, company_name: str) -> Dict:
        """
        包括的なニュース分析
        """
        # 企業センチメント
        company_sentiment = self.analyze_company_sentiment(ticker, company_name)

        # アナリストレポート
        analyst_reports = self.search_analyst_reports(company_name)

        # 市場センチメント
        market_sentiment = self.get_market_sentiment()

        return {
            "company_analysis": company_sentiment,
            "market_analysis": market_sentiment,
            "analyst_reports": analyst_reports,
            "summary": {
                "company_sentiment": company_sentiment["overall_sentiment"],
                "company_score": company_sentiment["sentiment_score"],
                "market_sentiment": market_sentiment["market_sentiment"],
                "market_score": market_sentiment["market_sentiment_score"]
            }
        }
