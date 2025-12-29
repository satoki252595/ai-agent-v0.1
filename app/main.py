# -*- coding: utf-8 -*-
"""
日本株リサーチAIエージェント
Japan Stock Research AI Agent

シンプルなチャット形式のAIリサーチアシスタント
"""
import streamlit as st
import sys
import os
import re
from datetime import datetime

# モジュールパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- ページ設定 ---
st.set_page_config(
    page_title="日本株AI",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- モダンUI CSS ---
st.markdown("""
<style>
    /* カラーパレット */
    :root {
        --primary: #6366f1;
        --primary-hover: #4f46e5;
        --accent: #22c55e;
        --danger: #ef4444;
        --warning: #f59e0b;
        --bg-primary: #09090b;
        --bg-secondary: #18181b;
        --bg-tertiary: #27272a;
        --bg-input: #1f1f23;
        --text-primary: #fafafa;
        --text-secondary: #a1a1aa;
        --text-muted: #71717a;
        --border: #3f3f46;
        --border-light: #52525b;
    }

    /* ベース */
    .stApp {
        background: var(--bg-primary) !important;
    }

    [data-testid="stSidebar"],
    [data-testid="stHeader"],
    footer,
    #MainMenu {
        display: none !important;
    }

    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    /* ヘッダー */
    .app-header {
        position: sticky;
        top: 0;
        z-index: 100;
        background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-primary) 80%, transparent 100%);
        padding: 1rem 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--border);
    }

    .app-logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .app-logo-icon {
        font-size: 1.5rem;
    }

    .app-logo-text {
        font-size: 1.125rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary) 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .header-actions {
        display: flex;
        gap: 0.5rem;
    }

    .header-btn {
        background: var(--bg-tertiary);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 0.5rem 0.75rem;
        color: var(--text-secondary);
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .header-btn:hover {
        background: var(--bg-input);
        color: var(--text-primary);
        border-color: var(--border-light);
    }

    /* チャットエリア */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem 1rem 140px 1rem;
        min-height: calc(100vh - 160px);
    }

    /* メッセージ */
    .message {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
        animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .message-avatar {
        width: 32px;
        height: 32px;
        border-radius: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.875rem;
        flex-shrink: 0;
    }

    .avatar-user {
        background: linear-gradient(135deg, var(--primary) 0%, #4f46e5 100%);
    }

    .avatar-ai {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
    }

    .message-content {
        flex: 1;
        max-width: calc(100% - 44px);
    }

    .message-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.25rem;
    }

    .message-sender {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .message-time {
        font-size: 0.7rem;
        color: var(--text-muted);
    }

    .message-bubble {
        padding: 0.875rem 1rem;
        border-radius: 0 0.75rem 0.75rem 0.75rem;
        line-height: 1.6;
        font-size: 0.9375rem;
    }

    .bubble-user {
        background: linear-gradient(135deg, var(--primary) 0%, #4f46e5 100%);
        color: white;
        border-radius: 0.75rem 0.75rem 0 0.75rem;
    }

    .bubble-ai {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        color: var(--text-primary);
    }

    .bubble-ai p { margin: 0 0 0.5rem 0; }
    .bubble-ai p:last-child { margin-bottom: 0; }
    .bubble-ai ul, .bubble-ai ol { margin: 0.5rem 0; padding-left: 1.25rem; }
    .bubble-ai li { margin: 0.25rem 0; color: var(--text-secondary); }
    .bubble-ai strong { color: var(--text-primary); }
    .bubble-ai code { background: var(--bg-tertiary); padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.875rem; }

    /* ウェルカム画面 */
    .welcome {
        text-align: center;
        padding: 3rem 1.5rem;
    }

    .welcome-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }

    .welcome-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .welcome-subtitle {
        color: var(--text-secondary);
        font-size: 0.9375rem;
        margin-bottom: 2rem;
    }

    .quick-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
        max-width: 500px;
        margin: 0 auto;
    }

    .quick-action {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 2rem;
        padding: 0.5rem 1rem;
        color: var(--text-secondary);
        font-size: 0.8125rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .quick-action:hover {
        border-color: var(--primary);
        color: var(--primary);
        background: rgba(99, 102, 241, 0.1);
    }

    /* 入力エリア */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(0deg, var(--bg-primary) 0%, var(--bg-primary) 85%, transparent 100%);
        padding: 1rem;
        z-index: 100;
    }

    .input-wrapper {
        max-width: 800px;
        margin: 0 auto;
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 1rem;
        padding: 0.75rem;
        display: flex;
        gap: 0.75rem;
        align-items: flex-end;
    }

    .input-wrapper:focus-within {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
    }

    .stTextArea textarea {
        background: transparent !important;
        border: none !important;
        color: var(--text-primary) !important;
        font-size: 0.9375rem !important;
        line-height: 1.5 !important;
        padding: 0.25rem 0 !important;
        min-height: 24px !important;
        max-height: 150px !important;
        resize: none !important;
    }

    .stTextArea textarea::placeholder {
        color: var(--text-muted) !important;
    }

    .stTextArea > div > div { background: transparent !important; }
    .stTextArea label { display: none !important; }

    .stButton > button {
        background: var(--primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 0.625rem !important;
        padding: 0.625rem 1.25rem !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s !important;
        min-height: 40px !important;
    }

    .stButton > button:hover {
        background: var(--primary-hover) !important;
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* タイピングインジケーター */
    .typing-indicator {
        display: flex;
        gap: 4px;
        padding: 0.75rem 1rem;
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 0 0.75rem 0.75rem 0.75rem;
        width: fit-content;
    }

    .typing-dot {
        width: 8px;
        height: 8px;
        background: var(--text-muted);
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
    }

    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes typing {
        0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
        30% { transform: translateY(-4px); opacity: 1; }
    }

    /* スピナー */
    .stSpinner > div {
        border-top-color: var(--primary) !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg-tertiary) !important;
        border-radius: 0.5rem !important;
        font-size: 0.8rem !important;
        color: var(--text-secondary) !important;
    }

    /* モバイル対応 */
    @media (max-width: 640px) {
        .app-header { padding: 0.75rem 1rem; }
        .app-logo-text { font-size: 1rem; }
        .chat-container { padding: 0.75rem 0.75rem 130px 0.75rem; }
        .message-bubble { padding: 0.75rem; font-size: 0.875rem; }
        .welcome { padding: 2rem 1rem; }
        .welcome-title { font-size: 1.25rem; }
        .input-wrapper { padding: 0.5rem; }
    }
</style>
""", unsafe_allow_html=True)


# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing" not in st.session_state:
    st.session_state.processing = False

# データベース初期化（遅延ロード）
@st.cache_resource
def get_stock_db():
    """構造化DBを取得"""
    from database.stock_db import StockDatabase
    return StockDatabase()

@st.cache_resource
def get_vector_db():
    """ベクトルDBを取得"""
    from database.vector_db import VectorDatabase
    return VectorDatabase()


# --- ヘルパー関数 ---
def extract_ticker(text: str) -> str:
    """テキストから銘柄コードを抽出"""
    # 4桁の数字パターン
    match = re.search(r'\b(\d{4})\b', text)
    if match:
        return match.group(1)
    return None


def search_company_by_name(company_name: str) -> list:
    """
    企業名から銘柄候補を検索

    Returns:
        [(ticker, name), ...] 形式の候補リスト
    """
    stock_db = get_stock_db()
    matches = stock_db.search_by_name(company_name, limit=5)

    if matches:
        return [(m.get("ticker"), m.get("name", "")) for m in matches]

    # DBに無い場合、yfinanceで直接検索を試行
    # 日本株の主要なサフィックス
    import yfinance as yf
    search_term = company_name.replace(" ", "")

    # 東証検索用のパターン
    candidates = []
    # 一般的な東証ティッカーパターンを試行（数字4桁.T）
    # ここではyfinanceのsearchを使用
    try:
        # yfinanceには直接の検索APIがないため、
        # 代替としてDuckDuckGoでティッカーを検索
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f"{company_name} 証券コード 銘柄コード site:yahoo.co.jp OR site:nikkei.com",
                region='jp-jp',
                max_results=3
            ))
        # 結果から4桁の数字を抽出
        for r in results:
            snippet = r.get("body", "") + r.get("title", "")
            ticker_match = re.search(r'\b(\d{4})\b', snippet)
            if ticker_match:
                found_ticker = ticker_match.group(1)
                # 重複チェック
                if not any(c[0] == found_ticker for c in candidates):
                    candidates.append((found_ticker, company_name))
    except Exception:
        pass

    return candidates[:5]


