import os
import pickle
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from config import Config


class LengthOfStayClassifier:
    """
    Care & Foster Triage: Predictive Length-of-Stay (LOS) Classifier.
    Gradient Boosting Ensemble Model predicting adoption risk category across all species:
      - Class 1: Low Risk (High probability of fast adoption < 30 days)
      - Class 0: High Risk (Risk of prolonged shelter stay >= 30 days requiring proactive foster care/media promotion)
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.metrics = {}
        self.model_path = os.path.join(Config.MODEL_DIR, 'los_gb_model.pkl')
        self.scaler_path = os.path.join(Config.MODEL_DIR, 'scaler.pkl')
        self.encoders_path = os.path.join(Config.MODEL_DIR, 'encoders.pkl')
        self.metrics_path = os.path.join(Config.MODEL_DIR, 'model_metrics.json')
        
    def _prepare_features(self, df, is_training=False):
        """Preprocesses tabular dataframe into scaled feature matrices for multi-species companions."""
        df_processed = df.copy()
        
        categorical_cols = ['species', 'size', 'coat_color', 'intake_season']
        
        for col in categorical_cols:
            if col not in df_processed.columns:
                df_processed[col] = 'Standard'
                
            if is_training:
                le = LabelEncoder()
                df_processed[col] = le.fit_transform(df_processed[col].astype(str))
                self.label_encoders[col] = le
            else:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    mapping = dict(zip(le.classes_, le.transform(le.classes_)))
                    df_processed[col] = df_processed[col].astype(str).map(mapping).fillna(0).astype(int)
                else:
                    df_processed[col] = 0

        # Fill any missing numerical fields with species-aware defaults
        num_defaults = {
            'age_months': 24, 'size': 1, 'energy_level': 5, 'trainability': 5, 'drive_level': 5,
            'vocalization_level': 4, 'separation_anxiety_risk': 3, 'leash_reactivity_score': 2,
            'cat_friendly_score': 6, 'dog_friendly_score': 6, 'space_needed': 4, 'yard_needed': 0,
            'exercise_needed_hours': 1.0, 'child_friendly_min_age': 0, 'grooming_needed': 4,
            'setup_budget_needed': 5, 'budget_needed': 4, 'sociability': 6, 'surrender_history': 0,
            'special_medical_needs': 0, 'shelter_capacity_utilization_pct': 70.0, 'adoption_fee': 75
        }
        for col, val in num_defaults.items():
            if col not in df_processed.columns:
                df_processed[col] = val

        feature_cols = [
            'age_months', 'size', 'energy_level', 'trainability', 'drive_level',
            'vocalization_level', 'separation_anxiety_risk', 'leash_reactivity_score',
            'cat_friendly_score', 'dog_friendly_score', 'space_needed', 'yard_needed',
            'exercise_needed_hours', 'child_friendly_min_age', 'grooming_needed',
            'setup_budget_needed', 'budget_needed', 'sociability', 'surrender_history',
            'special_medical_needs', 'shelter_capacity_utilization_pct', 'adoption_fee',
            'species', 'coat_color', 'intake_season'
        ]
        
        X = df_processed[feature_cols]
        return X, feature_cols

    def train(self, csv_path=None):
        """Trains Gradient Boosting Classifier to achieve >= 90% accuracy & precision."""
        if csv_path is None:
            csv_path = Config.CSV_DATA_PATH
            
        df = pd.read_csv(csv_path)
        
        # Target: Class 1 (< 30 days), Class 0 (>= 30 days)
        y = (df['length_of_stay_days'] < Config.LOS_HIGH_RISK_DAYS).astype(int)
        
        X, feature_cols = self._prepare_features(df, is_training=True)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Gradient Boosting Classifier
        self.model = GradientBoostingClassifier(
            n_estimators=180,
            learning_rate=0.08,
            max_depth=4,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate performance metrics
        y_pred = self.model.predict(X_test_scaled)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        self.metrics = {
            'algorithm': 'Gradient Boosting Classifier (Ensemble)',
            'accuracy': round(acc, 4),
            'precision': round(prec, 4),
            'recall': round(rec, 4),
            'f1_score': round(f1, 4),
            'accuracy_percentage': round(acc * 100, 2),
            'precision_percentage': round(prec * 100, 2),
            'samples_trained': len(X_train),
            'samples_tested': len(X_test)
        }
        
        self.save_model()
        print(f"Care & Foster Triage Model Trained! Accuracy: {acc*100:.2f}%, Precision: {prec*100:.2f}%")
        return self.metrics

    def save_model(self):
        """Saves trained model, scaler, encoders, and metrics to disk."""
        os.makedirs(Config.MODEL_DIR, exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        with open(self.encoders_path, 'wb') as f:
            pickle.dump(self.label_encoders, f)
        with open(self.metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def load_model(self):
        """Loads trained model artifacts from disk if they exist."""
        if (os.path.exists(self.model_path) and
            os.path.exists(self.scaler_path) and
            os.path.exists(self.encoders_path)):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                with open(self.encoders_path, 'rb') as f:
                    self.label_encoders = pickle.load(f)
                if os.path.exists(self.metrics_path):
                    with open(self.metrics_path, 'r') as f:
                        self.metrics = json.load(f)
                return True
            except Exception as e:
                print(f"Warning: Failed to load existing model artifacts: {e}")
                return False
        return False

    def predict_batch(self, animals_list):
        """Vectorized batch prediction for multiple animal profiles."""
        if not animals_list:
            return []
            
        if self.model is None or self.scaler is None:
            if not self.load_model():
                self.train()
                
        df_batch = pd.DataFrame(animals_list)
        X_batch, _ = self._prepare_features(df_batch, is_training=False)
        X_scaled = self.scaler.transform(X_batch)
        
        pred_classes = self.model.predict(X_scaled)
        probs = self.model.predict_proba(X_scaled)
        
        results = []
        for i, pred_class in enumerate(pred_classes):
            pred_int = int(pred_class)
            prob_row = probs[i]
            # Probabilities: index 1 is Class 1 (adoption <30d), index 0 is Class 0 (stay >=30d)
            adoption_prob = float(prob_row[1]) if len(prob_row) > 1 else float(pred_int)
            risk_prob = float(prob_row[0]) if len(prob_row) > 1 else 1.0 - float(pred_int)
            is_high_risk = (pred_int == 0)
            
            results.append({
                'predicted_class': pred_int,
                'class_label': 'High Stay Risk (≥30d Expected — Triage Priority)' if is_high_risk else 'Low Stay Risk (<30d Expected — Fast Track)',
                'adoption_probability': round(adoption_prob * 100, 1),
                'prolonged_stay_risk': round(risk_prob * 100, 1),
                'is_high_risk': is_high_risk,
                'recommended_action': 'PROACTIVE_FOSTER_AND_MEDIA_TRIAGE' if is_high_risk else 'STANDARD_ADOPTION_PIPELINE'
            })
        return results

    def predict(self, animal_data):
        """Predicts length-of-stay binary risk class for a single animal dict."""
        return self.predict_batch([animal_data])[0]
