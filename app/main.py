# -*- coding: utf-8 -*-
"""
日本株リサーチAIエージェント
Japan Stock Research AI Agent

シンプルなチャット形式のAIリサーチアシスタント
ローカルDB（TinyDB + ChromaDB）と連携
"""
import streamlit as st
import sys
import os
import re
from datetime import datetime

# モジュールパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.stock_data import StockDataFetcher
from modules.technical import TechnicalAnalyzer
from modules.fundamental import FundamentalAnalyzer
from modules.macro import MacroAnalyzer
from modules.patent import PatentResearcher
from modules.alpha import AlphaFinder
from modules.news import NewsAnalyzer
from modules.ai_agent import StockResearchAgent

# データベース
from database.stock_db import StockDatabase
from database.vector_db import VectorDatabase

# --- ページ設定 ---
st.set_page_config(
    page_title="日本株AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- シンプルCSS ---
st.markdown("""
<style>
    :root {
        --primary: #6366f1;
        --bg-dark: #0f0f0f;
        --bg-card: #1a1a1a;
        --bg-input: #252525;
        --text-primary: #ffffff;
        --text-secondary: #a1a1aa;
        --border: #2a2a2a;
    }

    .stApp {
        background: var(--bg-dark) !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { background: transparent !important; }
    footer { display: none !important; }

    .main .block-container {
        padding: 1rem !important;
        max-width: 800px !important;
    }

    .app-title {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        padding: 1rem 0;
        color: var(--primary);
    }

    .message {
        padding: 1rem;
        border-radius: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .message-user {
        background: var(--primary);
        color: white;
    }

    .message-ai {
        background: var(--bg-card);
        border: 1px solid var(--border);
    }

    .stTextArea textarea {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0.5rem !important;
        color: var(--text-primary) !important;
    }

    .stButton > button {
        background: var(--primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)


# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing" not in st.session_state:
    st.session_state.processing = False

# データベース初期化（キャッシュ）
@st.cache_resource
def get_stock_db():
    """構造化DBを取得"""
    return StockDatabase()

@st.cache_resource
def get_vector_db():
    """ベクトルDBを取得"""
    return VectorDatabase()

stock_db = get_stock_db()
vector_db = get_vector_db()


# --- ヘルパー関数 ---
def extract_ticker(text: str) -> str:
    """テキストから銘柄コードを抽出"""
    # 4桁の数字パターン
    match = re.search(r'\b(\d{4})\b', text)
    if match:
        return match.group(1)
    return None


def analyze_stock(ticker: str) -> dict:
    """
    銘柄を分析してデータを取得
    DBにキャッシュがあれば優先的に使用、なければライブデータを取得してDBに保存
    """
    result = {
        "info": None,
        "technical": None,
        "fundamental": None,
        "from_cache": False
    }

    # 1. DBからデータを確認
    if stock_db.is_data_fresh(ticker, "stocks", max_age_hours=6):
        cached_info = stock_db.get_stock(ticker)
        if cached_info:
            result["info"] = cached_info
            result["from_cache"] = True

            # キャッシュされたファンダメンタルズも取得
            cached_fund = stock_db.get_fundamentals(ticker)
            if cached_fund:
                result["fundamental"] = cached_fund

            # キャッシュされたテクニカルも取得
            cached_tech = stock_db.get_technicals(ticker)
            if cached_tech:
                result["technical"] = cached_tech

    # 2. キャッシュがない場合はライブデータを取得
    if not result["info"]:
        fetcher = StockDataFetcher()
        info = fetcher.get_stock_info(ticker)

        if "error" in info:
            return None

        result["info"] = info

        # DBに保存
        stock_db.upsert_stock(ticker, info)

        # 価格履歴を取得・保存
        hist = fetcher.get_historical_data(ticker, "3mo")
        if not hist.empty:
            prices = []
            for date, row in hist.iterrows():
                prices.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["open"]) if "open" in row else 0,
                    "high": float(row["high"]) if "high" in row else 0,
                    "low": float(row["low"]) if "low" in row else 0,
                    "close": float(row["close"]) if "close" in row else 0,
                    "volume": int(row["volume"]) if "volume" in row else 0
                })
            stock_db.save_prices(ticker, prices)

            # テクニカル分析
            ta = TechnicalAnalyzer(hist)
            tech_data = ta.get_trend_summary()
            result["technical"] = tech_data
            stock_db.save_technicals(ticker, tech_data)

        # ファンダメンタル分析
        fa = FundamentalAnalyzer(ticker)
        fund_data = fa.get_analysis_summary()
        result["fundamental"] = fund_data
        stock_db.save_fundamentals(ticker, fund_data)

        # ベクトルDBに企業情報を保存
        if info.get("description"):
            vector_db.add_company_description(
                ticker=ticker,
                name=info.get("name", ""),
                description=info.get("description", ""),
                sector=info.get("sector", ""),
                industry=info.get("industry", "")
            )

    return result


def get_macro_context() -> dict:
    """マクロ経済コンテキストを取得"""
    macro = MacroAnalyzer()
    return {
        "indices": macro.get_global_indices(),
        "forex": macro.get_forex_rates(),
        "regime": macro.get_market_regime()
    }


def search_related_info(query: str, ticker: str = None) -> dict:
    """
    ベクトルDBから関連情報をセマンティック検索
    """
    results = {}

    # 類似企業を検索
    similar_companies = vector_db.search_companies(query, n_results=3)
    if similar_companies:
        results["similar_companies"] = similar_companies

    # 関連ニュースを検索
    if ticker:
        news = vector_db.search_news(query, ticker=ticker, n_results=5)
    else:
        news = vector_db.search_news(query, n_results=5)
    if news:
        results["related_news"] = news

    # リサーチノートを検索
    research = vector_db.search_research(query, ticker=ticker, n_results=3)
    if research:
        results["research_notes"] = research

    return results


def get_realtime_news(ticker: str, company_name: str) -> dict:
    """
    リアルタイムで株式ニュースを取得・分析

    Args:
        ticker: 銘柄コード
        company_name: 企業名

    Returns:
        ニュース分析結果
    """
    news_analyzer = NewsAnalyzer()
    return news_analyzer.get_realtime_stock_news(ticker, company_name)


# --- メインUI ---
# サービス名
st.markdown('<div class="app-title">日本株リサーチAI</div>', unsafe_allow_html=True)

# チャット履歴の表示
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="message message-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="message message-ai">{msg["content"]}</div>', unsafe_allow_html=True)

# 入力フォーム
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.text_area(
        "質問",
        placeholder="質問を入力...",
        height=68,
        label_visibility="collapsed",
        key="user_input"
    )
with col2:
    send_button = st.button("送信", type="primary", use_container_width=True)


# 送信処理
if send_button and user_input and not st.session_state.processing:
    st.session_state.processing = True
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("分析中..."):
        try:
            agent = StockResearchAgent()

            # 銘柄コードの抽出
            ticker = extract_ticker(user_input)

            # コンテキストの構築
            context_data = ""

            if ticker:
                stock_data = analyze_stock(ticker)
                if stock_data:
                    info = stock_data["info"]
                    company_name = info.get('name', '')

                    context_data += f"""
【銘柄情報】
銘柄コード: {ticker}
企業名: {company_name}
現在株価: ¥{info.get('current_price', 0):,.0f}
時価総額: ¥{info.get('market_cap', 0):,.0f}
PER: {info.get('pe_ratio', 'N/A')}
PBR: {info.get('pb_ratio', 'N/A')}
配当利回り: {info.get('dividend_yield', 0) * 100 if info.get('dividend_yield') else 0:.2f}%
ROE: {info.get('roe', 0) * 100 if info.get('roe') else 0:.1f}%
セクター: {info.get('sector', 'N/A')}
"""
                    if stock_data["technical"]:
                        tech = stock_data["technical"]
                        context_data += f"""
【テクニカル分析】
総合シグナル: {tech.get('overall_signal', 'N/A')}
スコア: {tech.get('score', 0)}
買いシグナル数: {tech.get('buy_signals', 0)}
売りシグナル数: {tech.get('sell_signals', 0)}
"""
                    if stock_data["fundamental"]:
                        fund = stock_data["fundamental"]
                        context_data += f"""
【ファンダメンタル分析】
ファンダメンタルスコア: {fund.get('fundamental_score', 0)}/100
グレード: {fund.get('fundamental_grade', 'N/A')}
"""
                    # リアルタイムニュース検索
                    news_data = get_realtime_news(ticker, company_name)
                    if news_data:
                        context_data += f"""
【最新ニュース・IR情報】
センチメントスコア: {news_data.get('sentiment_score', 50)}/100
総合センチメント: {news_data.get('overall_sentiment', '中立')}
ポジティブニュース: {news_data.get('positive_count', 0)}件
ネガティブニュース: {news_data.get('negative_count', 0)}件
サマリー: {news_data.get('news_summary', '')}
"""
                        # IRニュース
                        ir_news = news_data.get('ir_news', [])
                        if ir_news:
                            context_data += "\n【IR関連ニュース】\n"
                            for article in ir_news[:3]:
                                sentiment_mark = "📈" if article.get('sentiment') == "ポジティブ" else "📉" if article.get('sentiment') == "ネガティブ" else "➖"
                                context_data += f"- {sentiment_mark} {article.get('title', '')[:60]}... ({article.get('source', '')})\n"

                        # 一般ニュース
                        general_news = news_data.get('general_news', [])
                        if general_news:
                            context_data += "\n【一般ニュース】\n"
                            for article in general_news[:3]:
                                sentiment_mark = "📈" if article.get('sentiment') == "ポジティブ" else "📉" if article.get('sentiment') == "ネガティブ" else "➖"
                                context_data += f"- {sentiment_mark} {article.get('title', '')[:60]}... ({article.get('source', '')})\n"

            # マクロ情報が必要そうな場合
            if any(word in user_input for word in ["市場", "環境", "マクロ", "日経", "相場", "セクター"]):
                macro_data = get_macro_context()
                regime = macro_data.get("regime", {})
                context_data += f"""
【市場環境】
市場レジーム: {regime.get('regime', 'N/A')}
リスクレベル: {regime.get('risk_level', 'N/A')}
"""
                if macro_data.get("indices", {}).get("nikkei225"):
                    nk = macro_data["indices"]["nikkei225"]
                    context_data += f"日経平均: ¥{nk.get('value', 0):,.0f} ({nk.get('change_pct', 0):.2f}%)\n"
                if macro_data.get("forex", {}).get("usdjpy"):
                    fx = macro_data["forex"]["usdjpy"]
                    context_data += f"USD/JPY: ¥{fx.get('rate', 0):.2f}\n"

                # 市場ニュースを取得
                news_analyzer = NewsAnalyzer()
                market_sentiment = news_analyzer.get_market_sentiment()
                if market_sentiment:
                    context_data += f"""
【市場センチメント】
市場センチメントスコア: {market_sentiment.get('market_sentiment_score', 50)}/100
市場センチメント: {market_sentiment.get('market_sentiment', '中立')}
サマリー: {market_sentiment.get('summary', '')}
"""
                    top_news = market_sentiment.get('top_news', [])
                    if top_news:
                        context_data += "\n【本日の主要ニュース】\n"
                        for article in top_news[:4]:
                            sentiment_mark = "📈" if article.get('sentiment') == "ポジティブ" else "📉" if article.get('sentiment') == "ネガティブ" else "➖"
                            context_data += f"- {sentiment_mark} {article.get('title', '')[:50]}... ({article.get('source', '')})\n"

            # スクリーニングが必要そうな場合
            if any(word in user_input for word in ["探して", "スクリーニング", "割安", "高配当", "成長", "おすすめ"]):
                alpha = AlphaFinder()
                if "割安" in user_input or "バリュー" in user_input:
                    df = alpha.screen_value_stocks()
                    if not df.empty:
                        top_5 = df.head(5)
                        context_data += "\n【バリュー株スクリーニング結果】\n"
                        for _, row in top_5.iterrows():
                            context_data += f"- {row['ticker']}: PER {row.get('per', 'N/A')}, PBR {row.get('pbr', 'N/A')}\n"

                elif "高配当" in user_input:
                    df = alpha.screen_value_stocks()
                    if not df.empty:
                        top_5 = df.sort_values("dividend_yield", ascending=False).head(5)
                        context_data += "\n【高配当株スクリーニング結果】\n"
                        for _, row in top_5.iterrows():
                            yield_pct = row.get('dividend_yield', 0) * 100 if row.get('dividend_yield') else 0
                            context_data += f"- {row['ticker']}: 配当利回り {yield_pct:.2f}%\n"

                elif "成長" in user_input or "グロース" in user_input:
                    df = alpha.screen_growth_stocks()
                    if not df.empty:
                        top_5 = df.head(5)
                        context_data += "\n【グロース株スクリーニング結果】\n"
                        for _, row in top_5.iterrows():
                            context_data += f"- {row['ticker']}: 売上成長 {row.get('revenue_growth', 0)*100:.1f}%\n"

            # AIレスポンス生成
            response_container = st.empty()
            full_response = ""

            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            prompt = ChatPromptTemplate.from_template("""あなたは日本株専門のAIアナリストです。
ユーザーの質問に対して、専門的かつわかりやすく回答してください。

{context}

ユーザーの質問: {question}

【回答ガイドライン】
- 簡潔で読みやすい形式で回答
- 重要なポイントは箇条書きを使用
- 投資判断に役立つ具体的な情報を提供
- リスクについても言及
- 日本語で回答

【ニュース・IR情報の活用】
- 最新ニュースやIR情報が提供されている場合は、必ず分析に反映
- センチメント（ポジティブ/ネガティブ）を考慮した見通しを提示
- 決算・配当・M&A等の重要IRは投資判断の材料として言及
- ニュースのトレンドから短期的な株価への影響を推測

回答:""")

            chain = prompt | agent.llm | StrOutputParser()

            for chunk in chain.stream({
                "context": context_data if context_data else "特定の銘柄データはありません。一般的な知識で回答してください。",
                "question": user_input
            }):
                full_response += chunk
                response_container.markdown(f'<div class="message message-ai">{full_response}</div>', unsafe_allow_html=True)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.session_state.processing = False
    st.rerun()
