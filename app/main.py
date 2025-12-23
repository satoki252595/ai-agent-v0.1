import streamlit as st
import os
import requests
import tempfile
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from io import BytesIO
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader

# --- 設定読み込み ---
OLLAMA_URL = st.secrets.get("OLLAMA_BASE_URL", "http://localhost:11435")
MODEL_NAME = st.secrets.get("MODEL_NAME", "nemotron-3-nano")

st.set_page_config(page_title="高機能AI要約エージェント", page_icon="🕵️", layout="wide")
st.title("🕵️ Web & PDF 本質的要約くん (Deep Dive)")
st.caption(f"Powered by **{MODEL_NAME}** | PDF URL Support")

# --- ロジック関数群 ---

def get_pdf_text_from_url(url):
    """URLからPDFをダウンロードしてテキスト化"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # メモリ上で処理するためにBytesIOを使用
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

def get_filtered_text_and_links(url):
    """URLのコンテンツタイプを判定して処理を分岐"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # まずHEADリクエストでContent-Typeを確認（効率化）
        try:
            head_resp = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            content_type = head_resp.headers.get('Content-Type', '').lower()
        except:
            content_type = '' # 判定できなければGETで試す

        # PDFの場合の処理
        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            st.info("📄 PDFファイルを検出しました。ダウンロードして解析します...")
            return get_pdf_text_from_url(url), []

        # Webページ(HTML)の場合の処理
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        # URLがリダイレクトでPDFになった場合もケア
        if 'application/pdf' in resp.headers.get('Content-Type', '').lower():
             st.info("📄 PDFファイルを検出しました。ダウンロードして解析します...")
             # バイナリから一時ファイル作成などの処理が必要だが、簡易的に再取得へ回す
             return get_pdf_text_from_url(url), []

        soup = BeautifulSoup(resp.content, 'html.parser')

        # ノイズ除去
        for tag in soup(['nav', 'header', 'footer', 'script', 'style', 'aside', 'form', 'noscript']):
            tag.decompose()

        # 本文特定
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
        if not main_content:
            return "", []

        text = main_content.get_text(separator="\n", strip=True)

        # リンク抽出
        links = []
        for a_tag in main_content.find_all('a', href=True):
            link = urljoin(url, a_tag['href'])
            if link.startswith("http") and link != url:
                # リンク先がPDFかどうかの厳密なチェックは重くなるため、拡張子で簡易判定
                if not link.lower().endswith('.pdf'):
                    links.append(link)
        
        return text, list(set(links))

    except Exception as e:
        return f"エラー ({url}): {e}", []

def process_uploaded_pdf(uploaded_file):
    """アップロードされたPDFの処理"""
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
        return f"PDF読み込みエラー: {e}"

# --- UI構築 ---

input_mode = st.sidebar.radio("入力ソースを選択", ["Web URL / PDF URL", "PDF ファイルアップロード"])

target_text = ""
context_info = ""

if input_mode == "Web URL / PDF URL":
    url_input = st.text_input("URLを入力 (Web記事またはPDF)", placeholder="https://example.com/report.pdf")
    
    # PDFの時は深掘り不要なのでオプションを隠すか、無視する
    max_links = st.sidebar.slider("Web記事の場合のリンク深掘り数", 0, 5, 2)
    
    if st.button("解析・要約を実行") and url_input:
        status_area = st.empty()
        
        with st.spinner("コンテンツを取得中..."):
            # メインコンテンツ取得（PDFかHTMLかは内部で判定）
            main_text, found_links = get_filtered_text_and_links(url_input)
            
            combined_content = f"【メインコンテンツ: {url_input}】\n{main_text[:15000]}\n\n" # 文字数制限緩和
            
            # HTMLでかつリンク深掘りが有効な場合のみ実行
            if found_links and max_links > 0:
                status_area.info(f"記事内に {len(found_links)} 件のリンクを発見。上位 {max_links} 件を調査します...")
                count = 0
                for link in found_links[:max_links]:
                    count += 1
                    with status_area.text(f"リンク調査中 ({count}/{max_links}): {link}"):
                        sub_text, _ = get_filtered_text_and_links(link)
                        # リンク先が長すぎる場合は要約に悪影響なので短めにカット
                        combined_content += f"--- 関連リンク情報 ({link}) ---\n{sub_text[:1000]}\n\n"
                context_info = f"メインコンテンツと、関連する {count} 件のリンク先情報を統合しました。"
            else:
                context_info = "単一のコンテンツ（PDFまたはWebページ）に基づき作成します。"
            
            target_text = combined_content
            status_area.success("読み込み完了。AI要約を開始します。")

elif input_mode == "PDF ファイルアップロード":
    uploaded_file = st.file_uploader("PDFファイルをアップロード", type=["pdf"])
    
    if uploaded_file and st.button("PDF要約を実行"):
        with st.spinner("PDFを読み込み中..."):
            target_text = process_uploaded_pdf(uploaded_file)
            context_info = f"ファイル名: {uploaded_file.name}"

# --- AI処理実行 ---

if target_text:
    # 警告：文字数が多すぎる場合の簡易カット（Ollamaのコンテキスト溢れ防止）
    # Nemotron-3-nano等はコンテキストが短い場合があるため調整
    if len(target_text) > 20000:
        st.warning("⚠️ テキスト量が非常に多いため、先頭20,000文字のみを解析対象とします。")
        target_text = target_text[:20000]

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.3, # 分析タスクなので少し創造性を下げる
        headers={"ngrok-skip-browser-warning": "true"},
        keep_alive="5m"
    )

    template = """
    あなたは高度な金融・ビジネス分析AIです。
    以下の情報を元に、ユーザーのために「本質的な要約レポート」を作成してください。
    
    入力データがIR資料（決算説明資料など）の場合は、特に「業績ハイライト」「将来の見通し」「重要な変化」に焦点を当ててください。

    【コンテキスト情報】
    {context_info}

    【解析対象テキスト】
    {target_text}

    【出力フォーマット】
    # タイトル（内容に基づく適切なもの）
    
    ## 🎯 エグゼクティブサマリー
    （全体の要点を3行程度で）

    ## 🔑 重要なポイント
    - （箇条書き）
    - （箇条書き）
    
    ## 📊 詳細分析
    （本文に基づいた詳細な解説）
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    st.subheader("🤖 AI要約レポート")
    st.write_stream(chain.stream({
        "target_text": target_text,
        "context_info": context_info
    }))
