#!/bin/bash

echo "🐍 Setting up GitHub-Neo4j Sync Environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install PyGithub==2.1.1
pip install fastapi==0.104.1
pip install "uvicorn[standard]==0.24.0"
pip install neo4j==5.15.0
pip install httpx==0.25.2
pip install apscheduler==3.10.4
pip install pydantic==2.5.0
pip install pydantic-settings==2.1.0

echo "✅ Environment setup complete!"
echo ""
echo "To activate the environment:"
echo "source venv/bin/activate"
echo ""
echo "To run the app:"
echo "python github_neo_4_j_sync.py"