#!/bin/bash

# Make script executable
chmod +x setup.sh

# Install spaCy model with word vectors
python -m spacy download en_core_web_md

# Verify installation
python -c "import spacy; spacy.load('en_core_web_md')"
