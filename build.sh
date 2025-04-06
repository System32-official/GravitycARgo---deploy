#!/bin/bash

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install --only-binary=:all: -r requirements.txt

echo "Build completed successfully."
