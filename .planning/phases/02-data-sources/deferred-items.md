# Deferred Items - Phase 02: Data Sources

## Pre-existing Test Failures

**Discovered during:** Plan 02-02 execution (full suite check)

4 tests in `tests/test_finnhub_client.py` fail due to a mocking issue where `finnhub` module is patched but `finnhub.FinnhubAPIException` becomes a MagicMock (not a real Exception subclass), causing `except finnhub.FinnhubAPIException` to raise `TypeError: catching classes that do not inherit from BaseException is not allowed`.

Affected tests:
- `TestRetry429::test_429_retries_once_after_5s`
- `TestRetry429::test_double_429_propagates`
- `TestNon429Exception::test_403_reraises_immediately`
- `TestCompanyProfile::test_company_profile_returns_data`

**Root cause:** The `@patch("screener.finnhub_client.finnhub")` patches the entire `finnhub` module, making `finnhub.FinnhubAPIException` a MagicMock rather than a real exception class. The tests need to set `mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException` before the patched code runs.

**Impact:** Plan 02-01 (FinnhubClient) has a test issue that needs fixing.
**Owner:** Plan 02-01 follow-up
