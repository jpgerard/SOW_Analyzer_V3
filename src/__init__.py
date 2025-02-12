"""SOW Analyzer V3 package."""

import os
import sys

# Add src directory to Python path
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import submodules
from . import document_processing
from . import analysis
from . import extraction
from . import reporting
from . import utils

__all__ = [
    'document_processing',
    'analysis',
    'extraction',
    'reporting',
    'utils'
]
