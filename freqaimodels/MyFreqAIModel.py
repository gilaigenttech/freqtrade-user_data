from typing import Any

import numpy as np
import pandas as pd
from pandas import DataFrame
from sklearn.ensemble import RandomForestClassifier

from freqtrade.freqai.base_models.BaseClassifierModel import BaseClassifierModel
from freqtrade.freqai.data_kitchen import FreqaiDataKitchen


class MyFreqAIModel(BaseClassifierModel):
    """Custom RandomForest-based classifier avoiding label-encoder pitfalls."""

    def fit(self, data_dictionary: dict, dk: FreqaiDataKitchen, **kwargs) -> Any:
        X = data_dictionary["train_features"].to_numpy()
        y = data_dictionary["train_labels"].to_numpy()[:, 0]
        sample_weights = data_dictionary.get("train_weights")

        params = {
            "n_estimators": 100,
            "random_state": 42,
        }
        params.update(self.model_training_parameters)

        model = RandomForestClassifier(**params)
        if sample_weights is not None:
            model.fit(X=X, y=y, sample_weight=sample_weights)
        else:
            model.fit(X=X, y=y)

        return model

    def predict(
        self, unfiltered_df: DataFrame, dk: FreqaiDataKitchen, **kwargs
    ) -> tuple[DataFrame, np.ndarray]:
        dk.find_features(unfiltered_df)
        filtered_df, _ = dk.filter_features(
            unfiltered_df, dk.training_features_list, training_filter=False
        )

        dk.data_dictionary["prediction_features"] = filtered_df

        (
            dk.data_dictionary["prediction_features"],
            outliers,
            _,
        ) = dk.feature_pipeline.transform(
            dk.data_dictionary["prediction_features"], outlier_check=True
        )

        predictions = self.model.predict(dk.data_dictionary["prediction_features"])
        if self.CONV_WIDTH == 1:
            predictions = np.reshape(predictions, (-1, len(dk.label_list)))

        pred_df = pd.DataFrame(predictions, columns=dk.label_list)
        for label in dk.label_list:
            pred_df[label] = pred_df[label].astype(str)

        proba = self.model.predict_proba(dk.data_dictionary["prediction_features"])
        if self.CONV_WIDTH == 1:
            proba = np.reshape(proba, (-1, len(self.model.classes_)))

        class_names = [str(cls) for cls in self.model.classes_]
        proba_df = pd.DataFrame(proba, columns=class_names)

        pred_df = pd.concat([pred_df, proba_df], axis=1)

        if dk.feature_pipeline["di"]:
            dk.DI_values = dk.feature_pipeline["di"].di_values
        else:
            dk.DI_values = np.zeros(outliers.shape[0])
        dk.do_predict = outliers

        return pred_df, dk.do_predict