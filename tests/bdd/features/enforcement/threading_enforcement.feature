@enforcement @threading
Feature: Threading/Multiprocessing Enforcement
  As a test author following Google's test size guidelines
  I want small tests to warn when using threading/multiprocessing
  So that I can identify tests that may need to be recategorized

  Background:
    Given the pytest-test-categories plugin is installed

  # =============================================================================
  # Note: Threading is MONITORED (warns) not BLOCKED
  # Many libraries use threading internally, so blocking would break legitimate
  # test infrastructure. Instead, we warn when threads are created.
  # =============================================================================

  # =============================================================================
  # Strict Mode Scenarios (Thread Monitoring Warns)
  # =============================================================================

  @strict @threading.Thread
  Scenario: Small test spawning Thread in strict mode emits warning
    Given enforcement mode is set to "strict"
    And a test file with a small test that spawns a Thread
    When the test suite runs
    Then the test passes
    And a threading warning is emitted containing "Small test created threads"

  @strict @ThreadPoolExecutor
  Scenario: Small test using ThreadPoolExecutor in strict mode emits warning
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses ThreadPoolExecutor
    When the test suite runs
    Then the test passes
    And a threading warning is emitted containing "Small test created threads"

  @strict @multiprocessing.Process
  Scenario: Small test using multiprocessing.Process in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses multiprocessing Process
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Spawn Violation"

  @strict @ProcessPoolExecutor
  Scenario: Small test using ProcessPoolExecutor in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses ProcessPoolExecutor
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Spawn Violation"

  # =============================================================================
  # Warn Mode Scenarios
  # =============================================================================

  @warn @threading.Thread
  Scenario: Small test spawning Thread in warn mode emits warning
    Given enforcement mode is set to "warn"
    And a test file with a small test that spawns a Thread
    When the test suite runs
    Then the test passes
    And a threading warning is emitted containing "Small test created threads"

  @warn @multiprocessing.Process
  Scenario: Small test using multiprocessing.Process in warn mode shows warning
    Given enforcement mode is set to "warn"
    And a test file with a small test that uses multiprocessing Process
    When the test suite runs
    Then the test passes
    And a warning is emitted containing "Subprocess Spawn Violation"

  # =============================================================================
  # Off Mode Scenarios
  # =============================================================================

  @off @threading.Thread
  Scenario: Small test spawning Thread in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a small test that spawns a Thread
    When the test suite runs
    Then the test passes
    And no threading warnings are emitted

  @off @multiprocessing.Process
  Scenario: Small test using multiprocessing.Process in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a small test that uses multiprocessing Process
    When the test suite runs
    Then the test passes
    And no process violation warnings are emitted

  # =============================================================================
  # Medium/Large Test Scenarios (No Restrictions)
  # =============================================================================

  @medium @strict
  Scenario: Medium test can spawn Thread regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a medium test that spawns a Thread
    When the test suite runs
    Then the test passes
    And no threading warnings are emitted

  @large @strict
  Scenario: Large test can use multiprocessing.Process regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a large test that uses multiprocessing Process
    When the test suite runs
    Then the test passes
    And no process violation errors occur

  # =============================================================================
  # Edge Cases
  # =============================================================================

  @strict @daemon-thread
  Scenario: Small test spawning daemon thread still emits warning
    Given enforcement mode is set to "strict"
    And a test file with a small test that spawns a daemon Thread
    When the test suite runs
    Then the test passes
    And a threading warning is emitted containing "Small test created threads"

  @strict @multiple-threads
  Scenario: Small test spawning multiple threads reports thread count
    Given enforcement mode is set to "strict"
    And a test file with a small test that spawns 3 threads
    When the test suite runs
    Then the test passes
    And the threading warning indicates multiple threads were created
