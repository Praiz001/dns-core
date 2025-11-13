"""Push Notification API Routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
import uuid
from datetime import datetime
import httpx

from app.schemas.push import (
    PushNotificationRequest,
    PushNotificationResponse,
    DeliveryStatusResponse
)
from app.services.push_service import PushService
from app.providers.fcm import FCMProvider
from app.utils.logger import get_logger
from app.utils.database import get_db_session
from app.utils.rabbitmq import get_rabbitmq_publisher
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.push_delivery import PushDelivery
from app.config import settings

router = APIRouter()
logger = get_logger(__name__)


async def fetch_user_device_token(user_id: str) -> str | None:
    """
    Fetch user's push notification device token from user service
    
    Args:
        user_id: User UUID
        
    Returns:
        Device token string or None if not found
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.USER_SERVICE_URL}/api/v1/users/{user_id}/push-token",
                timeout=5.0
            )
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, dict):
                # Try different possible keys
                token = (
                    result.get("data", {}).get("token") or
                    result.get("data", {}).get("push_token") or
                    result.get("push_token") or
                    result.get("token")
                )
                return token
            
            return None
            
    except httpx.HTTPError as e:
        logger.error(f"Error fetching device token for user {user_id}: {str(e)}")
        return None


def get_push_service() -> PushService:
    """Dependency to get push service instance"""
    fcm_provider = FCMProvider()
    return PushService(fcm_provider)


