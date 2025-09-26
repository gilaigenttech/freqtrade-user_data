#!/usr/bin/env python3
"""
Debug version of PerpSpotBasisStrategy to identify issues
"""
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import IntParameter, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import os

class PerpSpotBasisStrategy_Debug(IStrategy):
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
        print(f"Processing pair: {pair}")
        print(f"Dataframe shape: {dataframe.shape}")
        print(f"Date range: {dataframe['date'].min()} to {dataframe['date'].max()}")

        # Load futures data for basis calculations
        futures_data = self.load_futures_data(pair)
        if futures_data is not None:
            print(f"Futures data loaded successfully for {pair}")
            dataframe = self.merge_futures_data(dataframe, futures_data)
            dataframe = self.calculate_basis_features(dataframe)
        else:
            print(f"No futures data found for {pair}")

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

        # Debug: Print available columns
        print(f"Available columns: {dataframe.columns.tolist()}")
        
        # Check for FreqAI columns
        freqai_cols = [col for col in dataframe.columns if col.startswith('&-')]
        print(f"FreqAI columns found: {freqai_cols}")
        
        if '&-enter_long' in dataframe.columns:
            print(f"FreqAI enter_long signal range: {dataframe['&-enter_long'].min()} to {dataframe['&-enter_long'].max()}")
            print(f"FreqAI enter_long signal last 10 values: {dataframe['&-enter_long'].tail(10).tolist()}")
        else:
            print("WARNING: No &-enter_long column found!")

        return dataframe

    def load_futures_data(self, pair):
        """Load corresponding futures data"""
        try:
            # Convert spot pair to futures pair (BTC/USDT -> BTC/USDT:USDT)
            futures_pair = pair.replace('/', '_') + '_USDT-5m-futures.feather'
            futures_path = f'/home/gil/freqtrade/user_data/data/binance/futures/{futures_pair}'
            
            print(f"Looking for futures data at: {futures_path}")

            if not os.path.exists(futures_path):
                print(f"Futures data file does not exist: {futures_path}")
                return None

            df = pd.read_feather(futures_path)
            print(f"Loaded futures data: {df.shape} rows")
            return df
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
            
            print(f"Merged data shape: {merged.shape}")
            print(f"Perp data coverage: {merged['close_perp'].notna().sum()}/{len(merged)} rows")

            return merged
        except Exception as e:
            print(f"Error merging futures data: {e}")
            return spot_df

    def calculate_basis_features(self, dataframe: DataFrame) -> DataFrame:
        """Calculate perp-spot basis features"""
        if 'close_perp' not in dataframe.columns:
            print("No perp data available for basis calculation")
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

        print(f"Basis stats - Mean: {dataframe['basis'].mean():.4f}, Std: {dataframe['basis'].std():.4f}")
        print(f"Basis Z-score range: {dataframe['basis_zscore'].min():.2f} to {dataframe['basis_zscore'].max():.2f}")

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
        pair = metadata['pair']
        
        print(f"\n=== ENTRY LOGIC DEBUG for {pair} ===")
        print(f"Dataframe shape in entry: {dataframe.shape}")
        
        # Check for FreqAI signal
        if '&-enter_long' in dataframe.columns:
            freqai_signal = dataframe['&-enter_long'].iloc[-1]
            threshold = self.freqai_prediction_threshold.value
            print(f"FreqAI signal: {freqai_signal}, Threshold: {threshold}")
            
            if freqai_signal > threshold:
                print(f"FreqAI signal triggered! Setting enter_long=1")
                dataframe.loc[dataframe.index[-1], 'enter_long'] = 1
            else:
                print(f"FreqAI signal below threshold")
        else:
            print("No FreqAI signal column found!")
            
            # Alternative entry logic for testing without FreqAI
            print("Using alternative entry logic...")
            
            # Simple RSI + EMA crossover entry
            rsi_condition = dataframe['rsi'] < 30  # Oversold
            ema_condition = dataframe['ema_20'] > dataframe['ema_50']  # Uptrend
            
            entry_condition = rsi_condition & ema_condition
            
            if entry_condition.iloc[-1]:
                print("Alternative entry condition met!")
                dataframe.loc[dataframe.index[-1], 'enter_long'] = 1
            else:
                print("Alternative entry condition not met")

        # Debug: Check if any entry signals were set
        entry_signals = dataframe['enter_long'].sum() if 'enter_long' in dataframe.columns else 0
        print(f"Total entry signals in dataframe: {entry_signals}")
        
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

    # FreqAI configuration - same as original
    freqai_info = {
        "identifier": "SKLearnRandomForestClassifier",
        "features": [
            "rsi",
            "adx", 
            "ema_20",
            "ema_50",
            "macd",
            "macdsignal",
            "macdhist",
            "volume_ratio_ma",
            "obv",
            "vwap",
        ],
        "label_period_candles": 12, # Predict 1 hour into the future
        "data_split_parameters": {"split_train": 0.8, "split_test": 0.2},
        "model_training_parameters": {}
    }