# -*- coding: utf-8 -*-
"""
ユーティリティ関数
"""
import re
import time
from functools import wraps
from typing import Optional, Callable, Any


def format_ticker(code: str) -> str:
    """
    銘柄コードを正規化（東証形式に変換）
    例: "7203" -> "7203.T"
    """
    code = str(code).strip().upper()
    # 既にサフィックスがある場合
    if code.endswith('.T') or code.endswith('.JP'):
        return code
    # 数字のみの場合は東証サフィックスを追加
    if code.isdigit():
        return f"{code}.T"
    return code


def parse_ticker(ticker: str) -> str:
    """
    銘柄コードからサフィックスを除去
    例: "7203.T" -> "7203"
    """
    ticker = str(ticker).strip()
    for suffix in ['.T', '.JP', '.t', '.jp']:
        if ticker.endswith(suffix):
            return ticker[:-len(suffix)]
    return ticker


def format_number(value: float, decimals: int = 2) -> str:
    """
    数値をカンマ区切りでフォーマット
    例: 1234567.89 -> "1,234,567.89"
    """
    if value is None:
        return "N/A"
    try:
        if decimals == 0:
            return f"{int(value):,}"
        return f"{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    パーセンテージ表示
    例: 0.1234 -> "12.34%"
    """
    if value is None:
        return "N/A"
    try:
        return f"{value * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_currency(value: float, currency: str = "¥", decimals: int = 0) -> str:
    """
    通貨表示
    例: 1234567 -> "¥1,234,567"
    """
    if value is None:
        return "N/A"
    try:
        if decimals == 0:
            return f"{currency}{int(value):,}"
        return f"{currency}{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def clean_text(text: str) -> str:
    """
    テキストから制御文字を除去
    """
    if not text:
        return ""
    text = text.replace('\x00', '')
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)


def retry_on_failure(max_attempts: int = 3, delay: float = 2.0):
    """
    失敗時にリトライするデコレータ
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def calculate_change(current: float, previous: float) -> tuple:
    """
    変化率を計算
    Returns: (変化額, 変化率%)
    """
    if previous is None or previous == 0:
        return (0, 0)
    change = current - previous
    change_pct = (change / previous) * 100
    return (change, change_pct)


def is_market_open() -> bool:
    """
    東証が開いているかどうかを判定（簡易版）
    """
    import datetime
    now = datetime.datetime.now()
    # 土日は休場
    if now.weekday() >= 5:
        return False
    # 取引時間: 9:00-11:30, 12:30-15:00
    hour = now.hour
    minute = now.minute
    if (9 <= hour < 11) or (hour == 11 and minute <= 30):
        return True
    if (12 <= hour < 15 and (hour > 12 or minute >= 30)):
        return True
    return False


def truncate_text(text: str, max_length: int = 8000) -> str:
    """
    テキストを指定文字数で切り詰め
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def extract_stock_codes(text: str) -> list:
    """
    テキストから日本株の銘柄コードを抽出
    """
    # 4桁の数字パターン（日本株の証券コード）
    pattern = r'\b(\d{4})\b'
    matches = re.findall(pattern, text)
    # 1000-9999の範囲でフィルタ（有効な証券コード範囲）
    valid_codes = [m for m in matches if 1000 <= int(m) <= 9999]
    return list(set(valid_codes))


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """
    安全な除算（ゼロ除算を回避）
    """
    if denominator is None or denominator == 0:
        return default
    try:
        return numerator / denominator
    except (ValueError, TypeError):
        return default
