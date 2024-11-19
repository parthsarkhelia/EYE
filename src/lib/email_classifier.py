import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import spacy
from sentence_transformers import SentenceTransformer
from transformers import pipeline

logger = logging.getLogger(__name__)


class EmailAnalyzer:
    def __init__(self, model_path: Optional[str] = None):
        logger.info({"action": "initializing_email_analyzer", "model_path": model_path})

        try:
            # Initialize NLP models
            logger.info({"action": "loading_spacy_model"})
            self.nlp = spacy.load("en_core_web_lg")

            logger.info({"action": "loading_sentence_transformer"})
            self.sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")

            logger.info({"action": "initializing_classifier"})
            self.classifier = pipeline("zero-shot-classification")

            # Initialize all configurations
            self._initialize_configurations()

            logger.info({"action": "initialization_complete", "status": "success"})

        except Exception as e:
            logger.error(
                {
                    "action": "initialization_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def _initialize_configurations(self):
        logger.info({"action": "initializing_configurations"})

        try:
            # Email Categories with their patterns
            self.email_categories = {
                "credit_cards": {
                    "patterns": [
                        "statement",
                        "bill",
                        "payment_due",
                        "reward_points",
                        "limit_update",
                        "card payment",
                        "credit card",
                    ],
                    "extractors": [
                        r"card\s+ending\s+(?:\d{4})",
                        r"total\s+due\s*:?\s*(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)",
                        r"due\s+date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
                    ],
                },
                "spending": {
                    "patterns": [
                        "purchase",
                        "transaction",
                        "payment_confirmation",
                        "order",
                        "booking",
                        "payment successful",
                    ],
                    "extractors": [
                        r"amount\s*:?\s*(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)",
                        r"merchant\s*:?\s*([A-Za-z0-9\s&]+(?=\s|$))",
                        r"transaction\s+id\s*:?\s*([A-Za-z0-9]+)",
                    ],
                },
                "identity": {
                    "patterns": [
                        "verification",
                        "otp",
                        "kyc",
                        "document_verification",
                        "aadhaar",
                        "pan",
                        "identity",
                    ],
                    "extractors": [
                        r"verification\s+id\s*:?\s*([A-Za-z0-9]+)",
                        r"document\s+type\s*:?\s*([A-Za-z]+)",
                        r"status\s*:?\s*([A-Za-z]+)",
                    ],
                },
                "portfolio": {
                    "patterns": [
                        "trade_confirmation",
                        "demat",
                        "investment_update",
                        "dividend",
                        "stock",
                        "mutual fund",
                    ],
                    "extractors": [
                        r"(?:buy|sell)\s+(?:price|rate)\s*:?\s*(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)",
                        r"quantity\s*:?\s*(\d+)",
                        r"symbol\s*:?\s*([A-Z]+)",
                    ],
                },
                "travel": {
                    "patterns": [
                        "ticket",
                        "booking",
                        "itinerary",
                        "travel_insurance",
                        "flight",
                        "train",
                        "hotel",
                    ],
                    "extractors": [
                        r"(?:pnr|booking)\s+(?:number|id)\s*:?\s*([A-Z0-9]+)",
                        r"(?:from|source)\s*:?\s*([A-Za-z\s]+?)(?=\s+to|\s*$)",
                        r"(?:to|destination)\s*:?\s*([A-Za-z\s]+)(?=\s|$)",
                    ],
                },
            }

            # Company Categories with detection patterns
            self.company_categories = {
                "food_delivery": {
                    "companies": ["zomato", "swiggy", "uber_eats", "dominos"],
                    "patterns": [
                        "order confirmation",
                        "delivery update",
                        "food delivery",
                    ],
                },
                "e_commerce": {
                    "companies": ["amazon", "flipkart", "myntra", "ajio"],
                    "patterns": ["order confirmed", "shipment", "delivery"],
                },
                "credit_cards": {
                    "companies": ["hdfc", "icici", "axis", "sbi", "amex"],
                    "patterns": ["card statement", "due date", "minimum due"],
                },
                "banks": {
                    "companies": ["hdfc", "icici", "sbi", "axis", "kotak"],
                    "patterns": ["account statement", "neft", "imps", "upi"],
                },
                "portfolio": {
                    "companies": ["zerodha", "groww", "upstox", "cdsl", "nsdl"],
                    "patterns": ["trade confirmation", "contract note", "dividend"],
                },
                "travel": {
                    "companies": ["makemytrip", "goibibo", "irctc", "uber", "ola"],
                    "patterns": ["booking confirmed", "e-ticket", "trip summary"],
                },
            }

            # Extraction Patterns
            self.extraction_patterns = {
                "amounts": r"(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)",
                "dates": r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",
                "card_numbers": r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}",
                "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "phone": r"\+?91[-\s]?\d{10}",
                "urls": r"https?://(?:[\w-]|(?:%[\da-fA-F]{2}))+",
            }

            logger.info(
                {
                    "action": "configuration_complete",
                    "categories_configured": len(self.email_categories),
                    "companies_configured": len(self.company_categories),
                }
            )

        except Exception as e:
            logger.error(
                {
                    "action": "configuration_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def process_emails(self, emails: List[Dict]) -> Dict:
        logger.info({"action": "processing_emails", "email_count": len(emails)})

        try:
            results = {
                "credit_analysis": self.analyze_credit_payments(emails),
                "spending_analysis": self.analyze_spending(emails),
                "identity_analysis": self.analyze_identity(emails),
                "portfolio_analysis": self.analyze_portfolio(emails),
                "travel_analysis": self.analyze_travel(emails),
                "summary": {
                    "total_emails": len(emails),
                    "processed_at": datetime.now().isoformat(),
                    "categories_distribution": self._get_category_distribution(emails),
                },
            }

            logger.info(
                {
                    "action": "email_processing_complete",
                    "status": "success",
                    "categories_found": len(
                        results["summary"]["categories_distribution"]
                    ),
                }
            )

            return results

        except Exception as e:
            logger.error(
                {
                    "action": "email_processing_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def analyze_credit_payments(self, emails: List[Dict]) -> Dict:
        logger.info({"action": "analyzing_credit_payments", "email_count": len(emails)})

        try:
            analysis = defaultdict(
                lambda: {
                    "total_due": 0.0,
                    "payment_history": [],
                    "due_dates": [],
                    "credit_limit": None,
                    "reward_points": 0,
                    "transactions": [],
                }
            )

            for email in emails:
                if self._is_credit_card_email(email):
                    card_info = self._extract_credit_card_info(email)
                    if card_info:
                        card_id = card_info.get("card_id")
                        if card_id:
                            self._update_credit_analysis(analysis[card_id], card_info)

            result = {
                "cards": dict(analysis),
                "total_cards": len(analysis),
                "total_due": sum(card["total_due"] for card in analysis.values()),
                "upcoming_payments": self._get_upcoming_payments(analysis),
            }

            logger.info(
                {
                    "action": "credit_analysis_complete",
                    "cards_analyzed": len(analysis),
                    "total_due": result["total_due"],
                }
            )

            return result

        except Exception as e:
            logger.error(
                {
                    "action": "credit_analysis_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def analyze_spending(self, emails: List[Dict]) -> Dict:
        logger.info({"action": "analyzing_spending", "email_count": len(emails)})

        try:
            spending = {
                "categories": defaultdict(float),
                "merchants": defaultdict(float),
                "monthly": defaultdict(lambda: defaultdict(float)),
                "payment_methods": defaultdict(float),
            }

            for email in emails:
                if self._is_transaction_email(email):
                    transaction = self._extract_transaction_info(email)
                    if transaction:
                        self._update_spending_analysis(spending, transaction)

            result = {
                "category_wise": dict(spending["categories"]),
                "merchant_wise": dict(spending["merchants"]),
                "monthly_trends": dict(spending["monthly"]),
                "payment_methods": dict(spending["payment_methods"]),
                "total_spending": sum(spending["categories"].values()),
            }

            logger.info(
                {
                    "action": "spending_analysis_complete",
                    "categories_found": len(result["category_wise"]),
                    "total_spending": result["total_spending"],
                }
            )

            return result

        except Exception as e:
            logger.error(
                {
                    "action": "spending_analysis_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def analyze_identity(self, emails: List[Dict]) -> Dict:
        logger.info({"action": "analyzing_identity", "email_count": len(emails)})

        try:
            identity = {
                "verifications": defaultdict(list),
                "documents": defaultdict(list),
                "activities": [],
                "status": defaultdict(str),
            }

            for email in emails:
                if self._is_identity_email(email):
                    verification = self._extract_identity_info(email)
                    if verification:
                        self._update_identity_analysis(identity, verification)

            result = {
                "verifications": dict(identity["verifications"]),
                "documents": dict(identity["documents"]),
                "recent_activities": identity["activities"][-10:],
                "verification_status": dict(identity["status"]),
            }

            logger.info(
                {
                    "action": "identity_analysis_complete",
                    "verifications_found": len(result["verifications"]),
                    "documents_found": len(result["documents"]),
                }
            )

            return result

        except Exception as e:
            logger.error(
                {
                    "action": "identity_analysis_failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise

    def _is_credit_card_email(self, email: Dict) -> bool:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            patterns = self.email_categories["credit_cards"]["patterns"]
            return any(pattern.lower() in content.lower() for pattern in patterns)
        except Exception as e:
            logger.error({"action": "credit_card_email_check_failed", "error": str(e)})
            return False

    def _extract_credit_card_info(self, email: Dict) -> Dict:
        try:
            content = email.get("content", "")
            extractors = self.email_categories["credit_cards"]["extractors"]

            info = {
                "card_id": self._extract_pattern(content, extractors[0]),
                "total_due": self._extract_amount(content, extractors[1]),
                "due_date": self._extract_date(content, extractors[2]),
            }

            logger.debug(
                {
                    "action": "credit_card_info_extraction",
                    "info_found": {k: bool(v) for k, v in info.items()},
                }
            )

            return {k: v for k, v in info.items() if v}

        except Exception as e:
            logger.error(
                {"action": "credit_card_info_extraction_failed", "error": str(e)}
            )
            return {}

    def _extract_pattern(self, text: str, pattern: str) -> Optional[str]:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1) if match else None
        except Exception:
            return None

    def _extract_amount(self, text: str, pattern: str) -> Optional[float]:
        try:
            amount_str = self._extract_pattern(text, pattern)
            if amount_str:
                return float(amount_str.replace(",", ""))
            return None
        except Exception:
            return None

    def _extract_date(self, text: str, pattern: str) -> Optional[str]:
        try:
            date_str = self._extract_pattern(text, pattern)
            if date_str:
                return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            return None
        except Exception:
            return None

    def _get_category_distribution(self, emails: List[Dict]) -> Dict:
        try:
            distribution = defaultdict(int)
            for email in emails:
                category = self._categorize_email(email)
                if category:
                    distribution[category] += 1

            logger.info(
                {
                    "action": "category_distribution_complete",
                    "categories_found": len(distribution),
                }
            )

            return dict(distribution)

        except Exception as e:
            logger.error({"action": "category_distribution_failed", "error": str(e)})
            return {}

    def _categorize_email(self, email: Dict) -> Optional[str]:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            result = self.classifier(
                content,
                candidate_labels=list(self.email_categories.keys()),
                multi_label=False,
            )

            category = result["labels"][0] if result["scores"][0] > 0.5 else None

            logger.debug(
                {
                    "action": "email_categorization",
                    "category": category,
                    "confidence": result["scores"][0] if category else 0,
                }
            )

            return category

        except Exception as e:
            logger.error({"action": "email_categorization_failed", "error": str(e)})
            return None

    def analyze_portfolio(self, emails: List[Dict]) -> Dict:
        logger.info({"action": "analyzing_portfolio", "email_count": len(emails)})

        try:
            portfolio = {
                "transactions": defaultdict(list),
                "holdings": defaultdict(float),
                "dividends": defaultdict(float),
                "monthly_activity": defaultdict(lambda: defaultdict(int)),
            }

            for email in emails:
                if self._is_portfolio_email(email):
                    trade_info = self._extract_portfolio_info(email)
                    if trade_info:
                        self._update_portfolio_analysis(portfolio, trade_info)

            result = {
                "transactions": dict(portfolio["transactions"]),
                "current_holdings": dict(portfolio["holdings"]),
                "dividend_history": dict(portfolio["dividends"]),
                "activity_summary": dict(portfolio["monthly_activity"]),
            }

            logger.info(
                {
                    "action": "portfolio_analysis_complete",
                    "transactions_found": sum(
                        len(v) for v in portfolio["transactions"].values()
                    ),
                    "holdings_count": len(portfolio["holdings"]),
                }
            )

            return result

        except Exception as e:
            logger.error({"action": "portfolio_analysis_failed", "error": str(e)})
            raise

    def analyze_travel(self, emails: List[Dict]) -> Dict:
        logger.info({"action": "analyzing_travel", "email_count": len(emails)})

        try:
            travel = {
                "locations": defaultdict(int),
                "bookings": [],
                "expenses": defaultdict(float),
                "transport_modes": defaultdict(int),
                "frequent_routes": defaultdict(int),
            }

            for email in emails:
                if self._is_travel_email(email):
                    travel_info = self._extract_travel_info(email)
                    if travel_info:
                        self._update_travel_analysis(travel, travel_info)

            result = {
                "visited_locations": dict(travel["locations"]),
                "recent_bookings": travel["bookings"][-10:],
                "expense_summary": dict(travel["expenses"]),
                "transport_preferences": dict(travel["transport_modes"]),
                "common_routes": dict(travel["frequent_routes"]),
            }

            logger.info(
                {
                    "action": "travel_analysis_complete",
                    "locations_found": len(result["visited_locations"]),
                    "bookings_analyzed": len(travel["bookings"]),
                }
            )

            return result

        except Exception as e:
            logger.error({"action": "travel_analysis_failed", "error": str(e)})
            raise

    def _update_credit_analysis(self, analysis: Dict, info: Dict):
        try:
            if "total_due" in info:
                analysis["total_due"] = info["total_due"]
            if "due_date" in info:
                analysis["due_dates"].append(info["due_date"])
            if "transaction" in info:
                analysis["transactions"].append(info["transaction"])
            if "reward_points" in info:
                analysis["reward_points"] += info["reward_points"]

            logger.debug(
                {
                    "action": "credit_analysis_update",
                    "updated_fields": list(info.keys()),
                }
            )

        except Exception as e:
            logger.error({"action": "credit_analysis_update_failed", "error": str(e)})

    def _update_spending_analysis(self, analysis: Dict, transaction: Dict):
        try:
            if "category" in transaction and "amount" in transaction:
                analysis["categories"][transaction["category"]] += transaction["amount"]
                if "merchant" in transaction:
                    analysis["merchants"][transaction["merchant"]] += transaction[
                        "amount"
                    ]
                if "date" in transaction:
                    month_key = transaction["date"][:7]  # YYYY-MM
                    analysis["monthly"][month_key][transaction["category"]] += (
                        transaction["amount"]
                    )
                if "payment_method" in transaction:
                    analysis["payment_methods"][transaction["payment_method"]] += (
                        transaction["amount"]
                    )

            logger.debug(
                {
                    "action": "spending_analysis_update",
                    "transaction_amount": transaction.get("amount"),
                    "category": transaction.get("category"),
                }
            )

        except Exception as e:
            logger.error({"action": "spending_analysis_update_failed", "error": str(e)})

    def _update_identity_analysis(self, analysis: Dict, verification: Dict):
        try:
            if "document_type" in verification:
                analysis["documents"][verification["document_type"]].append(
                    verification
                )
            if "verification_type" in verification:
                analysis["verifications"][verification["verification_type"]].append(
                    verification
                )
            if "activity" in verification:
                analysis["activities"].append(verification["activity"])
            if "status" in verification and "document_type" in verification:
                analysis["status"][verification["document_type"]] = verification[
                    "status"
                ]

            logger.debug(
                {
                    "action": "identity_analysis_update",
                    "verification_type": verification.get("verification_type"),
                    "document_type": verification.get("document_type"),
                }
            )

        except Exception as e:
            logger.error({"action": "identity_analysis_update_failed", "error": str(e)})

    def _update_portfolio_analysis(self, analysis: Dict, trade: Dict):
        try:
            if "symbol" in trade and "transaction_type" in trade:
                analysis["transactions"][trade["symbol"]].append(trade)
                if trade["transaction_type"] == "buy":
                    analysis["holdings"][trade["symbol"]] += trade.get("quantity", 0)
                elif trade["transaction_type"] == "sell":
                    analysis["holdings"][trade["symbol"]] -= trade.get("quantity", 0)

            if "dividend" in trade and "symbol" in trade:
                analysis["dividends"][trade["symbol"]] += trade["dividend"]

            if "date" in trade:
                month_key = trade["date"][:7]
                analysis["monthly_activity"][month_key][trade["transaction_type"]] += 1

            logger.debug(
                {
                    "action": "portfolio_analysis_update",
                    "symbol": trade.get("symbol"),
                    "transaction_type": trade.get("transaction_type"),
                }
            )

        except Exception as e:
            logger.error(
                {"action": "portfolio_analysis_update_failed", "error": str(e)}
            )

    def _update_travel_analysis(self, analysis: Dict, travel: Dict):
        try:
            if "location" in travel:
                analysis["locations"][travel["location"]] += 1
            if "booking" in travel:
                analysis["bookings"].append(travel["booking"])
            if "expense" in travel:
                analysis["expenses"][travel["expense_type"]] += travel["expense"]
            if "transport_mode" in travel:
                analysis["transport_modes"][travel["transport_mode"]] += 1
            if "route" in travel:
                analysis["frequent_routes"][travel["route"]] += 1

            logger.debug(
                {
                    "action": "travel_analysis_update",
                    "location": travel.get("location"),
                    "transport_mode": travel.get("transport_mode"),
                }
            )

        except Exception as e:
            logger.error({"action": "travel_analysis_update_failed", "error": str(e)})

    def get_summary_report(self, analysis_results: Dict) -> Dict:
        logger.info({"action": "generating_summary_report"})

        try:
            summary = {
                "credit_summary": {
                    "total_cards": len(analysis_results["credit_analysis"]["cards"]),
                    "total_due": analysis_results["credit_analysis"]["total_due"],
                    "upcoming_payments": len(
                        analysis_results["credit_analysis"]["upcoming_payments"]
                    ),
                },
                "spending_summary": {
                    "total_spent": analysis_results["spending_analysis"][
                        "total_spending"
                    ],
                    "top_categories": self._get_top_items(
                        analysis_results["spending_analysis"]["category_wise"], 5
                    ),
                    "top_merchants": self._get_top_items(
                        analysis_results["spending_analysis"]["merchant_wise"], 5
                    ),
                },
                "portfolio_summary": {
                    "active_holdings": len(
                        analysis_results["portfolio_analysis"]["current_holdings"]
                    ),
                    "total_transactions": sum(
                        len(v)
                        for v in analysis_results["portfolio_analysis"][
                            "transactions"
                        ].values()
                    ),
                    "dividend_income": sum(
                        analysis_results["portfolio_analysis"][
                            "dividend_history"
                        ].values()
                    ),
                },
                "travel_summary": {
                    "locations_visited": len(
                        analysis_results["travel_analysis"]["visited_locations"]
                    ),
                    "total_bookings": len(
                        analysis_results["travel_analysis"]["recent_bookings"]
                    ),
                    "transport_preferences": self._get_top_items(
                        analysis_results["travel_analysis"]["transport_preferences"], 3
                    ),
                },
                "generated_at": datetime.now().isoformat(),
            }

            logger.info(
                {
                    "action": "summary_report_complete",
                    "report_sections": list(summary.keys()),
                }
            )

            return summary

        except Exception as e:
            logger.error(
                {"action": "summary_report_generation_failed", "error": str(e)}
            )
            raise

    @staticmethod
    def _get_top_items(data: Dict, limit: int) -> Dict:
        return dict(sorted(data.items(), key=lambda x: x[1], reverse=True)[:limit])


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize analyzer
    analyzer = EmailAnalyzer()

    # Example usage
    example_emails = [
        {
            "subject": "Your Credit Card Statement",
            "content": "Your HDFC credit card ending 1234 has a total due of Rs. 50,000 due on 25/12/2023",
        },
        {
            "subject": "Order Confirmation",
            "content": "Your order from Amazon for Rs. 2,500 has been confirmed",
        },
    ]

    # Process emails
    results = analyzer.process_emails(example_emails)

    # Generate summary
    summary = analyzer.get_summary_report(results)

    print("Analysis complete. Check logs for details.")
