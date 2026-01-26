@enforcement @configuration
Feature: Enforcement Configuration
  As a project maintainer
  I want to configure enforcement mode via CLI and config files
  So that I can gradually adopt hermeticity enforcement

  Background:
    Given the pytest-test-categories plugin is installed

  # =============================================================================
  # Default Behavior
  # =============================================================================

  @default
  Scenario: Default enforcement mode is off
    Given no enforcement configuration is specified
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no hermeticity violation warnings are emitted

  # =============================================================================
  # CLI Flag Configuration
  # =============================================================================

  @cli @strict
  Scenario: Enforcement mode can be set to strict via CLI flag
    Given enforcement mode is set via CLI to "strict"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test fails with a sleep violation error

  @cli @warn
  Scenario: Enforcement mode can be set to warn via CLI flag
    Given enforcement mode is set via CLI to "warn"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And a warning is emitted containing "Sleep Call Violation"

  @cli @off
  Scenario: Enforcement mode can be set to off via CLI flag
    Given enforcement mode is set via CLI to "off"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no hermeticity violation warnings are emitted

  # =============================================================================
  # pytest.ini Configuration
  # =============================================================================

  @ini @strict
  Scenario: Enforcement mode can be set to strict via pytest.ini
    Given enforcement mode is set via ini file to "strict"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test fails with a sleep violation error

  @ini @warn
  Scenario: Enforcement mode can be set to warn via pytest.ini
    Given enforcement mode is set via ini file to "warn"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And a warning is emitted containing "Sleep Call Violation"

  @ini @off
  Scenario: Enforcement mode can be set to off via pytest.ini
    Given enforcement mode is set via ini file to "off"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no hermeticity violation warnings are emitted

  # =============================================================================
  # CLI Overrides Config File
  # =============================================================================

  @cli @ini @override
  Scenario: CLI flag overrides pytest.ini setting
    Given enforcement mode is set via ini file to "off"
    And enforcement mode is set via CLI to "strict"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test fails with a sleep violation error

  @cli @ini @override @reverse
  Scenario: CLI flag can relax enforcement from ini setting
    Given enforcement mode is set via ini file to "strict"
    And enforcement mode is set via CLI to "off"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test passes
    And no hermeticity violation warnings are emitted

  # =============================================================================
  # Enforcement Applies to All Constraint Types
  # =============================================================================

  @strict @all-constraints
  Scenario: Strict mode enforces all constraint types
    Given enforcement mode is set to "strict"
    And a test file with a small test that violates multiple constraints
    When the test suite runs
    Then the test fails with the first violation error

  @warn @all-constraints
  Scenario: Warn mode warns about all constraint types
    Given enforcement mode is set to "warn"
    And a test file with a small test that violates multiple constraints
    When the test suite runs
    Then the test passes
    And warnings are emitted for multiple violation types

  # =============================================================================
  # Configuration Validation
  # =============================================================================

  @invalid @cli
  Scenario: Invalid CLI enforcement value is rejected
    Given an invalid enforcement mode "invalid" is set via CLI
    When the test suite runs
    Then pytest reports a configuration error
    And the error message indicates valid options are off, warn, strict

  # =============================================================================
  # Hermeticity Summary
  # =============================================================================

  @summary @warn
  Scenario: Hermeticity summary shows violation counts by type
    Given enforcement mode is set to "warn"
    And a test file with tests that violate sleep, network, and filesystem constraints
    When the test suite runs
    Then the hermeticity summary shows violation counts by type
    And the hermeticity summary distinguishes warnings from failures

  @summary @strict
  Scenario: Hermeticity summary shows failures in strict mode
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the test fails with a sleep violation error
    And the hermeticity summary shows the failure

  @summary @quiet
  Scenario: Hermeticity summary respects quiet mode
    Given enforcement mode is set to "warn"
    And quiet mode is enabled
    And a test file with a small test that uses "time.sleep(0.001)"
    When the test suite runs
    Then the hermeticity summary is abbreviated
