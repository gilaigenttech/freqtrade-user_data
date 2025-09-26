#!/usr/bin/env python3
"""
Working PerpSpotBasisStrategy - Ready to use!
"""
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import os

class PerpSpotBasisStrategy_Working(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    use_exit_signal = False

    # Reasonable ROI targets
    minimal_roi = {
        "0": 0.06,
        "60": 0.03,
        "120": 0.015,
        "240": 0
    }
    stoploss = -0.02

    process_only_new_candles = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']

        # Load futures data for basis calculations
        futures_data = self.load_futures_data(pair)
        if futures_data is not None:
            dataframe = self.merge_futures_data(dataframe, futures_data)
            dataframe = self.calculate_basis_features(dataframe)

        # Volume features
        dataframe = self.calculate_volume_features(dataframe)

        # Technical indicators
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # Bollinger Bands
        bb = ta.BBANDS(dataframe)
        dataframe['bb_upper'] = bb['upperband']
        dataframe['bb_middle'] = bb['middleband'] 
        dataframe['bb_lower'] = bb['lowerband']

        return dataframe

    def load_futures_data(self, pair):
        """Load corresponding futures data"""
        try:
            possible_paths = [
                f'/home/gil/freqtrade/user_data/data/binance/futures/{pair.replace("/", "_")}-5m-futures.feather',
                f'/home/gil/freqtrade/user_data/data/binance/futures/{pair.replace("/", "_")}_USDT-5m-futures.feather',
                f'/home/gil/freqtrade/user_data/data/binance/{pair.replace("/", "_")}_USDT-5m.feather'
            ]
            
            for futures_path in possible_paths:
                if os.path.exists(futures_path):
                    df = pd.read_feather(futures_path)
                    return df
            return None
            
        except Exception:
            return None

    def merge_futures_data(self, spot_df, futures_df):
        """Merge spot and futures data"""
        try:
            merged = pd.merge(spot_df, futures_df[['date', 'close', 'volume']],
                            left_on='date', right_on='date', how='left',
                            suffixes=('', '_perp'))
            merged[['close_perp', 'volume_perp']] = merged[['close_perp', 'volume_perp']].ffill()
            return merged
        except Exception:
            return spot_df

    def calculate_basis_features(self, dataframe: DataFrame) -> DataFrame:
        """Calculate perp-spot basis features"""
        if 'close_perp' not in dataframe.columns or dataframe['close_perp'].isna().all():
            return dataframe

        # Basic basis calculation (perp - spot) / spot * 100
        dataframe['basis'] = (dataframe['close_perp'] - dataframe['close']) / dataframe['close'] * 100

        # Basis moving averages
        dataframe['basis_ma_10'] = ta.SMA(dataframe['basis'], timeperiod=10)
        dataframe['basis_ma_30'] = ta.SMA(dataframe['basis'], timeperiod=30)

        # Basis rate of change
        dataframe['basis_roc'] = ta.ROC(dataframe['basis'], timeperiod=5)

        # Z-score of basis
        basis_mean = dataframe['basis'].rolling(window=50).mean()
        basis_std = dataframe['basis'].rolling(window=50).std()
        dataframe['basis_zscore'] = (dataframe['basis'] - basis_mean) / basis_std

        # Volume ratio
        dataframe['volume_ratio'] = dataframe['volume_perp'] / dataframe['volume']

        # Basis momentum
        dataframe['basis_momentum'] = dataframe['basis'] - dataframe['basis_ma_30']

        return dataframe

    def calculate_volume_features(self, dataframe):
        """Calculate volume features"""
        try:
            dataframe['volume_ma_20'] = ta.SMA(dataframe['volume'], timeperiod=20)
            dataframe['volume_ratio_ma'] = dataframe['volume'] / dataframe['volume_ma_20']
            dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])

            # VWAP
            vwap_period = 20
            cumulative_price_volume = (dataframe['close'] * dataframe['volume']).rolling(vwap_period).sum()
            cumulative_volume = dataframe['volume'].rolling(vwap_period).sum()
            dataframe['vwap'] = cumulative_price_volume / cumulative_volume

            return dataframe
        except Exception:
            return dataframe

    freqai_prediction_threshold = DecimalParameter(0.6, 0.8, default=0.7, space='buy', optimize=True, load=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0

        # Primary: FreqAI signal (if available)
        if ('&-enter_long' in dataframe.columns and 
            not dataframe['&-enter_long'].isna().all()):
            freqai_condition = dataframe['&-enter_long'] > self.freqai_prediction_threshold.value
            dataframe.loc[freqai_condition, 'enter_long'] = 1
        else:
            # Fallback strategy using basis + technical analysis
            
            # Basic technical conditions
            oversold = dataframe['rsi'] < 35
            uptrend = dataframe['ema_20'] > dataframe['ema_50']
            macd_bullish = dataframe['macd'] > dataframe['macdsignal']
            price_near_bb_lower = dataframe['close'] <= dataframe['bb_lower'] * 1.01
            volume_above_average = dataframe['volume_ratio_ma'] > 1.2
            
            # Basis trading signals (if available)
            basis_entry = False
            if 'basis_zscore' in dataframe.columns and not dataframe['basis_zscore'].isna().all():
                # Enter when basis is extremely negative (futures trading at discount)
                extreme_negative_basis = dataframe['basis_zscore'] < -2
                basis_recovering = dataframe['basis_roc'] > 0  # Basis starting to recover
                basis_entry = extreme_negative_basis & basis_recovering
            
            # Combine all conditions - need multiple confirmations
            technical_entry = oversold & uptrend & macd_bullish & price_near_bb_lower & volume_above_average
            
            # Enter if either strong technical setup OR basis opportunity
            entry_condition = technical_entry | basis_entry
            
            dataframe.loc[entry_condition, 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0

        # Technical exits
        overbought = dataframe['rsi'] > 70
        price_at_bb_upper = dataframe['close'] >= dataframe['bb_upper'] * 0.99
        macd_bearish = dataframe['macd'] < dataframe['macdsignal']
        
        # Basis exits (if available)
        basis_exit = False
        if 'basis_zscore' in dataframe.columns and not dataframe['basis_zscore'].isna().all():
            # Exit when basis normalizes or becomes extremely positive
            basis_normalized = dataframe['basis_zscore'] > 1
            basis_exit = basis_normalized

        exit_condition = overbought | price_at_bb_upper | (macd_bearish & overbought) | basis_exit
        dataframe.loc[exit_condition, 'exit_long'] = 1

        return dataframe

    # FreqAI configuration (optional - strategy works without it)
    freqai_info = {
        "identifier": "SKLearnRandomForestClassifier",
        "features": [
            "rsi",
            "ema_20",
            "ema_50",
            "adx",
            "macd",
            "macdsignal",
            "macdhist",
            "volume_ratio_ma",
            "obv",
            "vwap",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            # Basis features (will be ignored if not available)
            "basis_ma_10",
            "basis_ma_30",
            "basis_zscore",
            "basis_roc",
            "basis_momentum",
        ],
        "label_period_candles": 12,
        "data_split_parameters": {"split_train": 0.85, "split_test": 0.15},
        "model_training_parameters": {
            "n_estimators": 100,
            "max_depth": 8,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "random_state": 42,
            "n_jobs": -1
        }
    }