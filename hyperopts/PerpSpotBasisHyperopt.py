#!/usr/bin/env python3
"""
Hyperopt configuration for PerpSpotBasisStrategy_Enhanced
This file defines the hyperopt search space and loss function
"""

from freqtrade.optimize.hyperopt_interface import IHyperOpt
from freqtrade.optimize.space import Categorical, Dimension, Integer, SKDecimal
import numpy as np

class PerpSpotBasisHyperopt(IHyperOpt):
    """
    Hyperopt class for optimizing the PerpSpotBasisStrategy_Enhanced strategy
    """

    @staticmethod
    def buy_strategy_generator(params) -> dict:
        """
        Generate the buy strategy based on hyperopt parameters
        """
        return {
            'freqai_prediction_threshold': params['freqai_prediction_threshold'],
            'signal_quality_threshold': params['signal_quality_threshold'],
            'basis_volatility_threshold': params['basis_volatility_threshold'],
            'volume_confirmation_multiplier': params['volume_confirmation_multiplier'],
            'rsi_oversold_threshold': params['rsi_oversold_threshold'],
            'max_drawdown_threshold': params['max_drawdown_threshold'],
            'position_size_multiplier': params['position_size_multiplier'],
        }

    @staticmethod
    def sell_strategy_generator(params) -> dict:
        """
        Generate the sell strategy based on hyperopt parameters
        """
        return {
            'rsi_overbought_threshold': params['rsi_overbought_threshold'],
        }

    @staticmethod
    def indicator_space() -> list:
        """
        Define the hyperopt search space for indicators/parameters
        """
        return [
            # FreqAI prediction threshold
            SKDecimal(0.55, 0.85, decimals=2, name='freqai_prediction_threshold'),
            
            # Signal quality threshold
            SKDecimal(0.4, 0.7, decimals=2, name='signal_quality_threshold'),
            
            # Basis volatility threshold
            SKDecimal(0.02, 0.08, decimals=3, name='basis_volatility_threshold'),
            
            # Volume confirmation multiplier
            SKDecimal(1.3, 2.5, decimals=1, name='volume_confirmation_multiplier'),
            
            # RSI thresholds
            Integer(25, 35, name='rsi_oversold_threshold'),
            Integer(65, 75, name='rsi_overbought_threshold'),
            
            # Risk management
            SKDecimal(0.06, 0.12, decimals=2, name='max_drawdown_threshold'),
            SKDecimal(0.7, 1.3, decimals=2, name='position_size_multiplier'),
        ]

    @staticmethod
    def generate_roi_table(params) -> dict:
        """
        Generate ROI table based on hyperopt parameters
        """
        roi_t1 = params.get('roi_t1', 60)
        roi_t2 = params.get('roi_t2', 30)
        roi_t3 = params.get('roi_t3', 20)
        roi_p1 = params.get('roi_p1', 0.01)
        roi_p2 = params.get('roi_p2', 0.03)
        roi_p3 = params.get('roi_p3', 0.06)

        return {
            "0": roi_p1 + roi_p2 + roi_p3,
            str(roi_t3): roi_p2 + roi_p3,
            str(roi_t3 + roi_t2): roi_p3,
            str(roi_t3 + roi_t2 + roi_t1): 0
        }

    @staticmethod
    def roi_space() -> list:
        """
        Define the ROI search space
        """
        return [
            Integer(10, 40, name='roi_t1'),
            Integer(10, 30, name='roi_t2'), 
            Integer(10, 20, name='roi_t3'),
            SKDecimal(0.01, 0.04, decimals=3, name='roi_p1'),
            SKDecimal(0.02, 0.08, decimals=3, name='roi_p2'),
            SKDecimal(0.04, 0.15, decimals=3, name='roi_p3'),
        ]

    @staticmethod
    def stoploss_space() -> list:
        """
        Define the stoploss search space
        """
        return [
            SKDecimal(-0.12, -0.05, decimals=3, name='stoploss'),
        ]

    @staticmethod
    def trailing_space() -> list:
        """
        Define trailing stoploss search space
        """
        return [
            # Trailing stop is disabled in our strategy, but can be enabled
            Categorical([True, False], name='trailing_stop'),
            SKDecimal(0.01, 0.05, decimals=3, name='trailing_stop_positive'),
            SKDecimal(0.01, 0.03, decimals=3, name='trailing_stop_positive_offset'),
            Categorical([True, False], name='trailing_only_offset_is_reached'),
        ]

    def populate_indicators(self, dataframe, metadata):
        """
        This method should not be overridden.
        """
        pass

    def buy_strategy(self, dataframe, metadata):
        """
        This method should not be overridden.
        """
        pass

    def sell_strategy(self, dataframe, metadata):
        """
        This method should not be overridden.
        """
        pass