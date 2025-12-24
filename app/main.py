import streamlit as st
import os
import tempfile
import re
from urllib.parse import urljoin
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader

# --- 新規導入ライブラリ ---
import trafilatura
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# --- 設定 ---
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")

st.set_page_config(
    page_title="要約くん",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- UI/UX: デザインの強制固定 (どの端末でも崩れない設定) ---
st.markdown("""
<style>
    /* 1. ベースカラーの強制 (端末設定を無視) */
    .stApp {
        background-color: #121212 !important;
        color: #e0e0e0 !important;
        font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif !important;
    }

    /* 2. 入力フォームの視認性確保 */
    .stTextInput > div > div > input {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        caret-color: #2563eb !important; /* カーソルの色 */
    }
    /* プレースホルダーの色 */
    ::placeholder {
        color: #888 !important;
        opacity: 1 !important;
    }

    /* 3. テーブルデザイン (横スクロール & 配色固定) */
    [data-testid="stMarkdownContainer"] table {
        display: block;
        overflow-x: auto;
        white-space: nowrap;
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
        border: 1px solid #333;
    }
    [data-testid="stMarkdownContainer"] th {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        border-bottom: 2px solid #555 !important;
        padding: 12px;
    }
    [data-testid="stMarkdownContainer"] td {
        background-color: #1a1a1a !important;
        color: #ddd !important;
        border-bottom: 1px solid #333 !important;
        padding: 10px;
    }
    [data-testid="stMarkdownContainer"] tr:nth-child(even) td {
        background-color: #252525 !important; /* ストライプ */
    }

    /* 4. その他UIパーツ */
    h1, h2, h3, p, li, label, .stMarkdown {
        color: #e0e0e0 !important;
    }
    h1 {
        background: -webkit-linear-gradient(45deg, #eee, #aaa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent !important;
    }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #2563eb, #3b82f6) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        transition: opacity 0.2s;
    }
    .stButton > button:active {
        opacity: 0.8;
    }

    /* リンク色 */
    a { color: #4da6ff !important; }

    /* ステータスバー */
    .stStatusWidget {
        background-color: #1e1e1e !important;
        border: 1px solid #333 !important;
        color: #e0e0e0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- プロンプトテンプレート ---
PROMPT_TEMPLATES = {
    "ビジネス・戦略 (経営層向け)": """
あなたは戦略コンサルタントAIです。
入力情報を分析し、意思決定のためのレポートを作成してください。

【出力要件】
1. **比較や数値データはMarkdownの表（Table）を使用してください。**
2. 結論から述べる（アンサーファースト）。
3. 参照リンクの情報は、メイン記事の補強に必要な場合のみ統合してください。

【構造】
# タイトル
## 🎯 エグゼクティブサマリー
## 📊 重要指標 (表で可視化)
## 🚀 ビジネスへの影響と示唆
    """,
    "エンジニア・技術 (開発者向け)": """
あなたはシニアエンジニアです。
技術詳細、アーキテクチャ、トレードオフを分析してください。

【出力要件】
1. **技術比較、メリット・デメリットはMarkdownの表（Table）で整理してください。**
2. リンク先の詳細情報も含め、技術的な深掘りを行ってください。

【構造】
# タイトル
## 🏗 アーキテクチャと設計思想
## ⚔️ 技術比較・トレードオフ (表で可視化)
## 💡 実装のポイント
    """,
    "アカデミック (研究者向け)": """
あなたはトップジャーナルの査読者です。
新規性、手法、結果の妥当性を評価してください。

【出力要件】
1. **実験結果の比較はMarkdownの表（Table）を使用してください。**
2. 客観的で厳密な表現を用いること。

【構造】
# タイトル
## 🔬 アブストラクト (概要)
## 🧪 提案手法・アプローチ
## 📈 結果と考察 (表で可視化)
    """,
    "詳細解説 (Deep Dive)": """
あなたは優秀なテクニカルライターです。
詳細を省かずに、かつ分かりやすく解説してください。

【出力要件】
1. **複雑な情報はMarkdownの表（Table）を使って整理してください。**
2. 専門用語は噛み砕いて説明する。
    """
}

# --- ロジック関数 (Trafilatura & Tenacity採用) ---

def clean_text(text):
    """通信エラーの原因となるヌル文字等を削除"""
    if not text:
        return ""
    text = text.replace('\x00', '')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text

def escape_brackets(text):
    """LangChain用エスケープ"""
    return text.replace("{", "{{").replace("}", "}}")

# 【改善点】Tenacityによる自動リトライ (SSLエラー対策)
# ネットワークエラーが発生しても、2秒待って最大3回まで再試行する
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def fetch_url_content_robust(url):
    """Trafilaturaを使用した堅牢なコンテンツ取得"""
    try:
        # PDF判定 (拡張子またはHeadリクエスト)
        if url.lower().endswith('.pdf'):
            downloaded = trafilatura.downloads.fetch_url(url)
            if downloaded:
                return get_pdf_text_from_bytes(downloaded), "PDF", []
            
        # 1. TrafilaturaでHTML取得 (Requestsより高速・軽量)
        downloaded = trafilatura.downloads.fetch_url(url)
        
        if downloaded is None:
            return "", "取得失敗", []

        # 2. 本文抽出 (BeautifulSoupより高精度でノイズが少ない)
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            no_fallback=False
        )
        
        if not text:
            # TrafilaturaでダメならPDFかもしれないので念の為チェック
            if b"%PDF" in downloaded[:10]:
                 return get_pdf_text_from_bytes(downloaded), "PDF", []
            return "", "本文なし", []

        # タイトル抽出 (簡易的)
        match = re.search(r'<title>(.*?)</title>', str(downloaded), re.IGNORECASE)
        title = match.group(1) if match else "タイトルなし"

        # リンク抽出 (Trafilaturaはリンク抽出メソッドがないため、ここは簡易的に処理するか、
        # あるいは本文抽出時にリンクを残す設定にするが、今回はシンプルに正規表現で抽出)
        # ※Trafilaturaは本文のみを綺麗に抜くのが得意なため、リンク抽出は補助的に行う
        links = []
        # 簡易的なリンク抽出 (httpから始まるものを探す)
        raw_links = re.findall(r'href=[\'"]?([^\'" >]+)', str(downloaded))
        for link in raw_links:
            full_link = urljoin(url, link)
            if full_link.startswith("http") and full_link != url:
                links.append(full_link)

        return clean_text(text), title, list(set(links))

    except Exception as e:
        # Tenacityがキャッチしてリトライさせるために例外を再送出
        raise e

def get_pdf_text_from_bytes(pdf_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        os.remove(tmp_path)
        text = "\n".join([p.page_content for p in pages])
        return clean_text(text)
    except:
        return ""

def deep_dive_analysis(url, enable_deep_dive, max_links, status_container):
    status_container.write(f"メイン記事を取得中 (Trafilatura): {url}...")
    
    try:
        main_text, title, found_links = fetch_url_content_robust(url)
    except Exception as e:
        return f"エラー: 記事の取得に失敗しました ({e})", "エラー"

    if not main_text:
        return "エラー: 本文を抽出できませんでした。", "エラー"

    combined_text = f"=== メインコンテンツ (ソース: {url}) ===\n{main_text[:15000]}\n\n"
    
    if enable_deep_dive and found_links:
        # PDF以外のリンクに絞る
        target_links = [l for l in found_links if not l.lower().endswith('.pdf')][:max_links]
        
        if target_links:
            status_container.write(f"🔍 深掘り中: 関連リンク {len(target_links)} 件を調査します...")
            
            for i, link in enumerate(target_links):
                try:
                    status_container.write(f"読み込み中: {link}...")
                    sub_text, _, _ = fetch_url_content_robust(link)
                    if sub_text:
                        combined_text += f"=== 参考リンク {i+1} (ソース: {link}) ===\n{sub_text[:3000]}\n\n"
                except:
                    status_container.write(f"スキップ (取得失敗): {link}")
                    continue
            
    return combined_text, title

# --- 画面レイアウト ---

st.title("要約くん")
st.caption("文脈を理解するAI要約アシスタント v2.0")

with st.expander("⚙️ 分析設定 (クリックして開く)", expanded=False):
    selected_persona = st.selectbox("視点 (ペルソナ)", list(PROMPT_TEMPLATES.keys()))
    st.markdown("---")
    enable_deep_dive = st.checkbox("記事内のリンクも調査する (Deep Dive)", value=True)
    max_links = st.slider("調査するリンクの最大数", 1, 5, 2)
    st.markdown("---")
    user_prompt = st.text_area("カスタム指示", value=PROMPT_TEMPLATES[selected_persona], height=150)

tab1, tab2 = st.tabs(["🌐 URL分析", "📂 PDFアップロード"])
target_text = ""

with tab1:
    url_input = st.text_input("URLを入力", placeholder="https://example.com/article", label_visibility="collapsed")
    if url_input and st.button("URLを分析する"):
        with st.status("🚀 処理を開始しました...", expanded=True) as status:
            try:
                target_text, _ = deep_dive_analysis(url_input, enable_deep_dive, max_links, status)
                status.update(label="準備完了！AIが分析を開始します。", state="complete", expanded=False)
            except Exception as e:
                status.update(label="エラーが発生しました", state="error")
                st.error(f"詳細: {e}")

with tab2:
    uploaded_pdf = st.file_uploader("PDFをアップロード", type=["pdf"], label_visibility="collapsed")
    if uploaded_pdf and st.button("PDFを分析する"):
        with st.status("🚀 処理中...", expanded=True) as status:
            try:
                status.write("PDF解析中...")
                target_text = get_pdf_text_from_bytes(uploaded_pdf.getvalue())
                status.update(label="準備完了！AIが分析を開始します。", state="complete", expanded=False)
            except Exception as e:
                status.update(label="エラーが発生しました", state="error")
                st.error(f"詳細: {e}")

# --- AI実行 ---

if target_text:
    # 文字数制限 (コンテキスト溢れ防止)
    if len(target_text) > 20000:
        st.toast("⚠️ コンテンツが長すぎるため、先頭20,000文字のみを使用します。", icon="✂️")
        target_text = target_text[:20000]

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.3,
        headers={"ngrok-skip-browser-warning": "true"},
        keep_alive="5m"
    )

    # 安全なプロンプト作成 (波括弧エスケープ)
    safe_user_prompt = escape_brackets(user_prompt)

    final_prompt = f"""
    {safe_user_prompt}

    ---
    【リンク情報の扱いについて】
    入力テキストには「メインコンテンツ」と、場合により「参考リンク」が含まれます。
    - **メインコンテンツ** の内容を正として扱ってください。
    - **参考リンク** の情報は、メインコンテンツの理解を助ける、または補足するために不可欠な場合のみ統合してください。

    【出力ルール】
    1. 言語は **日本語** で出力すること。
    2. 見出しやリストを活用し、Markdown形式で整形すること。
    3. **比較やデータはMarkdownの表（Table）を使用すること**（UI側で見やすく表示されます）。
    4. 重要なキーワードは **太字** で強調すること。
    
    【入力テキスト】
    {{content}}
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
        st.caption("Markdownソース (コピー用)")
        st.code(full_response, language="markdown")
        st.toast("分析完了！", icon="✅")

    except Exception as e:
        st.error(f"AI処理エラー: {e}")
