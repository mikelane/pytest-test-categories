@enforcement @filesystem
Feature: Filesystem I/O Enforcement
  As a test author following Google's test size guidelines
  I want small tests to be blocked from filesystem I/O
  So that my tests remain hermetic and do not depend on external state

  Background:
    Given the pytest-test-categories plugin is installed

  # =============================================================================
  # Strict Mode Scenarios - Write Operations
  # =============================================================================

  @strict @write @open
  Scenario: Small test writing to file with open() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that writes using open()
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @write @pathlib
  Scenario: Small test using pathlib write_text() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that writes using pathlib write_text
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @write @pathlib.write_bytes
  Scenario: Small test using pathlib write_bytes() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that writes using pathlib write_bytes
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @read @open
  Scenario: Small test reading file with open() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that reads using open()
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @read @pathlib
  Scenario: Small test using pathlib read_text() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that reads using pathlib read_text
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @mkdir
  Scenario: Small test creating directory in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that creates a directory
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @os.makedirs
  Scenario: Small test using os.makedirs() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses os makedirs
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @os.remove
  Scenario: Small test using os.remove() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses os remove
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @shutil
  Scenario: Small test using shutil.copy() in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses shutil copy
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  # =============================================================================
  # Warn Mode Scenarios
  # =============================================================================

  @warn @write
  Scenario: Small test writing to file in warn mode shows warning but passes
    Given enforcement mode is set to "warn"
    And a test file with a small test that writes using open()
    When the test suite runs
    Then the test passes
    And the hermeticity summary shows 1 filesystem violation warning

  @warn @read
  Scenario: Small test reading file in warn mode shows warning but passes
    Given enforcement mode is set to "warn"
    And a test file with a small test that reads using open()
    When the test suite runs
    Then the test passes
    And the hermeticity summary shows 1 filesystem violation warning

  # =============================================================================
  # Off Mode Scenarios
  # =============================================================================

  @off @write
  Scenario: Small test writing to file in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a small test that writes using open()
    When the test suite runs
    Then the test passes
    And no filesystem violation warnings are emitted

  @off @read
  Scenario: Small test reading file in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a small test that reads using open()
    When the test suite runs
    Then the test passes
    And no filesystem violation warnings are emitted

  # =============================================================================
  # Medium/Large Test Scenarios (No Restrictions)
  # =============================================================================

  @medium @strict
  Scenario: Medium test can write to files regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a medium test that writes using open()
    When the test suite runs
    Then the test passes
    And no filesystem violation errors occur

  @large @strict
  Scenario: Large test can read and write files regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a large test that reads and writes files
    When the test suite runs
    Then the test passes
    And no filesystem violation errors occur

  # =============================================================================
  # Pytest Fixtures (Special Cases)
  # =============================================================================

  @strict @tmp_path
  Scenario: Small test using pytest tmp_path fixture in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses tmp_path fixture to write
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"

  @strict @tmpdir
  Scenario: Small test using pytest tmpdir fixture in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses tmpdir fixture to write
    When the test suite runs
    Then the test fails with a filesystem violation error
    And the error message contains "Filesystem Access Violation"
