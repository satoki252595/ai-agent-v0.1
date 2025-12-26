# -*- coding: utf-8 -*-
"""
特許情報収集モジュール
企業の特許動向、技術力の分析
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
import trafilatura
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_fixed


@dataclass
class PatentInfo:
    """特許情報"""
    title: str
    application_number: str
    applicant: str
    filing_date: str
    publication_date: str
    abstract: str
    url: str


class PatentResearcher:
    """特許情報リサーチャー"""

    def __init__(self):
        self.cache = {}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def search_patents(self, company_name: str, max_results: int = 10) -> List[Dict]:
        """
        企業名で特許を検索（Google Patents経由）
        """
        try:
            with DDGS() as ddgs:
                # Google Patentsで検索
                query = f'site:patents.google.com "{company_name}" 特許'
                results = list(ddgs.text(query, region='jp-jp', max_results=max_results))

            patents = []
            for r in results:
                patents.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })

            return patents
        except Exception as e:
            print(f"Patent search error: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def search_patents_by_keyword(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        技術キーワードで特許を検索
        """
        try:
            with DDGS() as ddgs:
                query = f'site:patents.google.com {keyword} 日本'
                results = list(ddgs.text(query, region='jp-jp', max_results=max_results))

            patents = []
            for r in results:
                patents.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })

            return patents
        except Exception as e:
            print(f"Patent search error: {e}")
            return []

    def search_jplatpat(self, company_name: str) -> List[Dict]:
        """
        J-PlatPat（特許庁データベース）での検索情報を取得
        ※直接APIアクセスは制限があるため、Web検索経由
        """
        with DDGS() as ddgs:
            query = f'site:j-platpat.inpit.go.jp "{company_name}"'
            results = list(ddgs.text(query, region='jp-jp', max_results=5))

        return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]

    def analyze_patent_portfolio(self, company_name: str) -> Dict:
        """
        企業の特許ポートフォリオを分析
        """
        patents = self.search_patents(company_name, max_results=20)

        if not patents:
            return {
                "company": company_name,
                "total_patents_found": 0,
                "analysis": "特許情報が見つかりませんでした",
                "patents": []
            }

        # 技術分野の抽出
        tech_keywords = {}
        for p in patents:
            title = p.get("title", "").lower()
            snippet = p.get("snippet", "").lower()
            text = title + " " + snippet

            # 技術キーワードをカウント
            tech_terms = [
                "AI", "人工知能", "機械学習", "ディープラーニング",
                "半導体", "センサー", "バッテリー", "電池",
                "5G", "通信", "ネットワーク",
                "自動運転", "EV", "電気自動車",
                "ロボット", "自動化", "IoT",
                "バイオ", "医療", "創薬",
                "材料", "素材", "化学",
                "エネルギー", "再生可能", "太陽光"
            ]

            for term in tech_terms:
                if term.lower() in text:
                    tech_keywords[term] = tech_keywords.get(term, 0) + 1

        # 技術力スコアを算出（簡易版）
        tech_score = min(100, len(patents) * 5 + len(tech_keywords) * 10)

        return {
            "company": company_name,
            "total_patents_found": len(patents),
            "technology_areas": dict(sorted(tech_keywords.items(), key=lambda x: x[1], reverse=True)[:10]),
            "tech_score": tech_score,
            "tech_grade": "A" if tech_score >= 80 else "B" if tech_score >= 60 else "C" if tech_score >= 40 else "D",
            "patents": patents[:10]  # 上位10件
        }

    def search_recent_patents(self, company_name: str, year: int = 2024) -> List[Dict]:
        """
        最近の特許出願を検索
        """
        with DDGS() as ddgs:
            query = f'site:patents.google.com "{company_name}" {year}'
            results = list(ddgs.text(query, region='jp-jp', max_results=10))

        return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]

    def compare_patent_strength(self, companies: List[str]) -> Dict:
        """
        複数企業の特許力を比較
        """
        comparison = {}

        for company in companies:
            analysis = self.analyze_patent_portfolio(company)
            comparison[company] = {
                "total_patents": analysis["total_patents_found"],
                "tech_score": analysis["tech_score"],
                "tech_grade": analysis["tech_grade"],
                "top_technologies": list(analysis.get("technology_areas", {}).keys())[:5]
            }

        # ランキング
        ranking = sorted(comparison.items(), key=lambda x: x[1]["tech_score"], reverse=True)

        return {
            "comparison": comparison,
            "ranking": [{"company": c[0], "score": c[1]["tech_score"]} for c in ranking]
        }

    def search_industry_patents(self, industry: str, max_results: int = 15) -> List[Dict]:
        """
        業界・分野別の特許トレンドを検索
        """
        industry_keywords = {
            "自動車": "自動車 EV 自動運転 特許",
            "半導体": "半導体 チップ 製造 特許",
            "医薬品": "医薬品 創薬 バイオ 特許",
            "電機": "電機 家電 IoT 特許",
            "通信": "通信 5G 6G ネットワーク 特許",
            "化学": "化学 材料 素材 特許",
            "機械": "機械 ロボット 自動化 特許",
            "エネルギー": "エネルギー 再生可能 バッテリー 特許"
        }

        keyword = industry_keywords.get(industry, f"{industry} 特許")

        with DDGS() as ddgs:
            query = f'site:patents.google.com {keyword}'
            results = list(ddgs.text(query, region='jp-jp', max_results=max_results))

        return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]

    def get_patent_news(self, company_name: str) -> List[Dict]:
        """
        特許関連ニュースを検索
        """
        with DDGS() as ddgs:
            query = f'{company_name} 特許 取得 OR 出願 OR 訴訟'
            results = list(ddgs.text(query, region='jp-jp', max_results=5))

        return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]

    def analyze_tech_innovation(self, ticker: str, company_name: str) -> Dict:
        """
        技術革新力の総合分析
        """
        # 特許ポートフォリオ分析
        portfolio = self.analyze_patent_portfolio(company_name)

        # 最近の特許
        recent = self.search_recent_patents(company_name)

        # 特許ニュース
        news = self.get_patent_news(company_name)

        # 総合評価
        innovation_score = portfolio["tech_score"]

        # 最近の活動があればボーナス
        if len(recent) > 3:
            innovation_score = min(100, innovation_score + 10)

        return {
            "ticker": ticker,
            "company": company_name,
            "innovation_score": innovation_score,
            "innovation_grade": "A" if innovation_score >= 80 else "B" if innovation_score >= 60 else "C" if innovation_score >= 40 else "D",
            "portfolio": portfolio,
            "recent_patents": recent[:5],
            "patent_news": news,
            "assessment": self._generate_assessment(portfolio, recent)
        }

    def _generate_assessment(self, portfolio: Dict, recent: List) -> str:
        """
        技術力の評価コメントを生成
        """
        total = portfolio["total_patents_found"]
        tech_areas = portfolio.get("technology_areas", {})

        if total == 0:
            return "特許情報が限定的です。知的財産戦略の確認が必要です。"

        top_techs = list(tech_areas.keys())[:3]
        tech_str = "、".join(top_techs) if top_techs else "不明"

        if portfolio["tech_score"] >= 80:
            return f"強力な特許ポートフォリオを保有。{tech_str}分野で技術的優位性があります。"
        elif portfolio["tech_score"] >= 60:
            return f"堅実な特許戦略。{tech_str}分野を中心に技術開発を進めています。"
        elif portfolio["tech_score"] >= 40:
            return f"特許活動は中程度。{tech_str}分野での競争力強化が期待されます。"
        else:
            return "特許活動は限定的。技術開発への投資拡大が望まれます。"
