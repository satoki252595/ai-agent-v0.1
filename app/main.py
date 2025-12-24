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
try:
    from database.vector_db import VectorDatabase
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False

# --- ページ設定 ---
st.set_page_config(
    page_title="日本株AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- モバイルファーストCSS ---
st.markdown("""
<style>
    /* ベースリセット */
    * {
        box-sizing: border-box;
    }

    /* ルート変数 */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --bg-dark: #0f0f0f;
        --bg-card: #1a1a1a;
        --bg-input: #252525;
        --text-primary: #ffffff;
        --text-secondary: #a1a1aa;
        --border: #2a2a2a;
        --success: #22c55e;
        --warning: #f59e0b;
        --danger: #ef4444;
    }

    /* アプリ全体 */
    .stApp {
        background: var(--bg-dark) !important;
        color: var(--text-primary) !important;
    }

    /* サイドバー非表示 */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* メインコンテンツ - モバイル最適化 */
    .main .block-container {
        padding: 1rem !important;
        max-width: 100% !important;
    }

    @media (min-width: 768px) {
        .main .block-container {
            padding: 2rem !important;
            max-width: 800px !important;
        }
    }

    /* ヘッダー */
    .app-header {
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 1rem;
    }

    .app-header h1 {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .app-header p {
        color: var(--text-secondary);
        font-size: 0.875rem;
        margin: 0.5rem 0 0 0;
    }

    /* チャットコンテナ */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        min-height: 50vh;
        padding-bottom: 100px;
    }

    /* メッセージバブル */
    .message {
        padding: 1rem;
        border-radius: 1rem;
        max-width: 100%;
        animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .message-user {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        margin-left: 1rem;
        border-bottom-right-radius: 0.25rem;
    }

    .message-ai {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-bottom-left-radius: 0.25rem;
    }

    .message-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
        font-weight: 600;
    }

    .message-user .message-label {
        color: rgba(255,255,255,0.8);
    }

    /* 入力エリア */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: var(--bg-dark);
        border-top: 1px solid var(--border);
        padding: 1rem;
        z-index: 1000;
    }

    .input-wrapper {
        max-width: 800px;
        margin: 0 auto;
        display: flex;
        gap: 0.75rem;
    }

    /* テキストエリア */
    .stTextArea textarea {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 1rem !important;
        color: var(--text-primary) !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        min-height: 56px !important;
        resize: none !important;
    }

    .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }

    .stTextArea textarea::placeholder {
        color: var(--text-secondary) !important;
    }

    /* 送信ボタン */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 1rem !important;
        padding: 0.875rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        min-height: 56px !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ステータスインジケーター */
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: var(--bg-card);
        border-radius: 2rem;
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-bottom: 1rem;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--success);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* サンプルクエリ */
    .sample-queries {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }

    .sample-query {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 2rem;
        padding: 0.5rem 1rem;
        font-size: 0.8125rem;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .sample-query:hover {
        border-color: var(--primary);
        color: var(--primary);
    }

    /* レスポンスカード */
    .response-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 1rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    .response-card h4 {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin: 0 0 0.5rem 0;
        font-weight: 600;
    }

    /* データ表示 */
    .data-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
        margin: 1rem 0;
    }

    @media (min-width: 768px) {
        .data-grid {
            grid-template-columns: repeat(4, 1fr);
        }
    }

    .data-item {
        background: var(--bg-input);
        border-radius: 0.75rem;
        padding: 0.75rem;
        text-align: center;
    }

    .data-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
    }

    .data-value {
        font-size: 1.125rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .data-value.positive { color: var(--success); }
    .data-value.negative { color: var(--danger); }

    /* スピナー */
    .stSpinner > div {
        border-top-color: var(--primary) !important;
    }

    /* マークダウンスタイル */
    .message-ai h1, .message-ai h2, .message-ai h3 {
        color: var(--text-primary);
        margin-top: 1rem;
    }

    .message-ai h1 { font-size: 1.25rem; }
    .message-ai h2 { font-size: 1.125rem; }
    .message-ai h3 { font-size: 1rem; }

    .message-ai ul, .message-ai ol {
        padding-left: 1.5rem;
        color: var(--text-secondary);
    }

    .message-ai li {
        margin: 0.25rem 0;
    }

    .message-ai strong {
        color: var(--text-primary);
    }

    /* フッター非表示 */
    footer { display: none !important; }

    /* Streamlitデフォルトを上書き */
    .stMarkdown { color: inherit; }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* 区切り線 */
    hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: 1rem 0;
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
    if VECTOR_DB_AVAILABLE:
        try:
            return VectorDatabase()
        except Exception as e:
            st.warning(f"VectorDB初期化エラー: {e}")
            return None
    return None

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
        try:
            fa = FundamentalAnalyzer(ticker)
            fund_data = fa.get_analysis_summary()
            result["fundamental"] = fund_data
            stock_db.save_fundamentals(ticker, fund_data)
        except:
            pass

        # ベクトルDBに企業情報を保存
        if vector_db and info.get("description"):
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
    if not vector_db:
        return {}

    try:
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
    except Exception as e:
        return {}


def get_db_stats() -> dict:
    """DB統計を取得"""
    stats = {"stock_db": stock_db.get_stats()}
    if vector_db:
        stats["vector_db"] = vector_db.get_stats()
    return stats


# --- メインUI ---
# ヘッダー
st.markdown("""
<div class="app-header">
    <h1>🤖 日本株リサーチAI</h1>
    <p>AIがあなたの投資リサーチをサポートします</p>
</div>
""", unsafe_allow_html=True)

# ステータス（DB接続状態を表示）
db_stats = get_db_stats()
stocks_in_db = db_stats.get("stock_db", {}).get("stocks_count", 0)
vector_ready = "vector_db" in db_stats

st.markdown(f"""
<div class="status-indicator">
    <span class="status-dot"></span>
    <span>AI Ready | DB: {stocks_in_db}銘柄{" | Vector検索可" if vector_ready else ""}</span>
</div>
""", unsafe_allow_html=True)

# チャット履歴がない場合のウェルカムメッセージ
if not st.session_state.messages:
    st.markdown("""
<div class="message message-ai">
    <div class="message-label">🤖 AI</div>
    <p>こんにちは！日本株リサーチAIです。</p>
    <p>銘柄分析、市場動向、投資戦略など、何でもお聞きください。</p>
    <p style="color: var(--text-secondary); font-size: 0.875rem; margin-top: 1rem;">例えば...</p>
</div>
""", unsafe_allow_html=True)

    # サンプルクエリ
    sample_queries = [
        "7203（トヨタ）を分析して",
        "半導体セクターの見通しは？",
        "高配当で割安な銘柄を探して",
        "今の市場環境を教えて"
    ]

    cols = st.columns(2)
    for i, query in enumerate(sample_queries):
        with cols[i % 2]:
            if st.button(query, key=f"sample_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()

# チャット履歴の表示
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
<div class="message message-user">
    <div class="message-label">👤 あなた</div>
    <p>{msg["content"]}</p>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="message message-ai">
    <div class="message-label">🤖 AI</div>
    {msg["content"]}
</div>
""", unsafe_allow_html=True)

# 入力フォーム
st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)  # 入力欄のスペース

with st.container():
    col1, col2 = st.columns([5, 1])

    with col1:
        user_input = st.text_area(
            "質問を入力",
            placeholder="銘柄コード、セクター、投資戦略など何でも質問してください...",
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
                    context_data += f"""
【銘柄情報】
銘柄コード: {ticker}
企業名: {info.get('name', 'N/A')}
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

回答:""")

            chain = prompt | agent.llm | StrOutputParser()

            for chunk in chain.stream({
                "context": context_data if context_data else "特定の銘柄データはありません。一般的な知識で回答してください。",
                "question": user_input
            }):
                full_response += chunk
                response_container.markdown(f"""
<div class="message message-ai">
    <div class="message-label">🤖 AI</div>
    {full_response}
</div>
""", unsafe_allow_html=True)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.session_state.processing = False
    st.rerun()


# 免責事項
st.markdown("""
<div style="text-align: center; color: var(--text-secondary); font-size: 0.75rem; padding: 1rem 0;">
    ※ 本サービスは情報提供を目的としており、投資助言ではありません。投資判断は自己責任でお願いします。
</div>
""", unsafe_allow_html=True)
