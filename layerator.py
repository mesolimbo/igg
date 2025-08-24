#!/usr/bin/env python3
"""
Layerator script - Regenerates the lambda-layer directory and its contents.
This script installs Python dependencies into the lambda layer structure
required for AWS Lambda deployments.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def main():
    """Main function to regenerate lambda layer."""
    script_dir = Path(__file__).parent
    layer_dir = script_dir / "lambda-layer"
    python_dir = layer_dir / "python"
    requirements_file = layer_dir / "requirements.txt"
    
    print("Starting lambda layer regeneration...")
    
    # Check if requirements.txt exists
    if not requirements_file.exists():
        print(f"ERROR: Requirements file not found: {requirements_file}")
        sys.exit(1)
    
    # Remove existing python directory if it exists
    if python_dir.exists():
        print(f"Removing existing python directory: {python_dir}")
        shutil.rmtree(python_dir)
    
    # Create lambda-layer directory structure
    python_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created directory: {python_dir}")
    
    # Install dependencies with proper dependency resolution
    print(f"Installing dependencies from {requirements_file} with full dependency resolution...")
    cmd = [
        sys.executable, "-m", "pip", "install",
        "-r", str(requirements_file),
        "-t", str(python_dir),
        "--upgrade"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("SUCCESS: Dependencies installed successfully!")
        if result.stdout:
            print("Installation output:")
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install dependencies: {e}")
        if e.stderr:
            print("Error output:")
            print(e.stderr)
        sys.exit(1)
    
    print("Lambda layer regeneration complete!")
    print(f"Layer created at: {layer_dir}")
    
    # Show summary
    installed_packages = [d for d in python_dir.iterdir() 
                         if d.is_dir() and not d.name.startswith('.') 
                         and not d.name.endswith('.dist-info')]
    
    print(f"Installed {len(installed_packages)} packages:")
    for package in sorted(installed_packages):
        print(f"  - {package.name}")


if __name__ == "__main__":
    main()