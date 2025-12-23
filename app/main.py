import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
import tempfile

# --- 設定読み込み ---
# Secrets優先、なければローカル環境変数
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")

st.set_page_config(page_title="高機能AI要約エージェント", page_icon="🕵️", layout="wide")
st.title("🕵️ Web & PDF 本質的要約くん (Deep Dive)")
st.caption(f"Powered by **{MODEL_NAME}** | Recursive Crawling & PDF Support")

# --- ロジック関数群 ---

def get_filtered_text_and_links(url):
    """
    URLから本文を抽出し、ヘッダー/フッターを除外した上で、
    本文内に含まれるリンクを取得する関数
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')

        # 1. ノイズ除去 (nav, header, footer, script, style等は削除)
        for tag in soup(['nav', 'header', 'footer', 'script', 'style', 'aside', 'form']):
            tag.decompose()

        # 2. 本文領域の特定 (main > article > body の優先順位)
        main_content = soup.find('main') or soup.find('article') or soup.body
        
        if not main_content:
            return "", []

        # 3. テキスト抽出
        text = main_content.get_text(separator="\n", strip=True)

        # 4. リンク抽出 (本文エリアにあるリンクのみ)
        links = []
        for a_tag in main_content.find_all('a', href=True):
            link = urljoin(url, a_tag['href'])
            # 外部サイトへの遷移やアンカーリンクを除外する簡易フィルタ
            if link.startswith("http") and link != url:
                links.append(link)
        
        # 重複排除
        return text, list(set(links))

    except Exception as e:
        return f"エラー ({url}): {e}", []

def process_pdf(uploaded_file):
    """PDFファイルからテキストを抽出する"""
    try:
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        loader = PyPDFLoader(tmp_path)
        pages = loader.load()
        text = "\n".join([p.page_content for p in pages])
        
        # 一時ファイル削除
        os.remove(tmp_path)
        return text
    except Exception as e:
        return f"PDF読み込みエラー: {e}"

# --- UI構築 ---

# サイドバーでモード切替
input_mode = st.sidebar.radio("入力ソースを選択", ["Web URL (深掘り)", "PDF アップロード"])

target_text = ""
context_info = ""

if input_mode == "Web URL (深掘り)":
    url_input = st.text_input("要約したい記事のURLを入力", placeholder="https://example.com/...")
    max_links = st.sidebar.slider("リンクを辿る最大数", 1, 5, 3)
    
    if st.button("深掘り要約を実行") and url_input:
        status_area = st.empty()
        
        with st.spinner("メインページを解析中..."):
            # 1. メインページの取得
            main_text, found_links = get_filtered_text_and_links(url_input)
            
            # メインコンテンツの構築
            combined_content = f"【メイン記事: {url_input}】\n{main_text[:5000]}\n\n"
            
            # 2. リンク先の取得 (1階層のみ)
            status_area.info(f"本文内に {len(found_links)} 件のリンクを発見。上位 {max_links} 件を調査します...")
            
            count = 0
            for link in found_links[:max_links]:
                count += 1
                with status_area.text(f"リンク調査中 ({count}/{max_links}): {link}"):
                    sub_text, _ = get_filtered_text_and_links(link)
                    combined_content += f"--- 関連リンク情報 ({link}) ---\n{sub_text[:2000]}\n\n"
            
            target_text = combined_content
            context_info = f"メイン記事と、関連する {count} 件のリンク先情報を統合しました。"
            status_area.success("情報収集完了！AI生成を開始します。")

elif input_mode == "PDF アップロード":
    uploaded_file = st.file_uploader("PDFファイルをアップロード", type=["pdf"])
    
    if uploaded_file and st.button("PDF要約を実行"):
        with st.spinner("PDFを読み込み中..."):
            target_text = process_pdf(uploaded_file)
            context_info = f"ファイル名: {uploaded_file.name}"

# --- AI処理実行 ---

if target_text:
    # LLM初期化
    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.7,
        headers={"ngrok-skip-browser-warning": "true"},
        keep_alive="5m" # メモリ読み込み維持
    )

    # プロンプト定義
    template = """
    あなたは高度なリサーチアシスタントAIです。
    以下の情報を元に、ユーザーの目的に沿った「本質的な要約」を作成してください。
    情報は複数のソース（メイン記事と関連リンク、またはPDF）から構成されています。
    情報の断片を統合し、包括的なレポートにしてください。

    【コンテキスト情報】
    {context_info}

    【解析対象テキスト】
    {target_text}

    【指示】
    - 日本語で出力すること
    - 重要な事実は箇条書きで整理すること
    - メイン記事の主張と、関連情報（もしあれば）の関係性を明確にすること
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    st.subheader("🤖 要約レポート")
    st.write_stream(chain.stream({
        "target_text": target_text,
        "context_info": context_info
    }))
