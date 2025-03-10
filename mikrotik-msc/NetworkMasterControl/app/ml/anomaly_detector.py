# File: app/ml/anomaly_detector.py
from sklearn.ensemble import IsolationForest
import joblib

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.01)

    def train(self, data):
        self.model.fit(data)
        joblib.dump(self.model, 'anomaly_model.pkl')

    def predict(self, sample):
        return self.model.predict([sample])
