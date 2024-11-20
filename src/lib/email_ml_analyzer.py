import re
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder

from src.lib.email_classifier import EmailAnalyzer


class MLEmailAnalyzer:
    def __init__(self):
        self.category_classifier = None
        self.merchant_classifier = None
        self.amount_predictor = None
        self.label_encoders = {}
        self.vectorizer = None

    def prepare_training_data(self, emails: List[Dict]) -> Tuple[pd.DataFrame, Dict]:
        processed_data = []

        for email in emails:
            # Combine subject and content
            text = f"{email.get('subject', '')} {email.get('content', '')}"

            # Extract features
            features = {
                "text": text,
                "sender": email.get("sender", "").lower(),
                "date": pd.to_datetime(email.get("date")),
                "day_of_week": pd.to_datetime(email.get("date")).dayofweek,
                "hour": pd.to_datetime(email.get("date")).hour,
                "length": len(text),
                "has_amount": bool(
                    re.search(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", text)
                ),
                "has_card_number": bool(
                    re.search(
                        r"(?:card|cc)(?:\s+account)?\s+(?:\d{4}\s+)?(?:X{4}\s+){2,3}(\d{4})",
                        text,
                    )
                ),
                "has_merchant": bool(
                    re.search(
                        r"at\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s*\.\s*|\s*$)", text
                    )
                ),
            }

            # Extract labels from existing rule-based system
            base_analyzer = EmailAnalyzer()
            transaction = base_analyzer._extract_transaction_details(
                text, email.get("date")
            )

            if transaction:
                features.update(
                    {
                        "category": transaction.get("category", "others"),
                        "merchant": transaction.get("merchant", "unknown"),
                        "amount": transaction.get("amount", 0.0),
                        "payment_mode": transaction.get("payment_mode", "unknown"),
                    }
                )
                processed_data.append(features)

        # Convert to DataFrame
        df = pd.DataFrame(processed_data)

        # Create label encoders for categorical variables
        categorical_columns = ["category", "merchant", "payment_mode", "sender"]
        encoders = {}

        for col in categorical_columns:
            if col in df.columns:
                encoder = LabelEncoder()
                df[f"{col}_encoded"] = encoder.fit_transform(df[col])
                encoders[col] = encoder

        return df, encoders

    def train_models(self, training_data: pd.DataFrame) -> None:
        # Initialize TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=5000, ngram_range=(1, 2), stop_words="english"
        )

        # Prepare text features
        X_text = self.vectorizer.fit_transform(training_data["text"])

        # Prepare additional features
        additional_features = training_data[
            [
                "day_of_week",
                "hour",
                "length",
                "has_amount",
                "has_card_number",
                "has_merchant",
            ]
        ].values
        X_combined = np.hstack((X_text.toarray(), additional_features))

        # Train Category Classifier
        y_category = training_data["category_encoded"]
        self.category_classifier = RandomForestClassifier(
            n_estimators=100, random_state=42
        )
        self.category_classifier.fit(X_combined, y_category)

        # Train Merchant Classifier
        y_merchant = training_data["merchant_encoded"]
        self.merchant_classifier = RandomForestClassifier(
            n_estimators=100, random_state=42
        )
        self.merchant_classifier.fit(X_combined, y_merchant)

        # Train Amount Predictor (for transactions)
        transaction_mask = training_data["amount"] > 0
        if transaction_mask.any():
            X_transactions = X_combined[transaction_mask]
            y_amount = training_data.loc[transaction_mask, "amount"]
            self.amount_predictor = RandomForestClassifier(
                n_estimators=100, random_state=42
            )
            self.amount_predictor.fit(X_transactions, y_amount)

    def predict(self, email: Dict) -> Dict:
        # Prepare features
        text = f"{email.get('subject', '')} {email.get('content', '')}"
        features = {
            "text": text,
            "date": pd.to_datetime(email.get("date")),
            "day_of_week": pd.to_datetime(email.get("date")).dayofweek,
            "hour": pd.to_datetime(email.get("date")).hour,
            "length": len(text),
            "has_amount": bool(
                re.search(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", text)
            ),
            "has_card_number": bool(
                re.search(
                    r"(?:card|cc)(?:\s+account)?\s+(?:\d{4}\s+)?(?:X{4}\s+){2,3}(\d{4})",
                    text,
                )
            ),
            "has_merchant": bool(
                re.search(
                    r"at\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s*\.\s*|\s*$)", text
                )
            ),
        }

        # Transform features
        X_text = self.vectorizer.transform([text])
        X_additional = np.array(
            [
                [
                    features["day_of_week"],
                    features["hour"],
                    features["length"],
                    features["has_amount"],
                    features["has_card_number"],
                    features["has_merchant"],
                ]
            ]
        )
        X_combined = np.hstack((X_text.toarray(), X_additional))

        # Make predictions
        predictions = {
            "category": self.label_encoders["category"].inverse_transform(
                self.category_classifier.predict(X_combined)
            )[0],
            "merchant": self.label_encoders["merchant"].inverse_transform(
                self.merchant_classifier.predict(X_combined)
            )[0],
        }

        # Predict amount if it's a transaction
        if features["has_amount"] and self.amount_predictor:
            predictions["predicted_amount"] = self.amount_predictor.predict(X_combined)[
                0
            ]

        # Add confidence scores
        predictions["category_confidence"] = np.max(
            self.category_classifier.predict_proba(X_combined)
        )
        predictions["merchant_confidence"] = np.max(
            self.merchant_classifier.predict_proba(X_combined)
        )

        return predictions


class HybridEmailAnalyzer:
    def __init__(self):
        self.rule_based = EmailAnalyzer()
        self.ml_based = MLEmailAnalyzer()
        self.is_trained = False

    def train(self, training_emails: List[Dict]) -> None:
        training_data, encoders = self.ml_based.prepare_training_data(training_emails)
        self.ml_based.label_encoders = encoders
        self.ml_based.train_models(training_data)
        self.is_trained = True

    def analyze_email(self, email: Dict) -> Dict:
        # Get rule-based analysis
        rule_based_result = self._get_rule_based_analysis(email)

        # Get ML-based analysis if trained
        ml_based_result = {}
        if self.is_trained:
            ml_based_result = self.ml_based.predict(email)

        # Combine results with confidence weighting
        combined_result = self._combine_analyses(rule_based_result, ml_based_result)

        return combined_result

    def _get_rule_based_analysis(self, email: Dict) -> Dict:
        content = f"{email.get('subject', '')} {email.get('content', '')}"
        transaction = self.rule_based._extract_transaction_details(
            content, email.get("date")
        )

        if transaction:
            return {
                "category": transaction.get("category"),
                "merchant": transaction.get("merchant"),
                "amount": transaction.get("amount"),
                "payment_mode": transaction.get("payment_mode"),
                "is_transaction": True,
            }
        return {"is_transaction": False}

    def _combine_analyses(self, rule_based: Dict, ml_based: Dict) -> Dict:
        if not ml_based:
            return rule_based

        result = {}

        # Combine category predictions
        if rule_based.get("category") and ml_based.get("category"):
            if ml_based["category_confidence"] > 0.8:
                result["category"] = ml_based["category"]
            else:
                result["category"] = rule_based["category"]

        # Combine merchant predictions
        if rule_based.get("merchant") and ml_based.get("merchant"):
            if ml_based["merchant_confidence"] > 0.8:
                result["merchant"] = ml_based["merchant"]
            else:
                result["merchant"] = rule_based["merchant"]

        # Use rule-based amount if available, otherwise use ML prediction
        result["amount"] = rule_based.get("amount") or ml_based.get("predicted_amount")

        # Keep additional fields from rule-based analysis
        result["payment_mode"] = rule_based.get("payment_mode")
        result["is_transaction"] = rule_based.get("is_transaction", False)

        # Add confidence scores
        result["ml_confidence"] = {
            "category": ml_based.get("category_confidence"),
            "merchant": ml_based.get("merchant_confidence"),
        }

        return result

    def evaluate_model(self, test_emails: List[Dict]) -> Dict:
        predictions = []
        actuals = []

        for email in test_emails:
            # Get predictions
            pred = self.analyze_email(email)
            predictions.append(pred)

            # Get actual values using rule-based system as ground truth
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            actual = self.rule_based._extract_transaction_details(
                content, email.get("date")
            )
            actuals.append(actual)

        # Calculate metrics
        metrics = {
            "category_accuracy": sum(
                1
                for p, a in zip(predictions, actuals)
                if p.get("category") == a.get("category")
            )
            / len(predictions),
            "merchant_accuracy": sum(
                1
                for p, a in zip(predictions, actuals)
                if p.get("merchant") == a.get("merchant")
            )
            / len(predictions),
            "amount_mae": np.mean(
                [
                    abs(p.get("amount", 0) - a.get("amount", 0))
                    for p, a in zip(predictions, actuals)
                ]
            ),
            "transaction_detection": sum(
                1
                for p, a in zip(predictions, actuals)
                if p.get("is_transaction") == bool(a)
            )
            / len(predictions),
        }

        return metrics
