import logging
from typing import Dict, List, Optional

import joblib

from src.lib.email_ml_analyzer import HybridEmailAnalyzer
from src.models.email_analyzer import (
    AnalysisResponse,
    BatchAnalysisResponse,
    BatchSummary,
    EmailInput,
    ModelParameters,
    TrainingMetrics,
    TrainingResponse,
)
from src.secrets import secrets


class AnalyzerService:
    def __init__(self):
        self.analyzer = HybridEmailAnalyzer()
        self.model_version = secrets["ml_app_name"]
        self.is_trained = False
        self.model_path = secrets["model_path"]
        self.load_model()  # Changed from _load_model to load_model

    def load_model(self) -> None:
        try:
            self.model_path.mkdir(exist_ok=True)
            model_file = self.model_path / f"email_analyzer_{self.model_version}.joblib"
            if model_file.exists():
                self.analyzer = joblib.load(model_file)
                self.is_trained = True
                logging.info(f"Loaded model version {self.model_version}")
            else:
                logging.info("No pre-trained model found. Starting with fresh model.")
        except Exception as e:
            logging.exception(f"Error loading model: {str(e)}")
            self.is_trained = False

    async def save_model(self) -> None:
        try:
            self.model_path.mkdir(exist_ok=True)
            model_file = self.model_path / f"email_analyzer_{self.model_version}.joblib"
            joblib.dump(self.analyzer, model_file)
            logging.info(f"Saved model version {self.model_version}")
        except Exception as e:
            logging.exception(f"Error saving model: {str(e)}")
            raise

    async def analyze_email(self, email: EmailInput) -> AnalysisResponse:
        if not self.is_trained:
            raise ValueError("Model not trained")

        try:
            # Convert Pydantic model to dict
            email_dict = {
                "subject": email.subject,
                "content": email.content,
                "sender": email.sender,
                "date": email.date.isoformat(),
            }

            result = self.analyzer.analyze_email(email_dict)
            return AnalysisResponse(
                category=result.get("category"),
                merchant=result.get("merchant"),
                amount=result.get("amount"),
                payment_mode=result.get("payment_mode"),
                is_transaction=result.get("is_transaction", False),
                confidence_scores=result.get("ml_confidence"),
            )
        except Exception as e:
            logging.exception(f"Error analyzing email: {str(e)}")
            raise

    async def analyze_batch(self, emails: List[EmailInput]) -> BatchAnalysisResponse:
        if not self.is_trained:
            raise ValueError("Model not trained")

        try:
            results = []
            total_amount = 0.0
            categories: Dict[str, int] = {}
            merchants: Dict[str, int] = {}

            for email in emails:
                result = await self.analyze_email(email)
                results.append(result)

                if result.is_transaction:
                    if result.amount:
                        total_amount += result.amount
                    if result.category:
                        categories[result.category] = (
                            categories.get(result.category, 0) + 1
                        )
                    if result.merchant:
                        merchants[result.merchant] = (
                            merchants.get(result.merchant, 0) + 1
                        )

            summary = BatchSummary(
                total_emails=len(emails),
                total_transactions=sum(1 for r in results if r.is_transaction),
                total_amount=total_amount,
                top_categories=dict(
                    sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
                ),
                top_merchants=dict(
                    sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:5]
                ),
            )

            return BatchAnalysisResponse(results=results, summary=summary)

        except Exception as e:
            logging.exception(f"Error analyzing batch: {str(e)}")
            raise

    async def train_model(
        self,
        training_data: List[EmailInput],
        model_params: Optional[ModelParameters] = None,
    ) -> TrainingResponse:
        try:
            # Convert Pydantic models to dicts
            training_emails = []
            for email in training_data:
                email_dict = {
                    "subject": email.subject,
                    "content": email.content,
                    "sender": email.sender,
                    "date": email.date.isoformat(),
                }
                training_emails.append(email_dict)

            # Configure training parameters if provided
            if model_params:
                self.analyzer.configure_training(model_params.dict())

            # Train the model
            self.analyzer.train(training_emails)
            self.is_trained = True

            # Evaluate model
            eval_size = min(len(training_emails), 100)
            metrics_dict = self.analyzer.evaluate_model(training_emails[:eval_size])

            metrics = TrainingMetrics(**metrics_dict)

            # Save the trained model
            await self.save_model()

            return TrainingResponse(
                status="success", metrics=metrics, model_version=self.model_version
            )
        except Exception as e:
            logging.exception(f"Error training model: {str(e)}")
            raise

    def get_status(self) -> Dict[str, any]:
        return {
            "is_trained": self.is_trained,
            "model_version": self.model_version,
            "model_path": str(self.model_path),
        }
