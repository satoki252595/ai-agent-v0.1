# -*- coding: utf-8 -*-
"""
東証上場銘柄データローダー
JPXの公式データから全上場銘柄を取得し、株価データをDBに格納
"""
import os
import sys
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple
import requests
from io import BytesIO

# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.stock_db import StockDatabase

# JPX公式データURL
JPX_DATA_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"

# 投資信託・ETF等を除外するためのキーワード
EXCLUDE_KEYWORDS = [
    "投資信託", "ETF", "ETN", "REIT", "インフラ", "受益証券",
    "出資証券", "優先出資", "カバードワラント"
]

# 除外する市場区分
EXCLUDE_MARKETS = [
    "ETF・ETN", "REIT・ベンチャーファンド・カントリーファンド・インフラファンド"
]


def download_jpx_data() -> pd.DataFrame:
    """
    JPXから上場銘柄一覧をダウンロード

    Returns:
        DataFrame: 銘柄一覧
    """
    print("JPXから銘柄一覧をダウンロード中...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(JPX_DATA_URL, headers=headers, timeout=30)
        response.raise_for_status()

        # Excelファイルを読み込み
        df = pd.read_excel(BytesIO(response.content), engine='xlrd')
        print(f"  ✓ {len(df)}件のデータを取得")
        return df

    except Exception as e:
        print(f"  ✗ ダウンロードエラー: {e}")
        raise


def filter_stocks(df: pd.DataFrame) -> pd.DataFrame:
    """
    株式銘柄のみをフィルタリング（投信・ETF等を除外）

    Args:
        df: JPXデータ

    Returns:
        DataFrame: 株式銘柄のみ
    """
    print("株式銘柄をフィルタリング中...")

    # カラム名を確認
    print(f"  カラム: {df.columns.tolist()}")

    # カラム名の正規化（日本語カラム対応）
    col_mapping = {}
    for col in df.columns:
        col_str = str(col).strip()
        if 'コード' in col_str:
            col_mapping[col] = 'ticker'
        elif '銘柄名' in col_str or '名称' in col_str:
            col_mapping[col] = 'name'
        elif '市場' in col_str:
            col_mapping[col] = 'market'
        elif '33業種' in col_str or '業種' in col_str:
            col_mapping[col] = 'sector_33'
        elif '17業種' in col_str:
            col_mapping[col] = 'sector_17'

    if col_mapping:
        df = df.rename(columns=col_mapping)

    original_count = len(df)

    # 市場区分で除外
    if 'market' in df.columns:
        for exclude_market in EXCLUDE_MARKETS:
            df = df[~df['market'].astype(str).str.contains(exclude_market, na=False)]

    # 銘柄名でETF等を除外
    if 'name' in df.columns:
        for keyword in EXCLUDE_KEYWORDS:
            df = df[~df['name'].astype(str).str.contains(keyword, na=False)]

    # 銘柄コードが4桁の数値のものだけに絞る
    if 'ticker' in df.columns:
        df['ticker'] = df['ticker'].astype(str).str.strip()
        df = df[df['ticker'].str.match(r'^\d{4}$', na=False)]

    filtered_count = len(df)
    print(f"  ✓ {original_count}件 → {filtered_count}件（{original_count - filtered_count}件除外）")

    return df


def fetch_stock_prices(tickers: List[str], batch_size: int = 20, delay: float = 2.0) -> Dict[str, Dict]:
    """
    yfinanceで株価データを取得

    Args:
        tickers: 銘柄コードリスト
        batch_size: バッチサイズ（API負荷軽減のため20推奨）
        delay: バッチ間の待機時間（秒、2.0秒以上推奨）

    Returns:
        Dict: 銘柄コード -> 株価データ
    """
    import yfinance as yf

    results = {}
    total = len(tickers)
    retry_count = 3  # リトライ回数
    retry_delay = 5.0  # リトライ時の待機時間（秒）

    print(f"株価データを取得中（{total}銘柄、バッチサイズ{batch_size}）...")

    for i in range(0, total, batch_size):
        batch = tickers[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"  バッチ {batch_num}/{total_batches} ({len(batch)}銘柄)...")

        # yfinance用にティッカーを変換（.T付加）
        yf_tickers = [f"{t}.T" for t in batch]

        # リトライロジック
        for attempt in range(retry_count):
            try:
                # バッチダウンロード
                data = yf.download(
                    yf_tickers,
                    period="5d",
                    group_by="ticker",
                    auto_adjust=True,
                    threads=True,
                    progress=False
                )

                success_count = 0
                for ticker in batch:
                    yf_ticker = f"{ticker}.T"
                    try:
                        if len(batch) == 1:
                            ticker_data = data
                        else:
                            ticker_data = data[yf_ticker] if yf_ticker in data.columns.get_level_values(0) else None

                        if ticker_data is not None and not ticker_data.empty:
                            latest = ticker_data.iloc[-1]
                            results[ticker] = {
                                'current_price': float(latest['Close']) if pd.notna(latest['Close']) else 0,
                                'volume': int(latest['Volume']) if pd.notna(latest['Volume']) else 0,
                                'high': float(latest['High']) if pd.notna(latest['High']) else 0,
                                'low': float(latest['Low']) if pd.notna(latest['Low']) else 0,
                                'open': float(latest['Open']) if pd.notna(latest['Open']) else 0,
                                'date': ticker_data.index[-1].strftime('%Y-%m-%d')
                            }
                            success_count += 1
                    except Exception as e:
                        pass

                print(f"    → {success_count}/{len(batch)}件成功")
                break  # 成功したらリトライループを抜ける

            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"    ⚠ エラー発生、{retry_delay}秒後にリトライ ({attempt + 1}/{retry_count}): {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # 指数バックオフ
                else:
                    print(f"    ✗ バッチエラー（リトライ上限）: {e}")

        # レート制限対策: バッチ間で必ず待機
        if i + batch_size < total:
            time.sleep(delay)

    print(f"  ✓ 合計 {len(results)}/{total}件の株価を取得")
    return results


def load_all_stocks(
    stock_db: StockDatabase = None,
    batch_size: int = 20,
    delay: float = 2.0,
    max_stocks: int = None,
    verbose: bool = True
) -> Dict[str, any]:
    """
    全上場銘柄をDBにロード

    Args:
        stock_db: StockDatabaseインスタンス
        batch_size: 株価取得時のバッチサイズ（20推奨、API負荷軽減）
        delay: バッチ間待機時間（2.0秒以上推奨）
        max_stocks: 最大取得銘柄数（テスト用）
        verbose: 詳細出力

    Returns:
        Dict: 結果サマリー
    """
    start_time = datetime.now()

    if stock_db is None:
        stock_db = StockDatabase()

    results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'total_time': 0
    }

    try:
        # 1. JPXデータをダウンロード
        df = download_jpx_data()

        # 2. 株式銘柄をフィルタリング
        df = filter_stocks(df)

        if max_stocks:
            df = df.head(max_stocks)
            print(f"テストモード: 最初の{max_stocks}銘柄のみ処理")

        tickers = df['ticker'].tolist()

        # 3. 株価データを取得
        prices = fetch_stock_prices(tickers, batch_size=batch_size, delay=delay)

        # 4. DBに保存
        print("DBに保存中...")

        for _, row in df.iterrows():
            ticker = str(row['ticker'])
            name = str(row.get('name', ''))

            try:
                stock_data = {
                    'ticker': ticker,
                    'name': name,  # JPXの銘柄名を正とする
                    'market': str(row.get('market', '')),
                    'sector': str(row.get('sector_33', '')),
                    'sector_17': str(row.get('sector_17', '')),
                }

                # 株価データをマージ
                if ticker in prices:
                    stock_data.update(prices[ticker])
                    results['success'].append(ticker)
                else:
                    results['skipped'].append(ticker)

                # DBに保存
                stock_db.upsert_stock(ticker, stock_data)

                if verbose and len(results['success']) % 100 == 0:
                    print(f"  進捗: {len(results['success'])}件保存完了")

            except Exception as e:
                results['failed'].append(ticker)
                if verbose:
                    print(f"  ✗ {ticker}: {e}")

        # DBをフラッシュ
        stock_db.close()

    except Exception as e:
        print(f"エラー: {e}")
        raise

    end_time = datetime.now()
    results['total_time'] = (end_time - start_time).total_seconds()

    print()
    print("=" * 50)
    print(f"完了!")
    print(f"  成功: {len(results['success'])}件")
    print(f"  スキップ（株価取得失敗）: {len(results['skipped'])}件")
    print(f"  失敗: {len(results['failed'])}件")
    print(f"  所要時間: {results['total_time']:.1f}秒")
    print("=" * 50)

    return results


