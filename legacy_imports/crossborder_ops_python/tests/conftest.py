import pytest

from app.config import SETTINGS
from app.main import app
from app.rate_limit import MemoryRateLimiter


@pytest.fixture(autouse=True)
def reset_app_state():
    yield
    app.state.settings = SETTINGS
    app.state.rate_limiter = MemoryRateLimiter(SETTINGS.rate_limit_per_minute)
    app.state.rate_limit_config = SETTINGS.rate_limit_per_minute
    app.dependency_overrides.clear()
