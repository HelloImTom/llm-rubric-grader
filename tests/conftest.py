import pytest

from grader import db


@pytest.fixture
def conn(tmp_path):
    """A fresh database for each test, in a temporary folder pytest cleans up."""
    connection = db.connect(tmp_path / "test.db")
    yield connection
    connection.close()
