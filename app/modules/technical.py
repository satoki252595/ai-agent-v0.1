# -*- coding: utf-8 -*-
"""
テクニカル分析モジュール
各種テクニカル指標の計算とチャート生成
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TechnicalSignal:
    """テクニカルシグナル"""
    indicator: str
    signal: str  # "買い", "売り", "中立"
    strength: float  # 0-100
    description: str


class TechnicalAnalyzer:
    """テクニカル分析クラス"""

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: OHLCV データフレーム（columns: open, high, low, close, volume）
        """
        self.df = df.copy()
        self._ensure_columns()

    def _ensure_columns(self):
        """カラム名を正規化"""
        col_mapping = {
            'Open': 'open', 'High': 'high', 'Low': 'low',
            'Close': 'close', 'Volume': 'volume', 'Adj Close': 'adj_close'
        }
        self.df.rename(columns=col_mapping, inplace=True)

    # ==================== トレンド指標 ====================

    def sma(self, period: int) -> pd.Series:
        """単純移動平均線 (Simple Moving Average)"""
        return self.df['close'].rolling(window=period).mean()

    def ema(self, period: int) -> pd.Series:
        """指数移動平均線 (Exponential Moving Average)"""
        return self.df['close'].ewm(span=period, adjust=False).mean()

    def wma(self, period: int) -> pd.Series:
        """加重移動平均線 (Weighted Moving Average)"""
        weights = np.arange(1, period + 1)
        return self.df['close'].rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        """
        ema_fast = self.ema(fast)
        ema_slow = self.ema(slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def bollinger_bands(self, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """
        ボリンジャーバンド
        """
        sma = self.sma(period)
        std = self.df['close'].rolling(window=period).std()

        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev),
            'bandwidth': ((sma + std * std_dev) - (sma - std * std_dev)) / sma * 100,
            'percent_b': (self.df['close'] - (sma - std * std_dev)) / ((sma + std * std_dev) - (sma - std * std_dev))
        }

    def ichimoku(self) -> Dict[str, pd.Series]:
        """
        一目均衡表（日本株では特に重要）
        """
        # 転換線（過去9日間の高値・安値の中間値）
        tenkan = (self.df['high'].rolling(window=9).max() +
                  self.df['low'].rolling(window=9).min()) / 2

        # 基準線（過去26日間の高値・安値の中間値）
        kijun = (self.df['high'].rolling(window=26).max() +
                 self.df['low'].rolling(window=26).min()) / 2

        # 先行スパンA（転換線と基準線の中間値を26日先行）
        senkou_a = ((tenkan + kijun) / 2).shift(26)

        # 先行スパンB（過去52日間の高値・安値の中間値を26日先行）
        senkou_b = ((self.df['high'].rolling(window=52).max() +
                     self.df['low'].rolling(window=52).min()) / 2).shift(26)

        # 遅行スパン（終値を26日遅行）
        chikou = self.df['close'].shift(-26)

        return {
            'tenkan': tenkan,       # 転換線
            'kijun': kijun,         # 基準線
            'senkou_a': senkou_a,   # 先行スパンA
            'senkou_b': senkou_b,   # 先行スパンB
            'chikou': chikou        # 遅行スパン
        }

    def parabolic_sar(self, af_start: float = 0.02, af_max: float = 0.2) -> pd.Series:
        """
        パラボリックSAR
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']

        sar = pd.Series(index=self.df.index, dtype=float)
        af = af_start
        ep = high.iloc[0]
        uptrend = True
        sar.iloc[0] = low.iloc[0]

        for i in range(1, len(self.df)):
            if uptrend:
                sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
                sar.iloc[i] = min(sar.iloc[i], low.iloc[i-1], low.iloc[i-2] if i > 1 else low.iloc[i-1])

                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + af_start, af_max)

                if low.iloc[i] < sar.iloc[i]:
                    uptrend = False
                    sar.iloc[i] = ep
                    ep = low.iloc[i]
                    af = af_start
            else:
                sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
                sar.iloc[i] = max(sar.iloc[i], high.iloc[i-1], high.iloc[i-2] if i > 1 else high.iloc[i-1])

                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + af_start, af_max)

                if high.iloc[i] > sar.iloc[i]:
                    uptrend = True
                    sar.iloc[i] = ep
                    ep = high.iloc[i]
                    af = af_start

        return sar

    # ==================== オシレーター指標 ====================

    def rsi(self, period: int = 14) -> pd.Series:
        """
        RSI (Relative Strength Index)
        """
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def stochastic(self, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """
        ストキャスティクス
        """
        lowest_low = self.df['low'].rolling(window=k_period).min()
        highest_high = self.df['high'].rolling(window=k_period).max()

        k = 100 * (self.df['close'] - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return {'k': k, 'd': d}

    def williams_r(self, period: int = 14) -> pd.Series:
        """
        ウィリアムズ%R
        """
        highest_high = self.df['high'].rolling(window=period).max()
        lowest_low = self.df['low'].rolling(window=period).min()
        return -100 * (highest_high - self.df['close']) / (highest_high - lowest_low)

    def cci(self, period: int = 20) -> pd.Series:
        """
        CCI (Commodity Channel Index)
        """
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        return (typical_price - sma_tp) / (0.015 * mad)

    def roc(self, period: int = 10) -> pd.Series:
        """
        ROC (Rate of Change)
        """
        return ((self.df['close'] - self.df['close'].shift(period)) /
                self.df['close'].shift(period)) * 100

    def momentum(self, period: int = 10) -> pd.Series:
        """
        モメンタム
        """
        return self.df['close'] - self.df['close'].shift(period)

    # ==================== ボラティリティ指標 ====================

    def atr(self, period: int = 14) -> pd.Series:
        """
        ATR (Average True Range)
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def historical_volatility(self, period: int = 20) -> pd.Series:
        """
        ヒストリカルボラティリティ（年率換算）
        """
        log_returns = np.log(self.df['close'] / self.df['close'].shift(1))
        return log_returns.rolling(window=period).std() * np.sqrt(252) * 100

    # ==================== 出来高指標 ====================

    def obv(self) -> pd.Series:
        """
        OBV (On-Balance Volume)
        """
        obv = pd.Series(index=self.df.index, dtype=float)
        obv.iloc[0] = self.df['volume'].iloc[0]

        for i in range(1, len(self.df)):
            if self.df['close'].iloc[i] > self.df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + self.df['volume'].iloc[i]
            elif self.df['close'].iloc[i] < self.df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - self.df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]

        return obv

    def vwap(self) -> pd.Series:
        """
        VWAP (Volume Weighted Average Price)
        """
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        return (typical_price * self.df['volume']).cumsum() / self.df['volume'].cumsum()

    def mfi(self, period: int = 14) -> pd.Series:
        """
        MFI (Money Flow Index) - 出来高を考慮したRSI
        """
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        money_flow = typical_price * self.df['volume']

        positive_flow = pd.Series(0.0, index=self.df.index)
        negative_flow = pd.Series(0.0, index=self.df.index)

        for i in range(1, len(self.df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.iloc[i] = money_flow.iloc[i]
            else:
                negative_flow.iloc[i] = money_flow.iloc[i]

        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()

        money_ratio = positive_sum / negative_sum
        return 100 - (100 / (1 + money_ratio))

    def adl(self) -> pd.Series:
        """
        ADL (Accumulation/Distribution Line)
        """
        clv = ((self.df['close'] - self.df['low']) -
               (self.df['high'] - self.df['close'])) / (self.df['high'] - self.df['low'])
        clv = clv.fillna(0)
        return (clv * self.df['volume']).cumsum()

    # ==================== トレンド強度指標 ====================

    def adx(self, period: int = 14) -> Dict[str, pd.Series]:
        """
        ADX (Average Directional Index)
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']

        plus_dm = high.diff()
        minus_dm = low.diff().abs()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = self.atr(1) * period  # True Range

        plus_di = 100 * (plus_dm.rolling(window=period).sum() / tr.rolling(window=period).sum())
        minus_di = 100 * (minus_dm.rolling(window=period).sum() / tr.rolling(window=period).sum())

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }

    # ==================== 総合分析 ====================

    def calculate_all_indicators(self) -> pd.DataFrame:
        """
        全てのテクニカル指標を計算
        """
        result = self.df.copy()

        # 移動平均
        for period in [5, 25, 75, 200]:
            result[f'sma_{period}'] = self.sma(period)
            result[f'ema_{period}'] = self.ema(period)

        # MACD
        macd = self.macd()
        result['macd'] = macd['macd']
        result['macd_signal'] = macd['signal']
        result['macd_hist'] = macd['histogram']

        # ボリンジャーバンド
        bb = self.bollinger_bands()
        result['bb_upper'] = bb['upper']
        result['bb_middle'] = bb['middle']
        result['bb_lower'] = bb['lower']
        result['bb_bandwidth'] = bb['bandwidth']

        # 一目均衡表
        ichimoku = self.ichimoku()
        result['ichimoku_tenkan'] = ichimoku['tenkan']
        result['ichimoku_kijun'] = ichimoku['kijun']
        result['ichimoku_senkou_a'] = ichimoku['senkou_a']
        result['ichimoku_senkou_b'] = ichimoku['senkou_b']

        # オシレーター
        result['rsi'] = self.rsi()
        stoch = self.stochastic()
        result['stoch_k'] = stoch['k']
        result['stoch_d'] = stoch['d']
        result['williams_r'] = self.williams_r()
        result['cci'] = self.cci()
        result['roc'] = self.roc()
        result['momentum'] = self.momentum()

        # ボラティリティ
        result['atr'] = self.atr()
        result['volatility'] = self.historical_volatility()

        # 出来高
        result['obv'] = self.obv()
        result['vwap'] = self.vwap()
        result['mfi'] = self.mfi()

        # ADX
        adx = self.adx()
        result['adx'] = adx['adx']
        result['plus_di'] = adx['plus_di']
        result['minus_di'] = adx['minus_di']

        return result

    def generate_signals(self) -> List[TechnicalSignal]:
        """
        テクニカルシグナルを生成
        """
        signals = []
        latest = self.df.iloc[-1]
        close = latest['close']

        # RSI シグナル
        rsi_value = self.rsi().iloc[-1]
        if rsi_value < 30:
            signals.append(TechnicalSignal(
                indicator="RSI",
                signal="買い",
                strength=min(100, (30 - rsi_value) * 5),
                description=f"RSI={rsi_value:.1f}で売られ過ぎゾーン。反発の可能性"
            ))
        elif rsi_value > 70:
            signals.append(TechnicalSignal(
                indicator="RSI",
                signal="売り",
                strength=min(100, (rsi_value - 70) * 5),
                description=f"RSI={rsi_value:.1f}で買われ過ぎゾーン。調整の可能性"
            ))
        else:
            signals.append(TechnicalSignal(
                indicator="RSI",
                signal="中立",
                strength=50,
                description=f"RSI={rsi_value:.1f}で中立圏"
            ))

        # MACD シグナル
        macd = self.macd()
        macd_line = macd['macd'].iloc[-1]
        signal_line = macd['signal'].iloc[-1]
        macd_prev = macd['macd'].iloc[-2]
        signal_prev = macd['signal'].iloc[-2]

        if macd_prev < signal_prev and macd_line > signal_line:
            signals.append(TechnicalSignal(
                indicator="MACD",
                signal="買い",
                strength=70,
                description="MACDがシグナル線を上抜け（ゴールデンクロス）"
            ))
        elif macd_prev > signal_prev and macd_line < signal_line:
            signals.append(TechnicalSignal(
                indicator="MACD",
                signal="売り",
                strength=70,
                description="MACDがシグナル線を下抜け（デッドクロス）"
            ))
        else:
            signals.append(TechnicalSignal(
                indicator="MACD",
                signal="中立",
                strength=50,
                description=f"MACD={macd_line:.2f}, シグナル={signal_line:.2f}"
            ))

        # ボリンジャーバンド シグナル
        bb = self.bollinger_bands()
        if close < bb['lower'].iloc[-1]:
            signals.append(TechnicalSignal(
                indicator="ボリンジャーバンド",
                signal="買い",
                strength=65,
                description="株価が-2σ下限を下抜け。反発の可能性"
            ))
        elif close > bb['upper'].iloc[-1]:
            signals.append(TechnicalSignal(
                indicator="ボリンジャーバンド",
                signal="売り",
                strength=65,
                description="株価が+2σ上限を上抜け。調整の可能性"
            ))

        # 移動平均線クロス
        sma_5 = self.sma(5).iloc[-1]
        sma_25 = self.sma(25).iloc[-1]
        sma_5_prev = self.sma(5).iloc[-2]
        sma_25_prev = self.sma(25).iloc[-2]

        if sma_5_prev < sma_25_prev and sma_5 > sma_25:
            signals.append(TechnicalSignal(
                indicator="移動平均線",
                signal="買い",
                strength=75,
                description="5日線が25日線を上抜け（短期ゴールデンクロス）"
            ))
        elif sma_5_prev > sma_25_prev and sma_5 < sma_25:
            signals.append(TechnicalSignal(
                indicator="移動平均線",
                signal="売り",
                strength=75,
                description="5日線が25日線を下抜け（短期デッドクロス）"
            ))

        # 一目均衡表シグナル
        ichimoku = self.ichimoku()
        tenkan = ichimoku['tenkan'].iloc[-1]
        kijun = ichimoku['kijun'].iloc[-1]

        if close > ichimoku['senkou_a'].iloc[-26] and close > ichimoku['senkou_b'].iloc[-26]:
            signals.append(TechnicalSignal(
                indicator="一目均衡表",
                signal="買い",
                strength=60,
                description="株価が雲の上にあり上昇トレンド"
            ))
        elif close < ichimoku['senkou_a'].iloc[-26] and close < ichimoku['senkou_b'].iloc[-26]:
            signals.append(TechnicalSignal(
                indicator="一目均衡表",
                signal="売り",
                strength=60,
                description="株価が雲の下にあり下降トレンド"
            ))

        # ストキャスティクス シグナル
        stoch = self.stochastic()
        k = stoch['k'].iloc[-1]
        d = stoch['d'].iloc[-1]

        if k < 20 and d < 20:
            signals.append(TechnicalSignal(
                indicator="ストキャスティクス",
                signal="買い",
                strength=60,
                description=f"K={k:.1f}, D={d:.1f}で売られ過ぎゾーン"
            ))
        elif k > 80 and d > 80:
            signals.append(TechnicalSignal(
                indicator="ストキャスティクス",
                signal="売り",
                strength=60,
                description=f"K={k:.1f}, D={d:.1f}で買われ過ぎゾーン"
            ))

        return signals

    def get_trend_summary(self) -> Dict:
        """
        トレンドの総合サマリー
        """
        signals = self.generate_signals()
        buy_signals = [s for s in signals if s.signal == "買い"]
        sell_signals = [s for s in signals if s.signal == "売り"]

        # スコア計算（-100 ~ +100）
        buy_score = sum(s.strength for s in buy_signals)
        sell_score = sum(s.strength for s in sell_signals)
        total_score = buy_score - sell_score

        # 総合判断
        if total_score > 150:
            overall = "強い買い"
        elif total_score > 50:
            overall = "買い"
        elif total_score < -150:
            overall = "強い売り"
        elif total_score < -50:
            overall = "売り"
        else:
            overall = "中立"

        return {
            "overall_signal": overall,
            "score": total_score,
            "buy_signals": len(buy_signals),
            "sell_signals": len(sell_signals),
            "signals": signals
        }
