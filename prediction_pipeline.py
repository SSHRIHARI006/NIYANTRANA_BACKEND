import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
import joblib

class PredictionPipeline:
    """
    A pipeline to load the trained model and scalers, and make predictions.
    """
    def __init__(self, model_path, feature_scaler_path, target_scaler_path):
        try:
            self.model = load_model(model_path)
            self.feature_scaler = joblib.load(feature_scaler_path)
            self.target_scaler = joblib.load(target_scaler_path)
            self.lookback = self.model.input_shape[1]
            self.feature_names = self.feature_scaler.get_feature_names_out()
            print(f"Pipeline initialized successfully for model: {model_path}")
        except Exception as e:
            print(f"Error initializing pipeline for {model_path}: {e}")
            raise

    def predict(self, input_df: pd.DataFrame) -> float:
        """
        Makes a single prediction based on the last 'lookback' days of data.
        """
        if len(input_df) != self.lookback:
            raise ValueError(f"Input DataFrame must have exactly {self.lookback} rows. Got {len(input_df)}.")
        
        # Ensure correct column order
        input_features = input_df[self.feature_names]

        scaled_features = self.feature_scaler.transform(input_features)
        input_tensor = np.expand_dims(scaled_features, axis=0)
        scaled_prediction = self.model.predict(input_tensor, verbose=0)[0][0]
        final_prediction = self.target_scaler.inverse_transform([[scaled_prediction]])[0][0]
        
        return float(final_prediction)