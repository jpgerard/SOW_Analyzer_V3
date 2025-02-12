#!/bin/bash

# Make script executable
chmod +x setup.sh

# Install spaCy model
python -m spacy download en_core_web_sm

# Verify installation
python -c "import spacy; spacy.load('en_core_web_sm')"
