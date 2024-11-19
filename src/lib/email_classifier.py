import logging
import re
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd


class AnalysisState(Enum):
    INITIALIZED = "initialized"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EmailAnalyzer:
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self._initialize_patterns()
        self._initialize_extractors()

    def _initialize_patterns(self):
        self.patterns = {
            "credit_cards": {
                "card_number": r"(?:x{4}\s*){3}\d{4}|(?:\d{4}\s*){3}\d{4}",
                "amount": r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "due_date": r"(?:due|payment)\s*(?:date)?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
                "card_type": r"(?:visa|mastercard|rupay|amex)",
                "credit_limit": r"(?:credit\s+limit|limit)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "min_due": r"(?:minimum|min)\s*(?:amount|payment)?[:\s]*(?:due)?[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "banks": r"(?:hdfc|icici|sbi|axis|kotak|citi|amex|yes|rbl|idfc)",
                "statement_period": r"(?:statement|billing)\s*period[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s*(?:to|-)\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
            },
            "spending": {
                "transaction": r"(?:transaction|payment|purchase)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "merchant": r"(?:merchant|store|outlet)[:\s]*([A-Za-z0-9\s&]+)",
                "category": r"(?:category|type)[:\s]*([A-Za-z\s]+)",
                "payment_method": r"(?:card|upi|netbanking|wallet)",
                "reward_points": r"(?:reward|points)[:\s]*(\d+)",
                "cashback": r"cashback[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "discount": r"discount[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)|(\d+)%\s*(?:off|discount)",
            },
            "identity": {
                "aadhaar": r"(?:aadhaar|uid|आधार)[:\s]*(\d{4}\s*\d{4}\s*\d{4})",
                "pan": r"[A-Z]{5}\d{4}[A-Z]",
                "passport": r"[A-Z]{1}\d{7}",
                "driving_license": r"(?:dl|driving)[:\s]*([A-Z]{2}\d{13})",
                "voter_id": r"[A-Z]{3}\d{7}",
                "gstin": r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[Z]{1}[A-Z\d]{1}",
                "verification_status": r"(?:verified|pending|failed|successful|complete)",
                "otp": r"otp[:\s]*(\d{4,8})",
            },
            "portfolio": {
                "stock_symbol": r"(?:nse|bse)[:\s]*([A-Z]+)",
                "quantity": r"(?:qty|quantity)[:\s]*(\d+)",
                "price": r"(?:price|rate)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "transaction_type": r"(?:buy|sell|purchase|sale)",
                "order_status": r"(?:executed|pending|cancelled|failed)",
                "exchange": r"(?:nse|bse|nfo|mcx)",
                "dividend": r"dividend[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "mutual_fund": r"(?:mutual\s+fund|mf)[:\s]*([A-Za-z0-9\s]+)",
                "nav": r"nav[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
            },
            "travel": {
                "pnr": r"pnr[:\s]*([A-Z0-9]{10})",
                "flight": r"(?:flight|carrier)[:\s]*([A-Z0-9\s]+)",
                "train": r"(?:train|express|mail)[:\s]*(\d{5})",
                "booking_id": r"booking[:\s]*(?:id|ref)[:\s]*([A-Z0-9]+)",
                "source": r"(?:from|source)[:\s]*([A-Za-z\s]+)",
                "destination": r"(?:to|destination)[:\s]*([A-Za-z\s]+)",
                "travel_date": r"(?:travel|journey|flight|departure)\s*date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
                "amount": r"(?:fare|amount|price)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
            },
        }

    def _initialize_extractors(self):
        self.category_extractors = {
            "credit_cards": self._extract_credit_card_info,
            "spending": self._extract_spending_info,
            "identity": self._extract_identity_info,
            "portfolio": self._extract_portfolio_info,
            "travel": self._extract_travel_info,
        }

    async def analyze_emails(self, emails: List[Dict]) -> Dict:
        try:
            results = {
                "credit_analysis": [],
                "spending_analysis": [],
                "identity_analysis": [],
                "portfolio_analysis": [],
                "travel_analysis": [],
                "summary": defaultdict(int),
            }

            for email in emails:
                category = await self._categorize_email(email)
                if category and category in self.category_extractors:
                    analysis = await self.category_extractors[category](email)
                    if analysis:
                        results[f"{category}_analysis"].append(analysis)
                        results["summary"][category] += 1

            return await self._finalize_results(results)

        except Exception as e:
            logging.error({"action": "email_analysis_failed", "error": str(e)})
            raise

    async def _categorize_email(self, email: Dict) -> Optional[str]:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            content = content.lower()

            # Check each category's patterns
            category_scores = {}
            for category, patterns in self.patterns.items():
                score = 0
                for pattern in patterns.values():
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    score += len(matches)
                category_scores[category] = score

            # Get category with highest score
            if category_scores:
                max_category = max(category_scores.items(), key=lambda x: x[1])
                if max_category[1] > 0:
                    return max_category[0]

            return None

        except Exception as e:
            logging.error({"action": "email_categorization_failed", "error": str(e)})
            return None

    async def _extract_credit_card_info(self, email: Dict) -> Dict:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            patterns = self.patterns["credit_cards"]

            info = {
                "timestamp": email.get("date"),
                "card_number": self._extract_pattern(content, patterns["card_number"]),
                "amount": self._extract_amount(content, patterns["amount"]),
                "due_date": self._extract_date(content, patterns["due_date"]),
                "card_type": self._extract_pattern(content, patterns["card_type"]),
                "credit_limit": self._extract_amount(content, patterns["credit_limit"]),
                "min_due": self._extract_amount(content, patterns["min_due"]),
                "bank": self._extract_pattern(content, patterns["banks"]),
                "statement_period": self._extract_statement_period(
                    content, patterns["statement_period"]
                ),
            }

            return {k: v for k, v in info.items() if v}

        except Exception as e:
            logging.error({"action": "credit_card_extraction_failed", "error": str(e)})
            return {}

    async def _extract_spending_info(self, email: Dict) -> Dict:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            patterns = self.patterns["spending"]

            info = {
                "timestamp": email.get("date"),
                "transaction_amount": self._extract_amount(
                    content, patterns["transaction"]
                ),
                "merchant": self._extract_pattern(content, patterns["merchant"]),
                "category": self._extract_pattern(content, patterns["category"]),
                "payment_method": self._extract_pattern(
                    content, patterns["payment_method"]
                ),
                "reward_points": self._extract_pattern(
                    content, patterns["reward_points"]
                ),
                "cashback": self._extract_amount(content, patterns["cashback"]),
                "discount": self._extract_pattern(content, patterns["discount"]),
            }

            return {k: v for k, v in info.items() if v}

        except Exception as e:
            logging.error({"action": "spending_extraction_failed", "error": str(e)})
            return {}

    async def _extract_identity_info(self, email: Dict) -> Dict:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            patterns = self.patterns["identity"]

            info = {
                "timestamp": email.get("date"),
                "aadhaar": self._extract_pattern(content, patterns["aadhaar"]),
                "pan": self._extract_pattern(content, patterns["pan"]),
                "passport": self._extract_pattern(content, patterns["passport"]),
                "driving_license": self._extract_pattern(
                    content, patterns["driving_license"]
                ),
                "voter_id": self._extract_pattern(content, patterns["voter_id"]),
                "gstin": self._extract_pattern(content, patterns["gstin"]),
                "verification_status": self._extract_pattern(
                    content, patterns["verification_status"]
                ),
                "otp": self._extract_pattern(content, patterns["otp"]),
            }

            return {k: v for k, v in info.items() if v}

        except Exception as e:
            logging.error({"action": "identity_extraction_failed", "error": str(e)})
            return {}

    async def _extract_portfolio_info(self, email: Dict) -> Dict:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            patterns = self.patterns["portfolio"]

            info = {
                "timestamp": email.get("date"),
                "stock_symbol": self._extract_pattern(
                    content, patterns["stock_symbol"]
                ),
                "quantity": self._extract_pattern(content, patterns["quantity"]),
                "price": self._extract_amount(content, patterns["price"]),
                "transaction_type": self._extract_pattern(
                    content, patterns["transaction_type"]
                ),
                "order_status": self._extract_pattern(
                    content, patterns["order_status"]
                ),
                "exchange": self._extract_pattern(content, patterns["exchange"]),
                "dividend": self._extract_amount(content, patterns["dividend"]),
                "mutual_fund": self._extract_pattern(content, patterns["mutual_fund"]),
                "nav": self._extract_amount(content, patterns["nav"]),
            }

            return {k: v for k, v in info.items() if v}

        except Exception as e:
            logging.error({"action": "portfolio_extraction_failed", "error": str(e)})
            return {}

    async def _extract_travel_info(self, email: Dict) -> Dict:
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            patterns = self.patterns["travel"]

            info = {
                "timestamp": email.get("date"),
                "pnr": self._extract_pattern(content, patterns["pnr"]),
                "flight": self._extract_pattern(content, patterns["flight"]),
                "train": self._extract_pattern(content, patterns["train"]),
                "booking_id": self._extract_pattern(content, patterns["booking_id"]),
                "source": self._extract_pattern(content, patterns["source"]),
                "destination": self._extract_pattern(content, patterns["destination"]),
                "travel_date": self._extract_date(content, patterns["travel_date"]),
                "amount": self._extract_amount(content, patterns["amount"]),
            }

            return {k: v for k, v in info.items() if v}

        except Exception as e:
            logging.error({"action": "travel_extraction_failed", "error": str(e)})
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
                for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        continue
            return None
        except Exception:
            return None

    def _extract_statement_period(
        self, text: str, pattern: str
    ) -> Optional[Dict[str, str]]:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and len(match.groups()) == 2:
                return {
                    "from": self._extract_date(
                        match.group(1), r"\d{1,2}[-/]\d{1,2}[-/]\d{4}"
                    ),
                    "to": self._extract_date(
                        match.group(2), r"\d{1,2}[-/]\d{1,2}[-/]\d{4}"
                    ),
                }
            return None
        except Exception:
            return None

    async def _finalize_results(self, results: Dict) -> Dict:
        try:
            final_results = {
                "credit_analysis": await self._analyze_credit_trends(
                    results["credit_analysis"]
                ),
                "spending_analysis": await self._analyze_spending_trends(
                    results["spending_analysis"]
                ),
                "identity_analysis": await self._analyze_identity_trends(
                    results["identity_analysis"]
                ),
                "portfolio_analysis": await self._analyze_portfolio_trends(
                    results["portfolio_analysis"]
                ),
                "travel_analysis": await self._analyze_travel_trends(
                    results["travel_analysis"]
                ),
                "summary": await self._generate_summary(results),
            }

            return final_results

        except Exception as e:
            logging.error({"action": "results_finalization_failed", "error": str(e)})
            raise

    async def _analyze_credit_trends(self, credit_data: List[Dict]) -> Dict:
        try:
            if not credit_data:
                return {}

            df = pd.DataFrame(credit_data)
            analysis = {
                "cards": self._analyze_cards(df),
                "spending_trends": self._analyze_spending_patterns(df),
                "payment_behavior": self._analyze_payment_behavior(df),
                "credit_utilization": self._analyze_credit_utilization(df),
            }

            return analysis

        except Exception as e:
            logging.error({"action": "credit_trends_analysis_failed", "error": str(e)})
            return {}

    def _analyze_cards(self, df: pd.DataFrame) -> Dict:
        try:
            cards_info = {}
            for card_number in df["card_number"].unique():
                card_df = df[df["card_number"] == card_number]
                cards_info[card_number] = {
                    "bank": card_df["bank"].iloc[0],
                    "card_type": card_df["card_type"].iloc[0],
                    "credit_limit": card_df["credit_limit"].max(),
                    "highest_bill": card_df["amount"].max(),
                    "average_bill": card_df["amount"].mean(),
                    "total_transactions": len(card_df),
                }
            return cards_info
        except Exception:
            return {}

    def _analyze_spending_patterns(self, df: pd.DataFrame) -> Dict:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            monthly_spending = df.groupby(df["timestamp"].dt.strftime("%Y-%m"))[
                ["amount"]
            ].sum()
            return {
                "monthly_totals": monthly_spending["amount"].to_dict(),
                "average_monthly": float(monthly_spending["amount"].mean()),
                "highest_month": {
                    "month": monthly_spending["amount"].idxmax(),
                    "amount": float(monthly_spending["amount"].max()),
                },
            }
        except Exception:
            return {}

    def _analyze_payment_behavior(self, df: pd.DataFrame) -> Dict:
        try:
            df["due_date"] = pd.to_datetime(df["due_date"])
            df["days_to_due"] = (
                df["due_date"] - pd.to_datetime(df["timestamp"])
            ).dt.days

            return {
                "average_days_to_due": float(df["days_to_due"].mean()),
                "min_payments_count": len(df[df["amount"] == df["min_due"]]),
                "full_payments_count": len(df[df["amount"] > df["min_due"]]),
                "payment_pattern": {
                    "early": len(df[df["days_to_due"] > 5]),
                    "ontime": len(df[df["days_to_due"].between(0, 5)]),
                    "delayed": len(df[df["days_to_due"] < 0]),
                },
            }
        except Exception:
            return {}

    def _analyze_credit_utilization(self, df: pd.DataFrame) -> Dict:
        try:
            df["utilization"] = (df["amount"] / df["credit_limit"]) * 100
            return {
                "average_utilization": float(df["utilization"].mean()),
                "max_utilization": float(df["utilization"].max()),
                "utilization_brackets": {
                    "low": len(df[df["utilization"] <= 30]),
                    "medium": len(df[df["utilization"].between(30, 70)]),
                    "high": len(df[df["utilization"] > 70]),
                },
            }
        except Exception:
            return {}

    async def _analyze_spending_trends(self, spending_data: List[Dict]) -> Dict:
        try:
            if not spending_data:
                return {}

            df = pd.DataFrame(spending_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            analysis = {
                "merchant_analysis": self._analyze_merchants(df),
                "category_analysis": self._analyze_categories(df),
                "payment_methods": self._analyze_payment_methods(df),
                "rewards_analysis": self._analyze_rewards(df),
                "temporal_analysis": self._analyze_temporal_patterns(df),
            }

            return analysis

        except Exception as e:
            logging.error(
                {"action": "spending_trends_analysis_failed", "error": str(e)}
            )
            return {}

    def _analyze_merchants(self, df: pd.DataFrame) -> Dict:
        try:
            merchant_spending = (
                df.groupby("merchant")["transaction_amount"]
                .agg(["sum", "count", "mean"])
                .round(2)
            )

            return {
                "top_merchants": merchant_spending.nlargest(5, "sum").to_dict("index"),
                "frequent_merchants": merchant_spending.nlargest(5, "count").to_dict(
                    "index"
                ),
                "merchant_categories": df.groupby(["merchant", "category"])
                .size()
                .to_dict(),
            }
        except Exception:
            return {}

    def _analyze_categories(self, df: pd.DataFrame) -> Dict:
        try:
            category_spending = (
                df.groupby("category")["transaction_amount"]
                .agg(["sum", "count", "mean"])
                .round(2)
            )

            monthly_category = (
                df.groupby([df["timestamp"].dt.strftime("%Y-%m"), "category"])[
                    "transaction_amount"
                ]
                .sum()
                .to_dict()
            )

            return {
                "category_totals": category_spending.to_dict("index"),
                "monthly_category_trends": monthly_category,
                "top_categories": category_spending.nlargest(5, "sum").index.tolist(),
            }
        except Exception:
            return {}

    def _analyze_payment_methods(self, df: pd.DataFrame) -> Dict:
        try:
            payment_method_stats = (
                df.groupby("payment_method")
                .agg(
                    {
                        "transaction_amount": ["sum", "count", "mean"],
                        "cashback": ["sum", "mean"],
                        "discount": ["sum", "mean"],
                    }
                )
                .round(2)
            )

            return {
                "method_usage": payment_method_stats.to_dict(),
                "preferred_method": df["payment_method"].mode().iloc[0],
                "method_by_amount": df.groupby("payment_method")["transaction_amount"]
                .sum()
                .sort_values(ascending=False)
                .to_dict(),
            }
        except Exception:
            return {}

    async def _analyze_identity_trends(self, identity_data: List[Dict]) -> Dict:
        try:
            if not identity_data:
                return {}

            df = pd.DataFrame(identity_data)

            analysis = {
                "verification_stats": self._analyze_verifications(df),
                "document_stats": self._analyze_documents(df),
                "temporal_patterns": self._analyze_verification_timing(df),
                "security_indicators": self._analyze_security_patterns(df),
            }

            return analysis

        except Exception as e:
            logging.error(
                {"action": "identity_trends_analysis_failed", "error": str(e)}
            )
            return {}

    def _analyze_verifications(self, df: pd.DataFrame) -> Dict:
        try:
            return {
                "total_verifications": len(df),
                "verification_status": df["verification_status"]
                .value_counts()
                .to_dict(),
                "verification_types": {
                    "aadhaar": df["aadhaar"].notna().sum(),
                    "pan": df["pan"].notna().sum(),
                    "passport": df["passport"].notna().sum(),
                    "driving_license": df["driving_license"].notna().sum(),
                    "voter_id": df["voter_id"].notna().sum(),
                    "gstin": df["gstin"].notna().sum(),
                },
            }
        except Exception:
            return {}

    async def _analyze_portfolio_trends(self, portfolio_data: List[Dict]) -> Dict:
        try:
            if not portfolio_data:
                return {}

            df = pd.DataFrame(portfolio_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            analysis = {
                "trading_analysis": self._analyze_trading_patterns(df),
                "holdings_analysis": self._analyze_holdings(df),
                "performance_metrics": self._analyze_performance(df),
                "dividend_analysis": self._analyze_dividends(df),
            }

            return analysis

        except Exception as e:
            logging.error(
                {"action": "portfolio_trends_analysis_failed", "error": str(e)}
            )
            return {}

    async def _analyze_travel_trends(self, travel_data: List[Dict]) -> Dict:
        try:
            if not travel_data:
                return {}

            df = pd.DataFrame(travel_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            analysis = {
                "travel_patterns": self._analyze_travel_patterns(df),
                "expense_analysis": self._analyze_travel_expenses(df),
                "destination_analysis": self._analyze_destinations(df),
                "booking_patterns": self._analyze_booking_behavior(df),
            }

            return analysis

        except Exception as e:
            logging.error({"action": "travel_trends_analysis_failed", "error": str(e)})
            return {}

    async def _generate_summary(self, results: Dict) -> Dict:
        try:
            summary = {
                "total_emails_analyzed": sum(results["summary"].values()),
                "category_distribution": dict(results["summary"]),
                "key_insights": await self._generate_key_insights(results),
                "analysis_timestamp": datetime.now().isoformat(),
            }

            return summary

        except Exception as e:
            logging.error({"action": "summary_generation_failed", "error": str(e)})
            return {}

    async def _generate_key_insights(self, results: Dict) -> List[str]:
        insights = []

        try:
            # Credit insights
            if results["credit_analysis"]:
                credit_data = results["credit_analysis"]
                insights.extend(
                    [
                        f"Found {len(credit_data)} credit card(s) in use",
                        "High credit utilization detected"
                        if any(card.get("utilization", 0) > 70 for card in credit_data)
                        else "Credit utilization is within safe limits",
                    ]
                )

            # Spending insights
            if results["spending_analysis"]:
                spending_data = results["spending_analysis"]
                insights.extend(
                    [
                        f"Most frequent spending category: {spending_data.get('top_category', 'N/A')}",
                        f"Preferred payment method: {spending_data.get('preferred_method', 'N/A')}",
                    ]
                )

            # Portfolio insights
            if results["portfolio_analysis"]:
                portfolio_data = results["portfolio_analysis"]
                insights.extend(
                    [
                        f"Active investments in {len(portfolio_data.get('holdings', []))} instruments",
                        f"Recent trading activity: {portfolio_data.get('recent_activity', 'Low')}",
                    ]
                )

            return insights

        except Exception as e:
            logging.error({"action": "insight_generation_failed", "error": str(e)})
            return ["Analysis completed but insights generation failed"]
