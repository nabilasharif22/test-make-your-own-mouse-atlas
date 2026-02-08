"""
atlas_loader.py
---------------
Loads atlas data.
This version uses a mock atlas with realistic size for visualization.
"""

import numpy as np


def load_mock_atlas():
    """
    Returns a larger fake 3D atlas using Allen structure IDs.
    Shape: (z, y, x) = (30, 40, 50)
    Simulates major brain regions.
    """
    atlas = np.zeros((30, 40, 50), dtype=int)
    
    # Background (0) is already set
    
    # Cortex (385) - top/anterior region
    atlas[5:20, 5:35, 5:45] = 385
    
    # Hippocampus (315) - middle region
    atlas[10:18, 10:30, 10:40] = 315
    
    # Cerebellum (1089) - posterior region
    atlas[15:28, 25:38, 30:48] = 1089
    
    # Striatum (363) - central region
    atlas[8:16, 15:25, 15:35] = 363
    
    # Define voxel size in micrometers (z, y, x). These are example values
    # realistic for small-animal atlases; adjust as needed.
    voxel_size_um = (25.0, 25.0, 25.0)

    return atlas, voxel_size_um
    