def analyze_stock(ticker: str) -> dict:
    """
    銘柄を分析してデータを取得
    DBにキャッシュがあれば優先的に使用、なければライブデータを取得してDBに保存
    """
    from modules.stock_data import StockDataFetcher
    from modules.technical import TechnicalAnalyzer
    from modules.fundamental import FundamentalAnalyzer

    stock_db = get_stock_db()
    vector_db = get_vector_db()

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
    from modules.macro import MacroAnalyzer
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
    vector_db = get_vector_db()
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
    from modules.news import NewsAnalyzer
    news_analyzer = NewsAnalyzer()
    return news_analyzer.get_realtime_stock_news(ticker, company_name)


# --- メインUI ---

# ヘッダー
col_logo, col_actions = st.columns([3, 1])
with col_logo:
    st.markdown('''
    <div class="app-logo">
        <span class="app-logo-icon">📈</span>
        <span class="app-logo-text">日本株リサーチAI</span>
    </div>
    ''', unsafe_allow_html=True)
with col_actions:
    if st.button("🗑️ クリア", key="clear_btn"):
        st.session_state.messages = []
        st.rerun()

st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# ウェルカム画面（メッセージがない場合）
if not st.session_state.messages:
    st.markdown('''
    <div class="welcome">
        <div class="welcome-icon">📊</div>
        <div class="welcome-title">日本株リサーチAIへようこそ</div>
        <div class="welcome-subtitle">銘柄コードや企業名を入力して分析を開始</div>
    </div>
    ''', unsafe_allow_html=True)

    # クイックアクション
    quick_cols = st.columns(4)
    quick_queries = ["7203 トヨタ", "市場環境", "高配当株", "9984 ソフトバンク"]
    for i, query in enumerate(quick_queries):
        with quick_cols[i]:
            if st.button(query, key=f"quick_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()

# チャット履歴の表示
for msg in st.session_state.messages:
    timestamp = msg.get("time", "")
    if msg["role"] == "user":
        st.markdown(f'''
        <div class="message">
            <div class="message-avatar avatar-user">👤</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">あなた</span>
                    <span class="message-time">{timestamp}</span>
                </div>
                <div class="message-bubble bubble-user">{msg["content"]}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
        <div class="message">
            <div class="message-avatar avatar-ai">🤖</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">AI</span>
                    <span class="message-time">{timestamp}</span>
                </div>
                <div class="message-bubble bubble-ai">{msg["content"]}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# 入力エリア用スペーサー
st.markdown('<div style="height: 80px;"></div>', unsafe_allow_html=True)

# 入力フォーム
col1, col2 = st.columns([6, 1])
with col1:
    user_input = st.text_area(
        "質問",
        placeholder="銘柄コード（例: 7203）や質問を入力...",
        height=50,
        label_visibility="collapsed",
        key="user_input"
    )
with col2:
    send_button = st.button("送信", type="primary", use_container_width=True, key="send_btn")


# 銘柄選択セッション状態
if "pending_candidates" not in st.session_state:
    st.session_state.pending_candidates = []

# 候補選択ボタンの処理
if st.session_state.pending_candidates:
    st.markdown("**該当する銘柄を選択してください：**")
    cols = st.columns(len(st.session_state.pending_candidates))
    for i, (ticker, name) in enumerate(st.session_state.pending_candidates):
        with cols[i]:
            if st.button(f"{ticker}\n{name[:10]}", key=f"cand_{ticker}", use_container_width=True):
                # 選択された銘柄でメッセージを追加
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"{ticker} {name}",
                    "time": datetime.now().strftime("%H:%M")
                })
                st.session_state.pending_candidates = []
                st.rerun()

# 送信処理
if send_button and user_input and not st.session_state.processing:
    st.session_state.processing = True
    current_time = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": user_input, "time": current_time})

    with st.spinner("分析中..."):
        try:
            from modules.ai_agent import StockResearchAgent
            from modules.news import NewsAnalyzer
            from modules.alpha import AlphaFinder
            agent = StockResearchAgent()

            # 銘柄コードの抽出
            ticker = extract_ticker(user_input)

            # 銘柄コードがない場合、企業名で検索
            if not ticker:
                # 企業名らしきキーワードを抽出（日本語のみ or 英数字含む単語）
                company_keywords = re.findall(r'[ァ-ヶー一-龯a-zA-Z]+', user_input)
                if company_keywords:
                    search_term = max(company_keywords, key=len)  # 最長のキーワード
                    candidates = search_company_by_name(search_term)

                    if len(candidates) == 1:
                        # 1件のみ → そのまま使用
                        ticker = candidates[0][0]
                    elif len(candidates) > 1:
                        # 複数候補 → ユーザーに選択を求める
                        response_time = datetime.now().strftime("%H:%M")
                        candidate_msg = f"「{search_term}」に該当する銘柄が複数見つかりました。\n\n"
                        for t, n in candidates:
                            candidate_msg += f"• **{t}** - {n}\n"
                        candidate_msg += "\n銘柄コードを含めて再度質問してください。\n例: 「{} について分析して」".format(candidates[0][0])

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": candidate_msg,
                            "time": response_time
                        })
                        st.session_state.pending_candidates = candidates[:4]
                        st.session_state.processing = False
                        st.rerun()

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

            # デバッグ: 取得したコンテキストを表示（開発用）
            if context_data:
                with st.expander("取得データ（デバッグ用）", expanded=False):
                    st.text(context_data[:2000] if len(context_data) > 2000 else context_data)

            # AIレスポンス生成
            response_container = st.empty()
            full_response = ""

            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            # データ有無を明示
            has_data = bool(context_data.strip())

            prompt = ChatPromptTemplate.from_template("""あなたは日本株専門のAIアナリストです。

【最重要ルール - 必ず守ること】
- 提供されたデータのみを使用して回答すること
- データにない情報は「データがありません」と正直に回答すること
- 数値（PER、PBR、株価、成長率等）を推測・創作しないこと
- 知らない企業について詳細を語らないこと

{context}

ユーザーの質問: {question}

【回答ガイドライン】
- 上記のコンテキストに含まれる情報のみを使用
- データがない項目は「不明」「データなし」と明記
- 簡潔で読みやすい形式
- 日本語で回答

回答:""")

            chain = prompt | agent.llm | StrOutputParser()

            # コンテキストがない場合はLLMを使わず固定メッセージ
            if not has_data:
                full_response = """申し訳ございません。この銘柄のデータを取得できませんでした。

**考えられる原因:**
- 銘柄コード（4桁の数字）が入力されていない
- 銘柄コードが正しくない
- データソースに接続できない

**ご利用方法:**
銘柄コードを含めて質問してください。
例: 「7203 トヨタ」「9984 ソフトバンクG」

※企業名のみでの検索は現在対応していません。"""
                response_container.markdown(f'''
                <div class="message">
                    <div class="message-avatar avatar-ai">🤖</div>
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-sender">AI</span>
                        </div>
                        <div class="message-bubble bubble-ai">{full_response}</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                for chunk in chain.stream({
                    "context": context_data,
                    "question": user_input
                }):
                    full_response += chunk
                    response_container.markdown(f'''
                    <div class="message">
                        <div class="message-avatar avatar-ai">🤖</div>
                        <div class="message-content">
                            <div class="message-header">
                                <span class="message-sender">AI</span>
                            </div>
                            <div class="message-bubble bubble-ai">{full_response}</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)

            response_time = datetime.now().strftime("%H:%M")
            st.session_state.messages.append({"role": "assistant", "content": full_response, "time": response_time})

        except Exception as e:
            error_time = datetime.now().strftime("%H:%M")
            error_msg = f"エラーが発生しました: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_msg, "time": error_time})

    st.session_state.processing = False
    st.rerun()
