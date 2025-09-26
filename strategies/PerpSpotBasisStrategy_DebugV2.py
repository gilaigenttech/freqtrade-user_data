# Enhanced Perp-Spot Basis Trading Strategy with Debug
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import pandas as pd
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, 
                              DecimalParameter, IntParameter, RealParameter)
import talib.abstract as ta
import pandas_ta as pta
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PerpSpotBasisStrategy_DebugV2(IStrategy):
    """
    Debug version to see what's happening with signals
    """
    INTERFACE_VERSION: int = 3

    # Timeframe
    timeframe = "5m"
    
    # ROI table - take profits at different time intervals
    minimal_roi = {
        "0": 0.15,     # 15% at any time
        "30": 0.08,    # 8% after 30 minutes
        "60": 0.04,    # 4% after 1 hour
        "120": 0       # 0% (hold) after 2 hours
    }

    # Stop loss
    stoploss = -0.08  # 8% stop loss

    # Process only new candles
    process_only_new_candles = True

    # FreqAI configuration
    freqai_label_period = 12
    freqai_min_return = 0.003

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Basic indicators
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['adx'] = ta.ADX(dataframe)
        
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_width'] = dataframe['bb_upperband'] - dataframe['bb_lowerband']
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']
        
        # Volume analysis
        dataframe['volume_sma'] = dataframe['volume'].rolling(window=20).mean()
        
        # Try to load futures data for basis calculation  
        try:
            futures_data = self.dp.get_pair_dataframe(
                pair=f"{metadata['pair'].split('/')[0]}/USDT:USDT",  # BTC/USDT -> BTC/USDT:USDT
                timeframe=self.timeframe
            )
            
            if len(futures_data) > 0:
                # Merge by timestamp
                merged = pd.merge(dataframe.reset_index(), futures_data[['date', 'close']].rename(columns={'close': 'futures_close'}), 
                                on='date', how='left')
                
                # Calculate basis
                basis = (merged['close'] - merged['futures_close']) / merged['futures_close'] * 100
                dataframe['basis'] = basis.values
                
                # Calculate basis statistics
                dataframe['basis_ma'] = dataframe['basis'].rolling(20).mean()
                dataframe['basis_std'] = dataframe['basis'].rolling(20).std()
                dataframe['basis_zscore'] = (dataframe['basis'] - dataframe['basis_ma']) / dataframe['basis_std']
                
                logger.info(f"Loaded futures data for {metadata['pair']} - basis calculated")
            else:
                dataframe['basis'] = 0
                dataframe['basis_ma'] = 0
                dataframe['basis_std'] = 1
                dataframe['basis_zscore'] = 0
                logger.warning(f"No futures data for {metadata['pair']}")
        except Exception as e:
            logger.error(f"Error loading futures data for {metadata['pair']}: {e}")
            dataframe['basis'] = 0
            dataframe['basis_ma'] = 0
            dataframe['basis_std'] = 1
            dataframe['basis_zscore'] = 0
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Very simple entry conditions for debugging
        conditions = [
            dataframe['volume'] > 0,  # Basic volume filter
        ]
        
        # Simple RSI oversold condition
        basic_condition = dataframe['rsi'] < 40
        
        dataframe.loc[
            basic_condition &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        # Count signals for debugging
        total_signals = dataframe['enter_long'].sum()
        logger.info(f"{metadata['pair']}: Generated {total_signals} entry signals")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Simple exit conditions
        dataframe.loc[
            dataframe['rsi'] > 60,
            'exit_long'
        ] = 1
        
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """Set FreqAI targets with simple logic"""
        # Calculate future returns
        future_return = dataframe["close"].shift(-self.freqai_label_period) / dataframe["close"] - 1
        
        # Simple labeling
        dataframe["&-enter_long"] = np.where(
            future_return > self.freqai_min_return,
            "enter",
            "hold"
        )
        
        dataframe["&-enter_long"] = dataframe["&-enter_long"].fillna("hold")
        
        return dataframe

    # FreqAI configuration - match config.json identifier
    freqai_info = {
        "identifier": "MyFreqAIModel_Enhanced",
        "features": [
            "%-rsi", "%-adx", "%-bb_width", "%-macd",
            "%-basis", "%-basis_zscore", "%-volume_sma"
        ],
        "label_period_candles": freqai_label_period,
        "data_split_parameters": {"test_size": 0.2, "shuffle": False},
        "model_training_parameters": {
            "n_estimators": 50,
            "max_depth": 5,
            "random_state": 42,
            "n_jobs": -1
        }
    }