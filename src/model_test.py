from datetime import datetime

from src.lib.email_analyzer import AnalyzerService
from src.models.email_analyzer import EmailInput

# Initialize service
service = AnalyzerService()

# Analyze email
email = EmailInput(
    subject="Test Email",
    content="Test content",
    sender="test@example.com",
    date=datetime.now(),
)

# Analyze
service.analyze_email(email)
