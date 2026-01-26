@enforcement @network
Feature: Network Access Enforcement
  As a test author following Google's test size guidelines
  I want small tests to be blocked from network access
  And medium tests to only access localhost
  So that my tests remain hermetic and do not depend on external services

  Background:
    Given the pytest-test-categories plugin is installed

  # =============================================================================
  # Small Tests - Strict Mode (Block All Network)
  # =============================================================================

  @strict @small @socket
  Scenario: Small test creating socket in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that creates a socket
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  @strict @small @http
  Scenario: Small test making HTTP request in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that makes an HTTP request
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  @strict @small @requests
  Scenario: Small test using requests library in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses requests get
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  @strict @small @urllib
  Scenario: Small test using urllib in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that uses urllib urlopen
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  @strict @small @localhost
  Scenario: Small test connecting to localhost in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that connects to localhost
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  # =============================================================================
  # Medium Tests - Strict Mode (Localhost Only)
  # =============================================================================

  @strict @medium @localhost
  Scenario: Medium test connecting to localhost in strict mode passes
    Given enforcement mode is set to "strict"
    And a test file with a medium test that connects to localhost
    When the test suite runs
    Then the test passes
    And no network violation errors occur

  @strict @medium @127.0.0.1
  Scenario: Medium test connecting to 127.0.0.1 in strict mode passes
    Given enforcement mode is set to "strict"
    And a test file with a medium test that connects to 127.0.0.1
    When the test suite runs
    Then the test passes
    And no network violation errors occur

  @strict @medium @external
  Scenario: Medium test connecting to external host in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a medium test that connects to external host
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  @strict @medium @httpbin
  Scenario: Medium test making request to httpbin.org in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a medium test that requests httpbin
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  # =============================================================================
  # Large Tests - Strict Mode (Allow All)
  # =============================================================================

  @strict @large @external
  Scenario: Large test can access external hosts regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with a large test that connects to external host
    When the test suite runs
    Then the test passes
    And no network violation errors occur

  @strict @xlarge @external
  Scenario: XLarge test can access external hosts regardless of enforcement mode
    Given enforcement mode is set to "strict"
    And a test file with an xlarge test that connects to external host
    When the test suite runs
    Then the test passes
    And no network violation errors occur

  # =============================================================================
  # Warn Mode Scenarios
  # =============================================================================

  @warn @small @socket
  Scenario: Small test creating socket in warn mode shows warning but passes
    Given enforcement mode is set to "warn"
    And a test file with a small test that creates a socket
    When the test suite runs
    Then the test passes
    And a warning is emitted containing "Network Access Violation"
    And the hermeticity summary shows 1 network violation warning

  @warn @medium @external
  Scenario: Medium test connecting to external host in warn mode shows warning
    Given enforcement mode is set to "warn"
    And a test file with a medium test that connects to external host
    When the test suite runs
    Then the test passes
    And a warning is emitted containing "Network Access Violation"

  # =============================================================================
  # Off Mode Scenarios
  # =============================================================================

  @off @small @socket
  Scenario: Small test creating socket in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a small test that creates a socket
    When the test suite runs
    Then the test passes
    And no network violation warnings are emitted

  @off @medium @external
  Scenario: Medium test connecting to external host in off mode passes silently
    Given enforcement mode is set to "off"
    And a test file with a medium test that connects to external host
    When the test suite runs
    Then the test passes
    And no network violation warnings are emitted

  # =============================================================================
  # Edge Cases
  # =============================================================================

  @strict @small @dns
  Scenario: Small test doing DNS lookup in strict mode fails
    Given enforcement mode is set to "strict"
    And a test file with a small test that does DNS lookup
    When the test suite runs
    Then the test fails with a network violation error
    And the error message contains "Network Access Violation"

  @strict @medium @ipv6-localhost
  Scenario: Medium test connecting to ::1 (IPv6 localhost) in strict mode passes
    Given enforcement mode is set to "strict"
    And a test file with a medium test that connects to ipv6 localhost
    When the test suite runs
    Then the test passes
    And no network violation errors occur
