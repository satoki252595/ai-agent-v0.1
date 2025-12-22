import streamlit as st
import os
from langchain_ollama import ChatOllama
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 設定 ---
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "nemotron-3-nano")

# --- UI設定 ---
st.set_page_config(page_title="AI要約エージェント", page_icon="📝")
st.title("📝 Web記事 本質的要約くん")
st.markdown(f"Powered by **{MODEL_NAME}**")

# --- サイドバー (URL入力) ---
with st.sidebar:
    st.header("対象の設定")
    url_input = st.text_input("要約したいURLを入力してください", placeholder="https://example.com/article")
    instruction = st.text_area("要約への指示 (任意)", value="この記事の要点と、そこから得られる本質的な洞察を日本語でまとめてください。")
    process_btn = st.button("要約を実行")

# --- ロジック関数 ---
def get_summary(url, user_instruction):
    # 1. Webサイトの読み込み
    try:
        loader = WebBaseLoader(url)
        docs = loader.load()
        content = docs[0].page_content[:10000] # 長すぎる場合はカット(コンテキスト制限対策)
    except Exception as e:
        return f"エラー: URLを読み込めませんでした。\n詳細: {e}"

    # 2. LLMの初期化
    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0.7
    )

    # 3. プロンプト作成
    template = """
    あなたは高度な情報分析AIです。以下のWebコンテンツを分析し、ユーザーの指示に従って回答してください。

    【Webコンテンツ】
    {content}

    【ユーザーの指示】
    {instruction}

    【出力形式】
    - Markdown形式で見やすく整形すること
    - 重要なポイントは箇条書きにする
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    # 4. 生成実行 (ストリーミング対応)
    return chain.stream({"content": content, "instruction": user_instruction})

# --- メイン処理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去の履歴表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ボタンが押された時の処理
if process_btn and url_input:
    # ユーザー入力を表示
    user_msg = f"URL: {url_input}\n指示: {instruction}"
    st.session_state.messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    # AIの回答生成
    with st.chat_message("assistant"):
        stream_handler = get_summary(url_input, instruction)
        response = st.write_stream(stream_handler)
    
    st.session_state.messages.append({"role": "assistant", "content": response})

elif process_btn and not url_input:
    st.error("URLを入力してください！")
