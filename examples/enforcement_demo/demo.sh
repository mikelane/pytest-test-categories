#!/bin/bash
# =============================================================================
# pytest-test-categories Enforcement Demo
# =============================================================================
#
# This script demonstrates the enforcement features of pytest-test-categories.
# It shows how the plugin catches common testing anti-patterns and guides
# developers toward hermetic, reliable tests.
#
# Usage: ./demo.sh
#
# Requirements:
#   - Python 3.11+
#   - uv (recommended) or pip
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Print functions
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC} ${BOLD}$1${NC}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

wait_for_keypress() {
    echo ""
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read -r
}

# Navigate to demo directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for dependencies
check_dependencies() {
    print_section "Checking Dependencies"

    if command -v uv &> /dev/null; then
        print_success "uv found - using uv for package management"
        RUNNER="uv run"
    elif command -v python3 &> /dev/null; then
        print_warning "uv not found - falling back to python3"
        RUNNER="python3 -m"
        print_info "For best experience, install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    else
        print_error "Neither uv nor python3 found. Please install Python 3.11+"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    print_section "Installing Demo Dependencies"

    # Check if we're running from within the pytest-test-categories repo
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    if [[ -f "$REPO_ROOT/src/pytest_test_categories/plugin.py" ]]; then
        print_info "Detected: Running from within pytest-test-categories repo"
        print_info "Using repo's installed plugin version"
        cd "$REPO_ROOT"
        if [[ "$RUNNER" == "uv run" ]]; then
            uv sync --all-groups 2>/dev/null || true
        fi
        cd "$SCRIPT_DIR"
        print_success "Using local plugin installation"
    else
        print_info "Detected: Standalone demo installation"
        if [[ "$RUNNER" == "uv run" ]]; then
            print_info "Installing with uv..."
            uv sync
        else
            print_info "Installing with pip..."
            python3 -m pip install pytest pytest-test-categories pytest-mock --quiet
        fi
        print_success "Dependencies installed"
    fi
}

# =============================================================================
# Demo Sections
# =============================================================================

demo_intro() {
    print_header "pytest-test-categories: Enforcement Demo"

    echo "This demo showcases how pytest-test-categories catches common"
    echo "anti-patterns that cause flaky tests."
    echo ""
    echo "You'll see:"
    echo "  1. Tests with hermeticity violations (the problem)"
    echo "  2. How enforcement modes (warn/strict) detect violations"
    echo "  3. Properly hermetic tests (the solution)"
    echo "  4. The Hermeticity Violation Summary"
    echo ""
    print_info "Demo directory: $SCRIPT_DIR"

    wait_for_keypress
}

demo_problem_warn_mode() {
    print_header "Part 1: The Problem (Warn Mode)"

    print_info "First, let's run tests with common anti-patterns in WARN mode."
    print_info "Tests will pass, but violations will be logged."
    echo ""
    echo -e "${YELLOW}Command:${NC} pytest --test-categories-enforcement=warn tests/test_problem_tests.py -v"
    echo ""

    wait_for_keypress

    # Run with warn mode
    set +e  # Don't exit on non-zero return
    $RUNNER pytest --test-categories-enforcement=warn tests/test_problem_tests.py -v 2>&1 || true
    set -e

    echo ""
    print_warning "Notice the violations detected but tests passed."
    print_info "Warn mode is useful during migration - see violations without breaking builds."

    wait_for_keypress
}

demo_problem_strict_mode() {
    print_header "Part 2: Strict Enforcement"

    print_info "Now let's run the same tests in STRICT mode."
    print_info "Tests with violations will FAIL."
    echo ""
    echo -e "${YELLOW}Command:${NC} pytest --test-categories-enforcement=strict tests/test_problem_tests.py -v --tb=no -q"
    echo ""

    wait_for_keypress

    # Run with strict mode (expect failures)
    set +e
    $RUNNER pytest --test-categories-enforcement=strict tests/test_problem_tests.py -v --tb=short 2>&1 || true
    set -e

    echo ""
    print_error "Tests failed due to hermeticity violations!"
    print_info "Strict mode ensures violations are caught before they reach production."

    wait_for_keypress
}

