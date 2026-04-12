#!/bin/bash
# Test runner script for Claude Code CLI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Claude Code CLI Test Runner${NC}"
echo "======================================"
echo ""

# Default options
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
PARALLEL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--unit)
            TEST_TYPE="unit"
            shift
            ;;
        -i|--integration)
            TEST_TYPE="integration"
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -u, --unit          Run unit tests only"
            echo "  -i, --integration   Run integration tests only"
            echo "  -c, --coverage      Generate coverage report"
            echo "  -v, --verbose       Verbose output"
            echo "  -p, --parallel      Run tests in parallel"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

# Add markers based on test type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD -m unit"
        echo -e "${YELLOW}Running unit tests only...${NC}"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD -m integration"
        echo -e "${YELLOW}Running integration tests only...${NC}"
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD -m 'not slow'"
        echo -e "${YELLOW}Running all tests (excluding slow)...${NC}"
        ;;
esac

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=html --cov-report=term"
    echo -e "${YELLOW}Coverage report enabled${NC}"
fi

# Add verbose if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add parallel if requested
if [ "$PARALLEL" = true ]; then
    if command -v pytest-xdist &> /dev/null; then
        PYTEST_CMD="$PYTEST_CMD -n auto"
        echo -e "${YELLOW}Running tests in parallel...${NC}"
    else
        echo -e "${YELLOW}pytest-xdist not installed, running sequentially${NC}"
    fi
fi

echo ""
echo -e "${GREEN}Executing: ${PYTEST_CMD}${NC}"
echo ""

# Run tests
eval $PYTEST_CMD
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    if [ "$COVERAGE" = true ]; then
        echo -e "${GREEN}Coverage report generated in htmlcov/${NC}"
    fi
else
    echo -e "${RED}Some tests failed${NC}"
fi

exit $TEST_EXIT_CODE
