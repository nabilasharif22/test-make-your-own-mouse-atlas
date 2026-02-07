"""
blade_cutter.py
---------------
Blade cutting simulation for virtual brain slicing.
"""

import numpy as np


def simulate_blade_cut(atlas, cut_axis='z', cut_position=None, blade_angle=0):
    """
    Simulate cutting the brain with a blade.
    
    Args:
        atlas: 3D numpy array
        cut_axis: 'x', 'y', or 'z'
        cut_position: position along axis (0 to 1), or None for middle
        blade_angle: rotation of blade in degrees
    
    Returns:
        Two resulting pieces of the brain
    """
    if cut_position is None:
        cut_position = 0.5
    
    axis_map = {'z': 0, 'y': 1, 'x': 2}
    axis_idx = axis_map[cut_axis]
    
    cut_idx = int(cut_position * atlas.shape[axis_idx])
    
    # Use numpy slicing to create two pieces
    if axis_idx == 0:  # z-axis
        piece1 = atlas[:cut_idx, :, :]
        piece2 = atlas[cut_idx:, :, :]
    elif axis_idx == 1:  # y-axis
        piece1 = atlas[:, :cut_idx, :]
        piece2 = atlas[:, cut_idx:, :]
    else:  # x-axis
        piece1 = atlas[:, :, :cut_idx]
        piece2 = atlas[:, :, cut_idx:]
    
    return piece1, piece2


def extract_slice_at_position(atlas, cut_axis='z', position=None):
    """
    Extract a single slice from the atlas at a given position.
    """
    if position is None:
        position = 0.5
    
    axis_map = {'z': 0, 'y': 1, 'x': 2}
    axis_idx = axis_map[cut_axis]
    
    slice_idx = int(position * atlas.shape[axis_idx])
    
    if axis_idx == 0:
        return atlas[slice_idx, :, :]
    elif axis_idx == 1:
        return atlas[:, slice_idx, :]
    else:
        return atlas[:, :, slice_idx]
