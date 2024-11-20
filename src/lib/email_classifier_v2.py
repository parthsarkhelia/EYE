import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional


class EmailClassifier:
    def __init__(self):
        self._init_patterns()
        self._init_categories()
        self._init_keywords()

    def _init_patterns(self):
        self.patterns = {
            "credit_card": {
                "card_numbers": [
                    r"(?:Credit\s+Card|Card)(?:\s+ending(?:\s+in)?|(?:\s+no\.?|number)?)\s+(?:in\s+)?(?:[Xx*]+|XX)(\d{4})",
                    r"(?:Credit\s+Card|Card)\s+XX(\d{4})",
                    r"Card\s+ending\s+(?:in\s+)?(\d{4})",
                    r"(?:Credit\s+Card|Card)\s+(?:ending\s+)?(?:[Xx*]+|XX)(\d{4})",
                    r"(?:Credit\s+Card|Card)\s+account\s+(?:[Xx*]+|XX)(\d{4})",
                ],
                "available_limit": [
                    r"Available\s+(?:Credit\s+)?Limit(?:\s+on\s+your\s+card)?\s+(?:is|:)\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"Available\s+limit:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                ],
                "total_limit": [
                    r"Total\s+(?:Credit\s+)?Limit(?:\s+is)?\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"Total\s+limit:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                ],
            },
            "payment": {
                "credit_payment": [
                    r"(?:payment\s+of|credited)\s+(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"Amount\s+of\s+(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+credited",
                    r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+credited",
                    r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+has\s+been\s+credited",
                ],
                "mode": [
                    r"(?:via|through|mode:|method:)\s+(UPI|NEFT|IMPS|Net\s*Banking|wallet)",
                    r"Payment(?:\s+received)?\s+via\s+([A-Za-z\s]+)",
                    r"paid\s+(?:using|through|by)\s+([A-Za-z\s]+)",
                ],
                "reference": [
                    r"Reference(?:\s+number)?[:\.]\s*([A-Z0-9]+)",
                    r"Reference:\s*([A-Z0-9]+)",
                    r"Ref\s*(?:no)?\.?\s*:\s*([A-Z0-9]+)",
                ],
            },
            "merchant": {
                "food_delivery": [
                    r"from\s+([A-Za-z0-9\s&\-\'\.]+?)(?:\sis\s+confirmed|\sis\s+ready|\sis\s+on|\!|\.|$)",
                    r"Order\s+(?:Confirmed|Ready):\s+([A-Za-z0-9\s&\-\'\.]+?)\s+\(Order\s+#",
                    r"order\s+from\s+([A-Za-z0-9\s&\-\'\.]+?)\s+is",
                    r"([A-Za-z0-9\s&\-\'\.]+?)\s+Order\s+#[A-Z0-9]+",
                ],
                "travel_transport": [
                    r"^([A-Za-z]+(?:\s+(?:Prime|Mini|Auto|Outstation|XL|Premier|bike))?\s+(?:booking|ride))",
                    r"^Your\s+([A-Za-z]+(?:\s+(?:Prime|Mini|Auto|Outstation|XL|Premier|bike))?\s+(?:booking|ride))",
                    r"([A-Za-z]+(?:\s+(?:Prime|Mini|Auto|Outstation|XL|Premier)))\s+(?:confirmed|Ride)",
                ],
                "shopping": [
                    r"^([A-Za-z]+(?:\.[a-z]+)?)\s+order\s+(?:#|ID:)\s*[A-Z0-9\-]+",
                    r"Order\s+(?:Confirmation|confirmed)\s+from\s+([A-Za-z\s]+)!",
                    r"([A-Za-z]+)\s+order\s+#[A-Z0-9\-]+",
                    r"Order\s+(?:from|at)\s+([A-Za-z\s&\-\.]+)",
                ],
                "credit_card_merchant": [
                    r"Info:\s+([A-Za-z0-9\s&\-\.]+?)(?:\.|$)",
                    r"at\s+([A-Za-z0-9\s&\-\.]+?)\s+on\s+\d{2}-\d{2}-\d{4}",
                    r"at\s+([A-Za-z0-9\s&\-\.]+?)\.\s+The\s+Available",
                ],
                "financial": [
                    r"(?:shares\s+of|in)\s+([A-Z\s]+)\s+at",
                    r"invested\s+in\s+([A-Za-z\s]+\s+Fund)",
                    r"(?:shares\s+of|in)\s+([A-Z]+)\s+(?:at|@)",
                    r"([A-Za-z\s]+\s+Fund)\s+(?:Units|NAV)",
                ],
            },
            "amount": {
                "transaction": [
                    r"(?:transaction\s+of|charged|used\s+for)\s+(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+(?:at|@)",
                ],
                "food": [
                    r"(?:Amount|Total):\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"Amount\s+paid:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"Total:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                ],
                "transport": [
                    r"(?:Fare|Amount)(?:\s+paid)?:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"(?:Fare|Amount)(?:\s+estimate)?:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"(?:Estimated\s+)?[Ff]are:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                ],
                "shopping": [
                    r"Total(?:\s+Amount)?:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"Amount:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"Total:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                ],
                "financial": [
                    r"Total\s+(?:investment|value|amount):\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                    r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+invested",
                    r"Amount:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+redeemed",
                ],
            },
        }

    def _init_categories(self):
        self.categories = {
            "credit_cards": [
                "hdfc",
                "icici",
                "sbi",
                "axis",
                "kotak",
                "yes",
                "idfc",
                "indusind",
                "rbl",
                "federal",
                "dcb",
                "bandhan",
                "tata",
                "au",
                "standard_chartered",
                "hsbc",
                "dbs",
                "slice",
                "uni",
                "onecard",
                "amex",
                "citi",
            ],
            "food_dining": ["zomato", "swiggy"],
            "travel_transport": ["uber", "ola", "rapido"],
            "shopping_retail": [
                "amazon",
                "flipkart",
                "myntra",
                "ajio",
                "bigbasket",
                "dmart",
                "tata cliq",
                "nykaa",
                "meesho",
            ],
            "financial": ["zerodha", "groww", "upstox"],
        }

    def _init_keywords(self):
        self.transaction_keywords = {
            "credit_card_transaction": [
                "transaction alert",
                "spent",
                "debited",
                "charged",
                "purchase",
                "has been used",
                "for using",
                "transaction of",
            ],
            "credit_card_payment": [
                "payment received",
                "payment confirmed",
                "thank you for your payment",
                "payment credited",
                "amount credited",
                "payment processed",
                "payment successful",
            ],
        }

    def classify_email(self, email: Dict) -> Dict:
        """
        Classify email and extract relevant information
        Args:
            email (Dict): Email dictionary containing subject, content, sender, date
        Returns:
            Dict: Classified information including email type, extracted details
        """
        try:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            sender = email.get("sender", "").lower()
            date = email.get("date", "")

            # Determine email type
            email_type = self._get_email_type(content, sender)

            # Extract information based on type
            result = {
                "email_type": email_type,
                "date": date,
                "sender": sender,
                "extracted_info": self._extract_info(content, email_type),
            }

            return result

        except Exception as e:
            self.logger.error(f"Error classifying email: {str(e)}")
            return {"error": str(e)}

    def _get_email_type(self, content: str, sender: str) -> str:
        """
        Determine email type based on content and sender
        """
        # First check sender domain
        for category, companies in self.categories.items():
            if any(company in sender for company in companies):
                if category == "credit_cards":
                    if any(
                        keyword in content.lower()
                        for keyword in self.transaction_keywords["credit_card_payment"]
                    ):
                        return "credit_card_payment"
                    if any(
                        keyword in content.lower()
                        for keyword in self.transaction_keywords[
                            "credit_card_transaction"
                        ]
                    ):
                        return "credit_card_transaction"
                return category

        # If sender doesn't match, check content
        content_lower = content.lower()
        if any(
            keyword in content_lower
            for keyword in self.transaction_keywords["credit_card_transaction"]
        ):
            return "credit_card_transaction"
        if any(
            keyword in content_lower
            for keyword in self.transaction_keywords["credit_card_payment"]
        ):
            return "credit_card_payment"

        return "unknown"

    def _extract_info(self, content: str, email_type: str) -> Dict:
        """
        Extract information based on email type
        """
        info = {}

        if email_type in ["credit_card_transaction", "credit_card_payment"]:
            info.update(self._extract_credit_card_info(content, email_type))
        elif email_type == "food_dining":
            info.update(self._extract_food_info(content))
        elif email_type == "travel_transport":
            info.update(self._extract_transport_info(content))
        elif email_type == "shopping_retail":
            info.update(self._extract_shopping_info(content))
        elif email_type == "financial":
            info.update(self._extract_financial_info(content))

        return info

    def _extract_credit_card_info(self, content: str, email_type: str) -> Dict:
        """Extract credit card related information"""
        info = {
            "card_number": self._extract_pattern_match(
                content, self.patterns["credit_card"]["card_numbers"]
            ),
            "merchant": self._extract_pattern_match(
                content, self.patterns["merchant"]["credit_card_merchant"]
            ),
        }

        if email_type == "credit_card_transaction":
            info["amount"] = self._extract_pattern_match(
                content, self.patterns["amount"]["transaction"]
            )
            info["available_limit"] = self._extract_pattern_match(
                content, self.patterns["credit_card"]["available_limit"]
            )
            info["total_limit"] = self._extract_pattern_match(
                content, self.patterns["credit_card"]["total_limit"]
            )
        else:  # credit_card_payment
            info["amount"] = self._extract_pattern_match(
                content, self.patterns["payment"]["credit_payment"]
            )
            info["payment_mode"] = self._extract_pattern_match(
                content, self.patterns["payment"]["mode"]
            )
            info["reference"] = self._extract_pattern_match(
                content, self.patterns["payment"]["reference"]
            )

        return info

    def _extract_food_info(self, content: str) -> Dict:
        """Extract food delivery related information"""
        return {
            "merchant": self._extract_pattern_match(
                content, self.patterns["merchant"]["food_delivery"]
            ),
            "amount": self._extract_pattern_match(
                content, self.patterns["amount"]["food"]
            ),
        }

    def _extract_transport_info(self, content: str) -> Dict:
        """Extract transport related information"""
        return {
            "service": self._extract_pattern_match(
                content, self.patterns["merchant"]["travel_transport"]
            ),
            "amount": self._extract_pattern_match(
                content, self.patterns["amount"]["transport"]
            ),
        }

    def _extract_shopping_info(self, content: str) -> Dict:
        """Extract shopping related information"""
        return {
            "merchant": self._extract_pattern_match(
                content, self.patterns["merchant"]["shopping"]
            ),
            "amount": self._extract_pattern_match(
                content, self.patterns["amount"]["shopping"]
            ),
        }

    def _extract_financial_info(self, content: str) -> Dict:
        """Extract financial transaction information"""
        return {
            "instrument": self._extract_pattern_match(
                content, self.patterns["merchant"]["financial"]
            ),
            "amount": self._extract_pattern_match(
                content, self.patterns["amount"]["financial"]
            ),
        }

    def _extract_pattern_match(
        self, content: str, patterns: List[str]
    ) -> Optional[str]:
        """
        Extract first match from a list of patterns
        Args:
            content (str): Text to search in
            patterns (List[str]): List of regex patterns
        Returns:
            Optional[str]: First match found or None
        """
        try:
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return None
        except Exception as e:
            self.logger.error(f"Error in pattern matching: {str(e)}")
            return None

    def process_emails(self, emails: List[Dict]) -> Dict:
        """
        Process a list of emails and provide categorized results
        Args:
            emails (List[Dict]): List of email dictionaries
        Returns:
            Dict: Processed results categorized by type
        """
        results = {
            "credit_card_transactions": [],
            "credit_card_payments": [],
            "food_dining": [],
            "travel_transport": [],
            "shopping_retail": [],
            "financial": [],
            "unknown": [],
            "summary": {
                "total_processed": len(emails),
                "categorized": {},
                "total_amounts": {},
                "processing_date": datetime.now().isoformat(),
            },
        }

        try:
            for email in emails:
                classified = self.classify_email(email)
                email_type = classified["email_type"]

                # Add to appropriate category
                if email_type in results:
                    results[email_type].append(classified)
                else:
                    results["unknown"].append(classified)

            # Generate summary
            results["summary"].update(self._generate_summary(results))

            return results

        except Exception as e:
            self.logger.error(f"Error processing emails: {str(e)}")
            return {"error": str(e)}

    def _generate_summary(self, results: Dict) -> Dict:
        """
        Generate summary statistics from processed results
        Args:
            results (Dict): Processed email results
        Returns:
            Dict: Summary statistics
        """
        summary = {
            "categorized": {},
            "total_amounts": {},
            "merchants": defaultdict(int),
            "payment_modes": defaultdict(int),
        }

        try:
            # Count by category
            for category in results.keys():
                if category not in ["summary", "unknown"]:
                    count = len(results[category])
                    summary["categorized"][category] = count

                    # Calculate total amounts
                    total = 0
                    for item in results[category]:
                        amount_str = item.get("extracted_info", {}).get("amount")
                        if amount_str:
                            try:
                                amount = float(amount_str.replace(",", ""))
                                total += amount
                            except ValueError:
                                continue

                        # Count merchants
                        merchant = item.get("extracted_info", {}).get("merchant")
                        if merchant:
                            summary["merchants"][merchant] += 1

                        # Count payment modes for credit card payments
                        if category == "credit_card_payments":
                            payment_mode = item.get("extracted_info", {}).get(
                                "payment_mode"
                            )
                            if payment_mode:
                                summary["payment_modes"][payment_mode] += 1

                    summary["total_amounts"][category] = round(total, 2)

            # Add top merchants and payment modes
            summary["top_merchants"] = dict(
                sorted(summary["merchants"].items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
            )

            summary["top_payment_modes"] = dict(
                sorted(
                    summary["payment_modes"].items(), key=lambda x: x[1], reverse=True
                )[:5]
            )

            return summary

        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            return {}

    def validate_extraction(self, email: Dict) -> bool:
        """
        Validate extracted information from email
        Args:
            email (Dict): Classified email with extracted information
        Returns:
            bool: True if extraction appears valid, False otherwise
        """
        try:
            email_type = email.get("email_type")
            info = email.get("extracted_info", {})

            if email_type in ["credit_card_transaction", "credit_card_payment"]:
                return self._validate_credit_card_info(info, email_type)
            elif email_type == "food_dining":
                return bool(info.get("merchant") and info.get("amount"))
            elif email_type == "travel_transport":
                return bool(info.get("service") and info.get("amount"))
            elif email_type == "shopping_retail":
                return bool(info.get("merchant") and info.get("amount"))
            elif email_type == "financial":
                return bool(info.get("instrument") and info.get("amount"))

            return False

        except Exception as e:
            self.logger.error(f"Error validating extraction: {str(e)}")
            return False

    def _validate_credit_card_info(self, info: Dict, email_type: str) -> bool:
        """
        Validate credit card related information
        Args:
            info (Dict): Extracted information
            email_type (str): Type of credit card email
        Returns:
            bool: True if valid, False otherwise
        """
        if not info.get("card_number"):
            return False

        if email_type == "credit_card_transaction":
            return bool(
                info.get("amount")
                and (info.get("available_limit") or info.get("total_limit"))
            )
        else:  # credit_card_payment
            return bool(
                info.get("amount")
                and (info.get("payment_mode") or info.get("reference"))
            )
