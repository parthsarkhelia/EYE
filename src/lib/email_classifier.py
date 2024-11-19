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

    def _init_patterns(self):
        # Exclude words that should not be considered as merchant names
        exclude_words = r"(?!(?:transaction|amount|bank|credit|debit|card|limit|inr|rs|rupees|available|\d+))"
        self.patterns = {
            "credit_card": {
                # Card identification patterns
                "card_numbers": [
                    r"(?:card|cc)\s+(?:no\.?|number|ending)\s+(?:in\s+)?(?:[Xx*]+|XX|xx)(\d{4})",
                    r"(?:card|cc)(?:\s+account)?\s+(?:\d{4}\s+)?(?:X{4}\s+){2,3}(\d{4})",
                    r"(?:credit\s+card|card)\s+(?:account\s+)?(\d{4})(?:\s+X{4}){2,3}",
                    r"(?:card\s+account\s+)?(\d{4})\s+X{4}\s+X{4}\s+(\d{4})",
                    r"(?:card|account).{0,30}?(\d{4})(?:\s|$)",
                ],
                "card_type": r"(?:credit|debit)\s+card\s+(?:no\.?|number)\s+(?:[Xx*]+|XX|xx)(\d{4})",
                # Statement patterns
                "statement_period": r"(?:STATEMENT\s+FOR\s+THE\s+PERIOD|FOR\s+THE\s+PERIOD|STATEMENT\s+PERIOD)\s*(?:FROM\s+)?([A-Za-z]+\s+\d{1,2},?\s*\d{4})\s*(?:TO|TILL|[-])\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})",
                "card_statement": r"(?:CREDIT\s+CARD\s+(?:E)?STATEMENT|(?:E)?STATEMENT\s+FOR)\s+(?:FOR\s+)?([A-Za-z]+\s+\d{4})",
                "due_date": r"(?:PAYMENT\s+)?DUE\s+(?:DATE|BY)[:\s]*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s*\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                "total_due": r"(?:TOTAL\s+(?:AMOUNT\s+)?DUE|PAYMENT\s+DUE|CURRENT\s+AMOUNT\s+DUE)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                "min_due": r"(?:MINIMUM|MIN\.?)\s+(?:AMOUNT\s+)?(?:DUE|PAYMENT)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                "credit_limit": r"(?:TOTAL\s+CREDIT\s+LIMIT|CREDIT\s+LIMIT|CARD\s+LIMIT)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                "available_limit": r"(?:AVAILABLE\s+CREDIT\s+LIMIT|AVAILABLE\s+LIMIT)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)",
                # Transaction patterns
                "transaction_amount": r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "transaction_date": r"(?:date|on)\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                "transaction_time": r"(?:at|@)\s*(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)",
                # Payment patterns
                "payment_received": r"(?:payment\s+received|thank\s+you\s+for\s+your\s+payment|payment\s+confirmed).*?(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "payment_mode": r"(?:payment\s+mode|paid\s+via|paid\s+using)[:\s]*([A-Za-z\s]+)",
            },
            "transaction": {
                "amount": r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
                "upi_id": r"(?:UPI|VPA|upi\s+id)[:\s]*([a-zA-Z0-9\.\-\_]+@[a-zA-Z]+)",
                "merchant": rf"at\s+{exclude_words}([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s*\.\s*|\s*$)",
                "merchant_alt": r"(?:at|in)\s+([A-Z][A-Za-z0-9\s&\-\.]+?(?:MART|SHOP|STORE|CINEMA|RESTAURANT|CAFE|HOTEL|MALL|ENTERPRISES|SOLUTIONS|LABS|TECHNOLOGIES|PVT|LTD))(?:\s+on|\s*\.\s*|\s*$)",
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
                "niyo",
                "fi",
            ],
            "food-dining": [
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
            "travel-transport": [
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
                "mart",
                "supermarket",
                "store",
                "retail",
                "shop",
                "mall",
            ],
            "utilities_bills": [
                "electricity",
                "water",
                "gas",
                "broadband",
                "internet",
                "mobile",
                "phone",
                "dth",
                "recharge",
                "bill",
                "fastag",
                "maintenance",
                "association",
                "society",
            ],
            "entertainment": [
                "netflix",
                "prime",
                "hotstar",
                "sony",
                "zee",
                "bookmyshow",
                "pvr",
                "inox",
                "cinemas",
                "movies",
                "theater",
                "games",
                "gaming",
            ],
            "health_medical": [
                "hospital",
                "clinic",
                "pharmacy",
                "medical",
                "doctor",
                "healthcare",
                "diagnostic",
                "lab",
                "apollo",
                "fortis",
                "manipal",
                "wellness",
            ],
            "education": [
                "school",
                "college",
                "university",
                "institute",
                "academy",
                "classes",
                "course",
                "training",
                "education",
                "learning",
                "udemy",
                "coursera",
            ],
            "financial": [
                "insurance",
                "investment",
                "mutual fund",
                "stocks",
                "trading",
                "loan",
                "emi",
                "bank",
                "finance",
                "payment",
                "zerodha",
                "groww",
                "upstox",
            ],
        }

        # Additional metadata for transactions
        self.transaction_types = {
            "credit": ["credit", "received", "refund", "cashback", "reversal"],
            "debit": ["debit", "paid", "payment", "spent", "withdraw", "purchase"],
            "pending": ["pending", "processing", "initiated", "authorization"],
        }

        self.payment_modes = {
            "upi": ["upi", "unified payments", "google pay", "phonepe", "paytm"],
            "netbanking": ["netbanking", "internet banking", "online banking"],
            "card": ["credit card", "debit card", "card payment", "visa", "mastercard"],
            "wallet": ["wallet", "paytm wallet", "amazon pay", "mobikwik"],
            "cash": ["cash", "cash deposit", "atm"],
        }

    def _extract_pattern(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_card_number(self, text: str) -> Optional[str]:
        for pattern in self.patterns["credit_card"]["card_numbers"]:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_amount(self, text: str, pattern: str) -> Optional[float]:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except (ValueError, IndexError):
                return None
        return None

    def _extract_date(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text)
        if match:
            try:
                date_str = match.group(1)
                for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                    except ValueError:
                        continue
            except (ValueError, IndexError):
                return None
        return None

    def _extract_rewards(self, content: str, card_info: Dict):
        points_match = re.search(r"(?:reward|points)[:\s]*(\d+)", content)
        if points_match:
            card_info["reward_points"] += int(points_match.group(1))

    async def analyze_emails(self, emails: List[Dict]) -> Dict:
        try:
            results = {
                "credit_analysis": self.analyze_credit_cards(emails),
                "spending_analysis": self.analyze_spending(emails),
                # "identity_analysis": self.analyze_identity(emails),
                # "portfolio_analysis": self.analyze_portfolio(emails),
                # "travel_analysis": self.analyze_travel(emails),
                "summary": {
                    "total_emails": len(emails),
                    "analysis_date": datetime.now().isoformat(),
                    "insights": [],
                },
            }

            # Generate insights
            insights = self.generate_insights(results)
            results["summary"]["insights"] = insights

            # # Generate heatmap if travel data exists
            # if results["travel_analysis"].get("routes"):
            #     results["travel_analysis"]["heatmap"] = self.generate_heatmap_data(
            #         results["travel_analysis"]
            #     )

            return results

        except Exception as e:
            logging.error(f"Error analyzing emails: {str(e)}", exc_info=True)
            raise Exception(f"Email analysis failed: {str(e)}")

    def analyze_credit_cards(self, emails: List[Dict]) -> Dict:
        credit_info = defaultdict(
            lambda: {
                "card_number": None,
                "issuer": None,
                "transactions": [],
                # "statements": [],
                # "credit_limit": None,
                "total_spend": 0,
                "payment_history": [],
                # "reward_points": 0,
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

            # Identify issuer from sender domain
            issuer = self._identify_issuer(sender)
            if not issuer:
                continue

            # Extract card details
            card_number = self._extract_card_number(content)
            if card_number:
                card_key = f"{issuer}_{card_number}"
                credit_info[card_key]["issuer"] = issuer
                credit_info[card_key]["card_number"] = card_number
                # Process based on email type
                if self._is_credit_card_transaction_alert(content):
                    self._process_transaction(content, date, credit_info[card_key])
                # elif self._is_credit_card_statement(content):
                # self._process_statement(content, date, credit_info[card_key])
                elif self._is_credit_card_payment_confirmation(content):
                    self._process_payment(content, date, credit_info[card_key])

                # Extract additional card-specific info
                self._extract_rewards(content, credit_info[card_key])

        # Calculate metrics for each card
        for card_info in credit_info.values():
            self._calculate_card_metrics(card_info)

        return dict(credit_info)

    def _identify_issuer(self, content: str) -> Optional[str]:
        content_lower = content.lower()

        # Check for issuer names in content
        for issuer in self.categories["credit_cards"]:
            # Create variations of issuer names (e.g., "hdfc", "hdfc bank", "hdfcbank")
            issuer_variations = [issuer, f"{issuer} bank", f"{issuer}bank"]

            if any(variation in content_lower for variation in issuer_variations):
                return issuer

        return None

    def _identify_network(self, content: str) -> Optional[str]:
        networks = {
            "visa": [
                "visa",
                "visa card",
                "visa credit",
                "visa debit",
                "visa platinum",
                "visa signature",
                "visa infinite",
                "visa business",
                "visa corporate",
                "visa electron",
                "vpay",
            ],
            "mastercard": [
                "mastercard",
                "master card",
                "master credit",
                "master debit",
                "mastercard world",
                "mastercard black",
                "mastercard platinum",
                "mastercard titanium",
                "mastercard corporate",
                "mastercard business",
                "cirrus",
                "maestro",
            ],
            "rupay": [
                "rupay",
                "rupay card",
                "ru pay",
                "rupay debit",
                "rupay credit",
                "rupay platinum",
                "rupay select",
                "rupay business",
                "rupay global",
                "rupay international",
            ],
            "amex": [
                "amex",
                "american express",
                "amex platinum",
                "amex gold",
                "amex centurion",
                "amex black",
                "amex business",
                "amex corporate",
            ],
            "diners": [
                "diners",
                "diners club",
                "diners international",
                "diners premium",
                "diners privilege",
                "diners business",
                "diners corporate",
                "discover",
                "diners black",
            ],
            "jcb": [
                "jcb",
                "japan credit bureau",
                "jcb gold",
                "jcb platinum",
                "jcb business",
                "jcb corporate",
            ],
        }

        content_lower = content.lower()
        return next(
            (
                network
                for network, keywords in networks.items()
                if any(keyword in content_lower for keyword in keywords)
            ),
            None,
        )

    def _is_credit_card_transaction_alert(self, content: str) -> bool:
        keywords = [
            "transaction alert",
            "spent",
            "debited",
            "charged",
            "purchase",
            "debit",
            "Thank you for using your credit card",
            "has been used",
            "for using",
        ]
        return any(keyword in content.lower() for keyword in keywords)

    def _is_credit_card_statement(self, content: str) -> bool:
        return "statement" in content.lower()

    def _is_credit_card_payment_confirmation(self, content: str) -> bool:
        keywords = [
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
        return any(keyword in content.lower() for keyword in keywords)

    def _is_credit_card_promotional(self, content: str) -> bool:
        promo_keywords = [
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
        ]
        return any(keyword in content.lower() for keyword in promo_keywords)

    def _process_transaction(self, content: str, date: str, card_info: Dict):
        amount = self._extract_amount(
            content, self.patterns["credit_card"]["transaction_amount"]
        )
        merchant = self._extract_pattern(
            content, self.patterns["transaction"]["merchant_alt"]
        )
        if not merchant:
            merchant = self._extract_pattern(
                content, self.patterns["transaction"]["merchant"]
            )
        if not merchant:
            merchant = "unknown"

        if amount:
            card_info["transactions"].append(
                {
                    "date": date,
                    "amount": amount,
                    "merchant": merchant,
                    "category": self._categorize_merchant(merchant),
                    "type": "debit",
                }
            )
            card_info["total_spend"] += amount

    def _process_statement(
        self, content: str, subject: str, date: str, card_info: Dict
    ):
        # First check subject for statement period
        period_match = re.search(
            self.patterns["credit_card"]["statement_period"], subject
        )
        if not period_match:
            period_match = re.search(
                self.patterns["credit_card"]["statement_period"], content
            )

        statement_info = {
            "date": date,
            "start_date": period_match.group(1) if period_match else None,
            "end_date": period_match.group(2) if period_match else None,
            "total_due": self._extract_amount(
                content, self.patterns["credit_card"]["total_due"]
            ),
            "min_due": self._extract_amount(
                content, self.patterns["credit_card"]["min_due"]
            ),
            "due_date": self._extract_date(
                content, self.patterns["credit_card"]["due_date"]
            ),
        }

        # Extract credit limits
        credit_limit = self._extract_amount(
            content, self.patterns["credit_card"]["credit_limit"]
        )
        available_limit = self._extract_amount(
            content, self.patterns["credit_card"]["available_limit"]
        )

        if credit_limit:
            card_info["credit_limit"] = credit_limit
        if available_limit:
            card_info["available_limit"] = available_limit

        if any(statement_info.values()):
            if "statements" not in card_info:
                card_info["statements"] = []
            card_info["statements"].append(statement_info)

    def _process_payment(self, content: str, date: str, card_info: Dict):
        amount = self._extract_amount(
            content, self.patterns["credit_card"]["transaction_amount"]
        )
        if amount:
            card_info["payment_history"].append(
                {
                    "date": date,
                    "amount": amount,
                    "type": "credit",
                    "mode": self._identify_payment_mode(content),
                }
            )

    def _calculate_card_metrics(self, card_info: Dict):
        if not card_info.get("statements"):
            return

        on_time_payments = sum(
            1
            for s in card_info.get("statements")
            for p in card_info.get("payment_history")
            if pd.to_datetime(p["date"]) <= pd.to_datetime(s.get("due_date"))
        )

        card_info["metrics"] = {
            "payment_behavior": {
                "total_statements": len(card_info.get("statements")),
                "on_time_payments": on_time_payments,
                "payment_ratio": on_time_payments / len(card_info.get("statements")),
            },
            "spending_pattern": {
                "average_monthly": card_info.get("total_spend")
                / max(len(card_info.get("statements")), 1),
                "credit_utilization": (
                    card_info.get("total_spend") / card_info.get("credit_limit") * 100
                )
                if card_info.get("credit_limit")
                else None,
            },
            "rewards_summary": {
                "total_points": card_info["reward_points"],
            },
        }

    def analyze_spending(self, emails: List[Dict]) -> Dict:
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
            date = email.get("date")

            # Skip the transactions which are credit-card payment confirmation
            if self._is_credit_card_payment_confirmation(content):
                continue

            # Skip non-transaction emails
            if not self._is_transaction_email(content):
                continue

            # Skip promotional content
            if self._is_credit_card_promotional(content):
                continue

            # Extract transaction details
            transaction = self._extract_transaction_details(content, date)
            if not transaction:
                continue

            # Update category-specific metrics
            self._update_category_metrics(transaction, spending_info)

            # Update overall spending metrics
            self._update_overall_metrics(transaction, spending_info)

        # Post-processing calculations
        self._calculate_spending_metrics(spending_info)
        return spending_info

    def _is_transaction_email(self, content: str) -> bool:
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

    def _categorize_merchant(self, merchant: str) -> str:
        if not merchant:
            return "others"

        merchant_lower = merchant.lower()

        # Skip categorization for unknown merchants
        if merchant_lower in ["unknown", "unknown merchant", "n/a"]:
            return "others"

        # Check each category's keywords
        for category, keywords in self.categories.items():
            if category != "credit_cards":  # Skip credit cards category
                if any(keyword.lower() in merchant_lower for keyword in keywords):
                    return category

        return "others"

    def _extract_transaction_details(self, content: str, date: str) -> Optional[Dict]:
        try:
            # Extract amount
            amount = self._extract_amount(
                content, self.patterns["transaction"]["amount"]
            )
            if not amount:
                return None

            # Extract merchant
            merchant = self._extract_pattern(
                content, self.patterns["transaction"]["merchant"]
            )
            if not merchant:
                merchant = self._extract_pattern(
                    content, self.patterns["transaction"]["merchant_alt"]
                )
            if not merchant:
                merchant = "unknown"

            # Categorize merchant
            category = self._categorize_merchant(merchant)

            # Extract reference and status
            reference = self._extract_pattern(
                content, self.patterns["transaction"]["reference"]
            )
            status = self._extract_pattern(
                content, self.patterns["transaction"]["status"]
            )

            # Build transaction detail dictionary
            transaction_details = {
                "date": date,
                "amount": float(amount),  # Ensure amount is float
                "merchant": merchant,
                "category": category,
                "reference": reference if reference else "N/A",
                "status": status if status else "completed",
                "payment_mode": self._identify_payment_mode(content),
            }

            return transaction_details

        except Exception as e:
            logging.error(f"Error extracting transaction details: {str(e)}")
            return None

    def _update_category_metrics(
        self, transaction: Optional[Dict], spending_info: Dict
    ):
        if not transaction or not isinstance(transaction, dict):
            return

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

            # Keep track of recent transactions (last 5)
            category_data["recent_transactions"].append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "amount": float(amount),
                    "merchant": merchant,
                }
            )

            # Sort and limit recent transactions
            category_data["recent_transactions"] = sorted(
                category_data["recent_transactions"],
                key=lambda x: pd.to_datetime(x["date"]),
                reverse=True,
            )[:5]

        except Exception as e:
            logging.error(f"Error updating category metrics: {str(e)}")

    def _identify_payment_mode(self, content: str) -> str:
        content_lower = content.lower()

        for mode, keywords in self.payment_modes.items():
            if any(keyword in content_lower for keyword in keywords):
                return mode

        return "unknown"

    def _update_overall_metrics(self, transaction: Dict, spending_info: Dict):
        amount = transaction["amount"]
        date = transaction["date"]

        overall = spending_info["overall"]

        # Update totals
        overall["total_spend"] += amount
        overall["total_transactions"] += 1

        # Update time-based metrics
        month_key = date.strftime("%Y-%m")

        overall["monthly_totals"][month_key] += amount

        if (
            not overall["peak_spending_month"]
            or overall["monthly_totals"][month_key]
            > overall["monthly_totals"][overall["peak_spending_month"]]
        ):
            overall["peak_spending_month"] = month_key

    def _calculate_spending_metrics(self, spending_info: Dict):
        try:
            # Calculate category averages and percentages
            total_spend = spending_info["overall"]["total_spend"]

            # Process category-specific metrics
            for category_data in spending_info["categories"].values():
                if category_data["transaction_count"] > 0:
                    # Calculate average transaction amount
                    category_data["average_transaction"] = round(
                        category_data["total_spend"]
                        / category_data["transaction_count"],
                        2,
                    )

                    # Calculate percentage of total spend
                    category_data["spend_percentage"] = round(
                        (category_data["total_spend"] / total_spend) * 100, 2
                    )

                    # Convert merchant tuples to structured dictionaries
                    merchant_items = sorted(
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
                        for merchant, count in merchant_items
                    ]

            # Calculate overall merchant metrics
            all_merchants = defaultdict(
                lambda: {"count": 0, "total_amount": 0, "categories": set()}
            )

            for category, data in spending_info["categories"].items():
                for transaction in data.get("recent_transactions", []):
                    merchant = transaction.get("merchant")
                    if merchant:
                        all_merchants[merchant]["count"] += 1
                        all_merchants[merchant]["total_amount"] += transaction.get(
                            "amount", 0
                        )
                        all_merchants[merchant]["categories"].add(category)

            # Convert to list and sort by transaction count
            top_merchants = sorted(
                [
                    {
                        "name": merchant,
                        "transaction_count": data["count"],
                        "total_spent": round(data["total_amount"], 2),
                        "average_transaction": round(
                            data["total_amount"] / data["count"], 2
                        ),
                        "categories": list(data["categories"]),
                        "percentage": round(
                            (
                                data["count"]
                                / spending_info["overall"]["total_transactions"]
                            )
                            * 100,
                            2,
                        ),
                    }
                    for merchant, data in all_merchants.items()
                ],
                key=lambda x: x["transaction_count"],
                reverse=True,
            )[:10]

            spending_info["overall"]["top_merchants"] = top_merchants

        except Exception as e:
            logging.error(f"Error calculating spending metrics: {str(e)}")
            # Ensure we have at least empty structures
            spending_info["overall"]["top_merchants"] = []

    def generate_insights(self, analysis_results: Dict) -> List[str]:
        insights = []

        # Credit card insights
        if analysis_results.get("credit_analysis"):
            credit = analysis_results["credit_analysis"]
            insights.extend(self._generate_credit_insights(credit))

        # Spending insights
        if analysis_results.get("spending_analysis"):
            spending = analysis_results["spending_analysis"]
            insights.extend(self._generate_spending_insights(spending))

        # Travel insights
        if analysis_results.get("travel_analysis"):
            travel = analysis_results["travel_analysis"]
            insights.extend(self._generate_travel_insights(travel))

        return insights

    def _generate_credit_insights(self, credit_data: Dict) -> List[str]:
        insights = []
        total_cards = len(credit_data)

        if total_cards > 0:
            insights.append(f"Active credit cards: {total_cards}")

            # Spending patterns
            for card_id, info in credit_data.items():
                bank = card_id.split("_")[0].upper()
                card_spent = sum(t["amount"] for t in info["transactions"])
                if card_spent > 0:
                    insights.append(
                        f"{bank} card ending {card_id.split('_')[1]}: ₹{card_spent:,.2f}"
                    )

                # Payment behavior
                if info.get("statements"):
                    on_time_payments = sum(
                        1
                        for s in info["statements"]
                        if pd.to_datetime(s["date"]) <= pd.to_datetime(s["due_date"])
                    )
                    payment_ratio = on_time_payments / len(info["statements"])
                    if payment_ratio >= 0.9:
                        insights.append(f"Excellent payment history for {bank} card")
                    elif payment_ratio < 0.7:
                        insights.append(f"Late payment alerts for {bank} card")

        return insights

    def _generate_spending_insights(self, spending_data: Dict) -> List[str]:
        insights = []
        categories = spending_data.get("categories", {})
        overall = spending_data.get("overall", {})

        # Skip if no spending data
        if not overall.get("total_spend"):
            return ["No spending data available for analysis."]

        try:
            # Overall spending insights
            total_spend = overall["total_spend"]
            total_transactions = overall["total_transactions"]
            insights.append(
                f"Total spending: ₹{total_spend:,.2f} across {total_transactions} transactions"
            )

            # Monthly average and peak spending
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

            # Category-wise analysis
            if categories:
                # Sort categories by total spend
                sorted_categories = sorted(
                    categories.items(), key=lambda x: x[1]["total_spend"], reverse=True
                )

                # Top spending categories
                top_categories = sorted_categories[:3]
                for category, data in top_categories:
                    spend_percentage = (data["total_spend"] / total_spend) * 100
                    insights.append(
                        f"{category.replace('_', ' ').title()}: ₹{data['total_spend']:,.2f} "
                        f"({spend_percentage:.1f}% of total)"
                    )

                # Largest single transactions
                for category, data in sorted_categories:
                    if (
                        data["largest_transaction"] > total_spend * 0.1
                    ):  # Significant transactions
                        insights.append(
                            f"Large {category.replace('_', ' ')} transaction: "
                            f"₹{data['largest_transaction']:,.2f}"
                        )

            # Spending pattern insights
            if monthly_totals:
                months = sorted(monthly_totals.keys())
                if len(months) >= 2:
                    latest_month = months[-1]
                    previous_month = months[-2]
                    month_over_month = (
                        (monthly_totals[latest_month] - monthly_totals[previous_month])
                        / monthly_totals[previous_month]
                        * 100
                    )
                    if abs(month_over_month) > 20:  # Significant change
                        change = "increased" if month_over_month > 0 else "decreased"
                        insights.append(
                            f"Spending {change} by {abs(month_over_month):.1f}% "
                            f"compared to previous month"
                        )

            # Category-specific insights
            for category, data in categories.items():
                # High frequency categories
                if data["transaction_count"] >= 10:
                    avg_transaction = data["total_spend"] / data["transaction_count"]
                    insights.append(
                        f"Average {category.replace('_', ' ')} transaction: ₹{avg_transaction:,.2f}"
                    )

                # Merchant concentration
                top_merchants = data.get("top_merchants", [])
                if top_merchants:
                    # Using the new dictionary structure
                    top_merchant = top_merchants[0]  # First merchant in the list
                    merchant_name = top_merchant.get("name", "Unknown")
                    transaction_count = top_merchant.get("transactions", 0)

                    if data["transaction_count"] > 0:
                        merchant_percentage = (
                            transaction_count / data["transaction_count"]
                        ) * 100
                        if merchant_percentage > 50:
                            insights.append(
                                f"Most frequent {category.replace('_', ' ')} merchant: "
                                f"{merchant_name} ({merchant_percentage:.1f}% of transactions)"
                            )

            # Add insights about top overall merchants
            top_overall_merchants = overall.get("top_merchants", [])
            if top_overall_merchants:
                top_merchant = top_overall_merchants[0]
                insights.append(
                    f"Most used merchant: {top_merchant['name']} "
                    f"(₹{top_merchant['total_spent']:,.2f} across "
                    f"{top_merchant['transaction_count']} transactions)"
                )

        except Exception as e:
            logging.error(f"Error generating spending insights: {str(e)}")
            insights.append(
                "Unable to generate complete spending insights due to an error."
            )

        return insights
