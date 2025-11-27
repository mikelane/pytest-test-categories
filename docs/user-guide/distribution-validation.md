# Distribution Validation

pytest-test-categories validates that your test suite follows the recommended test pyramid distribution. This helps maintain a healthy balance between fast unit tests and slower integration tests.

## Target Distribution

Following Google's recommendations, a healthy test suite should have:

| Size | Target | Tolerance | Acceptable Range |
|------|--------|-----------|------------------|
| Small | 80% | +/- 5% | 75% - 85% |
| Medium | 15% | +/- 5% | 10% - 20% |
| Large/XLarge | 5% | +/- 3% | 2% - 8% |

## How Validation Works

Distribution validation occurs after test collection:

1. **Collection**: pytest collects all tests and their markers
2. **Counting**: The plugin counts tests by size category
3. **Calculation**: Percentages are calculated
4. **Validation**: Distribution is compared against targets
5. **Reporting**: Summary is displayed with status indicators

## Distribution Summary

After test collection, you'll see a summary like:

```
======================== Test Size Distribution ========================
Small:   45 tests (81.8%) - Target: 80% +/- 5% [OK]
Medium:   8 tests (14.5%) - Target: 15% +/- 5% [OK]
Large:    2 tests ( 3.6%) - Target:  5% +/- 3% [OK]
XLarge:   0 tests ( 0.0%)
========================================================================
Total: 55 tests
```

Status indicators:
- `[OK]` - Within acceptable range
- `[WARNING]` - Outside acceptable range but not critical
- `[CRITICAL]` - Severely outside acceptable range

## Critical Thresholds

The plugin warns when distribution is severely imbalanced:

### Small Tests < 50%

This is a **critical** issue indicating an inverted test pyramid:

```
CRITICAL: Only 40% of tests are small (target: 80%)

Your test suite has an inverted pyramid with too few unit tests.
This leads to:
  - Slow CI/CD pipelines
  - Delayed feedback on changes
  - Brittle tests dependent on infrastructure
  - Higher maintenance costs

Recommendation: Convert integration tests to unit tests where possible.
```

### Medium Tests > 20%

This is a **warning** indicating too many integration tests:

```
WARNING: 25% of tests are medium (target: 15%)

Consider whether some medium tests could be converted to small tests
by mocking external dependencies.
```

### Large/XLarge Tests > 8%

This is a **warning** indicating too many slow tests:

```
WARNING: 12% of tests are large/xlarge (target: 5%)

End-to-end tests are valuable but expensive. Consider:
  - Consolidating similar e2e scenarios
  - Moving validation to lower-level tests
  - Using contract tests instead of full integration tests
```

## Improving Distribution

### Converting Medium to Small

Replace real dependencies with mocks:

```python
# Before: Medium test with real database
@pytest.mark.medium
def test_user_repository(database):
    repo = UserRepository(database)
    user = repo.create(name="Alice")
    assert user.id is not None

# After: Small test with mock
@pytest.mark.small
def test_user_repository(mocker):
    mock_db = mocker.Mock()
    mock_db.insert.return_value = {"id": "123", "name": "Alice"}

    repo = UserRepository(mock_db)
    user = repo.create(name="Alice")

    assert user.id == "123"
    mock_db.insert.assert_called_once()
```

### Converting Large to Medium

Use local services instead of external ones:

```python
# Before: Large test with external API
@pytest.mark.large
def test_payment_processing():
    result = PaymentGateway().charge(amount=100)
    assert result.success

# After: Medium test with local mock server
@pytest.mark.medium
def test_payment_processing(mock_payment_server):
    gateway = PaymentGateway(url=mock_payment_server.url)
    result = gateway.charge(amount=100)
    assert result.success
```

### Splitting Large Tests

Break down large tests into focused smaller tests:

```python
# Before: One large test doing everything
@pytest.mark.large
def test_complete_checkout_flow():
    cart = create_cart()
    add_items(cart)
    apply_discount(cart)
    process_payment(cart)
    send_confirmation(cart)
    verify_inventory_updated(cart)

# After: Multiple focused tests
@pytest.mark.small
def test_add_items_to_cart():
    cart = Cart()
    cart.add_item(item_id="SKU001", quantity=2)
    assert cart.total_items == 2

@pytest.mark.small
def test_apply_discount_reduces_total():
    cart = Cart(items=[item_50_dollars])
    cart.apply_discount("10OFF")
    assert cart.total == 45.00

@pytest.mark.medium
def test_payment_integration(local_payment_service):
    result = process_payment(cart, service=local_payment_service)
    assert result.success

@pytest.mark.large
def test_complete_flow_end_to_end():
    # Keep one e2e test for the happy path
    pass
```

## Tracking Distribution Over Time

Monitor your distribution to catch pyramid inversions early:

1. **CI Metrics**: Export distribution to your metrics system
2. **Trend Analysis**: Track percentages over time
3. **PR Checks**: Flag PRs that worsen distribution
4. **Team Reviews**: Discuss distribution in retrospectives

## Disabling Validation

If needed, distribution validation can be disabled by not using size markers. However, this is not recommended as it defeats the purpose of the plugin.

Instead, consider:
- Setting realistic targets for your project's current state
- Using `@pytest.mark.skip` for tests being refactored
- Creating a roadmap to improve distribution incrementally
