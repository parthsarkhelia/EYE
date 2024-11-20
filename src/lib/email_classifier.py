import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


class EmailAnalyzer:
    def __init__(self):
        self._init_patterns()
        self._init_categories()
        self._init_keywords()

    def _init_patterns(self):
        self.patterns = {
            "credit_card": {
                # Card identification patterns
                "card_numbers": [
                    r"(?:Credit\s+Card|Card)(?:\s+ending(?:\s+in)?|(?:\s+no\.?|number)?)\s+(?:in\s+)?(?:[Xx*]+|XX)(\d{4})",
                    r"(?:Credit\s+Card|Card)\s+XX(\d{4})",
                    r"Card\s+ending\s+(?:in\s+)?(\d{4})",
                    r"(?:Credit\s+Card|Card)\s+(?:ending\s+)?(?:[Xx*]+|XX)(\d{4})",
                    r"(?:Credit\s+Card|Card)\s+account\s+(?:[Xx*]+|XX)(\d{4})",
                ],
                # Statement patterns
                "statement_period": r"(?:STATEMENT\s+FOR\s+THE\s+PERIOD|FOR\s+THE\s+PERIOD|STATEMENT\s+PERIOD)\s*(?:FROM\s+)?([A-Za-z]+\s+\d{1,2},?\s*\d{4})\s*(?:TO|TILL|[-])\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
                "card_statement": r"(?:CREDIT\s+CARD\s+(?:E)?STATEMENT|(?:E)?STATEMENT\s+FOR)\s+(?:FOR\s+)?([A-Za-z]+\s+\d{4})",
                "due_date": r"(?:PAYMENT\s+)?DUE\s+(?:DATE|BY)[:\s]*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s*\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                "total_due": r"(?:TOTAL\s+(?:AMOUNT\s+)?DUE|PAYMENT\s+DUE|CURRENT\s+AMOUNT\s+DUE)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                "min_due": r"(?:MINIMUM|MIN\.?)\s+(?:AMOUNT\s+)?(?:DUE|PAYMENT)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                "credit_limit": r"(?:TOTAL\s+CREDIT\s+LIMIT|CREDIT\s+LIMIT|CARD\s+LIMIT)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                "available_limit": r"(?:AVAILABLE\s+CREDIT\s+LIMIT|AVAILABLE\s+LIMIT)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                # Transaction patterns
                "transaction_date": r"(?:date|on)\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                "transaction_time": r"(?:at|@)\s*(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)",
            },
            "transaction": {
                # Amount patterns for different categories
                "amount_patterns": {
                    "credit_card": [
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
                    ],
                    "financial": [
                        r"Total\s+(?:investment|value|amount):\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)",
                        r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+invested",
                        r"Amount:\s*(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)\s+redeemed",
                    ],
                },
                # Merchant patterns for different categories
                "merchant_patterns": {
                    "credit_card": [
                        r"Info:\s+([A-Za-z0-9\s&\-\.]+?)(?:\.|$)",
                        r"at\s+([A-Za-z0-9\s&\-\.]+?)\s+on\s+\d{2}-\d{2}-\d{4}",
                        r"at\s+([A-Za-z0-9\s&\-\.]+?)\.\s+The\s+Available",
                    ],
                    "food": [
                        r"from\s+([A-Za-z0-9\s&\-\'\.]+?)(?:\sis\s+confirmed|\sis\s+ready|\sis\s+on|\!|\.|$)",
                        r"Order\s+(?:Confirmed|Ready):\s+([A-Za-z0-9\s&\-\'\.]+?)\s+\(Order\s+#",
                        r"order\s+from\s+([A-Za-z0-9\s&\-\'\.]+?)\s+is",
                    ],
                    "transport": [
                        r"^([A-Za-z]+(?:\s+(?:Prime|Mini|Auto|Outstation|XL|Premier|bike))?\s+(?:booking|ride))",
                        r"^Your\s+([A-Za-z]+(?:\s+(?:Prime|Mini|Auto|Outstation|XL|Premier|bike))?\s+(?:booking|ride))",
                        r"([A-Za-z]+(?:\s+(?:Prime|Mini|Auto|Outstation|XL|Premier)))\s+(?:confirmed|Ride)",
                    ],
                    "shopping": [
                        r"^([A-Za-z]+(?:\.[a-z]+)?)\s+order\s+(?:#|ID:)\s*[A-Z0-9\-]+",
                        r"Order\s+(?:Confirmation|confirmed)\s+from\s+([A-Za-z\s]+)!",
                        r"([A-Za-z]+)\s+order\s+#[A-Z0-9\-]+",
                    ],
                },
                "upi_id": r"(?:UPI|VPA|upi\s+id)[:\s]*([a-zA-Z0-9\.\-\_]+@[a-zA-Z]+)",
                "reference": r"(?:ref\.?(?:erence)?|txn|transaction)\s*(?:no\.?|id|number)[:\s]*([A-Z0-9]+)",
                "status": r"(?:status|transaction\s+status)[:\s]*([A-Za-z]+)",
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
                "pnb",
                "boi",
                "canara",
                "union",
                "bob",
                "indian",
                "central",
                "ubi",
                "citi",
                "amex",
                "standard_chartered",
                "hsbc",
                "dbs",
                "slice",
                "uni",
                "onecard",
                "amex",
                "citi",
            ],
            "food_dining": [
                "zomato",
                "swiggy",
                "uber eats",
                "restaurant",
                "food",
                "cafe",
                "dhaba",
                "kitchen",
                "eatery",
                "biryani",
                "pizza",
                "bakery",
                "sweet",
                "catering",
                "ola store",
            ],
            "travel_transport": [
                "makemytrip",
                "goibibo",
                "irctc",
                "indigo",
                "spicejet",
                "vistara",
                "airasia",
                "air india",
                "uber",
                "ola",
                "olacab",
                "ola cab",
                "rapido",
                "redbus",
                "railway",
                "airways",
                "flight",
                "bus",
                "cab",
                "auto",
                "metro",
            ],
            "shopping_retail": [
                "amazon",
                "flipkart",
                "myntra",
                "ajio",
                "bigbasket",
                "grofers",
                "dmart",
                "reliance",
                "trends",
                "lifestyle",
                "shoppers stop",
                "tata cliq",
                "nykaa",
                "meesho",
            ],
            "financial": ["zerodha", "groww", "upstox"],
        }

    def _init_keywords(self):
        # Transaction keywords
        self.transaction_keywords = {
            "credit_card_transaction": [
                "transaction alert",
                "spent",
                "debited",
                "charged",
                "purchase",
                "debit",
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

        # Promotional keywords
        self.promotional_keywords = [
            "offer",
            "reward",
            "exclusive",
            "discount",
            "save",
            "deal",
            "cashback",
            "promotion",
            "special",
            "limited time",
            "apply now",
            "pre-approved",
            "upgrade your card",
            "voucher",
            "gift",
            "benefit",
            "redeem",
            "LPA",
            "CTC",
            "dream",
            "tickets",
            "hiring",
            "loan",
            "opportunity",
            "bonus",
            "free",
            "earn",
            "points",
            "miles",
            "launch",
            "new",
            "introducing",
            "privilege",
            "membership",
        ]

        # Payment confirmation keywords
        self.payment_confirmation_keywords = [
            "payment received",
            "payment confirmed",
            "thank you for your payment",
            "payment has been posted",
            "payment processed",
            "payment successful",
            "payment credited",
            "amount credited",
            "credit card payment received",
            "we've received your payment",
            "payment acknowledged",
            "payment successfully posted",
            "bill payment confirmed",
            "card payment successful",
            "EMI payment received",
            "auto-payment successful",
            "standing instruction executed",
            "auto debit successful",
            "credit posted to your account",
            "your account has been credited",
        ]

    def _is_credit_card_promotional(self, content: str) -> bool:
        """
        Check if the email content is promotional
        Args:
            content (str): Email content
        Returns:
            bool: True if promotional, False otherwise
        """
        content_lower = content.lower()

        # Check for promotional keywords
        if any(
            keyword.lower() in content_lower for keyword in self.promotional_keywords
        ):
            # If it contains transaction or payment keywords, it might be a legitimate transaction
            if any(
                keyword.lower() in content_lower
                for keyword in self.transaction_keywords["credit_card_transaction"]
            ):
                return False
            if any(
                keyword.lower() in content_lower
                for keyword in self.payment_confirmation_keywords
            ):
                return False
            return True

        return False

    def _is_transaction_email(self, content: str) -> bool:
        """
        Check if the email is a transaction notification
        Args:
            content (str): Email content
        Returns:
            bool: True if transaction related, False otherwise
        """
        transaction_indicators = [
            "transaction",
            "payment",
            "spent",
            "paid",
            "purchase",
            "debit",
            "credited",
            "charged",
            "authorized",
            "₹",
            "rs.",
            "inr",
            "amount",
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in transaction_indicators)

    def _is_payment_confirmation(self, content: str) -> bool:
        """
        Check if the email is a payment confirmation
        Args:
            content (str): Email content
        Returns:
            bool: True if payment confirmation, False otherwise
        """
        content_lower = content.lower()
        return any(
            keyword.lower() in content_lower
            for keyword in self.payment_confirmation_keywords
        )

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
            if isinstance(patterns, str):
                patterns = [patterns]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return None
        except Exception as e:
            logging.error(f"Error in pattern matching: {str(e)}")
            return None

    def _extract_pattern_matches(self, content: str, patterns: List[str]) -> List[str]:
        """
        Extract all matches from a list of patterns
        Args:
            content (str): Text to search in
            patterns (List[str]): List of regex patterns
        Returns:
            List[str]: List of all matches found
        """
        matches = []
        try:
            if isinstance(patterns, str):
                patterns = [patterns]

            for pattern in patterns:
                found = re.findall(pattern, content, re.IGNORECASE)
                matches.extend(
                    [
                        match.strip() if isinstance(match, str) else match[0].strip()
                        for match in found
                    ]
                )
            return matches
        except Exception as e:
            logging.error(f"Error in pattern matching: {str(e)}")
            return matches

    def _extract_pattern_with_index(
        self, content: str, patterns: List[str], group_index: int = 1
    ) -> Optional[str]:
        """
        Extract match from pattern with specific group index
        Args:
            content (str): Text to search in
            patterns (List[str]): List of regex patterns
            group_index (int): Index of the group to extract
        Returns:
            Optional[str]: Match found or None
        """
        try:
            if isinstance(patterns, str):
                patterns = [patterns]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match and len(match.groups()) >= group_index:
                    return match.group(group_index).strip()
            return None
        except Exception as e:
            logging.error(f"Error in pattern matching: {str(e)}")
            return None

    def _match_patterns(
        self, content: str, pattern_dict: Dict[str, List[str]]
    ) -> Dict[str, str]:
        """
        Match multiple patterns and return results as dictionary
        Args:
            content (str): Text to search in
            pattern_dict (Dict[str, List[str]]): Dictionary of pattern lists
        Returns:
            Dict[str, str]: Dictionary of matches found
        """
        results = {}
        try:
            for key, patterns in pattern_dict.items():
                match = self._extract_pattern_match(content, patterns)
                if match:
                    results[key] = match
            return results
        except Exception as e:
            logging.error(f"Error in pattern matching: {str(e)}")
            return results

    def _extract_entities(self, content: str, entity_type: str) -> Optional[str]:
        """
        Extract specific entity type using appropriate patterns
        Args:
            content (str): Text to search in
            entity_type (str): Type of entity to extract (card_number, amount, merchant, etc.)
        Returns:
            Optional[str]: Entity found or None
        """
        try:
            # Get patterns based on entity type
            if entity_type == "card_number":
                patterns = self.patterns["credit_card"]["card_numbers"]
            elif entity_type == "amount":
                patterns = self.patterns["transaction"]["amount_patterns"][
                    "credit_card"
                ]
            elif entity_type == "merchant":
                patterns = self.patterns["transaction"]["merchant_patterns"][
                    "credit_card"
                ]
            else:
                logging.warning(f"Unknown entity type: {entity_type}")
                return None

            return self._extract_pattern_match(content, patterns)

        except Exception as e:
            logging.error(f"Error extracting entity {entity_type}: {str(e)}")
            return None

    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted text
        Args:
            text (str): Text to clean
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        try:
            # Remove extra whitespace
            text = re.sub(r"\s+", " ", text)

            # Remove punctuation at ends
            text = text.strip(".,!?:;")

            # Remove any remaining whitespace
            text = text.strip()

            return text
        except Exception as e:
            logging.error(f"Error cleaning text: {str(e)}")
            return text

    def _validate_pattern_match(self, text: str, pattern_type: str) -> bool:
        """
        Validate if extracted text matches expected pattern
        Args:
            text (str): Text to validate
            pattern_type (str): Type of pattern to validate against
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not text:
                return False

            if pattern_type == "card_number":
                # Validate 4 digit card number
                return bool(re.match(r"^\d{4}$", text))

            elif pattern_type == "amount":
                # Validate amount format
                return bool(re.match(r"^\d+(?:,\d{3})*(?:\.\d{2})?$", text))

            elif pattern_type == "merchant":
                # Validate merchant name format
                return bool(re.match(r"^[A-Za-z0-9\s&\-\.]+$", text))

            return True

        except Exception as e:
            logging.error(f"Error validating pattern match: {str(e)}")
            return False

    def _extract_all_matches(self, content: str, entity_type: str) -> List[str]:
        """
        Extract all matches of a specific entity type
        Args:
            content (str): Text to search in
            entity_type (str): Type of entity to extract
        Returns:
            List[str]: List of all matches found
        """
        try:
            patterns = []

            # Get appropriate patterns based on entity type
            if entity_type in self.patterns["credit_card"]:
                patterns = self.patterns["credit_card"][entity_type]
            elif entity_type in self.patterns["transaction"]:
                patterns = self.patterns["transaction"][entity_type]

            if not patterns:
                return []

            return self._extract_pattern_matches(content, patterns)

        except Exception as e:
            logging.error(f"Error extracting all matches: {str(e)}")
            return []

    def _extract_amount(self, content: str, email_type: str) -> Optional[float]:
        """Extract amount based on email type"""
        amount_patterns = self.patterns["transaction"]["amount_patterns"].get(
            email_type, self.patterns["transaction"]["amount_patterns"]["credit_card"]
        )

        for pattern in amount_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    return float(amount_str)
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_merchant(self, content: str, email_type: str) -> Optional[str]:
        """Extract merchant based on email type"""
        merchant_patterns = self.patterns["transaction"]["merchant_patterns"].get(
            email_type, self.patterns["transaction"]["merchant_patterns"]["credit_card"]
        )

        for pattern in merchant_patterns:
            match = re.search(pattern, content)
            if match:
                merchant = match.group(1).strip()
                # Clean merchant name
                merchant = re.sub(r"\s+", " ", merchant)
                merchant = merchant.strip(".,!?")
                return merchant
        return None

    def _get_transaction_type(self, content: str, sender: str) -> str:
        """Determine transaction type from email content and sender"""
        sender_lower = sender.lower()

        # Check sender first
        if any(bank in sender_lower for bank in self.categories["credit_cards"]):
            if any(
                keyword in content.lower()
                for keyword in self.transaction_keywords["credit_card_payment"]
            ):
                return "credit_card_payment"
            return "credit_card"
        elif any(food in sender_lower for food in self.categories["food_dining"]):
            return "food"
        elif any(
            transport in sender_lower
            for transport in self.categories["travel_transport"]
        ):
            return "transport"
        elif any(shop in sender_lower for shop in self.categories["shopping_retail"]):
            return "shopping"
        elif any(finance in sender_lower for finance in self.categories["financial"]):
            return "financial"

        # If sender doesn't match, check content
        content_lower = content.lower()
        if "credit card" in content_lower or "card ending" in content_lower:
            return "credit_card"
        elif "order" in content_lower and any(
            food in content_lower for food in ["food", "meal", "restaurant"]
        ):
            return "food"
        elif any(
            transport in content_lower for transport in ["ride", "trip", "booking"]
        ):
            return "transport"
        elif "order" in content_lower and any(
            shop in content_lower for shop in ["delivered", "shipping"]
        ):
            return "shopping"

        return "unknown"

    def _identify_issuer(self, content: str) -> Optional[str]:
        """
        Identify credit card issuer from content or sender
        Args:
            content (str): Email content or sender
        Returns:
            Optional[str]: Identified issuer or None
        """
        try:
            content_lower = content.lower()

            # Direct mapping of issuers
            issuer_variations = {
                "hdfc": ["hdfc", "hdfc bank", "hdfcbank"],
                "icici": ["icici", "icici bank", "icicibank"],
                "sbi": ["sbi", "sbi card", "sbicard", "state bank"],
                "axis": ["axis", "axis bank", "axisbank"],
                "kotak": ["kotak", "kotak bank", "kotakbank"],
                "yes": ["yes", "yes bank", "yesbank"],
                "idfc": ["idfc", "idfc bank", "idfcbank", "idfc first"],
                "indusind": ["indusind", "indusind bank", "indusindbank"],
                "rbl": ["rbl", "rbl bank", "rblbank"],
                "federal": ["federal", "federal bank", "federalbank"],
                "dcb": ["dcb", "dcb bank", "dcbbank"],
                "bandhan": ["bandhan", "bandhan bank", "bandhanbank"],
                "tata": ["tata", "tata card", "tata neu"],
                "au": ["au", "au bank", "au small finance", "aubank"],
                "standard_chartered": ["standard chartered", "sc bank", "scb", "sc"],
                "hsbc": ["hsbc", "hsbc bank", "hsbcbank"],
                "dbs": ["dbs", "dbs bank", "dbsbank"],
                "citi": ["citi", "citibank", "citi bank"],
                "amex": ["amex", "american express"],
                "slice": ["slice", "sliceit"],
                "uni": ["uni", "uni cards", "unicards"],
                "onecard": ["onecard", "one card", "ftc"],
            }

            # Check each issuer's variations
            for issuer, variations in issuer_variations.items():
                if any(variation in content_lower for variation in variations):
                    return issuer

            return None

        except Exception as e:
            logging.error(f"Error identifying issuer: {str(e)}")
            return None

    def _identify_card_network(self, content: str) -> Optional[str]:
        """
        Identify card network from content
        Args:
            content (str): Email content
        Returns:
            Optional[str]: Identified card network or None
        """
        try:
            content_lower = content.lower()

            # Card network patterns
            networks = {
                "visa": [
                    "visa",
                    "visa card",
                    "visa credit",
                    "visa debit",
                    "visa platinum",
                    "visa signature",
                    "visa infinite",
                ],
                "mastercard": [
                    "mastercard",
                    "master card",
                    "master",
                    "mastercard world",
                    "mastercard black",
                    "mastercard platinum",
                    "mastercard titanium",
                ],
                "rupay": [
                    "rupay",
                    "ru pay",
                    "rupay card",
                    "rupay debit",
                    "rupay credit",
                    "rupay platinum",
                    "rupay select",
                ],
                "amex": [
                    "american express",
                    "amex",
                    "amex card",
                    "amex platinum",
                    "amex gold",
                    "amex centurion",
                ],
                "diners": [
                    "diners",
                    "diners club",
                    "diners international",
                    "diners premium",
                    "diners privilege",
                ],
            }

            for network, patterns in networks.items():
                if any(pattern in content_lower for pattern in patterns):
                    return network

            return None

        except Exception as e:
            logging.error(f"Error identifying card network: {str(e)}")
            return None

    def _identify_card_type(self, content: str) -> Optional[str]:
        """
        Identify card type from content
        Args:
            content (str): Email content
        Returns:
            Optional[str]: Identified card type or None
        """
        try:
            content_lower = content.lower()

            # Card type patterns
            types = {
                "credit": [
                    "credit card",
                    "credit account",
                    "credit limit",
                    "credit statement",
                    "creditcard",
                ],
                "debit": [
                    "debit card",
                    "debit account",
                    "atm card",
                    "debit statement",
                    "debitcard",
                ],
                "prepaid": [
                    "prepaid card",
                    "prepaid account",
                    "wallet card",
                    "gift card",
                    "prepaidcard",
                ],
            }

            for card_type, patterns in types.items():
                if any(pattern in content_lower for pattern in patterns):
                    return card_type

            return None

        except Exception as e:
            logging.error(f"Error identifying card type: {str(e)}")
            return None

    def get_card_details(self, content: str) -> Dict[str, Optional[str]]:
        """
        Get comprehensive card details from content
        Args:
            content (str): Email content
        Returns:
            Dict[str, Optional[str]]: Dictionary with card details
        """
        try:
            details = {
                "issuer": self._identify_issuer(content),
                "network": self._identify_card_network(content),
                "type": self._identify_card_type(content),
                "number": self._extract_pattern_match(
                    content, self.patterns["credit_card"]["card_numbers"]
                ),
            }

            # Add card variant if available
            variant = (
                self._identify_card_variant(content, details["issuer"])
                if details["issuer"]
                else None
            )
            if variant:
                details["variant"] = variant

            return details

        except Exception as e:
            logging.error(f"Error getting card details: {str(e)}")
            return {"issuer": None, "network": None, "type": None, "number": None}

    def _identify_card_variant(self, content: str, issuer: str) -> Optional[str]:
        """
        Identify card variant based on issuer and content
        Args:
            content (str): Email content
            issuer (str): Card issuer
        Returns:
            Optional[str]: Identified card variant or None
        """
        try:
            content_lower = content.lower()

            # Common variants across issuers
            common_variants = {
                "platinum": ["platinum", "platinum rewards"],
                "gold": ["gold", "gold rewards"],
                "business": ["business", "corporate", "commercial"],
                "premium": ["premium", "privilege", "preferred"],
                "basic": ["basic", "classic", "standard"],
            }

            # Issuer-specific variants
            issuer_variants = {
                "hdfc": {
                    "regalia": ["regalia", "regalia first"],
                    "diners": ["diners", "diners club"],
                    "infinia": ["infinia"],
                    "millenia": ["millenia"],
                },
                "icici": {
                    "sapphiro": ["sapphiro"],
                    "rubyx": ["rubyx"],
                    "emeralde": ["emeralde"],
                },
                "axis": {
                    "magnus": ["magnus"],
                    "burgundy": ["burgundy"],
                    "ace": ["ace"],
                },
                # Add more issuer-specific variants as needed
            }

            # Check common variants first
            for variant, patterns in common_variants.items():
                if any(pattern in content_lower for pattern in patterns):
                    return variant

            # Check issuer-specific variants
            if issuer in issuer_variants:
                for variant, patterns in issuer_variants[issuer].items():
                    if any(pattern in content_lower for pattern in patterns):
                        return variant

            return None

        except Exception as e:
            logging.error(f"Error identifying card variant: {str(e)}")
            return None

    async def analyze_emails(self, emails: List[Dict]) -> Dict:
        """Main analysis function"""
        try:
            results = {
                "credit_analysis": self.analyze_credit_cards(emails),
                "spending_analysis": self.analyze_spending(emails),
                "summary": {
                    "total_emails": len(emails),
                    "analysis_date": datetime.now().isoformat(),
                    "insights": [],
                },
            }

            # Generate insights
            insights = self.generate_insights(results)
            results["summary"]["insights"] = insights

            return results

        except Exception as e:
            logging.error(f"Error analyzing emails: {str(e)}", exc_info=True)
            raise Exception(f"Email analysis failed: {str(e)}")

    def analyze_credit_cards(self, emails: List[Dict]) -> Dict:
        """Analyze credit card related emails"""
        credit_info = defaultdict(
            lambda: {
                "card_number": None,
                "issuer": None,
                "transactions": [],
                "total_spend": 0,
                "payment_history": [],
            }
        )

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            sender = email.get("sender", "").lower()
            date = email.get("date")

            if not isinstance(date, str):
                date = date.strftime("%Y-%m-%d %H:%M:%S")

            # Skip promotional content
            if self._is_credit_card_promotional(content):
                continue

            # Get transaction type
            transaction_type = self._get_transaction_type(content, sender)
            if transaction_type not in ["credit_card", "credit_card_payment"]:
                continue

            # Extract card details
            card_number = self._extract_pattern_match(
                content, self.patterns["credit_card"]["card_numbers"]
            )
            if card_number:
                issuer = self._identify_issuer(sender)
                if not issuer:
                    continue

                card_key = f"{issuer}_{card_number}"
                credit_info[card_key]["issuer"] = issuer
                credit_info[card_key]["card_number"] = card_number

                if transaction_type == "credit_card":
                    self._process_transaction(content, date, credit_info[card_key])
                else:
                    self._process_payment(content, date, credit_info[card_key])

        return dict(credit_info)

    def analyze_spending(self, emails: List[Dict]) -> Dict:
        """Analyze spending patterns"""
        spending_info = {
            "categories": defaultdict(
                lambda: {
                    "total_spend": 0,
                    "transaction_count": 0,
                    "merchants": defaultdict(int),
                    "monthly_trends": defaultdict(float),
                    "average_transaction": 0,
                    "largest_transaction": 0,
                    "recent_transactions": [],
                }
            ),
            "overall": {
                "total_spend": 0,
                "total_transactions": 0,
                "monthly_totals": defaultdict(float),
                "peak_spending_month": None,
                "top_merchants": [],
            },
        }

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            sender = email.get("sender", "").lower()
            date = email.get("date")

            # Skip credit card payments
            if self._get_transaction_type(content, sender) == "credit_card_payment":
                continue

            # Skip promotional content
            if self._is_credit_card_promotional(content):
                continue

            # Extract and process transaction
            transaction = self._extract_transaction_details(content, date, sender)
            if transaction:
                # Update category metrics
                self._update_category_metrics(transaction, spending_info)
                # Update overall metrics
                self._update_overall_metrics(transaction, spending_info)

        # Calculate final metrics
        self._calculate_spending_metrics(spending_info)
        return spending_info

    def _extract_transaction_details(
        self, content: str, date: str, sender: str
    ) -> Optional[Dict]:
        """Extract transaction details based on email type"""
        try:
            # Determine transaction type
            transaction_type = self._get_transaction_type(content, sender)
            if transaction_type == "unknown":
                return None

            # Extract amount based on type
            amount = self._extract_amount(content, transaction_type)
            if not amount:
                return None

            # Extract merchant based on type
            merchant = self._extract_merchant(content, transaction_type)
            if not merchant:
                merchant = "unknown"

            # Get category
            category = self._categorize_merchant(merchant, transaction_type)

            # Extract reference and payment mode
            reference = self._extract_pattern_match(
                content, [self.patterns["transaction"]["reference"]]
            )
            payment_mode = (
                self._extract_pattern_match(content, self.patterns["payment"]["mode"])
                if "payment" in self.patterns
                else None
            )

            return {
                "date": date,
                "amount": float(amount),
                "merchant": merchant,
                "category": category,
                "type": transaction_type,
                "reference": reference or "N/A",
                "payment_mode": payment_mode or "unknown",
            }

        except Exception as e:
            logging.error(f"Error extracting transaction details: {str(e)}")
            return None

    def _categorize_merchant(self, merchant: str, transaction_type: str) -> str:
        """Categorize merchant based on transaction type and merchant name"""
        if transaction_type != "unknown":
            return transaction_type

        if not merchant or merchant.lower() == "unknown":
            return "others"

        merchant_lower = merchant.lower()

        # Check each category's keywords
        for category, merchants in self.categories.items():
            if any(m.lower() in merchant_lower for m in merchants):
                return category

        return "others"

    def _process_transaction(self, content: str, date: str, card_info: Dict):
        """Process credit card transaction"""
        transaction_type = self._get_transaction_type(content, "")
        amount = self._extract_amount(content, transaction_type)
        merchant = self._extract_merchant(content, transaction_type)

        if amount:
            transaction = {
                "date": date,
                "amount": amount,
                "merchant": merchant or "unknown",
                "type": "debit",
            }

            card_info["transactions"].append(transaction)
            card_info["total_spend"] += amount

    def _process_payment(self, content: str, date: str, card_info: Dict):
        """Process credit card payment"""
        amount = self._extract_amount(content, "credit_card_payment")
        if amount:
            payment = {
                "date": date,
                "amount": amount,
                "type": "credit",
                "mode": self._extract_pattern_match(
                    content, self.patterns["payment"]["mode"]
                )
                or "unknown",
            }
            card_info["payment_history"].append(payment)

    def _update_category_metrics(self, transaction: Dict, spending_info: Dict):
        """Update category-specific metrics"""
        try:
            category = transaction.get("category", "others")
            amount = transaction.get("amount", 0.0)
            date = transaction.get("date")
            merchant = transaction.get("merchant", "Unknown")

            if not all([category, amount, date, merchant]):
                return

            category_data = spending_info["categories"][category]

            # Update basic metrics
            category_data["total_spend"] += float(amount)
            category_data["transaction_count"] += 1
            category_data["merchants"][merchant] += 1

            # Update monthly trends
            try:
                month_key = pd.to_datetime(date).strftime("%Y-%m")
                category_data["monthly_trends"][month_key] += float(amount)
            except Exception as e:
                logging.error(f"Error processing date in category metrics: {str(e)}")

            # Update transaction extremes
            category_data["largest_transaction"] = max(
                category_data["largest_transaction"], float(amount)
            )

            # Track recent transactions
            category_data["recent_transactions"].append(
                {
                    "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount": float(amount),
                    "merchant": merchant,
                }
            )

            # Keep only recent 5 transactions
            category_data["recent_transactions"] = sorted(
                category_data["recent_transactions"],
                key=lambda x: pd.to_datetime(x["date"]),
                reverse=True,
            )[:5]

        except Exception as e:
            logging.error(f"Error updating category metrics: {str(e)}")

    def _update_overall_metrics(self, transaction: Dict, spending_info: Dict):
        """Update overall spending metrics"""
        amount = transaction.get("amount", 0.0)
        date = transaction.get("date")

        overall = spending_info["overall"]

        # Update totals
        overall["total_spend"] += amount
        overall["total_transactions"] += 1

        # Update monthly totals
        month_key = pd.to_datetime(date).strftime("%Y-%m")
        overall["monthly_totals"][month_key] += amount

        # Update peak spending month
        if (
            not overall["peak_spending_month"]
            or overall["monthly_totals"][month_key]
            > overall["monthly_totals"][overall["peak_spending_month"]]
        ):
            overall["peak_spending_month"] = month_key

    def _calculate_spending_metrics(self, spending_info: Dict):
        """Calculate final spending metrics"""
        try:
            total_spend = spending_info["overall"]["total_spend"]

            for category_data in spending_info["categories"].values():
                if category_data["transaction_count"] > 0:
                    # Calculate averages
                    category_data["average_transaction"] = round(
                        category_data["total_spend"]
                        / category_data["transaction_count"],
                        2,
                    )

                    # Calculate percentages
                    category_data["spend_percentage"] = round(
                        (category_data["total_spend"] / total_spend) * 100, 2
                    )

                    # Process merchant data
                    merchant_list = sorted(
                        category_data["merchants"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:5]

                    category_data["top_merchants"] = [
                        {
                            "name": merchant,
                            "transactions": count,
                            "percentage": round(
                                (count / category_data["transaction_count"]) * 100, 2
                            ),
                        }
                        for merchant, count in merchant_list
                    ]

        except Exception as e:
            logging.error(f"Error calculating spending metrics: {str(e)}")

    def generate_insights(self, analysis_results: Dict) -> List[str]:
        """
        Generate insights from analysis results
        Args:
            analysis_results (Dict): Analysis results dictionary
        Returns:
            List[str]: List of insights
        """
        try:
            insights = []

            # Credit card insights
            if analysis_results.get("credit_analysis"):
                credit_insights = self._generate_credit_insights(
                    analysis_results["credit_analysis"]
                )
                insights.extend(credit_insights)

            # Spending insights
            if analysis_results.get("spending_analysis"):
                spending_insights = self._generate_spending_insights(
                    analysis_results["spending_analysis"]
                )
                insights.extend(spending_insights)

            return insights

        except Exception as e:
            logging.error(f"Error generating insights: {str(e)}")
            return ["Unable to generate insights due to an error"]

    def _generate_credit_insights(self, credit_data: Dict) -> List[str]:
        """
        Generate insights from credit card analysis
        Args:
            credit_data (Dict): Credit card analysis data
        Returns:
            List[str]: List of credit card insights
        """
        insights = []
        try:
            total_cards = len(credit_data)

            if total_cards > 0:
                insights.append(f"Active credit cards: {total_cards}")

                # Card usage insights
                for card_id, info in credit_data.items():
                    bank = card_id.split("_")[0].upper()

                    # Spending insights
                    total_spent = sum(t["amount"] for t in info["transactions"])
                    if total_spent > 0:
                        insights.append(
                            f"{bank} card ending {card_id.split('_')[1]}: ₹{total_spent:,.2f}"
                        )

                    # Payment insights
                    if info.get("payment_history"):
                        total_payments = sum(
                            p["amount"] for p in info["payment_history"]
                        )
                        insights.append(
                            f"Total payments for {bank} card: ₹{total_payments:,.2f}"
                        )

                    # Calculate utilization if limits available
                    if "credit_limit" in info and info["credit_limit"]:
                        utilization = (total_spent / float(info["credit_limit"])) * 100
                        if utilization > 80:
                            insights.append(
                                f"High utilization ({utilization:.1f}%) on {bank} card"
                            )
                        elif utilization < 30:
                            insights.append(
                                f"Low utilization ({utilization:.1f}%) on {bank} card"
                            )

                    # Merchant analysis
                    if info.get("transactions"):
                        merchants = {}
                        for trans in info["transactions"]:
                            merchant = trans.get("merchant", "Unknown")
                            merchants[merchant] = merchants.get(merchant, 0) + 1

                        # Top merchants
                        if merchants:
                            top_merchant = max(merchants.items(), key=lambda x: x[1])
                            insights.append(
                                f"Most frequent merchant for {bank} card: {top_merchant[0]} ({top_merchant[1]} transactions)"
                            )

            return insights

        except Exception as e:
            logging.error(f"Error generating credit insights: {str(e)}")
            return ["Unable to generate credit card insights"]

    def _generate_spending_insights(self, spending_data: Dict) -> List[str]:
        """
        Generate insights from spending analysis
        Args:
            spending_data (Dict): Spending analysis data
        Returns:
            List[str]: List of spending insights
        """
        insights = []
        try:
            categories = spending_data.get("categories", {})
            overall = spending_data.get("overall", {})

            if not overall.get("total_spend"):
                return ["No spending data available for analysis"]

            # Overall spending insights
            total_spend = overall["total_spend"]
            total_transactions = overall["total_transactions"]
            insights.append(
                f"Total spending: ₹{total_spend:,.2f} across {total_transactions} transactions"
            )

            # Monthly analysis
            monthly_totals = overall.get("monthly_totals", {})
            if monthly_totals:
                avg_monthly = total_spend / max(len(monthly_totals), 1)
                insights.append(f"Average monthly spending: ₹{avg_monthly:,.2f}")

                peak_month = overall.get("peak_spending_month")
                if peak_month:
                    peak_amount = monthly_totals[peak_month]
                    insights.append(
                        f"Highest spending in {peak_month}: ₹{peak_amount:,.2f}"
                    )

            # Category analysis
            if categories:
                # Sort categories by spend
                sorted_cats = sorted(
                    categories.items(), key=lambda x: x[1]["total_spend"], reverse=True
                )

                # Top spending categories
                for category, data in sorted_cats[:3]:
                    spend_percent = (data["total_spend"] / total_spend) * 100
                    insights.append(
                        f"{category.replace('_', ' ').title()}: ₹{data['total_spend']:,.2f} "
                        f"({spend_percent:.1f}% of total)"
                    )

                # Large transactions
                for category, data in sorted_cats:
                    if data["largest_transaction"] > total_spend * 0.1:
                        insights.append(
                            f"Large {category.replace('_', ' ')} transaction: "
                            f"₹{data['largest_transaction']:,.2f}"
                        )

            # Spending trends
            if len(monthly_totals) >= 2:
                months = sorted(monthly_totals.keys())
                latest = months[-1]
                previous = months[-2]
                change = (
                    (monthly_totals[latest] - monthly_totals[previous])
                    / monthly_totals[previous]
                    * 100
                )

                if abs(change) > 20:
                    direction = "increased" if change > 0 else "decreased"
                    insights.append(
                        f"Spending {direction} by {abs(change):.1f}% compared to previous month"
                    )

            # Merchant insights
            top_merchants = overall.get("top_merchants", [])
            if top_merchants:
                top_merchant = top_merchants[0]
                insights.append(
                    f"Most used merchant: {top_merchant['name']} "
                    f"(₹{top_merchant['total_spent']:,.2f} across "
                    f"{top_merchant['transaction_count']} transactions)"
                )

            return insights

        except Exception as e:
            logging.error(f"Error generating spending insights: {str(e)}")
            return ["Unable to generate spending insights"]

    def _generate_merchant_insights(self, transactions: List[Dict]) -> List[str]:
        """
        Generate insights about merchant patterns
        Args:
            transactions (List[Dict]): List of transactions
        Returns:
            List[str]: List of merchant insights
        """
        insights = []
        try:
            if not transactions:
                return insights

            # Merchant frequency analysis
            merchant_data = defaultdict(
                lambda: {"count": 0, "amount": 0.0, "dates": []}
            )

            for trans in transactions:
                merchant = trans.get("merchant", "Unknown")
                amount = trans.get("amount", 0.0)
                date = trans.get("date")

                merchant_data[merchant]["count"] += 1
                merchant_data[merchant]["amount"] += amount
                if date:
                    merchant_data[merchant]["dates"].append(date)

            # Sort merchants by frequency
            sorted_merchants = sorted(
                merchant_data.items(), key=lambda x: x[1]["count"], reverse=True
            )

            # Top merchant insights
            if sorted_merchants:
                top_merchant = sorted_merchants[0]
                insights.append(
                    f"Most frequent merchant: {top_merchant[0]} "
                    f"({top_merchant[1]['count']} transactions, "
                    f"₹{top_merchant[1]['amount']:,.2f} total)"
                )

            # Recurring payment detection
            for merchant, data in merchant_data.items():
                if data["count"] >= 3:  # At least 3 transactions
                    dates = [pd.to_datetime(d) for d in data["dates"]]
                    if dates:
                        date_diffs = [
                            (dates[i + 1] - dates[i]).days
                            for i in range(len(dates) - 1)
                        ]
                        avg_diff = sum(date_diffs) / len(date_diffs)

                        # Check if transactions are regular (within 5 days variance)
                        if all(abs(diff - avg_diff) <= 5 for diff in date_diffs):
                            insights.append(
                                f"Possible recurring payment: {merchant} "
                                f"(~every {int(avg_diff)} days)"
                            )

            return insights

        except Exception as e:
            logging.error(f"Error generating merchant insights: {str(e)}")
            return []
