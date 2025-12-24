import streamlit as st
import os
import re
import time
from urllib.parse import urljoin
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader

# --- 新規ライブラリ ---
import trafilatura
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from duckduckgo_search import DDGS

# --- 設定 ---
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")

st.set_page_config(
    page_title="要約くん Deep Research",
    page_icon="🕵️‍♂️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- UI/UX: デザイン設定 ---
st.markdown("""
<style>
    /* 全体テーマ */
    .stApp { background-color: #121212 !important; color: #e0e0e0 !important; font-family: 'Hiragino Kaku Gothic ProN', sans-serif !important; }
    
    /* 入力欄 */
    .stTextArea > div > div > textarea {
        background-color: #1e1e1e !important; color: white !important; border: 1px solid #444 !important; border-radius: 12px;
    }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #d946ef, #8b5cf6) !important; /* Agentっぽい紫グラデーション */
        color: white !important; border: none !important; font-weight: bold !important; padding: 16px; border-radius: 12px;
    }
    
    /* テーブル */
    [data-testid="stMarkdownContainer"] table { display: block; overflow-x: auto; white-space: nowrap; border-collapse: collapse; border: 1px solid #333; margin: 20px 0; }
    [data-testid="stMarkdownContainer"] th { background-color: #2d2d2d !important; color: #fff; padding: 10px; border-bottom: 2px solid #555; }
    [data-testid="stMarkdownContainer"] td { padding: 10px; border-bottom: 1px solid #333; background-color: #1e1e1e; }

    /* ステータス表示 */
    .stStatusWidget { background-color: #1e1e1e !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)

# --- ツール関数: 検索と取得 ---

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def search_web(query, max_results=3):
    """DuckDuckGoでWeb検索を行う"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region='jp-jp', safesearch='off', max_results=max_results))
        return results # [{'title':..., 'href':..., 'body':...}, ...]
    except Exception as e:
        print(f"Search Error: {e}")
        return []

def clean_text(text):
    if not text: return ""
    text = text.replace('\x00', '')
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def fetch_content(url):
    """URLから本文を抽出 (Trafilatura)"""
    try:
        if url.lower().endswith('.pdf'):
            return "PDFファイルのためスキップしました（現在はWebページのみ対応）"
        
        downloaded = trafilatura.downloads.fetch_url(url)
        if downloaded is None: return ""
        
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        return clean_text(text) if text else ""
    except Exception:
        return ""

# --- エージェント思考ロジック ---

def get_llm():
    return ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.3,
        headers={"ngrok-skip-browser-warning": "true"},
        keep_alive="5m"
    )

def plan_research(topic):
    """【計画】ユーザーのトピックから検索クエリリストを作成"""
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
    あなたはプロのリサーチャーです。
    ユーザーの依頼：「{topic}」
    
    この依頼を達成するために必要な情報を集めるための「Web検索クエリ」を3つ考えてください。
    
    出力形式:
    - クエリ1
    - クエリ2
    - クエリ3
    (余計な説明は不要。クエリのみを箇条書きで出力)
    """)
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"topic": topic})
    queries = [line.strip("- ").strip() for line in response.split("\n") if line.strip()]
    return queries[:3] # 最大3つ

def analyze_findings(topic, current_notes):
    """【修正】集まった情報を分析し、不足情報を特定する"""
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
    現在の調査テーマ：「{topic}」
    これまでの調査ノート：
    {notes}
    
    上記の情報で、ユーザーの依頼に答えるのに十分ですか？
    もし不足があれば、追加で何を検索すべきか、具体的な「追加検索クエリ」を1つだけ出力してください。
    十分であれば "SUFFICIENT" とだけ出力してください。
    """)
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"topic": topic, "notes": current_notes[:10000]})
    return response.strip()

