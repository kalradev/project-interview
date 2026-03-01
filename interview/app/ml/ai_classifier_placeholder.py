"""
Placeholder for training ai_classifier.pkl.

To create app/ml/ai_classifier.pkl, run a training script that:
1. Uses AITextDetector().feature_vector(text) for each sample (or same feature extraction).
2. Collects features + labels (0=human, 1=AI).
3. Trains a classifier (e.g. sklearn.ensemble.RandomForestClassifier).
4. Saves with joblib: joblib.dump({"classifier": clf, "vectorizer": None}, "app/ml/ai_classifier.pkl")

Without the file, AITextDetector uses the heuristic fallback.
"""
