#!/bin/bash
# Non-interactive demo for asciinema recording
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_cmd() {
    echo -e "${YELLOW}\$ $1${NC}"
    sleep 0.5
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use the repo's venv
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PATH="$REPO_ROOT/.venv/bin:$PATH"

clear
print_header "pytest-test-categories: Enforcement Demo"
echo "This plugin catches flaky test patterns and enforces hermetic testing."
echo ""
sleep 2

# Part 1: Problem tests in WARN mode
print_header "Part 1: Problem Tests (WARN Mode)"
echo "Tests with violations - they PASS but violations are logged:"
echo ""
print_cmd "pytest --test-categories-enforcement=warn tests/test_problem_tests.py -v --tb=no"
sleep 1

pytest --test-categories-enforcement=warn tests/test_problem_tests.py -v --tb=no 2>&1 || true

sleep 3

# Part 2: Strict mode
print_header "Part 2: STRICT Mode - Violations FAIL"
echo "Same tests, but now violations cause test failures:"
echo ""
print_cmd "pytest --test-categories-enforcement=strict tests/test_problem_tests.py --tb=line -q"
sleep 1

pytest --test-categories-enforcement=strict tests/test_problem_tests.py --tb=line -q 2>&1 || true

sleep 3

# Part 3: Solutions
print_header "Part 3: Hermetic Tests PASS in Strict Mode"
echo "Properly written tests use mocking and dependency injection:"
echo ""
print_cmd "pytest --test-categories-enforcement=strict tests/test_solution_tests.py -v"
sleep 1

pytest --test-categories-enforcement=strict tests/test_solution_tests.py -v

sleep 2

# Summary
print_header "Summary"
echo -e "${GREEN}Hermetic tests = Fast, Reliable, Deterministic${NC}"
echo ""
echo "Adoption path:"
echo "  1. enforcement=off   - Explore your codebase"
echo "  2. enforcement=warn  - See violations, fix incrementally"
echo "  3. enforcement=strict - Prevent regressions"
echo ""
echo -e "${CYAN}pip install pytest-test-categories${NC}"
echo ""
sleep 3
