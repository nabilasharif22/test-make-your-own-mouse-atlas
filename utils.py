"""
utils.py
--------
Small helper functions.
"""

import numpy as np
from allen_api import get_structure_info


def summarize_slice(slice_2d):
    """
    Return unique structure IDs in a slice with Allen API info.
    """
    unique_ids = list(np.unique(slice_2d))
    structures = {}
    
    for sid in unique_ids:
        if sid == 0:  # Skip background
            continue
        info = get_structure_info(sid)
        structures[sid] = info
    
    return structures