# 主要銘柄リスト（ネットワーク制限時のフォールバック用）
MAJOR_STOCKS = [
    # 日経225主要銘柄
    ("7203", "トヨタ自動車"),
    ("6758", "ソニーグループ"),
    ("9984", "ソフトバンクグループ"),
    ("6861", "キーエンス"),
    ("9432", "日本電信電話"),
    ("8306", "三菱UFJフィナンシャル・グループ"),
    ("6501", "日立製作所"),
    ("7267", "本田技研工業"),
    ("4502", "武田薬品工業"),
    ("6902", "デンソー"),
    ("7741", "HOYA"),
    ("6098", "リクルートホールディングス"),
    ("8035", "東京エレクトロン"),
    ("4063", "信越化学工業"),
    ("6367", "ダイキン工業"),
    ("9433", "KDDI"),
    ("4661", "オリエンタルランド"),
    ("6954", "ファナック"),
    ("7974", "任天堂"),
    ("9983", "ファーストリテイリング"),
    ("6594", "日本電産"),
    ("6971", "京セラ"),
    ("8058", "三菱商事"),
    ("8031", "三井物産"),
    ("7751", "キヤノン"),
    ("6702", "富士通"),
    ("4519", "中外製薬"),
    ("6857", "アドバンテスト"),
    ("6273", "SMC"),
    ("3382", "セブン＆アイ・ホールディングス"),
    ("4568", "第一三共"),
    ("6981", "村田製作所"),
    ("9020", "東日本旅客鉄道"),
    ("8316", "三井住友フィナンシャルグループ"),
    ("2914", "日本たばこ産業"),
    ("6503", "三菱電機"),
    ("9022", "東海旅客鉄道"),
    ("8411", "みずほフィナンシャルグループ"),
    ("4901", "富士フイルムホールディングス"),
    ("8766", "東京海上ホールディングス"),
    ("7269", "スズキ"),
    ("6762", "TDK"),
    ("4578", "大塚ホールディングス"),
    ("6988", "日東電工"),
    ("8001", "伊藤忠商事"),
    ("3659", "ネクソン"),
    ("6146", "ディスコ"),
    ("7201", "日産自動車"),
    ("6723", "ルネサスエレクトロニクス"),
    ("7735", "SCREENホールディングス"),
    # 追加：成長株・高配当株
    ("2413", "エムスリー"),
    ("4385", "メルカリ"),
    ("6526", "ソシオネクスト"),
    ("6920", "レーザーテック"),
    ("9101", "日本郵船"),
    ("9104", "商船三井"),
    ("9107", "川崎汽船"),
    ("8053", "住友商事"),
    ("8002", "丸紅"),
    ("5401", "日本製鉄"),
    ("5411", "JFEホールディングス"),
    ("8801", "三井不動産"),
    ("8802", "三菱地所"),
    ("6301", "小松製作所"),
    ("7011", "三菱重工業"),
    ("7012", "川崎重工業"),
    ("2802", "味の素"),
    ("4452", "花王"),
    ("4911", "資生堂"),
    ("7182", "ゆうちょ銀行"),
    ("8604", "野村ホールディングス"),
    ("8630", "SOMPOホールディングス"),
    ("8725", "MS＆ADインシュアランスグループホールディングス"),
    ("4503", "アステラス製薬"),
    ("4506", "住友ファーマ"),
    ("4523", "エーザイ"),
    ("6506", "安川電機"),
    ("6645", "オムロン"),
    ("6752", "パナソニックホールディングス"),
    ("6770", "アルプスアルパイン"),
    ("6841", "横河電機"),
    ("7733", "オリンパス"),
    ("7752", "リコー"),
    ("9613", "NTTデータグループ"),
    ("9719", "SCSK"),
    ("4755", "楽天グループ"),
    ("4689", "LINEヤフー"),
    ("3938", "LINE"),
    ("2432", "ディー・エヌ・エー"),
    ("3092", "ZOZO"),
    ("7832", "バンダイナムコホールディングス"),
    ("9766", "コナミグループ"),
    ("9697", "カプコン"),
    ("7453", "良品計画"),
    ("3099", "三越伊勢丹ホールディングス"),
    ("8267", "イオン"),
    ("9843", "ニトリホールディングス"),
    ("2871", "ニチレイ"),
    ("2801", "キッコーマン"),
    ("2502", "アサヒグループホールディングス"),
    ("2503", "キリンホールディングス"),
]


