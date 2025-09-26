from typing import Any
import numpy as np
import pandas as pd
from pandas import DataFrame
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import warnings
warnings.filterwarnings('ignore')

from freqtrade.freqai.base_models.BaseClassifierModel import BaseClassifierModel
from freqtrade.freqai.data_kitchen import FreqaiDataKitchen


class MyFreqAIModel_Enhanced(BaseClassifierModel):
    """
    Enhanced RandomForest-based classifier with feature selection and improved preprocessing
    """

    def fit(self, data_dictionary: dict, dk: FreqaiDataKitchen, **kwargs) -> Any:
        """
        Enhanced fit method with feature selection and better preprocessing
        """
        X = data_dictionary["train_features"]
        y = data_dictionary["train_labels"].values.ravel()
        sample_weights = data_dictionary.get("train_weights")

        # Handle string labels
        self.label_encoder = LabelEncoder()
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Feature selection to reduce overfitting
        if X.shape[1] > 10:  # Only if we have many features
            self.feature_selector = SelectKBest(score_func=f_classif, k=min(12, X.shape[1]))
            X_selected = self.feature_selector.fit_transform(X, y_encoded)
        else:
            self.feature_selector = None
            X_selected = X.values if hasattr(X, 'values') else X

        # Enhanced model parameters
        params = {
            "n_estimators": 150,
            "max_depth": 10,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
            "bootstrap": True,
            "random_state": 42,
            "n_jobs": -1,
            "class_weight": "balanced"  # Handle imbalanced data
        }
        
        # Override with user parameters
        params.update(self.model_training_parameters)

        # Create and train model
        self.model = RandomForestClassifier(**params)
        
        if sample_weights is not None:
            self.model.fit(X_selected, y_encoded, sample_weight=sample_weights)
        else:
            self.model.fit(X_selected, y_encoded)

        # Feature importance analysis
        if hasattr(self.model, 'feature_importances_'):
            feature_names = X.columns if hasattr(X, 'columns') else [f'feature_{i}' for i in range(X.shape[1])]
            if self.feature_selector is not None:
                selected_features = self.feature_selector.get_support()
                feature_names = [name for i, name in enumerate(feature_names) if selected_features[i]]
            
            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            dk.data["feature_importance"] = importance_df
            print(f"Top 5 most important features:")
            print(importance_df.head().to_string(index=False))

        return self.model

    def predict(self, unfiltered_df: DataFrame, dk: FreqaiDataKitchen, **kwargs) -> tuple[DataFrame, np.ndarray]:
        """
        Enhanced prediction with proper feature selection and preprocessing
        """
        # Prepare features
        dk.find_features(unfiltered_df)
        filtered_df, _ = dk.filter_features(
            unfiltered_df, dk.training_features_list, training_filter=False
        )

        dk.data_dictionary["prediction_features"] = filtered_df

        # Apply feature pipeline
        (
            dk.data_dictionary["prediction_features"],
            outliers,
            _,
        ) = dk.feature_pipeline.transform(
            dk.data_dictionary["prediction_features"], outlier_check=True
        )

        # Apply feature selection if used during training
        X = dk.data_dictionary["prediction_features"]
        if hasattr(self, 'feature_selector') and self.feature_selector is not None:
            X_selected = self.feature_selector.transform(X)
        else:
            X_selected = X.values if hasattr(X, 'values') else X

        # Get predictions
        predictions = self.model.predict(X_selected)
        probabilities = self.model.predict_proba(X_selected)

        # Decode predictions back to original labels
        if hasattr(self, 'label_encoder'):
            predictions_decoded = self.label_encoder.inverse_transform(predictions)
        else:
            predictions_decoded = predictions

        # Reshape if necessary
        if self.CONV_WIDTH == 1:
            predictions_decoded = np.reshape(predictions_decoded, (-1, len(dk.label_list)))
            probabilities = np.reshape(probabilities, (-1, len(self.model.classes_)))

        # Create prediction DataFrame
        pred_df = pd.DataFrame(predictions_decoded, columns=dk.label_list)
        
        # Add probability columns
        if hasattr(self, 'label_encoder'):
            class_names = self.label_encoder.classes_
        else:
            class_names = [str(cls) for cls in self.model.classes_]
        
        proba_df = pd.DataFrame(probabilities, columns=class_names)
        
        # Combine predictions and probabilities
        pred_df = pd.concat([pred_df, proba_df], axis=1)

        # Set outlier detection
        if dk.feature_pipeline["di"]:
            dk.DI_values = dk.feature_pipeline["di"].di_values
        else:
            dk.DI_values = np.zeros(outliers.shape[0])
        dk.do_predict = outliers

        return pred_df, dk.do_predict