@router.post("/send", response_model=PushNotificationResponse, status_code=status.HTTP_200_OK)
async def send_push_notification(
    notification: PushNotificationRequest,
    push_service: PushService = Depends(get_push_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Send a push notification to a user
    
    - **user_id**: Target user ID
    - **title**: Notification title
    - **body**: Notification body/message
    - **data**: Optional custom data payload
    - **priority**: Notification priority (normal/high)
    - **badge**: Badge count for iOS
    """
    try:
        logger.info(f"Received push notification request for user: {notification.user_id}")
        
        # Generate notification ID
        notification_id = uuid.uuid4()
        
        # Convert user_id to UUID
        try:
            user_uuid = uuid.UUID(notification.user_id) if isinstance(notification.user_id, str) else notification.user_id
        except (ValueError, AttributeError):
            # If user_id is not a valid UUID, generate a deterministic one
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, notification.user_id)
            logger.warning(f"Invalid UUID for user_id '{notification.user_id}', generated: {user_uuid}")
        
        # Fetch device token from user service
        device_token = await fetch_user_device_token(str(user_uuid))
        
        if not device_token:
            logger.warning(f"No device token found for user {user_uuid}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No push notification device token registered for user {notification.user_id}"
            )
        
        # Create delivery record
        delivery = PushDelivery(
            notification_id=notification_id,
            user_id=user_uuid,
            device_token=device_token,
            title=notification.title,
            body=notification.body,
            data=notification.data or {},
            provider="fcm",
            status="queued",
            sent_at=datetime.utcnow()
        )
        
        session.add(delivery)
        await session.commit()
        
        # Publish to RabbitMQ for async processing
        publisher = await get_rabbitmq_publisher()
        notification_payload = {
            "notification_id": str(notification_id),
            "user_id": str(user_uuid),
            "device_token": device_token,
            "title": notification.title,
            "body": notification.body,
            "data": notification.data or {},
            "priority": notification.priority or "normal",
            "badge": notification.badge
        }
        
        published = await publisher.publish_notification(notification_payload)
        
        if not published:
            logger.error(f"Failed to publish notification {notification_id} to RabbitMQ")
            # Update status to failed
            delivery.status = "failed"
            delivery.error_message = "Failed to queue notification for delivery"
            await session.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to queue notification for delivery"
            )
        
        logger.info(f"Push notification {notification_id} queued successfully")
        
        return PushNotificationResponse(
            message_id=str(notification_id),
            status="queued",
            message="Push notification queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send push notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue push notification: {str(e)}"
        )


@router.get("/status/{message_id}", response_model=DeliveryStatusResponse)
async def get_delivery_status(
    message_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get delivery status for a push notification
    
    - **message_id**: The unique message ID returned when sending
    """
    try:
        from sqlalchemy import select
        
        # Convert message_id string to UUID
        try:
            notification_uuid = uuid.UUID(message_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid message ID format: {message_id}"
            )
        
        # Query delivery record by notification_id
        result = await session.execute(
            select(PushDelivery).where(PushDelivery.notification_id == notification_uuid)
        )
        delivery = result.scalar_one_or_none()
        
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Push notification with ID {message_id} not found"
            )
        
        return DeliveryStatusResponse(
            message_id=str(delivery.notification_id),
            user_id=str(delivery.user_id),
            status=delivery.status,
            sent_at=delivery.sent_at,
            delivered_at=delivery.created_at,  
            error_message=delivery.error_message,
            provider=delivery.provider
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get delivery status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve delivery status: {str(e)}"
        )


@router.post("/send-bulk", status_code=status.HTTP_202_ACCEPTED)
async def send_bulk_push_notifications(
    notifications: List[PushNotificationRequest],
    push_service: PushService = Depends(get_push_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Send push notifications to multiple users
    
    - **notifications**: List of push notification requests
    
    Returns summary of queued notifications including any failures
    """
    try:
        logger.info(f"Received bulk push notification request for {len(notifications)} users")
        
        if not notifications:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Notifications list cannot be empty"
            )
        
        if len(notifications) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send more than 1000 notifications in a single request"
            )
        
        queued_messages = []
        failed_messages = []
        publisher = await get_rabbitmq_publisher()
        
        for notification in notifications:
            try:
                # Generate notification ID
                notification_id = uuid.uuid4()
                
                # Convert user_id to UUID
                try:
                    user_uuid = uuid.UUID(notification.user_id) if isinstance(notification.user_id, str) else notification.user_id
                except (ValueError, AttributeError):
                    user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, notification.user_id)
                
                # Fetch device token
                device_token = await fetch_user_device_token(str(user_uuid))
                
                if not device_token:
                    logger.warning(f"No device token for user {user_uuid}, skipping")
                    failed_messages.append({
                        "user_id": notification.user_id,
                        "reason": "No device token registered"
                    })
                    continue
                
                # Create delivery record
                delivery = PushDelivery(
                    notification_id=notification_id,
                    user_id=user_uuid,
                    device_token=device_token,
                    title=notification.title,
                    body=notification.body,
                    data=notification.data or {},
                    provider="fcm",
                    status="queued",
                    sent_at=datetime.utcnow()
                )
                
                session.add(delivery)
                
                # Publish to RabbitMQ
                notification_payload = {
                    "notification_id": str(notification_id),
                    "user_id": str(user_uuid),
                    "device_token": device_token,
                    "title": notification.title,
                    "body": notification.body,
                    "data": notification.data or {},
                    "priority": notification.priority or "normal",
                    "badge": notification.badge
                }
                
                published = await publisher.publish_notification(notification_payload)
                
                if published:
                    queued_messages.append(str(notification_id))
                    logger.debug(f"Queued notification {notification_id} for user {user_uuid}")
                else:
                    failed_messages.append({
                        "user_id": notification.user_id,
                        "message_id": str(notification_id),
                        "reason": "Failed to publish to queue"
                    })
                    delivery.status = "failed"
                    delivery.error_message = "Failed to publish to queue"
                    
            except Exception as e:
                logger.error(f"Failed to queue notification for user {notification.user_id}: {str(e)}")
                failed_messages.append({
                    "user_id": notification.user_id,
                    "reason": str(e)
                })
        
        # Commit all delivery records
        await session.commit()
        
        response_data = {
            "message": f"Processed {len(notifications)} notifications",
            "queued": len(queued_messages),
            "failed": len(failed_messages),
            "message_ids": queued_messages,
            "status": "completed"
        }
        
        if failed_messages:
            response_data["failures"] = failed_messages
        
        logger.info(f"Bulk send completed: {len(queued_messages)} queued, {len(failed_messages)} failed")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send bulk push notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process bulk push notifications: {str(e)}"
        )
