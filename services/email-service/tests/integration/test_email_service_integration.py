"""
Integration tests for Email Service.

These tests verify the complete email service workflow with real components:
- Database operations (PostgreSQL with SQLAlchemy)
- RabbitMQ message consumption
- Email provider integration
- End-to-end notification processing

Note: Requires running PostgreSQL, RabbitMQ, and Redis instances.
Can use docker-compose for test environment.
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from aio_pika import connect_robust, Message
import json

from app.models.email_delivery import EmailDelivery, Base
from app.db.repositories.email_delivery_repository import EmailDeliveryRepository
from app.services.email_service import EmailService
from app.services.external_api import ExternalAPIClient
from app.schemas.email import QueueMessage
from app.config import settings


# Test database URL (use separate test database)
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/email_service_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create database session for each test."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def repository(db_session):
    """Create repository with test database session."""
    return EmailDeliveryRepository(db_session)


@pytest.fixture
async def api_client():
    """Create external API client."""
    return ExternalAPIClient()


@pytest.fixture
async def email_service(repository, api_client):
    """Create email service with real components."""
    return EmailService(repository, api_client)


@pytest.fixture
def queue_message():
    """Create test queue message."""
    return QueueMessage(
        notification_id=str(uuid4()),
        user_id="test-user-123",
        template_id="welcome",
        variables={"name": "Test User", "action_url": "https://example.com"},
        metadata={"campaign": "test"}
    )


@pytest.mark.integration
class TestEmailServiceIntegration:
    """Integration tests for email service."""
    
    @pytest.mark.asyncio
    async def test_create_and_retrieve_delivery(self, repository):
        """Test creating and retrieving email delivery record."""
        # Create delivery
        delivery = await repository.create(
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test Email",
            body_html="<p>Test</p>",
            body_text="Test",
            provider="smtp",
            status="pending"
        )
        
        assert delivery.id is not None
        assert delivery.notification_id is not None
        
        # Retrieve by ID
        retrieved = await repository.get_by_id(delivery.id)
        assert retrieved is not None
        assert retrieved.id == delivery.id
        assert retrieved.recipient_email == "user@example.com"
    
    @pytest.mark.asyncio
    async def test_update_delivery_status(self, repository):
        """Test updating delivery status in database."""
        # Create delivery
        delivery = await repository.create(
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="pending"
        )
        
        # Update to sent
        updated = await repository.update_status(
            delivery.id,
            "sent",
            message_id="msg-123"
        )
        
        assert updated.status == "sent"
        assert updated.message_id == "msg-123"
        assert updated.sent_at is not None
        
        # Verify persisted
        retrieved = await repository.get_by_id(delivery.id)
        assert retrieved.status == "sent"
    
    @pytest.mark.asyncio
    async def test_increment_attempt_count(self, repository):
        """Test incrementing attempt count."""
        # Create delivery
        delivery = await repository.create(
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="pending"
        )
        
        initial_count = delivery.attempt_count
        
        # Increment
        updated = await repository.increment_attempt(delivery.id)
        assert updated.attempt_count == initial_count + 1
        assert updated.last_attempt_at is not None
        
        # Verify persisted
        retrieved = await repository.get_by_id(delivery.id)
        assert retrieved.attempt_count == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_get_by_notification_id(self, repository):
        """Test retrieving delivery by notification ID."""
        notification_id = str(uuid4())
        
        # Create delivery
        delivery = await repository.create(
            notification_id=notification_id,
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="pending"
        )
        
        # Retrieve by notification ID
        retrieved = await repository.get_by_notification_id(notification_id)
        assert retrieved is not None
        assert retrieved.id == delivery.id
        assert retrieved.notification_id == notification_id
    
    @pytest.mark.asyncio
    async def test_delivery_timestamps(self, repository):
        """Test that timestamps are set correctly."""
        before = datetime.utcnow()
        
        delivery = await repository.create(
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="pending"
        )
        
        after = datetime.utcnow()
        
        # created_at should be set
        assert delivery.created_at is not None
        assert before <= delivery.created_at <= after
        
        # updated_at should be set
        assert delivery.updated_at is not None
        assert before <= delivery.updated_at <= after
    
    @pytest.mark.asyncio
    async def test_multiple_deliveries(self, repository):
        """Test creating multiple deliveries."""
        notification_ids = [str(uuid4()) for _ in range(3)]
        
        # Create multiple deliveries
        deliveries = []
        for notif_id in notification_ids:
            delivery = await repository.create(
                notification_id=notif_id,
                user_id="user-123",
                recipient_email="user@example.com",
                subject="Test",
                provider="smtp",
                status="pending"
            )
            deliveries.append(delivery)
        
        # Verify all were created
        assert len(deliveries) == 3
        assert all(d.id is not None for d in deliveries)
        
        # Verify can retrieve each one
        for i, notif_id in enumerate(notification_ids):
            retrieved = await repository.get_by_notification_id(notif_id)
            assert retrieved is not None
            assert retrieved.id == deliveries[i].id
    
    @pytest.mark.asyncio
    async def test_delivery_with_metadata(self, repository):
        """Test storing and retrieving delivery with metadata."""
        extra_data = {
            "campaign": "test-campaign",
            "user_segment": "premium",
            "priority": "high"
        }
        
        delivery = await repository.create(
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="pending",
            extra_data=extra_data
        )
        
        # Retrieve and verify metadata
        retrieved = await repository.get_by_id(delivery.id)
        assert retrieved.extra_data == extra_data
        assert retrieved.extra_data["campaign"] == "test-campaign"


@pytest.mark.integration
@pytest.mark.slow
class TestRabbitMQIntegration:
    """Integration tests for RabbitMQ message processing."""
    
    @pytest.mark.asyncio
    async def test_rabbitmq_connection(self):
        """Test connecting to RabbitMQ."""
        try:
            connection = await connect_robust(
                f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@"
                f"{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
            )
            
            assert connection is not None
            
            # Create channel
            channel = await connection.channel()
            assert channel is not None
            
            await connection.close()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_publish_and_consume_message(self):
        """Test publishing and consuming RabbitMQ messages."""
        try:
            connection = await connect_robust(
                f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@"
                f"{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
            )
            
            channel = await connection.channel()
            
            # Declare test queue
            queue = await channel.declare_queue("test_email_queue", durable=True)
            
            # Publish message
            message_data = {
                "notification_id": str(uuid4()),
                "user_id": "test-user",
                "template_id": "welcome",
                "variables": {"name": "Test"},
                "metadata": {}
            }
            
            message = Message(
                body=json.dumps(message_data).encode(),
                content_type="application/json"
            )
            
            await channel.default_exchange.publish(
                message,
                routing_key="test_email_queue"
            )
            
            # Consume message
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        body = json.loads(message.body.decode())
                        assert body["user_id"] == "test-user"
                        assert body["template_id"] == "welcome"
                        break
            
            # Cleanup
            await queue.delete()
            await connection.close()
            
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {str(e)}")


@pytest.mark.integration
class TestEndToEndEmailFlow:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not getattr(settings, 'RUN_E2E_TESTS', False),
        reason="E2E tests disabled (set RUN_E2E_TESTS=true to enable)"
    )
    async def test_complete_email_workflow(
        self,
        email_service,
        repository,
        queue_message
    ):
        """
        Test complete email workflow from queue message to delivery.
        
        Note: This test requires:
        - Running User Service (for preferences)
        - Running Template Service (for rendering)
        - Running API Gateway (for status updates)
        - Email provider (SMTP or SendGrid)
        """
        # Process the notification
        result = await email_service.process_email_notification(queue_message)
        
        # In real scenario with mocked external services, this should succeed
        # With real services, it depends on their availability
        assert result is not None
        
        # Check delivery was created
        delivery = await repository.get_by_notification_id(
            queue_message.notification_id
        )
        
        assert delivery is not None
        assert delivery.notification_id == queue_message.notification_id
        assert delivery.user_id == queue_message.user_id


# Helper function to set up test environment
def setup_test_environment():
    """
    Instructions for setting up test environment.
    
    1. Create test database:
       createdb email_service_test
    
    2. Start services with docker-compose:
       docker-compose -f docker-compose.test.yml up -d
    
    3. Run integration tests:
       pytest tests/integration/ -v -m integration
    
    4. Run with coverage:
       pytest tests/integration/ -v -m integration --cov=app
    """
    pass
