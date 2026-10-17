import os
import pytest


@pytest.fixture
def database_url():
    return os.environ["DATABASE_URL"]
