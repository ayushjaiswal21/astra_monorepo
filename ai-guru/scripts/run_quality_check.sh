#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting code quality checks..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed.
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed.
    exit 1
fi

# Install Python dependencies if not installed
echo "🔧 Checking Python dependencies..."
pip install flake8 pylint black mypy --quiet

# Run Python linter
echo "🔍 Running flake8..."
flake8 backend/ --config=setup.cfg || {
    echo "❌ flake8 found issues"
    exit 1
}

# Run Python type checker
echo "🔍 Running mypy..."
mypy backend/ --config-file=mypy.ini || {
    echo "⚠️  mypy found type issues"
}

# Run Python formatter check
echo "🎨 Checking code formatting with black..."
black --check backend/ || {
    echo "❌ Some files need formatting with black"
    echo "   Run 'black backend/' to fix formatting"
    exit 1
}

# Install Node.js dependencies if not installed
echo "🔧 Checking Node.js dependencies..."
cd frontend
npm install --silent

# Run ESLint
echo "🔍 Running ESLint..."
npm run lint || {
    echo "❌ ESLint found issues"
    exit 1
}

# Run tests
echo "🧪 Running tests..."
cd ..
python -m pytest backend/tests/ -v || {
    echo "❌ Tests failed"
    exit 1
}

echo "✅ All checks passed!"
exit 0
