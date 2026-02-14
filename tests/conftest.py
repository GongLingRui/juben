"""
Pytest configuration and shared fixtures for Juben project tests
"""
import os
import sys
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_user_id():
    """Mock user ID for testing."""
    return "test_user_12345"


@pytest.fixture
def mock_session_id():
    """Mock session ID for testing."""
    return "test_session_abc123"


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "llm": {
            "provider": "zhipu",
            "model": "glm-4.5",
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
        },
        "postgres": {
            "host": "localhost",
            "port": 5432,
            "db": "test_db",
            "user": "test_user",
        }
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM API response."""
    return {
        "choices": [{
            "message": {
                "content": "This is a mock LLM response for testing purposes.",
                "role": "assistant"
            }
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


@pytest.fixture
def mock_chat_message():
    """Mock chat message for testing."""
    return {
        "id": "msg_123",
        "user_id": "test_user_12345",
        "session_id": "test_session_abc123",
        "role": "user",
        "content": "这是一个测试消息",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_script_outline():
    """Mock script outline for testing."""
    return {
        "id": "outline_123",
        "title": "测试短剧大纲",
        "genre": "都市情感",
        "target_audience": "25-35岁女性",
        "total_episodes": 80,
        "theme": "身份反转与复仇",
        "main_characters": [
            {"name": "林雨晴", "role": "女主角", "trait": "隐藏身份的CEO"},
            {"name": "顾子轩", "role": "男主角", "trait": "温柔体贴的医生"}
        ],
        "plot_outline": "一个关于隐藏身份与真爱的故事..."
    }


# Mock clients for services that may not be available in test environment

@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    with patch('utils.redis_client.get_redis_client') as mock:
        client = AsyncMock()
        client.get.return_value = None
        client.set.return_value = True
        client.delete.return_value = 1
        client.exists.return_value = False
        client.ping.return_value = True
        mock.return_value = client
        yield client


@pytest.fixture
def mock_db_client():
    """Mock PostgreSQL client helpers."""
    with patch('utils.database_client.fetch_one') as mock_one, \
         patch('utils.database_client.fetch_all') as mock_all, \
         patch('utils.database_client.execute') as mock_exec:
        mock_one.return_value = None
        mock_all.return_value = []
        mock_exec.return_value = "OK"
        yield {"fetch_one": mock_one, "fetch_all": mock_all, "execute": mock_exec}


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    with patch('llm_client.ZhipuClient') as mock:
        client = AsyncMock()
        client.generate.return_value = "这是模拟的LLM响应内容"
        client.generate_stream.return_value = iter(["这是", "模拟的", "流式", "响应"])
        mock.return_value = client
        yield client


# Test data fixtures

@pytest.fixture
def sample_user_request():
    """Sample user request for testing."""
    return {
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "message": "帮我策划一个关于都市复仇的短剧",
        "request_type": "planning"
    }


@pytest.fixture
def sample_script_data():
    """Sample script data for testing."""
    return {
        "title": "隐世千金",
        "genre": "都市情感",
        "format": "竖屏短剧",
        "total_episodes": 100,
        "target_audience": "25-40岁女性",
        "main_characters": [
            {
                "name": "苏雨晴",
                "age": 26,
                "identity": "隐藏身份的集团千金",
                "personality": "外柔内刚，聪慧过人"
            },
            {
                "name": "陆景深",
                "age": 28,
                "identity": "商业帝国继承人",
                "personality": "霸道深情，护短"
            }
        ],
        "core_conflict": "身份差距与真爱之间的矛盾",
        "theme": "真爱超越身份与财富"
    }


@pytest.fixture
def sample_evaluation_criteria():
    """Sample evaluation criteria for testing."""
    return {
        "dimensions": [
            {"name": "情绪价值", "weight": 0.3, "description": "能否引发观众情绪共鸣"},
            {"name": "节奏控制", "weight": 0.25, "description": "情节推进是否紧凑"},
            {"name": "人设塑造", "weight": 0.2, "description": "人物形象是否鲜明"},
            {"name": "商业价值", "weight": 0.15, "description": "变现潜力"},
            {"name": "创新性", "weight": 0.1, "description": "新颖独特之处"}
        ],
        "scoring_method": "weighted_average",
        "pass_threshold": 70
    }


# Environment setup for tests

@pytest.fixture(autouse=True)
def set_test_env():
    """Set test environment variables."""
    original_env = os.environ.copy()
    os.environ.update({
        "ENVIRONMENT": "test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "POSTGRES_SSLMODE": "disable",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "LOG_LEVEL": "DEBUG",
    })
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Markers configuration

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, may require external services)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (comprehensive, may be skipped in CI)"
    )
    config.addinivalue_line(
        "markers", "llm: Tests that call LLM APIs (may require API keys)"
    )
    config.addinivalue_line(
        "markers", "database: Tests that require database access"
    )
    config.addinivalue_line(
        "markers", "redis: Tests that require Redis access"
    )
    config.addinivalue_line(
        "markers", "milvus: Tests that require Milvus access"
    )
