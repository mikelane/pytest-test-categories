@enforcement @subprocess
Feature: Subprocess Spawn Enforcement
  As a test author following Google's test size guidelines
  I want small tests to be blocked from spawning subprocesses
  So that my tests remain isolated, fast, and hermetic

  Background:
    Given the pytest-test-categories plugin is installed

  # =============================================================================
  # Strict Mode Scenarios
  # =============================================================================

  @strict @subprocess.run
  Scenario: Small test using subprocess.run() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "subprocess.run(['echo', 'test'])"
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @subprocess.Popen
  Scenario: Small test using subprocess.Popen() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "subprocess.Popen(['echo', 'test'])"
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @subprocess.call
  Scenario: Small test using subprocess.call() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "subprocess.call(['echo', 'test'])"
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @subprocess.check_output
  Scenario: Small test using subprocess.check_output() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "subprocess.check_output(['echo', 'test'])"
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @subprocess.check_call
  Scenario: Small test using subprocess.check_call() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "subprocess.check_call(['echo', 'test'])"
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @os.system
  Scenario: Small test using os.system() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that calls os system function
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @os.popen
  Scenario: Small test using os.popen() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that calls os popen function
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @os.execv
  Scenario: Small test using os.execv() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that calls os execv function
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  @strict @os.spawn
  Scenario: Small test using os.spawnl() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses os.spawnl
    When the test suite runs
    Then the test fails with a process violation error
    And the error message contains "Subprocess Violation"

  # =============================================================================
  # Warn Mode Scenarios
  # =============================================================================

  @warn @subprocess.run
  Scenario: Small test using subprocess.run() in warn mode shows warning but passes
    Given enforcement mode is set to "warn"
    And a test file with a small test that uses "subprocess.run(['echo', 'test'])"
    When the test suite runs
    Then the test passes
    And the hermeticity summary shows 1 process violation warning

  @warn @os.system
  Scenario: Small test using os.system() in warn mode shows warning but passes
    Given enforcement mode is set to "warn"
    And a test file with a small test that calls os system function
    When the test suite runs
    Then the test passes
    And the hermeticity summary shows 1 process violation warning

  # =============================================================================
  # Off Mode Scenarios
  # =============================================================================

  @off @subprocess.run
  Scenario: Small test using subprocess.run() in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a small test that uses "subprocess.run(['echo', 'test'])"
    When the test suite runs
    Then the test passes
    And no process violation warnings are emitted

  # =============================================================================
  # Medium/Large Test Scenarios (No Restrictions)
  # =============================================================================

  @medium @strict
  Scenario: Medium test can use subprocess.run() regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a medium test that uses "subprocess.run(['echo', 'test'])"
    When the test suite runs
    Then the test passes
    And no process violation errors occur

  @large @strict
  Scenario: Large test can use subprocess.run() regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a large test that uses "subprocess.run(['echo', 'test'])"
    When the test suite runs
    Then the test passes
    And no process violation errors occur
