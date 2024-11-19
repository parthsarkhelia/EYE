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
            "identity": {
                "aadhaar": r"(?:aadhaar|aadhar|uid|आधार)[:\s]*(?:\d{4}\s*){3}\d{4}",
                "pan": r"(?:pan|permanent\s+account\s+number)[:\s]*([A-Z]{5}\d{4}[A-Z])",
                "gstin": r"(?:gstin|gst\s+no)[:\s]*\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]{3}",
                "voter_id": r"(?:voter\s+id|epic\s+no)[:\s]*[A-Z]{3}\d{7}",
                "driving_license": r"(?:dl\s+no|driving\s+licen[cs]e)[:\s]*(?:[A-Z]{2}20\d{14})",
                "passport": r"(?:passport\s+no)[:\s]*[A-Z]\d{7}",
                "otp": r"(?:OTP|one\s+time\s+password|verification\s+code|security\s+code)[:\s]*(\d{4,8})",
                "mobile": r"(?:mobile|phone|contact)[:\s]*(?:\+91[\-\s]*)?(\d{10})",
                "email": r"(?:email|e-mail)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Z|a-z]{2,})",
            },
            "bank": {
                "account": r"(?:a/c|account)\s*(?:no\.?|number)[:\s]*[Xx*]*(\d{4})",
                "ifsc": r"(?:ifsc|ifsc\s+code)[:\s]*([A-Z]{4}0[A-Z0-9]{6})",
                "branch": r"(?:branch)[:\s]*([A-Za-z\s]+)",
                "balance": r"(?:balance|available\s+balance)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
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

    async def analyze_emails(self, emails: List[Dict]) -> Dict:
        try:
            results = {
                "credit_analysis": self.analyze_credit_cards(emails),
                # "spending_analysis": self.analyze_spending(emails),
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
        ]
        return any(keyword in content.lower() for keyword in promo_keywords)

    def _extract_rewards(self, content: str, card_info: Dict):
        points_match = re.search(r"(?:reward|points)[:\s]*(\d+)", content)
        if points_match:
            card_info["reward_points"] += int(points_match.group(1))

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
                    "mode": self._extract_payment_mode(content),
                }
            )

    def _extract_payment_mode(self, content: str) -> str:
        mode_match = re.search(self.patterns["credit_card"]["payment_mode"], content)
        return mode_match.group(1).strip().lower() if mode_match else "unknown"

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
        spending = {
            "by_category": defaultdict(float),
            "by_merchant": defaultdict(float),
            "monthly": defaultdict(float),
            "transactions": [],
        }

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            date = email.get("date")

            # Extract transactions
            txn_matches = re.finditer(self.patterns["transaction"]["amount"], content)
            for match in txn_matches:
                amount = float(match.group(1).replace(",", ""))
                merchant = match.group(2).strip()

                # Categorize transaction
                category = self._categorize_merchant(merchant)

                if amount > 0:
                    spending["by_category"][category] += amount
                    spending["by_merchant"][merchant] += amount

                    if date:
                        month_key = pd.to_datetime(date).strftime("%Y-%m")
                        spending["monthly"][month_key] += amount

                    spending["transactions"].append(
                        {
                            "date": date,
                            "amount": amount,
                            "merchant": merchant,
                            "category": category,
                        }
                    )

        return dict(spending)

    def analyze_identity(self, emails: List[Dict]) -> Dict:
        identity = {"verifications": [], "otps": [], "documents": defaultdict(list)}

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            date = email.get("date")

            # Extract OTPs
            otp_match = re.search(self.patterns["identity"]["otp"], content)
            if otp_match:
                identity["otps"].append(
                    {
                        "date": date,
                        "sender": email.get("sender"),
                        "otp": otp_match.group(1),
                    }
                )

            # Extract document verifications
            for doc_type, pattern in [
                ("aadhaar", self.patterns["identity"]["aadhaar"]),
                ("pan", self.patterns["identity"]["pan"]),
            ]:
                if re.search(pattern, content):
                    identity["documents"][doc_type].append(
                        {
                            "date": date,
                            "sender": email.get("sender"),
                            "status": self._extract_verification_status(content),
                        }
                    )

        return dict(identity)

    def analyze_portfolio(self, emails: List[Dict]) -> Dict:
        portfolio = {
            "transactions": [],
            "holdings": defaultdict(float),
            "notifications": [],
        }

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            date = email.get("date")

            # Extract trading activity
            if any(
                term in content.lower()
                for term in ["trade", "buy", "sell", "purchased", "sold"]
            ):
                price_match = re.search(self.patterns["portfolio"]["price"], content)
                qty_match = re.search(self.patterns["portfolio"]["quantity"], content)

                if price_match and qty_match:
                    portfolio["transactions"].append(
                        {
                            "date": date,
                            "price": float(price_match.group(1).replace(",", "")),
                            "quantity": int(qty_match.group(1)),
                            "type": "buy" if "buy" in content.lower() else "sell",
                        }
                    )

        return portfolio

    def analyze_travel(self, emails: List[Dict]) -> Dict:
        travel = {
            "flights": [],
            "hotels": [],
            "transport": [],
            "locations": defaultdict(int),
            "routes": defaultdict(int),
        }

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}"
            date = email.get("date")

            # Extract flight information
            flight_match = re.search(self.patterns["travel"]["flight"], content)
            if flight_match:
                source_dest_match = re.search(
                    self.patterns["travel"]["source_dest"], content
                )
                if source_dest_match:
                    source = source_dest_match.group(1).strip()
                    dest = source_dest_match.group(2).strip()

                    travel["flights"].append(
                        {
                            "date": date,
                            "flight": flight_match.group(1),
                            "source": source,
                            "destination": dest,
                        }
                    )

                    travel["locations"][source] += 1
                    travel["locations"][dest] += 1
                    travel["routes"][f"{source}-{dest}"] += 1

            # Extract hotel stays
            hotel_match = re.search(self.patterns["travel"]["hotel"], content)
            if hotel_match:
                travel["hotels"].append(
                    {
                        "date": date,
                        "hotel": hotel_match.group(1).strip(),
                        "location": self._extract_location(content),
                    }
                )

        return travel

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

    def _categorize_merchant(self, merchant: str) -> str:
        merchant_lower = merchant.lower()

        for category, keywords in self.categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category

        return "others"

    def _extract_verification_status(self, text: str) -> str:
        status_keywords = {
            "success": ["successful", "completed", "verified"],
            "failure": ["failed", "rejected", "unsuccessful"],
            "pending": ["pending", "in process", "initiated"],
        }

        text_lower = text.lower()
        for status, keywords in status_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return status

        return "unknown"

    def _extract_location(self, text: str) -> Optional[str]:
        # Add location extraction logic here
        return None

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

        # Category analysis
        if spending_data["by_category"]:
            total_spent = sum(spending_data["by_category"].values())
            insights.append(f"Total spending: ₹{total_spent:,.2f}")

            # Top categories
            top_categories = sorted(
                spending_data["by_category"].items(), key=lambda x: x[1], reverse=True
            )[:3]
            cat_text = ", ".join(f"{cat}: ₹{amt:,.2f}" for cat, amt in top_categories)
            insights.append(f"Top spending categories: {cat_text}")

            # Monthly trend
            if spending_data["monthly"]:
                months = sorted(spending_data["monthly"].items())
                if len(months) > 1:
                    latest = months[-1][1]
                    previous = months[-2][1]
                    change = (latest - previous) / previous * 100
                    insights.append(
                        f"Monthly spending {'increased' if change > 0 else 'decreased'} by {abs(change):.1f}%"
                    )

        return insights

    def _generate_travel_insights(self, travel_data: Dict) -> List[str]:
        insights = []

        if travel_data["flights"]:
            total_flights = len(travel_data["flights"])
            insights.append(f"Total flights: {total_flights}")

            # Popular routes
            if travel_data["routes"]:
                top_routes = sorted(
                    travel_data["routes"].items(), key=lambda x: x[1], reverse=True
                )[:3]
                routes_text = ", ".join(
                    f"{route}: {count}x" for route, count in top_routes
                )
                insights.append(f"Most frequent routes: {routes_text}")

            # Location frequency
            if travel_data["locations"]:
                top_locations = sorted(
                    travel_data["locations"].items(), key=lambda x: x[1], reverse=True
                )[:3]
                loc_text = ", ".join(f"{loc}: {count}x" for loc, count in top_locations)
                insights.append(f"Most visited: {loc_text}")

        return insights

    def generate_heatmap_data(self, travel_data: Dict) -> List[Dict]:
        heatmap_data = []

        # Process routes for heatmap
        for route, frequency in travel_data["routes"].items():
            source, destination = route.split("-")
            heatmap_data.append(
                {
                    "source": source.strip(),
                    "destination": destination.strip(),
                    "weight": frequency,
                    "value": frequency * 100,  # Scale for visualization
                }
            )

        return heatmap_data

    def analyze_portfolio_metrics(self, portfolio_data: Dict) -> Dict:
        metrics = {
            "total_transactions": len(portfolio_data["transactions"]),
            "buy_sell_ratio": 0,
            "average_transaction_size": 0,
            "position_changes": [],
        }

        if portfolio_data["transactions"]:
            buys = sum(1 for t in portfolio_data["transactions"] if t["type"] == "buy")
            sells = len(portfolio_data["transactions"]) - buys
            metrics["buy_sell_ratio"] = buys / sells if sells > 0 else float("inf")

            # Calculate average transaction size
            total_value = sum(
                t["price"] * t["quantity"] for t in portfolio_data["transactions"]
            )
            metrics["average_transaction_size"] = total_value / len(
                portfolio_data["transactions"]
            )

            # Track position changes
            sorted_txns = sorted(
                portfolio_data["transactions"], key=lambda x: x["date"]
            )
            for txn in sorted_txns:
                metrics["position_changes"].append(
                    {
                        "date": txn["date"],
                        "value_change": txn["price"]
                        * txn["quantity"]
                        * (1 if txn["type"] == "buy" else -1),
                    }
                )

        return metrics
