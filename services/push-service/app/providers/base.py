"""Base Push Provider Interface"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class PushMessage:
    """Push notification message data"""
    device_token: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    click_action: Optional[str] = None
    priority: str = "high"


@dataclass
class SendResult:
    """Push notification send result"""
    success: bool
    message_id: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None


class IPushProvider(ABC):
    """Push notification provider interface"""
    
    @abstractmethod
    async def send(self, message: PushMessage) -> SendResult:
        """Send push notification"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass
