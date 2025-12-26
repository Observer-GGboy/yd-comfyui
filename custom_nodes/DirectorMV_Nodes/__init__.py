"""
DirectorMV_Nodes - MV Director System for ComfyUI

A comprehensive MV generation system with identity preservation,
storyboard parsing, and quality control.

Architecture Principles:
- AIX and all existing custom_nodes are READ-ONLY dependencies
- All new functionality is implemented within this package
- Reuse via workflow composition or Adapter pattern
- No monkey patching, no modification to existing packages
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DirectorMV")

# Package info
__version__ = "0.1.0"
__author__ = "DirectorMV Team"

# Add package to path for internal imports
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)


def check_dependencies() -> list[str]:
    """
    Check if required ComfyUI nodes are installed.
    Returns list of missing dependencies.
    """
    required_nodes = [
        "PuLID_ComfyUI",
        "ComfyUI-AdvancedLivePortrait",
    ]
    
    custom_nodes_dir = os.path.dirname(PACKAGE_DIR)
    missing = []
    
    for node in required_nodes:
        node_path = os.path.join(custom_nodes_dir, node)
        if not os.path.exists(node_path):
            missing.append(node)
    
    if missing:
        logger.warning(f"DirectorMV: Missing recommended dependencies: {missing}")
        logger.warning("Some features may not work without these nodes.")
    
    return missing


# Check dependencies on load (warning only, don't fail)
_missing_deps = check_dependencies()

# Import node mappings
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Export for ComfyUI
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

logger.info(f"DirectorMV_Nodes v{__version__} loaded successfully")
logger.info(f"Registered {len(NODE_CLASS_MAPPINGS)} nodes")