def summarize_page(topic, url, content):
    """【読解】Webページの内容をメモ化する（コンテキスト節約）"""
    if len(content) < 200: return "" # 内容が薄すぎる場合は無視
    
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
    テーマ：「{topic}」
    
    以下のWebページの内容から、テーマに関連する重要な事実、数値、意見を抽出して、日本語の短いメモにしてください。
    無関係な部分は無視してください。
    
    Webページ内容:
    {content}
    """)
    # コンテキスト溢れ防止のためページ内容は切り詰める
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"topic": topic, "content": content[:8000]})

def write_final_report(topic, all_notes):
    """【統合】最終レポート作成"""
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
    あなたは最高峰のレポート作成AIです。
    以下の「調査ノート」を元に、ユーザーのテーマ「{topic}」に対する包括的なレポートを作成してください。

    【調査ノート】
    {notes}

    【出力形式】
    # {topic} に関する調査レポート
    
    ## 🎯 エグゼクティブサマリー
    （結論を簡潔に）
    
    ## 🔍 調査結果詳細
    （見出しを分けて構造的に記述。数値や比較はMarkdownの表を使用すること）
    
    ## 💡 考察・示唆
    （集められた情報から言えること）
    
    ※必ず日本語で出力してください。
    """)
    return prompt | llm | StrOutputParser()

# --- メインロジック ---

def run_deep_research(topic, status_container):
    all_notes = ""
    visited_urls = set()
    
    # 1. 計画フェーズ
    status_container.write("🤔 調査計画を立案中...")
    queries = plan_research(topic)
    status_container.write(f"📋 検索プラン: {queries}")
    
    # 2. 実行フェーズ (ラウンド1)
    status_container.write("🌍 Web調査を開始 (Round 1)...")
    for q in queries:
        status_container.write(f"🔎 検索中: {q}...")
        results = search_web(q, max_results=2)
        
        for res in results:
            url = res['href']
            if url in visited_urls: continue
            visited_urls.add(url)
            
            status_container.write(f"📖 読解中: {res['title']}...")
            content = fetch_content(url)
            if content:
                summary = summarize_page(topic, url, content)
                all_notes += f"\n--- Source: {res['title']} ({url}) ---\n{summary}\n"
    
    # 3. 修正フェーズ (自律判断)
    status_container.write("🧠 情報の充足度を確認中...")
    gap_analysis = analyze_findings(topic, all_notes)
    
    if "SUFFICIENT" not in gap_analysis and len(gap_analysis) < 50: # 短いクエリが返ってきた場合
        new_query = gap_analysis.replace('"', '').strip()
        status_container.write(f"🚀 追加調査が必要と判断: 「{new_query}」を調査します")
        
        results = search_web(new_query, max_results=2)
        for res in results:
            url = res['href']
            if url in visited_urls: continue
            
            status_container.write(f"📖 追加読解中: {res['title']}...")
            content = fetch_content(url)
            if content:
                summary = summarize_page(topic, url, content)
                all_notes += f"\n--- Source: {res['title']} ({url}) ---\n{summary}\n"
    else:
        status_container.write("✅ 十分な情報が集まりました。")

    # 4. 統合フェーズ
    status_container.write("✍️ 最終レポートを作成中...")
    return write_final_report(topic, all_notes), all_notes

# --- UI構築 ---

st.title("要約くん Deep Research")
st.caption("自律型AIリサーチエージェント")

st.markdown("""
<div style="background-color: #262626; padding: 15px; border-radius: 10px; border-left: 5px solid #d946ef; margin-bottom: 20px;">
    <strong>💡 使い方:</strong> URLではなく、「知りたいこと」を入力してください。<br>
    例：「最新の量子コンピュータの技術動向と、主要企業のシェアについて調べて」
</div>
""", unsafe_allow_html=True)

topic_input = st.text_area("リサーチテーマを入力", height=100, placeholder="ここに調査したいテーマを入力してください...")

if st.button("リサーチを開始 (Start Agent)"):
    if not topic_input:
        st.warning("テーマを入力してください。")
    else:
        with st.status("🚀 エージェント起動...", expanded=True) as status:
            try:
                # リサーチ実行
                report_chain, raw_notes = run_deep_research(topic_input, status)
                
                # ストリーミング出力用コンテナ
                st.markdown("---")
                output_container = st.empty()
                full_response = ""
                
                # 最終レポートの生成と表示
                for chunk in report_chain.stream({"topic": topic_input, "notes": raw_notes}):
                    full_response += chunk
                    output_container.markdown(full_response)
                
                status.update(label="リサーチ完了！", state="complete", expanded=False)
                
                # 生データの確認用
                with st.expander("📚 収集された調査ノート (Raw Data)"):
                    st.text(raw_notes)
                    
            except Exception as e:
                status.update(label="エラーが発生しました", state="error")
                st.error(f"Agent Error: {e}")
