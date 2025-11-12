"""
Integration tests for database session management.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from sqlalchemy import text

from app.db.session import get_db, get_db_session, AsyncSessionLocal


class TestDatabaseSessionIntegration:
    """Integration tests for database sessions."""
    
    @pytest.mark.asyncio
    async def test_get_db_dependency_injection(self):
        """Test get_db can be used as FastAPI dependency."""
        db_gen = get_db()
        
        # Verify it's an async generator
        assert hasattr(db_gen, '__anext__')
        assert hasattr(db_gen, 'aclose')
        
        await db_gen.aclose()
    
    @pytest.mark.asyncio
    async def test_session_factory_configuration(self):
        """Test AsyncSessionLocal is properly configured."""
        assert AsyncSessionLocal is not None
        assert hasattr(AsyncSessionLocal, '__call__')
    
    @pytest.mark.asyncio  
    async def test_get_db_session_context_manager(self):
        """Test get_db_session works as async context manager."""
        # Mock the session to avoid real DB connection
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch('app.db.session.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__.return_value = mock_session
            mock_factory.return_value.__aexit__.return_value = None
            
            async with get_db_session() as session:
                assert session is not None
            
            # Verify session lifecycle methods were called
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self):
        """Test session rolls back on error."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch('app.db.session.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__.return_value = mock_session
            mock_factory.return_value.__aexit__.return_value = None
            
            try:
                async with get_db_session() as session:
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_can_be_created(self):
        """Test multiple sessions can be created independently."""
        db_gen1 = get_db()
        db_gen2 = get_db()
        
        # Verify both are generators
        assert hasattr(db_gen1, '__anext__')
        assert hasattr(db_gen2, '__anext__')
        assert db_gen1 is not db_gen2
        
        await db_gen1.aclose()
        await db_gen2.aclose()
