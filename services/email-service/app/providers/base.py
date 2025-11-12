"""
Email Provider Base Interface

Defines the contract for all email provider implementations.
Uses Strategy Pattern for flexible provider switching.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailMessage:
    """Email message data structure."""
    to: str
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class SendResult:
    """Email send result."""
    success: bool
    message_id: Optional[str] = None
    provider: str = ""
    error: Optional[str] = None


class IEmailProvider(ABC):
    """
    Email provider interface.
    
    All email providers must implement this interface.
    Follows Interface Segregation Principle.
    """
    
    @abstractmethod
    async def send(self, message: EmailMessage) -> SendResult:
        """
        Send an email message.
        
        Args:
            message: Email message to send
            
        Returns:
            SendResult with success status and message ID
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass
