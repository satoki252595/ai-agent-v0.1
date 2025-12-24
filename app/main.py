# -*- coding: utf-8 -*-
"""
日本株リサーチAIエージェント
Japan Stock Research AI Agent

プロ投資家向け総合分析プラットフォーム
- テクニカル分析
- ファンダメンタルズ分析
- マクロ経済分析
- 特許情報収集
- アルファ発見
- AIレポート生成
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# モジュールパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OLLAMA_URL, MODEL_NAME, WATCHLIST_DEFAULT, SECTORS
from modules.stock_data import StockDataFetcher
from modules.technical import TechnicalAnalyzer
from modules.fundamental import FundamentalAnalyzer
from modules.macro import MacroAnalyzer
from modules.patent import PatentResearcher
from modules.alpha import AlphaFinder
from modules.news import NewsAnalyzer
from modules.ai_agent import StockResearchAgent
from utils.helpers import format_ticker, parse_ticker, format_number, format_percentage, format_currency

# --- ページ設定 ---
st.set_page_config(
    page_title="日本株リサーチAI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- カスタムCSS ---
st.markdown("""
<style>
    /* ダークテーマ */
    .stApp {
        background-color: #0e1117 !important;
        color: #fafafa !important;
    }

    /* サイドバー */
    [data-testid="stSidebar"] {
        background-color: #1a1d24 !important;
    }

    /* メトリクスカード */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: bold !important;
    }

    /* ポジティブ/ネガティブ色 */
    .positive { color: #00d26a !important; }
    .negative { color: #ff4b4b !important; }
    .neutral { color: #ffa500 !important; }

    /* カード */
    .card {
        background-color: #1e2129;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #2d3139;
    }

    /* ヘッダー */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }

    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #667eea, #764ba2) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
    }

    /* タブ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #1e2129;
        border-radius: 8px;
        padding: 10px 20px;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #667eea, #764ba2) !important;
    }

    /* テーブル */
    .dataframe {
        background-color: #1e2129 !important;
    }

    /* 入力フィールド */
    .stTextInput > div > div > input {
        background-color: #1e2129 !important;
        color: white !important;
        border: 1px solid #3d4249 !important;
    }

    /* セレクトボックス */
    .stSelectbox > div > div {
        background-color: #1e2129 !important;
    }
</style>
""", unsafe_allow_html=True)


# --- ヘルパー関数 ---
def create_candlestick_chart(df: pd.DataFrame, title: str = "株価チャート") -> go.Figure:
    """ローソク足チャートを作成"""
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='価格'
    ))

    # 移動平均線を追加
    if len(df) >= 25:
        sma_25 = df['close'].rolling(25).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma_25, name='SMA25', line=dict(color='orange', width=1)))

    if len(df) >= 75:
        sma_75 = df['close'].rolling(75).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma_75, name='SMA75', line=dict(color='blue', width=1)))

    fig.update_layout(
        title=title,
        yaxis_title='株価',
        xaxis_title='日付',
        template='plotly_dark',
        height=500,
        xaxis_rangeslider_visible=False
    )

    return fig


def create_technical_gauge(score: float, title: str) -> go.Figure:
    """テクニカルスコアのゲージチャート"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text': title},
        gauge={
            'axis': {'range': [-100, 100]},
            'bar': {'color': "#667eea"},
            'steps': [
                {'range': [-100, -50], 'color': "#ff4b4b"},
                {'range': [-50, 0], 'color': "#ffa500"},
                {'range': [0, 50], 'color': "#90EE90"},
                {'range': [50, 100], 'color': "#00d26a"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))

    fig.update_layout(
        template='plotly_dark',
        height=250
    )

    return fig


def display_metric_card(label: str, value: str, delta: str = None, delta_color: str = "normal"):
    """メトリクスカードを表示"""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


# --- サイドバー ---
with st.sidebar:
    st.markdown("## 📈 日本株リサーチAI")
    st.markdown("---")

    # 機能選択
    page = st.radio(
        "機能を選択",
        ["🏠 ダッシュボード", "📊 個別銘柄分析", "🔍 スクリーニング",
         "🌍 マクロ分析", "📰 ニュース", "🔬 特許分析", "🤖 AIリサーチ"],
        index=0
    )

    st.markdown("---")

    # 銘柄入力（共通）
    ticker_input = st.text_input(
        "銘柄コード",
        value="7203",
        help="4桁の証券コードを入力（例: 7203 = トヨタ）"
    )

    # ウォッチリスト
    st.markdown("### 📌 ウォッチリスト")
    selected_watchlist = st.multiselect(
        "監視銘柄",
        options=WATCHLIST_DEFAULT,
        default=WATCHLIST_DEFAULT[:5]
    )

    st.markdown("---")
    st.markdown("### ⚙️ 設定")
    analysis_period = st.selectbox(
        "分析期間",
        ["1mo", "3mo", "6mo", "1y", "2y"],
        index=3
    )


# --- メインコンテンツ ---

# 初期化
fetcher = StockDataFetcher()
macro_analyzer = MacroAnalyzer()
alpha_finder = AlphaFinder()
news_analyzer = NewsAnalyzer()
patent_researcher = PatentResearcher()
agent = StockResearchAgent()


# ==================== ダッシュボード ====================
if page == "🏠 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📈 日本株リサーチAI ダッシュボード</h1></div>', unsafe_allow_html=True)

    # マーケットサマリー
    st.markdown("### 🌍 マーケットサマリー")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        indices = macro_analyzer.get_global_indices()
        if "nikkei225" in indices:
            nk = indices["nikkei225"]
            st.metric(
                "日経平均",
                f"¥{nk['value']:,.0f}",
                f"{nk['change_pct']:.2f}%",
                delta_color="normal" if nk['change_pct'] >= 0 else "inverse"
            )

    with col2:
        if "topix" in indices:
            tp = indices["topix"]
            st.metric(
                "TOPIX",
                f"{tp['value']:,.2f}",
                f"{tp['change_pct']:.2f}%",
                delta_color="normal" if tp['change_pct'] >= 0 else "inverse"
            )

    with col3:
        forex = macro_analyzer.get_forex_rates()
        if "usdjpy" in forex:
            usd = forex["usdjpy"]
            st.metric(
                "USD/JPY",
                f"¥{usd['rate']:.2f}",
                f"{usd['change_pct']:.2f}%",
                delta_color="inverse" if usd['change_pct'] >= 0 else "normal"
            )

    with col4:
        vix = macro_analyzer.get_volatility_indices()
        if "vix" in vix:
            v = vix["vix"]
            st.metric(
                "VIX",
                f"{v['value']:.2f}",
                v['status']
            )

    st.markdown("---")

    # 市場レジーム
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 📊 市場レジーム")
        regime = macro_analyzer.get_market_regime()
        st.info(f"**{regime['regime']}**")
        st.write(f"リスクレベル: **{regime['risk_level']}**")

        rotation = macro_analyzer.get_sector_rotation_signal()
        st.markdown("#### 推奨セクター")
        for sector in rotation['recommended_sectors'][:3]:
            st.write(f"✅ {sector}")

    with col2:
        st.markdown("### 🚀 アルファシグナル")
        with st.spinner("スクリーニング中..."):
            top_alpha = alpha_finder.get_top_alpha_stocks(5)
            if top_alpha:
                alpha_df = pd.DataFrame([
                    {
                        "銘柄": s.ticker,
                        "シグナル": s.signal_type,
                        "スコア": s.strength,
                        "説明": s.description[:30] + "..."
                    }
                    for s in top_alpha
                ])
                st.dataframe(alpha_df, use_container_width=True)

    st.markdown("---")

    # ウォッチリスト
    st.markdown("### 📌 ウォッチリスト")
    if selected_watchlist:
        watch_data = []
        for ticker in selected_watchlist:
            info = fetcher.get_stock_info(ticker)
            if "error" not in info:
                watch_data.append({
                    "銘柄コード": ticker,
                    "企業名": info.get("name", "")[:15],
                    "株価": f"¥{info.get('current_price', 0):,.0f}",
                    "PER": f"{info.get('pe_ratio', 0):.1f}" if info.get('pe_ratio') else "N/A",
                    "PBR": f"{info.get('pb_ratio', 0):.2f}" if info.get('pb_ratio') else "N/A",
                    "配当利回り": f"{info.get('dividend_yield', 0)*100:.2f}%" if info.get('dividend_yield') else "N/A"
                })

        if watch_data:
            st.dataframe(pd.DataFrame(watch_data), use_container_width=True)


# ==================== 個別銘柄分析 ====================
elif page == "📊 個別銘柄分析":
    st.markdown(f"## 📊 個別銘柄分析: {ticker_input}")

    if st.button("🔍 分析開始", type="primary"):
        with st.spinner("データ取得中..."):
            # 株価情報取得
            info = fetcher.get_stock_info(ticker_input)
            hist = fetcher.get_historical_data(ticker_input, analysis_period)

            if "error" in info or hist.empty:
                st.error("データの取得に失敗しました。銘柄コードを確認してください。")
            else:
                company_name = info.get("name", ticker_input)

                # ヘッダー情報
                st.markdown(f"### {company_name}（{ticker_input}）")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    current = info.get('current_price', 0)
                    prev = info.get('previous_close', 0)
                    change_pct = ((current - prev) / prev * 100) if prev else 0
                    st.metric("現在株価", f"¥{current:,.0f}", f"{change_pct:.2f}%")
                with col2:
                    st.metric("時価総額", format_currency(info.get('market_cap', 0)))
                with col3:
                    st.metric("PER", f"{info.get('pe_ratio', 0):.1f}" if info.get('pe_ratio') else "N/A")
                with col4:
                    st.metric("配当利回り", f"{info.get('dividend_yield', 0)*100:.2f}%" if info.get('dividend_yield') else "N/A")

                # タブで分析結果を表示
                tab1, tab2, tab3, tab4 = st.tabs(["📈 チャート", "📊 テクニカル", "💰 ファンダメンタル", "🤖 AI分析"])

                with tab1:
                    # ローソク足チャート
                    fig = create_candlestick_chart(hist, f"{company_name} 株価チャート")
                    st.plotly_chart(fig, use_container_width=True)

                    # 出来高チャート
                    fig_vol = px.bar(hist, x=hist.index, y='volume', title='出来高')
                    fig_vol.update_layout(template='plotly_dark', height=200)
                    st.plotly_chart(fig_vol, use_container_width=True)

                with tab2:
                    # テクニカル分析
                    ta = TechnicalAnalyzer(hist)
                    trend = ta.get_trend_summary()

                    col1, col2 = st.columns([1, 2])
                    with col1:
                        fig_gauge = create_technical_gauge(trend['score'], "テクニカルスコア")
                        st.plotly_chart(fig_gauge, use_container_width=True)
                        st.markdown(f"**総合シグナル: {trend['overall_signal']}**")

                    with col2:
                        st.markdown("#### シグナル一覧")
                        for signal in trend['signals']:
                            color = "🟢" if signal.signal == "買い" else "🔴" if signal.signal == "売り" else "🟡"
                            st.write(f"{color} **{signal.indicator}**: {signal.signal} ({signal.description})")

                    # RSIチャート
                    rsi = ta.rsi()
                    fig_rsi = go.Figure()
                    fig_rsi.add_trace(go.Scatter(x=rsi.index, y=rsi, name='RSI', line=dict(color='purple')))
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
                    fig_rsi.update_layout(title='RSI (14)', template='plotly_dark', height=250)
                    st.plotly_chart(fig_rsi, use_container_width=True)

                with tab3:
                    # ファンダメンタルズ分析
                    fa = FundamentalAnalyzer(ticker_input)
                    summary = fa.get_analysis_summary()

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("#### バリュエーション")
                        val = summary.get('valuation', {})
                        st.write(f"- PER: **{val.get('per', 'N/A')}**")
                        st.write(f"- PBR: **{val.get('pbr', 'N/A')}**")
                        st.write(f"- PSR: **{val.get('psr', 'N/A')}**")
                        st.write(f"- EV/EBITDA: **{val.get('ev_ebitda', 'N/A')}**")

                        st.markdown("#### 収益性")
                        prof = summary.get('profitability', {})
                        st.write(f"- ROE: **{format_percentage(prof.get('roe'))}**")
                        st.write(f"- ROA: **{format_percentage(prof.get('roa'))}**")
                        st.write(f"- 営業利益率: **{format_percentage(prof.get('operating_margin'))}**")

                    with col2:
                        st.markdown("#### ファンダメンタルスコア")
                        score = summary.get('fundamental_score', 0)
                        grade = summary.get('fundamental_grade', 'N/A')

                        fig_fund = go.Figure(go.Indicator(
                            mode="gauge+number+delta",
                            value=score,
                            title={'text': f"総合スコア (グレード: {grade})"},
                            gauge={
                                'axis': {'range': [0, 100]},
                                'bar': {'color': "#667eea"},
                                'steps': [
                                    {'range': [0, 40], 'color': "#ff4b4b"},
                                    {'range': [40, 60], 'color': "#ffa500"},
                                    {'range': [60, 80], 'color': "#90EE90"},
                                    {'range': [80, 100], 'color': "#00d26a"}
                                ]
                            }
                        ))
                        fig_fund.update_layout(template='plotly_dark', height=250)
                        st.plotly_chart(fig_fund, use_container_width=True)

                        st.markdown("#### 財務健全性")
                        health = summary.get('financial_health', {})
                        st.write(f"- 自己資本比率: **{format_percentage(health.get('current_ratio'))}**")
                        st.write(f"- D/E比率: **{health.get('debt_to_equity', 'N/A')}**")

                with tab4:
                    # AI分析レポート生成
                    st.markdown("#### 🤖 AIによる総合分析レポート")

                    if st.button("📝 レポート生成", key="generate_report"):
                        with st.spinner("AI分析中..."):
                            # データ収集
                            ta = TechnicalAnalyzer(hist)
                            technical_data = ta.get_trend_summary()

                            fa = FundamentalAnalyzer(ticker_input)
                            fundamental_data = fa.get_analysis_summary()

                            macro_data = macro_analyzer.get_macro_summary()

                            news_data = news_analyzer.analyze_company_sentiment(ticker_input, company_name)

                            patent_data = patent_researcher.analyze_patent_portfolio(company_name)

                            alpha_signal = alpha_finder.calculate_alpha_score(ticker_input)

                            # レポート生成（ストリーミング）
                            report_container = st.empty()
                            full_report = ""

                            for chunk in agent.generate_stock_report(
                                ticker_input,
                                company_name,
                                technical_data,
                                fundamental_data,
                                macro_data,
                                news_data,
                                patent_data,
                                {"signal_type": alpha_signal.signal_type, "strength": alpha_signal.strength, "description": alpha_signal.description}
                            ):
                                full_report += chunk
                                report_container.markdown(full_report)


# ==================== スクリーニング ====================
elif page == "🔍 スクリーニング":
    st.markdown("## 🔍 スクリーニング")

    screening_type = st.selectbox(
        "スクリーニングタイプ",
        ["バリュー株", "グロース株", "クオリティ株", "モメンタム株", "売られすぎ銘柄", "ブレイクアウト候補"]
    )

    if st.button("🔍 スクリーニング実行", type="primary"):
        with st.spinner("スクリーニング中..."):
            if screening_type == "バリュー株":
                df = alpha_finder.screen_value_stocks()
                if not df.empty:
                    st.markdown("### バリュー株（割安銘柄）")
                    st.dataframe(df[['ticker', 'name', 'per', 'pbr', 'dividend_yield', 'value_score']].head(20), use_container_width=True)

            elif screening_type == "グロース株":
                df = alpha_finder.screen_growth_stocks()
                if not df.empty:
                    st.markdown("### グロース株（成長銘柄）")
                    st.dataframe(df[['ticker', 'name', 'revenue_growth', 'earnings_growth', 'roe', 'growth_score']].head(20), use_container_width=True)

            elif screening_type == "クオリティ株":
                df = alpha_finder.screen_quality_stocks()
                if not df.empty:
                    st.markdown("### クオリティ株（優良銘柄）")
                    st.dataframe(df[['ticker', 'name', 'roe', 'operating_margin', 'debt_to_equity', 'quality_score']].head(20), use_container_width=True)

            elif screening_type == "モメンタム株":
                df = alpha_finder.screen_momentum_stocks()
                if not df.empty:
                    st.markdown("### モメンタム株（上昇トレンド）")
                    st.dataframe(df[['ticker', 'return_1m', 'return_3m', 'rsi', 'momentum_score']].head(20), use_container_width=True)

            elif screening_type == "売られすぎ銘柄":
                df = alpha_finder.find_oversold_stocks()
                if not df.empty:
                    st.markdown("### 売られすぎ銘柄（逆張り候補）")
                    st.dataframe(df[['ticker', 'name', 'rsi', 'drawdown_from_52w_high', 'oversold_score']].head(20), use_container_width=True)

            elif screening_type == "ブレイクアウト候補":
                df = alpha_finder.find_breakout_candidates()
                if not df.empty:
                    st.markdown("### ブレイクアウト候補")
                    st.dataframe(df[['ticker', 'price', 'resistance', 'breakout_pct', 'volume_ratio', 'signal']].head(20), use_container_width=True)


# ==================== マクロ分析 ====================
elif page == "🌍 マクロ分析":
    st.markdown("## 🌍 マクロ経済分析")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📈 グローバル株価指数")
        indices = macro_analyzer.get_global_indices()
        indices_data = []
        for name, data in indices.items():
            indices_data.append({
                "指数": name,
                "価格": f"{data['value']:,.2f}",
                "変動": f"{data['change_pct']:.2f}%"
            })
        st.dataframe(pd.DataFrame(indices_data), use_container_width=True)

    with col2:
        st.markdown("### 💱 為替レート")
        forex = macro_analyzer.get_forex_rates()
        forex_data = []
        for pair, data in forex.items():
            forex_data.append({
                "通貨ペア": pair.upper(),
                "レート": f"{data['rate']:.2f}",
                "変動": f"{data['change_pct']:.2f}%"
            })
        st.dataframe(pd.DataFrame(forex_data), use_container_width=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🛢️ コモディティ")
        commodities = macro_analyzer.get_commodity_prices()
        comm_data = []
        for name, data in commodities.items():
            comm_data.append({
                "商品": name,
                "価格": f"${data['price']:.2f}",
                "変動": f"{data['change_pct']:.2f}%"
            })
        st.dataframe(pd.DataFrame(comm_data), use_container_width=True)

    with col2:
        st.markdown("### 📊 市場レジーム")
        regime = macro_analyzer.get_market_regime()
        st.info(f"**現在のレジーム:** {regime['regime']}")
        st.write(f"**リスクレベル:** {regime['risk_level']}")
        st.write(f"**VIX:** {regime['vix']['current']:.1f} ({regime['vix']['status']})")
        st.write(f"**日経トレンド:** {regime['nikkei']['trend']} ({regime['nikkei']['return_3m']:.1f}%)")
        st.write(f"**為替トレンド:** {regime['forex']['trend']}")

    st.markdown("---")

    st.markdown("### 🔄 セクターローテーション")
    rotation = macro_analyzer.get_sector_rotation_signal()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ✅ 推奨セクター")
        for sector in rotation['recommended_sectors']:
            st.write(f"• {sector}")
    with col2:
        st.markdown("#### ⚠️ 回避セクター")
        for sector in rotation['sectors_to_avoid']:
            st.write(f"• {sector}")

    st.info(f"**理由:** {rotation['reason']}")


# ==================== ニュース ====================
elif page == "📰 ニュース":
    st.markdown("## 📰 ニュース・センチメント分析")

    company_name = st.text_input("企業名を入力", value="トヨタ自動車")

    if st.button("📰 ニュース取得", type="primary"):
        with st.spinner("ニュース収集中..."):
            analysis = news_analyzer.analyze_company_sentiment(ticker_input, company_name)

            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown("### センチメント")
                score = analysis['sentiment_score']
                sentiment = analysis['overall_sentiment']

                color = "#00d26a" if sentiment == "ポジティブ" else "#ff4b4b" if sentiment == "ネガティブ" else "#ffa500"
                st.markdown(f"<h1 style='color:{color};'>{sentiment}</h1>", unsafe_allow_html=True)
                st.metric("スコア", f"{score:.1f}/100")
                st.write(f"ポジティブ: {analysis['positive_count']}件")
                st.write(f"ネガティブ: {analysis['negative_count']}件")
                st.write(f"中立: {analysis['neutral_count']}件")

            with col2:
                st.markdown("### 最新ニュース")
                for news in analysis['all_news'][:10]:
                    sentiment_icon = "🟢" if news['sentiment'] == "ポジティブ" else "🔴" if news['sentiment'] == "ネガティブ" else "🟡"
                    st.markdown(f"{sentiment_icon} **{news['title']}**")
                    st.caption(f"{news['source']} | [リンク]({news['url']})")
                    st.markdown("---")


# ==================== 特許分析 ====================
elif page == "🔬 特許分析":
    st.markdown("## 🔬 特許・技術力分析")

    company_name = st.text_input("企業名を入力", value="ソニー")

    if st.button("🔬 特許分析開始", type="primary"):
        with st.spinner("特許情報収集中..."):
            analysis = patent_researcher.analyze_tech_innovation(ticker_input, company_name)

            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown("### 技術力評価")
                st.metric("技術スコア", f"{analysis['innovation_score']}/100")
                st.metric("グレード", analysis['innovation_grade'])
                st.info(analysis['assessment'])

            with col2:
                st.markdown("### 技術分野")
                tech_areas = analysis['portfolio'].get('technology_areas', {})
                if tech_areas:
                    fig = px.bar(
                        x=list(tech_areas.values()),
                        y=list(tech_areas.keys()),
                        orientation='h',
                        title='技術分野分布'
                    )
                    fig.update_layout(template='plotly_dark', height=300)
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            st.markdown("### 📄 発見された特許")
            for patent in analysis['portfolio'].get('patents', [])[:10]:
                st.markdown(f"**{patent.get('title', '')}**")
                st.caption(f"[詳細]({patent.get('url', '')})")
                st.write(patent.get('snippet', '')[:200])
                st.markdown("---")


# ==================== AIリサーチ ====================
elif page == "🤖 AIリサーチ":
    st.markdown("## 🤖 自律型AIリサーチエージェント")

    st.markdown("""
    <div style="background-color: #1e2129; padding: 15px; border-radius: 10px; border-left: 5px solid #667eea; margin-bottom: 20px;">
        <strong>💡 使い方:</strong> 調査したいテーマを自由に入力してください。<br>
        例：「半導体セクターの今後の見通しと注目銘柄」「日銀の金融政策が自動車株に与える影響」
    </div>
    """, unsafe_allow_html=True)

    research_topic = st.text_area(
        "リサーチテーマを入力",
        height=100,
        placeholder="例: 2024年に業績が伸びそうなAI関連銘柄を分析してください"
    )

    if st.button("🚀 リサーチ開始", type="primary"):
        if not research_topic:
            st.warning("リサーチテーマを入力してください")
        else:
            with st.status("🔍 AIエージェント起動...", expanded=True) as status:
                # リサーチ実行
                research_result = agent.research_topic(research_topic, status)

                status.update(label="📝 レポート生成中...", state="running")

                # レポート生成
                report_container = st.empty()
                full_report = ""

                prompt_data = f"""
リサーチテーマ: {research_topic}

収集した情報:
{research_result['notes']}

上記の情報を元に、投資家向けの詳細なレポートを作成してください。
- エグゼクティブサマリー
- 調査結果の詳細
- 投資への示唆
- リスク要因

日本語で出力してください。
"""

                from langchain_core.prompts import ChatPromptTemplate
                from langchain_core.output_parsers import StrOutputParser

                report_prompt = ChatPromptTemplate.from_template("""
{input}
""")
                chain = report_prompt | agent.llm | StrOutputParser()

                for chunk in chain.stream({"input": prompt_data}):
                    full_report += chunk
                    report_container.markdown(full_report)

                status.update(label="✅ リサーチ完了", state="complete")

                # 生データ表示
                with st.expander("📚 収集された調査ノート"):
                    st.text(research_result['notes'])


# --- フッター ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    📈 日本株リサーチAI | 投資判断は自己責任でお願いいたします。
</div>
""", unsafe_allow_html=True)
