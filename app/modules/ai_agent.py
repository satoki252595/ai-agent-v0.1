# -*- coding: utf-8 -*-
"""
日本株リサーチAIエージェント
全モジュールを統合したAI分析エージェント
"""
import streamlit as st
from typing import Dict, List, Optional, Generator
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from duckduckgo_search import DDGS
import trafilatura
from tenacity import retry, stop_after_attempt, wait_fixed
import os

# 設定
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11435"))
MODEL_NAME = st.secrets.get("MODEL_NAME", os.environ.get("MODEL_NAME", "nemotron-3-nano"))
LLM_TEMPERATURE = 0.3


class StockResearchAgent:
    """日本株リサーチAIエージェント"""

    def __init__(self):
        self.llm = self._get_llm()

    def _get_llm(self):
        """LLMインスタンスを取得"""
        return ChatOllama(
            model=MODEL_NAME,
            base_url=OLLAMA_URL,
            temperature=LLM_TEMPERATURE,
            headers={"ngrok-skip-browser-warning": "true"},
            keep_alive="5m"
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Web検索を実行"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region='jp-jp', safesearch='off', max_results=max_results))
            return results
        except Exception as e:
            print(f"Search Error: {e}")
            return []

    def fetch_content(self, url: str) -> str:
        """URLから本文を抽出"""
        if url.lower().endswith('.pdf'):
            return ""
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return ""
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        return text if text else ""

    def generate_stock_report(
        self,
        ticker: str,
        company_name: str,
        technical_data: Dict,
        fundamental_data: Dict,
        macro_data: Dict,
        news_data: Dict,
        patent_data: Dict = None,
        alpha_signal: Dict = None
    ) -> Generator[str, None, None]:
        """
        総合株式分析レポートを生成（ストリーミング）
        """
        data_summary = self._create_data_summary(
            ticker, company_name, technical_data, fundamental_data,
            macro_data, news_data, patent_data, alpha_signal
        )

        prompt = ChatPromptTemplate.from_template("""
あなたは日本株専門の一流アナリストです。
以下のデータを分析し、投資家向けの包括的なレポートを作成してください。

【分析対象】
銘柄コード: {ticker}
企業名: {company_name}

【収集データ】
{data_summary}

【レポート形式】
# {company_name}（{ticker}）投資分析レポート

## 📊 投資判断サマリー
- **総合評価**: [強い買い/買い/中立/売り/強い売り]
- **目標株価**: [分析に基づく目標株価]
- **リスクレベル**: [低/中/高]

## 📈 テクニカル分析
（移動平均、RSI、MACD、一目均衡表などの分析結果を記載）

## 💰 ファンダメンタルズ分析
（バリュエーション、収益性、財務健全性、成長性の分析を記載）

## 🌍 マクロ環境影響
（為替、金利、市場環境が当該銘柄に与える影響を分析）

## 📰 ニュース・センチメント
（最新ニュースとセンチメント分析の結果を記載）

## 🔬 技術力・特許動向
（特許ポートフォリオと技術革新力の評価）

## ⚠️ リスク要因
（投資における主要なリスクを列挙）

## 💡 投資戦略提案
（具体的なエントリーポイント、ターゲット、損切りラインを提案）

---
※本レポートは情報提供を目的としており、投資助言ではありません。
投資判断は自己責任でお願いいたします。

必ず日本語で出力してください。
""")

        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({
            "ticker": ticker,
            "company_name": company_name,
            "data_summary": data_summary
        }):
            yield chunk

    def _create_data_summary(
        self,
        ticker: str,
        company_name: str,
        technical_data: Dict,
        fundamental_data: Dict,
        macro_data: Dict,
        news_data: Dict,
        patent_data: Dict = None,
        alpha_signal: Dict = None
    ) -> str:
        """分析データのサマリーを作成"""
        summary_parts = []

        # テクニカルデータ
        if technical_data:
            tech_summary = f"""
【テクニカル指標】
- 総合シグナル: {technical_data.get('overall_signal', 'N/A')}
- スコア: {technical_data.get('score', 'N/A')}
- 買いシグナル数: {technical_data.get('buy_signals', 0)}
- 売りシグナル数: {technical_data.get('sell_signals', 0)}
"""
            if 'signals' in technical_data:
                for signal in technical_data['signals'][:5]:
                    tech_summary += f"- {signal.indicator}: {signal.signal} ({signal.description})\n"
            summary_parts.append(tech_summary)

        # ファンダメンタルデータ
        if fundamental_data:
            fund_summary = f"""
【ファンダメンタルズ】
- ファンダメンタルスコア: {fundamental_data.get('fundamental_score', 'N/A')}/100
- グレード: {fundamental_data.get('fundamental_grade', 'N/A')}
- PER: {fundamental_data.get('valuation', {}).get('per', 'N/A')}
- PBR: {fundamental_data.get('valuation', {}).get('pbr', 'N/A')}
- ROE: {fundamental_data.get('profitability', {}).get('roe', 'N/A')}
- 配当利回り: {fundamental_data.get('dividend', {}).get('dividend_yield', 'N/A')}
- 売上成長率: {fundamental_data.get('growth', {}).get('revenue_growth', 'N/A')}
- 営業利益率: {fundamental_data.get('profitability', {}).get('operating_margin', 'N/A')}
- 自己資本比率: {fundamental_data.get('financial_health', {}).get('current_ratio', 'N/A')}
"""
            summary_parts.append(fund_summary)

        # マクロデータ
        if macro_data:
            macro_summary = f"""
【マクロ環境】
- 市場レジーム: {macro_data.get('market_regime', {}).get('regime', 'N/A')}
- リスクレベル: {macro_data.get('market_regime', {}).get('risk_level', 'N/A')}
- 推奨セクター: {', '.join(macro_data.get('sector_rotation', {}).get('recommended_sectors', [])[:3])}
"""
            if 'forex' in macro_data:
                forex = macro_data['forex']
                macro_summary += f"- ドル円: {forex.get('usdjpy', {}).get('rate', 'N/A')}\n"
            summary_parts.append(macro_summary)

        # ニュースデータ
        if news_data:
            news_summary = f"""
【ニュース・センチメント】
- センチメントスコア: {news_data.get('sentiment_score', 50)}/100
- 総合センチメント: {news_data.get('overall_sentiment', '中立')}
- ポジティブニュース: {news_data.get('positive_count', 0)}件
- ネガティブニュース: {news_data.get('negative_count', 0)}件
"""
            if 'positive_headlines' in news_data:
                for headline in news_data['positive_headlines'][:2]:
                    news_summary += f"- [ポジ] {headline.get('title', '')[:50]}\n"
            if 'negative_headlines' in news_data:
                for headline in news_data['negative_headlines'][:2]:
                    news_summary += f"- [ネガ] {headline.get('title', '')[:50]}\n"
            summary_parts.append(news_summary)

        # 特許データ
        if patent_data:
            patent_summary = f"""
【特許・技術力】
- 技術スコア: {patent_data.get('tech_score', 'N/A')}/100
- 技術グレード: {patent_data.get('tech_grade', 'N/A')}
- 発見特許数: {patent_data.get('total_patents_found', 0)}
- 主要技術分野: {', '.join(list(patent_data.get('technology_areas', {}).keys())[:5])}
"""
            summary_parts.append(patent_summary)

        # アルファシグナル
        if alpha_signal:
            alpha_summary = f"""
【アルファシグナル】
- シグナル: {alpha_signal.get('signal_type', 'N/A')}
- 強度: {alpha_signal.get('strength', 0)}/100
- 説明: {alpha_signal.get('description', '')}
"""
            summary_parts.append(alpha_summary)

        return "\n".join(summary_parts)

    def generate_quick_analysis(self, ticker: str, company_name: str, info: Dict) -> Generator[str, None, None]:
        """クイック分析を生成"""
        prompt = ChatPromptTemplate.from_template("""
あなたは日本株専門アナリストです。
以下の銘柄情報に基づいて、簡潔な投資分析を提供してください。

銘柄: {company_name}（{ticker}）
現在株価: {current_price}円
時価総額: {market_cap}
PER: {per}
PBR: {pbr}
配当利回り: {dividend_yield}
ROE: {roe}
セクター: {sector}

【出力形式】
## {company_name} クイック分析

### 投資判断
[買い/中立/売り] - 理由を1文で

### 注目ポイント
- ポイント1
- ポイント2
- ポイント3

### リスク
- リスク1
- リスク2

※簡潔に日本語で出力してください。
""")

        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({
            "ticker": ticker,
            "company_name": company_name,
            "current_price": info.get("current_price", "N/A"),
            "market_cap": info.get("market_cap", "N/A"),
            "per": info.get("pe_ratio", "N/A"),
            "pbr": info.get("pb_ratio", "N/A"),
            "dividend_yield": info.get("dividend_yield", "N/A"),
            "roe": info.get("roe", "N/A"),
            "sector": info.get("sector", "N/A")
        }):
            yield chunk

    def research_topic(self, topic: str, status_container=None) -> Dict:
        """トピックに関する自律リサーチを実行"""
        all_notes = ""
        visited_urls = set()

        if status_container:
            status_container.write("🤔 調査計画を立案中...")

        queries = self._plan_research(topic)

        if status_container:
            status_container.write(f"📋 検索プラン: {queries}")

        if status_container:
            status_container.write("🌍 Web調査を開始...")

        for q in queries:
            if status_container:
                status_container.write(f"🔎 検索中: {q}...")

            results = self.search_web(q, max_results=3)

            for res in results:
                url = res.get('href', '')
                if url in visited_urls:
                    continue
                visited_urls.add(url)

                if status_container:
                    status_container.write(f"📖 読解中: {res.get('title', '')}...")

                content = self.fetch_content(url)
                if content:
                    summary = self._summarize_content(topic, content[:5000])
                    all_notes += f"\n--- Source: {res.get('title', '')} ({url}) ---\n{summary}\n"

        return {
            "topic": topic,
            "notes": all_notes,
            "sources_count": len(visited_urls)
        }

    def _plan_research(self, topic: str) -> List[str]:
        """リサーチクエリを計画"""
        prompt = ChatPromptTemplate.from_template("""
あなたは投資リサーチャーです。
ユーザーの依頼：「{topic}」

この依頼を達成するために必要な情報を集めるための「Web検索クエリ」を3つ考えてください。

出力形式:
- クエリ1
- クエリ2
- クエリ3
(余計な説明は不要。クエリのみを箇条書きで出力)
""")
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({"topic": topic})
        queries = [line.strip("- ").strip() for line in response.split("\n") if line.strip()]
        return queries[:3]

    def _summarize_content(self, topic: str, content: str) -> str:
        """コンテンツを要約"""
        prompt = ChatPromptTemplate.from_template("""
テーマ：「{topic}」

以下の内容から、テーマに関連する重要な事実、数値、意見を抽出して、日本語の短いメモにしてください。

内容:
{content}
""")
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"topic": topic, "content": content[:5000]})

    def generate_sector_report(self, sector: str, stocks: List[Dict]) -> Generator[str, None, None]:
        """セクター分析レポートを生成"""
        stocks_info = "\n".join([
            f"- {s.get('ticker')}: {s.get('name', '')} (PER: {s.get('per', 'N/A')}, ROE: {s.get('roe', 'N/A')})"
            for s in stocks[:10]
        ])

        prompt = ChatPromptTemplate.from_template("""
あなたはセクターアナリストです。
以下のセクターと銘柄情報に基づいて、セクター分析レポートを作成してください。

セクター: {sector}

主要銘柄:
{stocks_info}

【レポート形式】
# {sector}セクター分析

## セクター概況
（現在の市場環境と業界動向）

## 注目銘柄
（投資妙味のある銘柄とその理由）

## セクター見通し
（今後の展望とカタリスト）

## 投資戦略
（セクターへの投資アプローチ）

日本語で出力してください。
""")

        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({
            "sector": sector,
            "stocks_info": stocks_info
        }):
            yield chunk

    def compare_stocks(self, stocks_data: List[Dict]) -> Generator[str, None, None]:
        """複数銘柄の比較分析"""
        comparison_table = "| 銘柄 | PER | PBR | ROE | 配当利回り |\n|---|---|---|---|---|\n"
        for s in stocks_data:
            comparison_table += f"| {s.get('ticker', '')} | {s.get('per', 'N/A')} | {s.get('pbr', 'N/A')} | {s.get('roe', 'N/A')} | {s.get('dividend_yield', 'N/A')} |\n"

        prompt = ChatPromptTemplate.from_template("""
あなたは株式アナリストです。
以下の銘柄を比較分析してください。

{comparison_table}

【出力形式】
## 銘柄比較分析

### バリュエーション比較
（各銘柄の割安度を比較）

### 収益性比較
（ROE等の収益性指標を比較）

### 投資推奨
（最も魅力的な銘柄とその理由）

日本語で出力してください。
""")

        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({"comparison_table": comparison_table}):
            yield chunk
