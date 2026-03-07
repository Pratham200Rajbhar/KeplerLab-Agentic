"""Test script for unified streaming architecture.

Run this to validate the new streaming system works correctly.
"""

import asyncio
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_stream_manager():
    """Test StreamManager core functionality."""
    from app.services.stream import StreamManager
    
    logger.info("Testing StreamManager...")
    
    manager = StreamManager(
        user_id="test-user",
        notebook_id="test-notebook",
        session_id="test-session",
        user_message="Test message",
        intent="RAG",
    )
    
    # Test token emission
    event = await manager.emit_token("Hello ")
    assert "event: token" in event
    assert "Hello " in event
    logger.info("✓ Token emission works")
    
    event = await manager.emit_token("world!")
    assert "world!" in event
    
    # Test content accumulation
    assert manager.context.full_content == "Hello world!"
    logger.info("✓ Content accumulation works")
    
    # Test step emission
    event = await manager.emit_step("test_step", "running", "Testing step")
    assert "event: step" in event
    assert "test_step" in event
    logger.info("✓ Step emission works")
    
    # Test metadata
    event = await manager.emit_metadata({"test_key": "test_value"})
    assert "event: meta" in event
    assert manager.context.metadata["test_key"] == "test_value"
    logger.info("✓ Metadata works")
    
    # Test state
    assert manager.context.elapsed >= 0
    assert len(manager.context.steps) == 1
    logger.info("✓ State tracking works")
    
    logger.info("✅ StreamManager tests passed!")


async def test_sse_formatters():
    """Test SSE formatting utilities."""
    from app.services.stream import (
        format_token,
        format_step,
        format_error,
        format_done,
        format_metadata,
        format_artifact,
    )
    
    logger.info("Testing SSE formatters...")
    
    # Test token
    event = format_token("Hello")
    assert "event: token\n" in event
    assert '"content": "Hello"' in event
    logger.info("✓ format_token works")
    
    # Test step
    event = format_step("retrieval", "running", "Searching...")
    assert "event: step\n" in event
    assert "retrieval" in event
    logger.info("✓ format_step works")
    
    # Test error
    error = Exception("Test error")
    event = format_error(error)
    assert "event: error\n" in event
    assert "Test error" in event
    logger.info("✓ format_error works")
    
    # Test done
    event = format_done(1.23, {"chunks_used": 5})
    assert "event: done\n" in event
    assert "1.23" in event
    logger.info("✓ format_done works")
    
    # Test metadata
    event = format_metadata({"intent": "RAG"})
    assert "event: meta\n" in event
    assert "RAG" in event
    logger.info("✓ format_metadata works")
    
    # Test artifact
    event = format_artifact("art-123", "test.pdf", "/files/test.pdf", "application/pdf", 1024)
    assert "event: artifact\n" in event
    assert "test.pdf" in event
    logger.info("✓ format_artifact works")
    
    logger.info("✅ SSE formatter tests passed!")


async def test_storage_service():
    """Test ChatStorage (requires DB connection)."""
    from app.services.stream import ChatStorage
    from app.db.prisma_client import prisma
    
    logger.info("Testing ChatStorage...")
    
    try:
        # Test would require actual DB connection
        # This is a placeholder for integration tests
        logger.info("⚠ Storage tests require DB connection")
        logger.info("  Run integration tests with: pytest tests/test_stream_storage.py")
    except Exception as e:
        logger.error(f"Storage test setup failed: {e}")


async def test_rag_pipeline_mock():
    """Test RAG pipeline with mock data."""
    logger.info("Testing RAG pipeline (mock)...")
    
    # Mock test - actual test requires full app context
    logger.info("⚠ Pipeline tests require full app context")
    logger.info("  Run with: python -m pytest tests/test_rag_unified.py")


def run_all_tests():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("TESTING UNIFIED STREAMING SYSTEM")
    logger.info("=" * 60)
    
    try:
        # Run async tests
        asyncio.run(test_stream_manager())
        asyncio.run(test_sse_formatters())
        asyncio.run(test_storage_service())
        asyncio.run(test_rag_pipeline_mock())
        
        logger.info("=" * 60)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("=" * 60)
        return True
    
    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
