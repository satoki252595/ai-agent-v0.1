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
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- UI/UX: Global Styling (Dark/Glass/Table) ---
st.markdown("""
<style>
    /* 1. Global Theme */
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 2. Responsive Tables (Scrollable) */
    [data-testid="stMarkdownContainer"] table {
        display: block;
        overflow-x: auto;
        white-space: nowrap;
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
        border-radius: 8px;
        border: 1px solid #333;
    }
    [data-testid="stMarkdownContainer"] th {
        background-color: #2d2d2d;
        color: #ffffff;
        padding: 12px 15px;
        text-align: left;
        border-bottom: 2px solid #444;
    }
    [data-testid="stMarkdownContainer"] td {
        padding: 10px 15px;
        border-bottom: 1px solid #333;
        background-color: #1e1e1e;
    }
    [data-testid="stMarkdownContainer"] tr:nth-child(even) td {
        background-color: #252525;
    }

    /* 3. Typography & Inputs */
    h1 {
        background: -webkit-linear-gradient(45deg, #eee, #999);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        margin-bottom: 0 !important;
    }
    .stTextInput > div > div > input {
        background-color: #1e1e1e;
        color: white;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 12px;
    }

    /* 4. Action Button */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    .stButton > button:active {
        transform: scale(0.98);
    }
    
    /* 5. Custom Status Container */
    .stStatusWidget {
        background-color: #1e1e1e !important;
        border: 1px solid #333 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Prompts ---
PROMPT_TEMPLATES = {
    "Strategic (Business)": """
あなたは戦略コンサルタントAIです。
入力情報を分析し、意思決定のためのレポートを作成してください。

【出力要件】
1. **比較や数値データはMarkdownの表（Table）を使用してください。**
2. 結論から述べる（Answer First）。
3. 参照リンクの情報は、メイン記事の補強に必要な場合のみ統合してください。

【構造】
# タイトル
## 🎯 Executive Summary
## 📊 Key Metrics (表で可視化)
## 🚀 Strategic Implications
    """,
    "Technical (Engineering)": """
あなたはGoogleのStaff Engineerです。
技術詳細、アーキテクチャ、トレードオフを分析してください。

【出力要件】
1. **技術比較、Pros/ConsはMarkdownの表（Table）で整理してください。**
2. リンク先の詳細情報も含め、技術的な深掘りを行ってください。

【構造】
# タイトル
## 🏗 Architecture & Design
## ⚔️ Trade-offs (表で可視化)
## 💡 Implementation Notes
    """,
    "Academic (Research)": """
あなたはトップジャーナルの査読者です。
新規性、手法、結果の妥当性を評価してください。

【出力要件】
1. **実験結果の比較はMarkdownの表（Table）を使用してください。**
2. 客観的で厳密な表現を用いること。

【構造】
# タイトル
## 🔬 Abstract
## 🧪 Methodologies
## 📈 Results & Discussion (表で可視化)
    """,
    "Deep Dive (General)": """
あなたは優秀なテクニカルライターです。
詳細を省かずに解説してください。

【出力要件】
1. **複雑な情報はMarkdownの表（Table）を使って整理してください。**
2. 専門用語は噛み砕いて説明する。
    """
}

# --- Logic Functions (Deep Dive Enabled) ---

def fetch_url_content(url):
    """単一URLのコンテンツを取得"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        # PDF Check
        try:
            h = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            if 'application/pdf' in h.headers.get('Content-Type', '').lower() or url.lower().endswith('.pdf'):
                return get_pdf_text_from_bytes(requests.get(url, headers=headers).content), "PDF", []
        except:
            pass

        # HTML Get
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        if 'application/pdf' in resp.headers.get('Content-Type', '').lower():
            return get_pdf_text_from_bytes(resp.content), "PDF", []

        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Cleanup
        for tag in soup(['nav', 'header', 'footer', 'script', 'style', 'form', 'iframe', 'noscript']):
            tag.decompose()
        
        # Main Content Extraction
        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
        if not main:
            return "", "Unknown", []

        text = main.get_text(separator="\n", strip=True)
        title = soup.title.string if soup.title else "No Title"
        
        # Extract Links (Body only)
        links = []
        for a in main.find_all('a', href=True):
            link = urljoin(url, a['href'])
            if link.startswith("http") and link != url:
                links.append(link)
                
        return text, title, list(set(links)) # Unique links

    except Exception as e:
        return f"Error: {e}", "Error", []

def get_pdf_text_from_bytes(pdf_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        os.remove(tmp_path)
        return "\n".join([p.page_content for p in pages])
    except:
        return ""

def deep_dive_analysis(url, enable_deep_dive, max_links, status_container):
    """再帰的な深掘り処理"""
    status_container.write(f"Fetching Main URL: {url}...")
    main_text, title, found_links = fetch_url_content(url)
    
    combined_text = f"=== MAIN CONTENT (Source: {url}) ===\n{main_text[:15000]}\n\n"
    
    if enable_deep_dive and found_links:
        # Filter PDF links from deep dive (optional, to save time)
        target_links = [l for l in found_links if not l.lower().endswith('.pdf')][:max_links]
        
        status_container.write(f"🔍 Deep Dive: Analyzing {len(target_links)} related links...")
        
        for i, link in enumerate(target_links):
            status_container.write(f"reading: {link}...")
            sub_text, _, _ = fetch_url_content(link)
            # リンク先は短めに切り詰めてコンテキスト溢れを防ぐ
            combined_text += f"=== REFERENCE LINK {i+1} (Source: {link}) ===\n{sub_text[:3000]}\n\n"
            
    return combined_text, title

# --- UI Layout ---

st.title("Essence")
st.caption("Context-Aware Intelligence.")

# Settings Accordion
with st.expander("⚙️ Analysis Settings", expanded=False):
    # Persona
    selected_persona = st.selectbox("Perspective", list(PROMPT_TEMPLATES.keys()))
    
    st.markdown("---")
    
    # Deep Dive Settings
    st.markdown("#### 🕵️ Deep Dive (Link Crawler)")
    enable_deep_dive = st.checkbox("Enable Recursive Crawling", value=True, help="記事内のリンクを辿って情報を補完します")
    max_links = st.slider("Max Links to Follow", 1, 5, 2, help="調査するリンクの上限数")
    
    st.markdown("---")
    
    # Custom Prompt
    user_prompt = st.text_area("Custom Instructions", value=PROMPT_TEMPLATES[selected_persona], height=150)

# Main Input
tab1, tab2 = st.tabs(["🌐 URL Analysis", "📂 PDF Upload"])

target_text = ""

with tab1:
    url_input = st.text_input("URL", placeholder="https://example.com/article", label_visibility="collapsed")
    if url_input and st.button("Analyze URL"):
        with st.status("🚀 Processing...", expanded=True) as status:
            try:
                target_text, _ = deep_dive_analysis(url_input, enable_deep_dive, max_links, status)
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
                target_text = get_pdf_text_from_bytes(uploaded_pdf.getvalue())
                status.update(label="Ready to Analyze!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Failed: {e}")

# --- AI Execution ---

if target_text:
    # Context trimming
    if len(target_text) > 25000:
        st.toast("⚠️ Content truncated to 25k chars.", icon="✂️")
        target_text = target_text[:25000]

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.3,
        headers={"ngrok-skip-browser-warning": "true"},
        keep_alive="5m"
    )

    # 思考と統合を促すプロンプト
    final_prompt = f"""
    {user_prompt}

    ---
    【IMPORTANT INSTRUCTION ON LINKS】
    The input below contains "MAIN CONTENT" and optionally "REFERENCE LINKS".
    - Your primary source of truth is the **MAIN CONTENT**.
    - Use information from **REFERENCE LINKS** *only if* it clarifies, supports, or adds critical context to the MAIN CONTENT.
    - If a reference link is irrelevant (e.g., ads, unrelated topic), ignore it.

    【OUTPUT RULES】
    1. Output in **Markdown**.
    2. Use **Tables** for comparisons/data (The UI handles scrolling).
    3. Use **Bold** for emphasis.
    4. Language: **Japanese**.
    
    【INPUT CONTENT】
    {target_text}
    """

    prompt = ChatPromptTemplate.from_template(final_prompt)
    chain = prompt | llm | StrOutputParser()

    st.markdown("---")
    
    output_container = st.empty()
    full_response = ""

    try:
        for chunk in chain.stream({"content": target_text}):
            full_response += chunk
            output_container.markdown(full_response)
        
        st.markdown("---")
        st.caption("Markdown Source")
        st.code(full_response, language="markdown")
        st.toast("Analysis Complete!", icon="✅")

    except Exception as e:
        st.error(f"AI Error: {e}")
