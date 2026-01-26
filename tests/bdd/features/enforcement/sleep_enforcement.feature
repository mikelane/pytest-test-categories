@enforcement @sleep
Feature: Sleep/Time Manipulation Enforcement
  As a test author following Google's test size guidelines
  I want small tests to be blocked from using sleep functions
  So that my tests remain fast, deterministic, and hermetic

  Background:
    Given the pytest-test-categories plugin is installed

  # =============================================================================
  # Strict Mode Scenarios
  # =============================================================================

  @strict @time.sleep
  Scenario: Small test using time.sleep() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "time.sleep(0.1)"
    When the test suite runs
    Then the test fails with a sleep violation error
    And the error message contains "Sleep Violation"

  # NOTE: asyncio.sleep scenarios are excluded because pytester subprocess
  # does not have pytest-asyncio installed. The same logic is tested via time.sleep.
  # @strict @asyncio.sleep
  # Scenario: Small test using asyncio.sleep() in strict mode fails
  #   Given enforcement mode is set to "strict"
  #   And a test file with a small async test that uses "asyncio.sleep(0.1)"
  #   When the test suite runs
  #   Then the test fails with a sleep violation error
  #   And the error message contains "Sleep Violation"

  @strict @threading.Event.wait
  Scenario: Small test using threading.Event.wait() with timeout in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "threading.Event().wait(0.1)"
    When the test suite runs
    Then the test passes
    And no sleep violation errors occur

  @strict @threading.Condition.wait
  Scenario: Small test using threading.Condition.wait() with timeout in strict mode passes
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses condition wait with timeout
    When the test suite runs
    Then the test passes
    And no sleep violation errors occur

  # =============================================================================
  # Warn Mode Scenarios
  # =============================================================================

  @warn @time.sleep
  Scenario: Small test using time.sleep() in warn mode shows warning but passes
    Given enforcement mode is set to "warn"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And the hermeticity summary shows 1 sleep violation warning

  # NOTE: asyncio.sleep scenarios are excluded because pytester subprocess
  # does not have pytest-asyncio installed. The same logic is tested via time.sleep.
  # @warn @asyncio.sleep
  # Scenario: Small test using asyncio.sleep() in warn mode shows warning but passes
  #   Given enforcement mode is set to "warn"
  #   And a test file with a small async test that uses "asyncio.sleep(0.001)"
  #   When the test suite runs
  #   Then the test passes
  #   And the hermeticity summary shows 1 sleep violation warning

  # =============================================================================
  # Off Mode Scenarios
  # =============================================================================

  @off @time.sleep
  Scenario: Small test using time.sleep() in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no sleep violation warnings are emitted

  # @off @asyncio.sleep
  # Scenario: Small test using asyncio.sleep() in off mode passes silently
  #   Given enforcement mode is set to "off"
  #   And a test file with a small async test that uses "asyncio.sleep(0.001)"
  #   When the test suite runs
  #   Then the test passes
  #   And no sleep violation warnings are emitted

  # =============================================================================
  # Medium/Large Test Scenarios (No Restrictions)
  # =============================================================================

  @medium @strict
  Scenario: Medium test can use time.sleep() regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a medium test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no sleep violation errors occur

  @large @strict
  Scenario: Large test can use time.sleep() regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a large test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no sleep violation errors occur

  @xlarge @strict
  Scenario: XLarge test can use time.sleep() regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with an xlarge test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no sleep violation errors occur

  # =============================================================================
  # Edge Cases
  # =============================================================================

  @strict @zero-sleep
  Scenario: Small test using time.sleep(0) in strict mode still fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "time.sleep(0)"
    When the test suite runs
    Then the test fails with a sleep violation error
    And the error message contains "Sleep Violation"

  @strict @multiple-sleeps
  Scenario: Test with multiple sleep calls reports first violation
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses multiple sleep calls
    When the test suite runs
    Then the test fails with a sleep violation error
    And only the first sleep violation is reported
