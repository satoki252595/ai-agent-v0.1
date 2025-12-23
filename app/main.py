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

# --- Config ---
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")

st.set_page_config(
    page_title="Essence",
    page_icon="💎",
    layout="centered", # スマホでの視線移動を最小限にするためCentered
    initial_sidebar_state="collapsed"
)

# --- UI/UX: Global Styling (Dark/Glass/Table) ---
st.markdown("""
<style>
    /* 1. 全体のトーン & マナー (Deep Dark) */
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 2. テーブルのスマホ最適化 (ここが重要) */
    /* Markdown内のテーブルを検出し、横スクロール可能にする */
    [data-testid="stMarkdownContainer"] table {
        display: block;
        overflow-x: auto;
        white-space: nowrap; /* 折返しを防ぎ、表の形を維持 */
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
        border-radius: 8px;
        border: 1px solid #333;
    }
    
    /* テーブルのデザイン (Notion/GitHub風) */
    [data-testid="stMarkdownContainer"] th {
        background-color: #2d2d2d;
        color: #ffffff;
        padding: 12px 15px;
        text-align: left;
        border-bottom: 2px solid #444;
        font-weight: 600;
    }
    [data-testid="stMarkdownContainer"] td {
        padding: 10px 15px;
        border-bottom: 1px solid #333;
        background-color: #1e1e1e;
    }
    [data-testid="stMarkdownContainer"] tr:nth-child(even) td {
        background-color: #252525; /* ストライプ */
    }

    /* 3. タイポグラフィ */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.05em !important;
        background: -webkit-linear-gradient(45deg, #eee, #999);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0 !important;
    }
    h2, h3 {
        color: #fff !important;
        margin-top: 30px !important;
    }

    /* 4. 入力エリアのUX */
    .stTextInput > div > div > input {
        background-color: #1e1e1e;
        color: white;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 12px;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4da6ff;
        box-shadow: 0 0 0 2px rgba(77, 166, 255, 0.2);
    }

    /* 5. アクションボタン (Floating風) */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 12px;
        padding: 16px;
        font-size: 16px;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        transition: transform 0.1s;
    }
    .stButton > button:active {
        transform: scale(0.98);
    }

    /* 6. 不要な余白の削除 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Prompt Strategies (表の使用を解禁・推奨) ---
PROMPT_TEMPLATES = {
    "ビジネス・経営層 (Strategic)": """
あなたはマッキンゼー出身の戦略コンサルタントAIです。
入力情報を分析し、意思決定のためのレポートを作成してください。

【出力要件】
1. **比較や数値データは必ずMarkdownの表（Table）を使用して可視化してください。**
2. 結論から述べる（Answer First）。
3. 論理的かつ断定的な口調。

【構造】
# タイトル
## 🎯 Executive Summary
## 📊 Key Metrics (表で出力)
## 🚀 Strategic Implications
    """,
    "エンジニア (Technical)": """
あなたはGoogleのStaff Engineerです。
技術的な詳細、アーキテクチャ、トレードオフを分析してください。

【出力要件】
1. **技術選定の比較、Pros/Consは必ずMarkdownの表（Table）で整理してください。**
2. コードの断片がある場合は適切にフォーマットする。

【構造】
# タイトル
## 🏗 Architecture & Design
## ⚔️ Trade-offs (表で出力)
## 💡 Implementation Notes
    """,
    "研究者 (Academic)": """
あなたはトップジャーナルの査読者です。
新規性、手法、結果の妥当性を評価してください。

【出力要件】
1. **実験結果や手法の比較はMarkdownの表（Table）を使用してください。**
2. 客観的で厳密な表現を用いること。

【構造】
# タイトル
## 🔬 Abstract
## 🧪 Methodologies
## 📈 Results & Discussion (表で出力)
    """,
    "Deep Dive (詳細解説)": """
あなたは優秀なテクニカルライターです。
誰にでもわかるように、しかし詳細を省かずに解説してください。

【出力要件】
1. **複雑な情報はMarkdownの表（Table）を使って整理整頓してください。**
2. 専門用語は噛み砕いて説明する。
    """
}

# --- Logic Functions ---
def get_pdf_text(url=None, uploaded_file=None):
    try:
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
        else:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
        
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        os.remove(tmp_path)
        return "\n".join([p.page_content for p in pages])
    except Exception as e:
        raise e

def get_web_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Check Header for PDF
    try:
        h = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        if 'application/pdf' in h.headers.get('Content-Type', '').lower() or url.lower().endswith('.pdf'):
            return get_pdf_text(url=url), "PDF Document"
    except:
        pass

    # GET
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    
    if 'application/pdf' in resp.headers.get('Content-Type', '').lower():
        return get_pdf_text(url=url), "PDF Document"

    soup = BeautifulSoup(resp.content, 'html.parser')
    for tag in soup(['nav', 'header', 'footer', 'script', 'style', 'form']):
        tag.decompose()
    
    main = soup.find('main') or soup.find('article') or soup.body
    text = main.get_text(separator="\n", strip=True) if main else ""
    title = soup.title.string if soup.title else "No Title"
    return text, title

# --- UI Layout ---

# Header
st.title("Essence")
st.caption("The Essence of Intelligence.")

# Settings Accordion (Mobile Friendly: Hidden by default)
with st.expander("⚙️ Analysis Settings", expanded=False):
    selected_persona = st.selectbox("Perspective", list(PROMPT_TEMPLATES.keys()))
    user_prompt = st.text_area("Custom Instructions", value=PROMPT_TEMPLATES[selected_persona], height=150)

# Main Input Tab
tab1, tab2 = st.tabs(["🌐 URL", "📂 PDF Upload"])

target_text = ""
source_title = ""

with tab1:
    url_input = st.text_input("URL", placeholder="https://...", label_visibility="collapsed")
    if url_input and st.button("Analyze URL"):
        with st.status("🚀 Processing...", expanded=True) as status:
            try:
                status.write("Fetching content...")
                target_text, source_title = get_web_content(url_input)
                status.write("Content loaded.")
                status.update(label="Ready to Analyze!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Failed: {e}")

with tab2:
    uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded_pdf and st.button("Analyze PDF"):
        with st.status("🚀 Processing...", expanded=True) as status:
            try:
                status.write("Extracting text from PDF...")
                target_text, source_title = get_pdf_text(uploaded_file=uploaded_pdf), uploaded_pdf.name
                status.update(label="Ready to Analyze!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Failed: {e}")

# --- AI Execution ---

if target_text:
    # Length Check
    if len(target_text) > 25000:
        st.toast("⚠️ Content too long. Truncating to 25k chars.", icon="✂️")
        target_text = target_text[:25000]

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.3,
        headers={"ngrok-skip-browser-warning": "true"},
        keep_alive="5m"
    )

    final_prompt = f"""
    {user_prompt}

    ---
    【IMPORTANT OUTPUT RULES】
    1. Output in **Markdown**.
    2. Use **Tables** for comparisons/data (The UI handles scrolling).
    3. Use **Bold** for emphasis.
    4. Keep the tone professional.
    
    【INPUT CONTENT】
    {target_text}
    """

    prompt = ChatPromptTemplate.from_template(final_prompt)
    chain = prompt | llm | StrOutputParser()

    st.markdown("---")
    
    # Streaming Output Container
    output_container = st.empty()
    full_response = ""

    try:
        # Stream logic
        for chunk in chain.stream({"content": target_text}):
            full_response += chunk
            output_container.markdown(full_response)
        
        # Post-process UI
        st.markdown("---")
        st.caption("Markdown Source (One-click Copy)")
        st.code(full_response, language="markdown")
        st.toast("Analysis Complete!", icon="✅")

    except Exception as e:
        st.error(f"AI Error: {e}")
