#!/usr/bin/env python3
"""
Fixed version of PerpSpotBasisStrategy
"""
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import os

class PerpSpotBasisStrategy_Fixed(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    use_exit_signal = False

    # More reasonable ROI
    minimal_roi = {
        "0": 0.08,
        "60": 0.04,
        "120": 0.02,
        "240": 0
    }
    stoploss = -0.02  # Using config stoploss

    process_only_new_candles = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']

        # Try to load futures data, but don't fail if it's not available
        futures_data = self.load_futures_data(pair)
        if futures_data is not None:
            dataframe = self.merge_futures_data(dataframe, futures_data)
            dataframe = self.calculate_basis_features(dataframe)

        # Always calculate these basic features
        dataframe = self.calculate_volume_features(dataframe)

        # Technical indicators
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # Bollinger Bands for additional signals
        bb = ta.BBANDS(dataframe)
        dataframe['bb_upper'] = bb['upperband']
        dataframe['bb_middle'] = bb['middleband']
        dataframe['bb_lower'] = bb['lowerband']

        return dataframe

    def load_futures_data(self, pair):
        """Load corresponding futures data if available"""
        try:
            futures_pair = pair.replace('/', '_') + '_USDT-5m-futures.feather'
            futures_path = f'/home/gil/freqtrade/user_data/data/binance/futures/{futures_pair}'

            if not os.path.exists(futures_path):
                return None

            df = pd.read_feather(futures_path)
            return df
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
        """Calculate perp-spot basis features if perp data is available"""
        if 'close_perp' not in dataframe.columns or dataframe['close_perp'].isna().all():
            return dataframe

        # Basic basis calculation
        dataframe['basis'] = (dataframe['close_perp'] - dataframe['close']) / dataframe['close'] * 100

        # Only calculate if we have valid data
        if not dataframe['basis'].isna().all():
            dataframe['basis_ma_10'] = ta.SMA(dataframe['basis'], timeperiod=10)
            dataframe['basis_ma_30'] = ta.SMA(dataframe['basis'], timeperiod=30)
            dataframe['basis_roc'] = ta.ROC(dataframe['basis'], timeperiod=5)

            # Z-score of basis
            basis_mean = dataframe['basis'].rolling(window=50).mean()
            basis_std = dataframe['basis'].rolling(window=50).std()
            dataframe['basis_zscore'] = (dataframe['basis'] - basis_mean) / basis_std

        return dataframe

    def calculate_volume_features(self, dataframe):
        """Calculate volume features"""
        try:
            dataframe['volume_ma_20'] = ta.SMA(dataframe['volume'], timeperiod=20)
            dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma_20']
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

        # Primary: FreqAI signal
        if '&-enter_long' in dataframe.columns:
            freqai_condition = dataframe['&-enter_long'] > self.freqai_prediction_threshold.value
            dataframe.loc[freqai_condition, 'enter_long'] = 1
        else:
            # Fallback: Conservative technical analysis
            oversold = dataframe['rsi'] < 30
            uptrend = dataframe['ema_20'] > dataframe['ema_50']
            macd_bullish = dataframe['macd'] > dataframe['macdsignal']
            near_bb_lower = dataframe['close'] <= dataframe['bb_lower'] * 1.02  # Within 2% of BB lower
            volume_confirmation = dataframe['volume_ratio'] > 1.1
            
            # Require multiple confirmations
            entry_condition = oversold & uptrend & macd_bullish & near_bb_lower & volume_confirmation
            
            # Additional filter: only enter if price is above VWAP (trend confirmation)
            price_above_vwap = dataframe['close'] > dataframe['vwap']
            entry_condition = entry_condition & price_above_vwap
            
            dataframe.loc[entry_condition, 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0

        # Exit conditions
        overbought = dataframe['rsi'] > 75
        near_bb_upper = dataframe['close'] >= dataframe['bb_upper'] * 0.98
        
        # Exit if basis normalizes (only if we have basis data)
        basis_exit = False
        if 'basis_zscore' in dataframe.columns and not dataframe['basis_zscore'].isna().all():
            basis_exit = dataframe['basis_zscore'] > 1.5

        exit_condition = overbought | near_bb_upper | basis_exit
        dataframe.loc[exit_condition, 'exit_long'] = 1

        return dataframe

    # FreqAI configuration - robust feature set
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
            "volume_ratio",
            "obv",
            "vwap",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            # Include basis features if available, FreqAI will handle missing values
            "basis_ma_10",
            "basis_ma_30",
            "basis_zscore",
        ],
        "label_period_candles": 24,  # Predict 2 hours ahead
        "data_split_parameters": {"split_train": 0.8, "split_test": 0.2},
        "model_training_parameters": {
            "n_estimators": 100,
            "max_depth": 8,
            "min_samples_split": 10,
            "min_samples_leaf": 5,
            "random_state": 42,
            "n_jobs": -1
        }
    }