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

# --- 設定 ---
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")

st.set_page_config(
    page_title="要約くん",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- UI/UX: デザイン設定 (ダークモード・スマホ最適化) ---
st.markdown("""
<style>
    /* 1. 全体テーマ (目に優しいダークグレー) */
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
        font-family: 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
    }

    /* 2. 横スクロール対応テーブル (スマホで見やすく) */
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
        font-weight: bold;
    }
    [data-testid="stMarkdownContainer"] td {
        padding: 10px 15px;
        border-bottom: 1px solid #333;
        background-color: #1e1e1e;
    }
    [data-testid="stMarkdownContainer"] tr:nth-child(even) td {
        background-color: #252525;
    }

    /* 3. タイポグラフィ & 入力欄 */
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

    /* 4. アクションボタン (押しやすく) */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        font-family: 'Hiragino Kaku Gothic ProN', sans-serif;
    }
    .stButton > button:active {
        transform: scale(0.98);
    }
    
    /* 5. ステータスコンテナ */
    .stStatusWidget {
        background-color: #1e1e1e !important;
        border: 1px solid #333 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- プロンプトテンプレート集 ---
PROMPT_TEMPLATES = {
    "ビジネス・戦略 (経営層向け)": """
あなたはマッキンゼー出身の戦略コンサルタントAIです。
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
あなたはGoogleのシニアエンジニアです。
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

# --- ロジック関数 (深掘り対応) ---

def fetch_url_content(url):
    """単一URLのコンテンツを取得"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        # PDF判定
        try:
            h = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            if 'application/pdf' in h.headers.get('Content-Type', '').lower() or url.lower().endswith('.pdf'):
                return get_pdf_text_from_bytes(requests.get(url, headers=headers).content), "PDF", []
        except:
            pass

        # HTML取得
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        if 'application/pdf' in resp.headers.get('Content-Type', '').lower():
            return get_pdf_text_from_bytes(resp.content), "PDF", []

        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # 不要タグ削除
        for tag in soup(['nav', 'header', 'footer', 'script', 'style', 'form', 'iframe', 'noscript']):
            tag.decompose()
        
        # 本文抽出
        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
        if not main:
            return "", "不明", []

        text = main.get_text(separator="\n", strip=True)
        title = soup.title.string if soup.title else "タイトルなし"
        
        # リンク抽出 (本文内のみ)
        links = []
        for a in main.find_all('a', href=True):
            link = urljoin(url, a['href'])
            if link.startswith("http") and link != url:
                links.append(link)
                
        return text, title, list(set(links))

    except Exception as e:
        return f"エラー: {e}", "エラー", []

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
    """メイン記事とリンク先の情報を収集"""
    status_container.write(f"メイン記事を取得中: {url}...")
    main_text, title, found_links = fetch_url_content(url)
    
    combined_text = f"=== メインコンテンツ (ソース: {url}) ===\n{main_text[:15000]}\n\n"
    
    if enable_deep_dive and found_links:
        # PDFリンクは重いため深掘り対象から除外（HTMLのみ対象）
        target_links = [l for l in found_links if not l.lower().endswith('.pdf')][:max_links]
        
        if target_links:
            status_container.write(f"🔍 深掘り中: 関連リンク {len(target_links)} 件を調査します...")
            
            for i, link in enumerate(target_links):
                status_container.write(f"読み込み中: {link}...")
                sub_text, _, _ = fetch_url_content(link)
                combined_text += f"=== 参考リンク {i+1} (ソース: {link}) ===\n{sub_text[:3000]}\n\n"
            
    return combined_text, title

# --- 画面レイアウト ---

st.title("要約くん")
st.caption("文脈を理解するAI要約アシスタント")

# 設定アコーディオン
with st.expander("⚙️ 分析設定 (クリックして開く)", expanded=False):
    # ペルソナ選択
    selected_persona = st.selectbox("視点 (ペルソナ)", list(PROMPT_TEMPLATES.keys()))
    
    st.markdown("---")
    
    # 深掘り設定
    st.markdown("#### 🕵️ リンク深掘り設定")
    enable_deep_dive = st.checkbox("記事内のリンクも調査する (Deep Dive)", value=True, help="メイン記事内のリンクを辿り、情報を補完します。")
    max_links = st.slider("調査するリンクの最大数", 1, 5, 2, help="数を増やすと処理時間が長くなります。")
    
    st.markdown("---")
    
    # カスタムプロンプト
    user_prompt = st.text_area("カスタム指示 (プロンプト)", value=PROMPT_TEMPLATES[selected_persona], height=150)

# 入力タブ
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
                st.error(f"失敗しました: {e}")

with tab2:
    uploaded_pdf = st.file_uploader("PDFをアップロード", type=["pdf"], label_visibility="collapsed")
    if uploaded_pdf and st.button("PDFを分析する"):
        with st.status("🚀 処理中...", expanded=True) as status:
            try:
                status.write("PDFからテキストを抽出中...")
                target_text = get_pdf_text_from_bytes(uploaded_pdf.getvalue())
                status.update(label="準備完了！AIが分析を開始します。", state="complete", expanded=False)
            except Exception as e:
                status.update(label="エラーが発生しました", state="error")
                st.error(f"失敗しました: {e}")

# --- AI実行 ---

if target_text:
    # 文字数制限
    if len(target_text) > 25000:
        st.toast("⚠️ コンテンツが長すぎるため、先頭25,000文字のみを使用します。", icon="✂️")
        target_text = target_text[:25000]

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.3,
        headers={"ngrok-skip-browser-warning": "true"},
        keep_alive="5m"
    )

    # 統合プロンプト
    final_prompt = f"""
    {user_prompt}

    ---
    【リンク情報の扱いについて】
    入力テキストには「メインコンテンツ」と、場合により「参考リンク」が含まれます。
    - **メインコンテンツ** の内容を正として扱ってください。
    - **参考リンク** の情報は、メインコンテンツの理解を助ける、または補足するために不可欠な場合のみ統合してください。
    - 無関係なリンク（広告や無関係な記事）の情報は無視してください。

    【出力ルール】
    1. 言語は **日本語** で出力すること。
    2. 見出しやリストを活用し、Markdown形式で整形すること。
    3. **比較やデータはMarkdownの表（Table）を使用すること**（UI側で見やすく表示されます）。
    4. 重要なキーワードは **太字** で強調すること。
    
    【入力テキスト】
    {target_text}
    """

    prompt = ChatPromptTemplate.from_template(final_prompt)
    chain = prompt | llm | StrOutputParser()

    st.markdown("---")
    
    output_container = st.empty()
    full_response = ""

    try:
        # ストリーミング出力
        for chunk in chain.stream({"content": target_text}):
            full_response += chunk
            output_container.markdown(full_response)
        
        st.markdown("---")
        st.caption("Markdownソース (コピー用)")
        st.code(full_response, language="markdown")
        st.toast("分析が完了しました！", icon="✅")

    except Exception as e:
        st.error(f"AI処理エラー: {e}")
