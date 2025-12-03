#!/usr/bin/env python
"""Entry point for Streamlit app"""
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the app
from app import *  # This will run the Streamlit app
