import base64
import email
import json
import re
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import requests
from pydantic import BaseModel
from pymongo import MongoClient


class EmailData(BaseModel):
    subject: str
    content: str
    sender: str
    recipient: str
    date: datetime
    labels: Optional[List[str]] = None
    thread_id: str
    message_id: str
    unique_id: str


class GmailFetcher:
    def __init__(self, access_token: str, mongo_uri: str, database_name: str):
        """
        Initialize the Gmail fetcher with authentication and database configuration.
        """
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.base_url = "https://www.googleapis.com/gmail/v1/users/me/messages"

        # Initialize MongoDB connection
        self.client = MongoClient(mongo_uri)
        self.db = self.client[database_name]
        self.raw_emails = self.db.raw_emails
        self.processed_emails = self.db.processed_emails

    def clean_email_address(self, email_str: str) -> str:
        """
        Clean email address by removing angle brackets and normalizing format.
        Example: "John Doe <john@example.com>" -> "john@example.com"
        """
        # Extract email address from string containing name and email
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        matches = re.findall(email_pattern, email_str)
        if matches:
            return matches[0].lower()
        return email_str.replace("<", "").replace(">", "").strip().lower()

    def decode_body(self, payload: Dict) -> str:
        """
        Recursively decode email body from payload.
        """
        if "body" in payload and "data" in payload["body"]:
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        if "parts" in payload:
            text_content = []
            for part in payload["parts"]:
                if part.get("mimeType", "").startswith("text/"):
                    if "data" in part.get("body", {}):
                        decoded_data = base64.urlsafe_b64decode(
                            part["body"]["data"]
                        ).decode("utf-8")
                        text_content.append(decoded_data)
            return "\n".join(text_content)

        return ""

    def extract_email_data(self, raw_message: Dict, unique_id: str) -> EmailData:
        """
        Extract relevant email data from Gmail API response and convert to EmailData format.
        """
        headers = {
            header["name"].lower(): header["value"]
            for header in raw_message["payload"]["headers"]
        }

        # Extract subject
        subject = headers.get("subject", "")

        # Extract content
        content = self.decode_body(raw_message["payload"])

        # Extract and clean sender and recipient
        sender = self.clean_email_address(headers.get("from", ""))
        recipient = self.clean_email_address(headers.get("to", ""))

        # Extract and parse date
        date_str = headers.get("date", "")
        try:
            # Parse email date format
            date = email.utils.parsedate_to_datetime(date_str)
        except:
            # Fallback to current time if parsing fails
            date = datetime.utcnow()

        # Create EmailData object
        email_data = EmailData(
            subject=subject,
            content=content,
            sender=sender,
            recipient=recipient,
            date=date,
            labels=raw_message.get("labelIds", []),
            thread_id=raw_message["threadId"],
            message_id=raw_message["id"],
            unique_id=unique_id,
        )

        return email_data

    def fetch_message(self, message_id: str) -> Optional[Dict]:
        """
        Fetch a single message from Gmail API.
        """
        try:
            url = f"{self.base_url}/{message_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching message {message_id}: {str(e)}")
            return None

    def store_message(self, raw_message: Dict, email_data: EmailData) -> bool:
        """
        Store both raw and processed message data in MongoDB.
        """
        try:
            # Store raw message with unique_id
            raw_message["stored_at"] = datetime.utcnow()
            raw_message["raw_email_source"] = "gmail_api"
            raw_message["unique_id"] = email_data.unique_id

            # Store processed email data
            processed_data = email_data.dict()
            processed_data["stored_at"] = datetime.utcnow()
            processed_data["raw_message_id"] = raw_message["id"]

            # Use transactions to ensure both writes succeed
            with self.client.start_session() as session:
                with session.start_transaction():
                    # Update or insert raw message
                    self.raw_emails.update_one(
                        {"id": raw_message["id"]},
                        {"$set": raw_message},
                        upsert=True,
                        session=session,
                    )

                    # Update or insert processed email
                    self.processed_emails.update_one(
                        {"message_id": email_data.message_id},
                        {"$set": processed_data},
                        upsert=True,
                        session=session,
                    )

            return True
        except Exception as e:
            print(f"Error storing message {raw_message.get('id', 'unknown')}: {str(e)}")
            return False

    def cleanup_raw_emails(self, unique_id: str):
        """
        Remove raw emails after successful processing.
        """
        try:
            # Find all successfully processed emails for this unique_id
            processed = self.processed_emails.find({"unique_id": unique_id})
            processed_ids = [email["raw_message_id"] for email in processed]

            # Remove corresponding raw emails
            if processed_ids:
                self.raw_emails.delete_many({"id": {"$in": processed_ids}})
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    def process_messages(self, message_list: List[Dict]) -> Dict:
        """
        Process a list of messages, fetching and storing each one.
        """
        # Generate unique identifier for this batch
        unique_id = str(uuid.uuid4())

        results = {
            "total": len(message_list),
            "successful": 0,
            "failed": 0,
            "failed_ids": [],
            "unique_id": unique_id,
        }
        logging.info("In process message")
        for idx, message in enumerate(message_list):
            message_id = message["id"]
            print(f"Processing message {idx + 1}/{len(message_list)}: {message_id}")

            # Add delay to respect API rate limits
            if idx > 0:
                time.sleep(0.1)

            # Fetch message
            raw_message = self.fetch_message(message_id)
            if raw_message:
                try:
                    # Transform to EmailData format with unique_id
                    email_data = self.extract_email_data(raw_message, unique_id)

                    # Store both raw and processed data
                    if self.store_message(raw_message, email_data):
                        results["successful"] += 1
                        continue
                except Exception as e:
                    print(f"Error processing message {message_id}: {str(e)}")

            results["failed"] += 1
            results["failed_ids"].append(message_id)

        # Cleanup raw emails after successful processing
        self.cleanup_raw_emails(unique_id)
        logging.info("Cleaned Up Raw Email")
        logging.info({"unique_id":unique_id})
        return results

def gmail_processor(access_token: str, mongoUri: str, dbName: str, data: List[Dict]):

    # Initialize fetcher
    fetcher = GmailFetcher(access_token, mongoUri, dbName)

    # Process messages
    results = fetcher.process_messages(data)

    # Print summary
    print("\nProcessing Complete!")
    print(f"Batch Unique ID: {results['unique_id']}")
    print(f"Total messages: {results['total']}")
    print(f"Successfully processed: {results['successful']}")
    print(f"Failed: {results['failed']}")
    if results["failed_ids"]:
        print("\nFailed message IDs:")
        for failed_id in results["failed_ids"]:
            print(f"- {failed_id}")