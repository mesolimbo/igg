#!/usr/bin/env python3
"""
Lambda Layer generator for IGG project.
Creates a Lambda layer with heavy dependencies (pandas, nltk) for use with model_processor.py
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def main():
    """Build Lambda layer with heavy dependencies."""
    print("Building Lambda layer for IGG...")
    
    # Paths
    project_root = Path(__file__).parent
    layer_dir = project_root / "lambda-layer"
    python_dir = layer_dir / "python"
    requirements_file = project_root / "lambda-layer" / "requirements.txt"
    
    # Clean up existing layer
    if layer_dir.exists():
        print(f"Cleaning up existing layer: {layer_dir}")
        shutil.rmtree(layer_dir)
    
    # Create layer directory structure
    python_dir.mkdir(parents=True, exist_ok=True)
    
    # Create requirements.txt for layer (heavy dependencies only)
    layer_requirements = [
        "pandas>=1.5.0",
        "nltk>=3.8",
        # boto3/botocore are provided by Lambda runtime
        # mcp is only needed for the MCP server, not Lambda
    ]
    
    with open(requirements_file, 'w') as f:
        f.write('\n'.join(layer_requirements))
    
    print(f"Created layer requirements: {requirements_file}")
    
    # Install dependencies to layer
    pip_command = [
        sys.executable, "-m", "pip", "install",
        "-r", str(requirements_file),
        "-t", str(python_dir),
        "--no-deps",  # Don't install sub-dependencies automatically
        "--platform", "linux_x86_64",  # Lambda platform
        "--implementation", "cp",
        "--python-version", "3.11",
        "--only-binary=:all:",  # Only use binary wheels
    ]
    
    print(f"Installing dependencies to layer...")
    print(f"Command: {' '.join(pip_command)}")
    
    try:
        result = subprocess.run(pip_command, check=True, capture_output=True, text=True)
        print("Dependencies installed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        print(f"Error output: {e.stderr}")
        return 1
    
    # Install sub-dependencies manually
    subdeps = [
        "numpy>=1.20.0",
        "python-dateutil>=2.8.0", 
        "pytz>=2020.1",
        "six>=1.15.0",
        "regex>=2021.0.0",
        "click>=7.0.0",
        "joblib>=1.0.0",
        "tqdm>=4.50.0",
    ]
    
    subdep_command = [
        sys.executable, "-m", "pip", "install"
    ] + subdeps + [
        "-t", str(python_dir),
        "--platform", "linux_x86_64",
        "--implementation", "cp", 
        "--python-version", "3.11",
        "--only-binary=:all:",
    ]
    
    print(f"Installing sub-dependencies...")
    try:
        subprocess.run(subdep_command, check=True, capture_output=True)
        print("Sub-dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Some sub-dependencies failed: {e}")
        # Continue anyway, Lambda might have some of these
    
    # Check layer size
    layer_size = sum(f.stat().st_size for f in python_dir.rglob('*') if f.is_file())
    layer_size_mb = layer_size / (1024 * 1024)
    
    print(f"Layer size: {layer_size_mb:.1f} MB")
    
    if layer_size_mb > 250:  # Lambda layer size limit
        print("Warning: Layer size exceeds 250MB limit")
        return 1
    
    print("Lambda layer built successfully!")
    print(f"Layer location: {layer_dir}")
    print()
    print("Next steps:")
    print("1. Deploy with CDK: pipenv run cdk deploy")
    print("2. The layer will be automatically used by model_processor Lambda")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())