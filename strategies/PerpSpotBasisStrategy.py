#!/usr/bin/env python3
"""
Enhanced FreqAI strategy with perp-spot basis features
"""
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import os

class PerpSpotBasisStrategy(IStrategy):
    timeframe = "5m"
    can_short = False
    startup_candle_count = 200

    # Disable FreqAI exit signals - they cause premature exits
    use_exit_signal = False

    # ROI and stoploss
    minimal_roi = {
        "0": 0.217,
        "31": 0.058,
        "65": 0.04,
        "142": 0
    }
    stoploss = -0.274

    # Process only new candles
    process_only_new_candles = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']

        # Load futures data for basis calculations
        futures_data = self.load_futures_data(pair)
        if futures_data is not None:
            dataframe = self.merge_futures_data(dataframe, futures_data)
            dataframe = self.calculate_basis_features(dataframe)

        # Simplified feature set
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

        return dataframe

    def load_futures_data(self, pair):
        """Load corresponding futures data"""
        try:
            # Try multiple futures data path formats
            possible_paths = [
                f'/home/gil/freqtrade/user_data/data/binance/futures/{pair.replace("/", "_")}-5m-futures.feather',
                f'/home/gil/freqtrade/user_data/data/binance/futures/{pair.replace("/", "_")}_USDT-5m-futures.feather',
                f'/home/gil/freqtrade/user_data/data/binance/{pair.replace("/", "_")}_USDT-5m.feather'
            ]
            
            for futures_path in possible_paths:
                if os.path.exists(futures_path):
                    print(f"Loading futures data from: {futures_path}")
                    df = pd.read_feather(futures_path)
                    return df
            
            print(f"No futures data found for {pair}")
            return None
            
        except Exception as e:
            print(f"Error loading futures data: {e}")
            return None

    def merge_futures_data(self, spot_df, futures_df):
        """Merge spot and futures data"""
        try:
            # Merge on date column
            merged = pd.merge(spot_df, futures_df[['date', 'close', 'volume']],
                            left_on='date', right_on='date', how='left',
                            suffixes=('', '_perp'))

            # Forward fill missing futures data
            merged[['close_perp', 'volume_perp']] = merged[['close_perp', 'volume_perp']].ffill()

            return merged
        except Exception as e:
            print(f"Error merging futures data: {e}")
            return spot_df

    def calculate_basis_features(self, dataframe: DataFrame) -> DataFrame:
        """Calculate perp-spot basis features"""
        if 'close_perp' not in dataframe.columns:
            return dataframe

        # Basic basis calculation (perp - spot) / spot
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

        # Extreme basis conditions
        dataframe['basis_extreme_bull'] = (dataframe['basis_zscore'] > 2).astype(int)
        dataframe['basis_extreme_bear'] = (dataframe['basis_zscore'] < -2).astype(int)

        return dataframe

    def calculate_volume_features(self, dataframe):
        """Enhanced volume analysis features"""
        try:
            # Volume moving averages
            dataframe['volume_ma_10'] = ta.SMA(dataframe['volume'], timeperiod=10)
            dataframe['volume_ma_30'] = ta.SMA(dataframe['volume'], timeperiod=30)

            # Volume rate of change
            dataframe['volume_roc'] = ta.ROC(dataframe['volume'], timeperiod=5)

            # Volume ratio (current vs moving average)
            dataframe['volume_ratio_ma'] = dataframe['volume'] / dataframe['volume_ma_30']

            # On-balance volume (OBV)
            dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])

            # Volume weighted average price (VWAP)
            # A/D is not a good proxy for VWAP. Let's calculate a rolling VWAP.
            vwap_period = 20
            cumulative_price_volume = (dataframe['close'] * dataframe['volume']).rolling(vwap_period).sum()
            cumulative_volume = dataframe['volume'].rolling(vwap_period).sum()
            dataframe['vwap'] = cumulative_price_volume / cumulative_volume

            # Volume extremes
            dataframe['high_volume'] = (dataframe['volume'] > dataframe['volume_ma_30'] * 1.5).astype(int)
            dataframe['low_volume'] = (dataframe['volume'] < dataframe['volume_ma_30'] * 0.5).astype(int)

            return dataframe
        except Exception as e:
            print(f"Error calculating volume features: {e}")
            return dataframe

    freqai_prediction_threshold = DecimalParameter(0.5, 0.9, default=0.75, space='buy', optimize=True, load=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Check if FreqAI signal exists and is valid
        if ('&-enter_long' in dataframe.columns and 
            not dataframe['&-enter_long'].isna().all() and
            dataframe['&-enter_long'].iloc[-1] > self.freqai_prediction_threshold.value):
            dataframe.loc[dataframe.index[-1], 'enter_long'] = 1
        else:
            # Fallback technical analysis when FreqAI is not available
            dataframe.loc[:, 'enter_long'] = 0
            
            # Conservative entry conditions
            oversold = dataframe['rsi'] < 30
            uptrend = dataframe['ema_20'] > dataframe['ema_50']
            macd_bullish = dataframe['macd'] > dataframe['macdsignal']
            
            # Combine conditions
            entry_condition = oversold & uptrend & macd_bullish
            dataframe.loc[entry_condition, 'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0

        # Basis normalization exit
        if 'basis_zscore' in dataframe.columns:
            long_basis_normalization = dataframe['basis_zscore'] > 1.0
            dataframe.loc[long_basis_normalization, 'exit_long'] = 1

        # RSI overbought exit
        strong_overbought = dataframe['rsi'] > 75
        dataframe.loc[strong_overbought, 'exit_long'] = 1

        return dataframe

    # Plot configuration for multi-pair analysis
    plot_config = {
        'main_plot': {
            'close': {'color': 'blue'},
            'close_perp': {'color': 'red'},
            'ema_20': {'color': 'orange'},
        },
        'subplots': {
            "AI Signal": {
                "&-enter_long": {"color": "green"},
            },
            'Basis Analysis': {
                'basis': {'color': 'green'},
                'basis_zscore': {'color': 'purple'},
            },
            'Volume Analysis': {
                'volume': {'color': 'blue', 'type': 'bar'},
                'volume_ma_30': {'color': 'red', 'type': 'scatter'},
            },
            'Technical': {
                'rsi': {'color': 'red'},
                'adx': {'color': 'purple'},
            },
        }
    }

    # FreqAI configuration
    freqai_info = {
        "identifier": "SKLearnRandomForestClassifier",
        "features": [
            "basis_zscore",
            "volume_ratio_ma",
            "rsi",
            "adx",
            "ema_20",
            "ema_50",
            "basis_ma_10",
            "basis_ma_30",
            "basis_roc",
            "volume_roc",
            "obv",
            "vwap",
            "macd",
            "macdsignal",
            "macdhist",
        ],
        "label_period_candles": 12, # Predict 1 hour into the future
        "data_split_parameters": {"split_train": 0.8, "split_test": 0.2},
        "model_training_parameters": {}
    }