def load_major_stocks(stock_db: StockDatabase = None, verbose: bool = True, delay: float = 1.5) -> Dict[str, any]:
    """
    主要銘柄のみをロード（ネットワーク制限時のフォールバック）

    Args:
        stock_db: StockDatabaseインスタンス
        verbose: 詳細出力
        delay: 銘柄間の待機時間（秒、1.5秒以上推奨）

    Returns:
        Dict: 結果サマリー
    """
    import yfinance as yf

    if stock_db is None:
        stock_db = StockDatabase()

    results = {
        'success': [],
        'failed': []
    }

    retry_count = 3  # リトライ回数

    print(f"主要{len(MAJOR_STOCKS)}銘柄をロード中（待機時間: {delay}秒/銘柄）...")

    for idx, (ticker, name) in enumerate(MAJOR_STOCKS):
        # リトライロジック
        for attempt in range(retry_count):
            try:
                yf_ticker = f"{ticker}.T"
                stock = yf.Ticker(yf_ticker)

                # 株価データを取得
                hist = stock.history(period="5d")

                if hist.empty:
                    if attempt < retry_count - 1:
                        time.sleep(2.0)  # リトライ前に待機
                        continue
                    results['failed'].append(ticker)
                    if verbose:
                        print(f"  ✗ {ticker} ({name}): データなし")
                    break

                latest = hist.iloc[-1]
                info = stock.info

                stock_data = {
                    'ticker': ticker,
                    'name': name,  # ハードコードした日本語名を使用
                    'current_price': float(latest['Close']) if pd.notna(latest['Close']) else 0,
                    'volume': int(latest['Volume']) if pd.notna(latest['Volume']) else 0,
                    'high': float(latest['High']) if pd.notna(latest['High']) else 0,
                    'low': float(latest['Low']) if pd.notna(latest['Low']) else 0,
                    'open': float(latest['Open']) if pd.notna(latest['Open']) else 0,
                    'market_cap': info.get('marketCap', 0),
                    'pe_ratio': info.get('trailingPE'),
                    'pb_ratio': info.get('priceToBook'),
                    'dividend_yield': info.get('dividendYield'),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                }

                stock_db.upsert_stock(ticker, stock_data)
                results['success'].append(ticker)

                if verbose:
                    print(f"  ✓ [{idx+1}/{len(MAJOR_STOCKS)}] {ticker} ({name}): ¥{stock_data['current_price']:,.0f}")

                break  # 成功したらリトライループを抜ける

            except Exception as e:
                if attempt < retry_count - 1:
                    retry_wait = 3.0 * (attempt + 1)  # 指数バックオフ
                    if verbose:
                        print(f"  ⚠ {ticker}: エラー発生、{retry_wait}秒後にリトライ ({attempt + 1}/{retry_count})")
                    time.sleep(retry_wait)
                else:
                    results['failed'].append(ticker)
                    if verbose:
                        print(f"  ✗ {ticker} ({name}): {e}")

        # レート制限対策: 各銘柄の処理後に待機
        if idx < len(MAJOR_STOCKS) - 1:
            time.sleep(delay)

    stock_db.close()

    print()
    print(f"完了: {len(results['success'])}件成功, {len(results['failed'])}件失敗")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="東証上場銘柄データローダー")
    parser.add_argument("--major-only", action="store_true", help="主要銘柄のみロード")
    parser.add_argument("--max", type=int, help="最大取得銘柄数（テスト用）")
    parser.add_argument("--batch-size", type=int, default=50, help="バッチサイズ")
    parser.add_argument("--delay", type=float, default=1.0, help="バッチ間待機時間（秒）")

    args = parser.parse_args()

    if args.major_only:
        load_major_stocks(verbose=True)
    else:
        load_all_stocks(
            batch_size=args.batch_size,
            delay=args.delay,
            max_stocks=args.max,
            verbose=True
        )
