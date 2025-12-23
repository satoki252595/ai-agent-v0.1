import streamlit as st
import os
import requests
import tempfile
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader

# --- 設定 & 定数 ---
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")

# --- Notion風スタイル設定 ---
st.set_page_config(
    page_title="Essence - AI Summary",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS: Notion風のダークな雰囲気とフォント調整
st.markdown("""
<style>
    .stApp {
        background-color: #191919;
        color: #e0e0e0;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #ffffff !important;
    }
    .stButton>button {
        background-color: #37352f;
        color: white;
        border: 1px solid #555;
        border-radius: 4px;
    }
    .stTextInput>div>div>input {
        background-color: #2f2f2f;
        color: white;
    }
    /* 引用ブロックのスタイル */
    blockquote {
        background-color: #2f2f2f;
        border-left: 3px solid #d44c47;
        padding: 1rem;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- プロンプトテンプレート集 ---
PROMPT_TEMPLATES = {
    "ビジネス・経営層向け (戦略・影響)": """
あなたはマッキンゼーやBCG出身の戦略コンサルタントAIです。
入力された情報を以下の観点で分析し、意思決定に役立つレポートを作成してください。

1. **エグゼクティブサマリー**: 30秒で読める要約
2. **市場・業界への影響**: この情報がビジネス環境に与えるインパクト
3. **重要数値・KPI**: 売上、成長率、コスト削減効果などの具体的な数字
4. **ネクストアクション**: 経営層が検討すべき次のステップ

文体は簡潔、断定的、論理的にしてください。
""",
    "エンジニア・技術者向け (実装・アーキテクチャ)": """
あなたはGoogleのシニアスタッフエンジニアです。
入力された技術文書や記事から、以下の技術的本質を抽出してください。

1. **アーキテクチャの要点**: 採用されている技術スタック、設計思想
2. **解決された課題**: どのような技術的負債やボトルネックが解消されたか
3. **トレードオフ**: メリットの裏にあるデメリットや制約事項
4. **コード/実装のヒント**: 実装時に注意すべき具体的なポイント

文体は技術用語を正確に使い、箇条書きで構造化してください。
""",
    "研究者・アカデミア向け (手法・新規性)": """
あなたはトップジャーナルの査読者（Reviewer）です。
入力された論文やレポートを以下の学術的観点で分析してください。

1. **リサーチクエスチョン**: 何を解決しようとしているのか
2. **提案手法の新規性**: 既存研究との決定的な違い（Novelty）
3. **検証結果と限界**: 実験結果の妥当性と、残された課題（Limitation）
4. **分野への貢献**: この知見が学術界に与える示唆

文体はアカデミックかつ客観的にしてください。
""",
    "汎用・詳細要約 (Deep Dive)": """
あなたは優秀な要約編集者です。
入力された情報を、誰が読んでも理解できるように詳細に構造化してください。

- 専門用語には簡単な補足を入れること
- 抽象的な概念は具体例に落とし込むこと
- 重要な事実は漏らさず列挙すること
"""
}

# --- ロジック関数群 ---

def get_pdf_text_from_url(url):
    """URLからPDFをダウンロードしてテキスト化"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name

        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        text = "\n".join([p.page_content for p in pages])
        
        os.remove(tmp_path)
        return text
    except Exception as e:
        return f"PDF取得エラー: {e}"

def get_content_from_url(url):
    """URLのコンテンツタイプを判定してテキスト化"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # HEADリクエストでContent-Type確認
        try:
            head_resp = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            content_type = head_resp.headers.get('Content-Type', '').lower()
        except:
            content_type = ''

        # PDF判定
        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            st.toast("📄 PDFを検出しました", icon="ℹ️")
            return get_pdf_text_from_url(url), "PDF Document"

        # HTML判定
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        if 'application/pdf' in resp.headers.get('Content-Type', '').lower():
             st.toast("📄 PDFを検出しました(Redirect)", icon="ℹ️")
             return get_pdf_text_from_url(url), "PDF Document"

        soup = BeautifulSoup(resp.content, 'html.parser')
        for tag in soup(['nav', 'header', 'footer', 'script', 'style', 'aside', 'form', 'noscript']):
            tag.decompose()

        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
        if not main_content:
            return "", "Unknown"

        text = main_content.get_text(separator="\n", strip=True)
        return text, soup.title.string if soup.title else "No Title"

    except Exception as e:
        return f"エラー: {e}", "Error"

def process_uploaded_pdf(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        text = "\n".join([p.page_content for p in pages])
        os.remove(tmp_path)
        return text
    except Exception as e:
        return f"エラー: {e}"

# --- サイドバー設定 ---
with st.sidebar:
    st.title("✨ Essence")
    st.caption("Context-Aware AI Summarizer")
    
    st.markdown("---")
    
    # 1. 入力ソース
    input_mode = st.radio("Input Source", ["Web URL / PDF URL", "PDF Upload"], label_visibility="collapsed")
    
    st.markdown("---")
    
    # 2. プロンプト選択
    st.subheader("🛠 Settings")
    selected_template_name = st.selectbox(
        "Target Persona",
        options=list(PROMPT_TEMPLATES.keys()),
        index=0
    )
    
    # プロンプト編集エリア（デフォルト値をセット）
    user_system_prompt = st.text_area(
        "Custom Instructions",
        value=PROMPT_TEMPLATES[selected_template_name],
        height=200,
        help="AIへの指示を自由にカスタマイズできます"
    )

# --- メインエリア ---

st.title("Essence")
st.markdown("#### 本質を、抽出する。")

target_text = ""
source_title = ""

# 入力UI
if input_mode == "Web URL / PDF URL":
    url_input = st.text_input("", placeholder="https://example.com/article_or_report.pdf", label_visibility="collapsed")
    if url_input and st.button("Analyze", type="primary"):
        with st.spinner("Fetching content..."):
            target_text, source_title = get_content_from_url(url_input)

elif input_mode == "PDF Upload":
    uploaded_file = st.file_uploader("", type=["pdf"], label_visibility="collapsed")
    if uploaded_file and st.button("Analyze", type="primary"):
        with st.spinner("Reading PDF..."):
            target_text = process_uploaded_pdf(uploaded_file)
            source_title = uploaded_file.name

# AI解析実行
if target_text:
    # エラー判定
    if target_text.startswith("エラー") or target_text.startswith("PDF取得エラー"):
        st.error(target_text)
    else:
        # 文字数制限と警告
        if len(target_text) > 25000:
            st.warning(f"⚠️ テキストが長大です（{len(target_text)}文字）。精度維持のため先頭25,000文字を分析対象とします。")
            target_text = target_text[:25000]

        # LLM設定
        llm = ChatOllama(
            model=MODEL_NAME,
            base_url=OLLAMA_URL,
            temperature=0.3, # 分析の精度重視
            headers={"ngrok-skip-browser-warning": "true"},
            keep_alive="5m"
        )

        # 最終的なプロンプトの組み立て
        # Chain of Thought (思考の連鎖) を促す指示を追加
        final_prompt_template = f"""
        {user_system_prompt}
        
        ---
        【以下の手順で処理を実行してください】
        1. まず、入力テキスト全体を読み、文脈と構造を理解する。
        2. 重要なキーワード、数値、主張を抽出する。
        3. 上記の「ターゲットペルソナ」の視点で、情報を再構成する。
        4. 以下の形式のMarkdownで出力する。

        # (ここに内容に基づいた魅力的なタイトル)
        
        ## 💡 Essence (本質的要約)
        (ここに核心となる要約を記述)

        ## 🏷️ Tags
        (関連するキーワードをハッシュタグ形式で5つ #AI #Tech 等)

        ---
        
        (以下、ペルソナごとの要求項目を出力)

        ---
        
        【入力テキスト】
        {{content}}
        """

        prompt = ChatPromptTemplate.from_template(final_prompt_template)
        chain = prompt | llm | StrOutputParser()

        st.markdown("---")
        st.subheader("Result")
        
        # ストリーミング表示
        result_container = st.empty()
        full_response = ""
        
        try:
            for chunk in chain.stream({"content": target_text}):
                full_response += chunk
                result_container.markdown(full_response)
            
            # 完了後のアクションエリア
            st.markdown("---")
            col1, col2 = st.columns([1, 4])
            with col1:
                st.success("Analysis Complete")
            with col2:
                # コピー用のコードブロック（Notion貼り付け用）
                st.expander("Copy Markdown Source").code(full_response, language="markdown")
                
        except Exception as e:
            st.error(f"AI Processing Error: {e}")
