# Examples

This section provides practical examples of using pytest-test-categories in various scenarios.

## Topics

```{toctree}
:maxdepth: 2

network-isolation
```

## Quick Examples

### Basic Test Marking

```python
import pytest

@pytest.mark.small
def test_unit_logic():
    """Fast, hermetic unit test."""
    assert calculate_discount(100, 20) == 80

@pytest.mark.medium
def test_database_integration(db):
    """Integration test with local database."""
    user = UserRepository(db).create(name="Alice")
    assert user.id is not None

@pytest.mark.large
def test_end_to_end(staging_api):
    """End-to-end test with external services."""
    order = staging_api.create_order()
    assert order.status == "created"
```

### Using Base Classes

```python
from pytest_test_categories import SmallTest, MediumTest

class TestCalculator(SmallTest):
    def test_add(self):
        assert Calculator().add(1, 2) == 3

    def test_subtract(self):
        assert Calculator().subtract(5, 3) == 2

class TestUserRepository(MediumTest):
    def test_create_user(self, db):
        user = UserRepository(db).create(name="Alice")
        assert user.id is not None
```

### Mocking for Small Tests

```python
import pytest

@pytest.mark.small
def test_email_sender(mocker):
    """Mock external dependencies for small tests."""
    mock_smtp = mocker.patch("smtplib.SMTP")

    send_welcome_email("user@example.com")

    mock_smtp.return_value.send_message.assert_called_once()
```

### Fixtures with Size Markers

```python
import pytest

@pytest.fixture
def mock_api_client(mocker):
    """Fixture providing a mock API client for small tests."""
    client = mocker.Mock()
    client.get.return_value = {"status": "ok"}
    return client

@pytest.mark.small
def test_api_handler(mock_api_client):
    handler = APIHandler(client=mock_api_client)
    result = handler.fetch_status()
    assert result == "ok"
```