demo_solutions() {
    print_header "Part 3: The Solution (Hermetic Tests)"

    print_info "Now let's run properly hermetic tests in STRICT mode."
    print_info "These tests pass because they don't violate hermeticity."
    echo ""
    echo -e "${YELLOW}Command:${NC} pytest --test-categories-enforcement=strict tests/test_solution_tests.py -v"
    echo ""

    wait_for_keypress

    # Run hermetic tests in strict mode
    $RUNNER pytest --test-categories-enforcement=strict tests/test_solution_tests.py -v

    echo ""
    print_success "All tests pass in strict mode!"
    print_info "These tests use proper patterns: time injection, mocking, dependency injection."

    wait_for_keypress
}

demo_violation_summary() {
    print_header "Part 4: The Violation Summary"

    print_info "Let's see the full violation summary in warn mode."
    print_info "This shows all violations grouped by type."
    echo ""
    echo -e "${YELLOW}Command:${NC} pytest --test-categories-enforcement=warn tests/test_problem_tests.py --tb=no"
    echo ""

    wait_for_keypress

    # Run to show summary
    set +e
    $RUNNER pytest --test-categories-enforcement=warn tests/test_problem_tests.py --tb=no 2>&1 || true
    set -e

    echo ""
    print_info "The summary shows exactly which tests have which violations."
    print_info "Use this to prioritize fixing tests during migration."

    wait_for_keypress
}

demo_mixed_suite() {
    print_header "Part 5: Mixed Test Suite"

    print_info "In real projects, you'll have a mix of small, medium, and large tests."
    print_info "Medium tests can use localhost, filesystem, and subprocesses."
    echo ""
    echo -e "${YELLOW}Command:${NC} pytest --test-categories-enforcement=strict tests/test_solution_tests.py -v -m 'small or medium'"
    echo ""

    wait_for_keypress

    $RUNNER pytest --test-categories-enforcement=strict tests/test_solution_tests.py -v -m "small or medium"

    echo ""
    print_success "Both small and medium tests pass with appropriate constraints!"

    wait_for_keypress
}

demo_distribution() {
    print_header "Part 6: Test Distribution Report"

    print_info "pytest-test-categories can also report on your test distribution."
    print_info "Google recommends: 80% small, 15% medium, 5% large."
    echo ""
    echo -e "${YELLOW}Command:${NC} pytest tests/test_solution_tests.py --test-size-report=basic"
    echo ""

    wait_for_keypress

    $RUNNER pytest tests/test_solution_tests.py --test-size-report=basic

    wait_for_keypress
}

demo_summary() {
    print_header "Summary: Key Takeaways"

    echo -e "${BOLD}What we learned:${NC}"
    echo ""
    echo "  1. ${RED}The Problem:${NC} Tests with hidden external dependencies are flaky"
    echo "     - Network calls, sleep, filesystem, subprocess, threading"
    echo ""
    echo "  2. ${YELLOW}Detection:${NC} pytest-test-categories catches violations"
    echo "     - warn mode: See violations without breaking builds"
    echo "     - strict mode: Fail tests that violate hermeticity"
    echo ""
    echo "  3. ${GREEN}Solutions:${NC} Proper patterns for hermetic tests"
    echo "     - Time injection for TTL/expiration testing"
    echo "     - HTTP mocking (responses, pytest-httpx)"
    echo "     - pyfakefs or io.StringIO for filesystem"
    echo "     - Dependency injection for subprocess/executor"
    echo "     - Test logic synchronously, use medium tests for integration"
    echo ""
    echo "  4. ${BLUE}Adoption Path:${NC}"
    echo "     - Week 1: enforcement=off, explore violations"
    echo "     - Weeks 2-4: enforcement=warn, fix incrementally"
    echo "     - Week 5+: enforcement=strict, prevent regressions"
    echo ""
    echo -e "${BOLD}Resources:${NC}"
    echo "  - Documentation: https://pytest-test-categories.readthedocs.io"
    echo "  - PyPI: https://pypi.org/project/pytest-test-categories/"
    echo "  - GitHub: https://github.com/mikelane/pytest-test-categories"
    echo ""
    print_success "Demo complete! Happy hermetic testing!"
}

# =============================================================================
# Main
# =============================================================================

main() {
    check_dependencies
    install_dependencies
    demo_intro
    demo_problem_warn_mode
    demo_problem_strict_mode
    demo_solutions
    demo_violation_summary
    demo_mixed_suite
    demo_distribution
    demo_summary
}

# Run main
main
