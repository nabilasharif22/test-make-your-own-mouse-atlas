"""
brain_3d.py
-----------
3D brain visualization with smooth surface rendering using marching cubes.
"""

import numpy as np
import plotly.graph_objects as go
from scipy.ndimage import gaussian_filter
from skimage import measure


def create_smooth_volume(atlas, sigma=2.0):
    """
    Create a smooth 3D volume by applying Gaussian filtering.
    Returns a 3D array suitable for isosurface rendering.
    """
    smoothed = gaussian_filter(atlas.astype(float), sigma=sigma)
    return smoothed


def plot_3d_brain(atlas, title="3D Brain Atlas", show_axes=True):
    """
    Create an interactive 3D brain visualization with smooth surface mesh.
    Uses marching cubes algorithm for true surface rendering.
    """
    smoothed_atlas = create_smooth_volume(atlas, sigma=2.0)
    threshold = smoothed_atlas.max() * 0.4
    
    try:
        # Use marching cubes to generate surface mesh
        verts, faces, _, _ = measure.marching_cubes(smoothed_atlas, level=threshold)
        
        # Create figure with mesh
        fig = go.Figure(data=[go.Mesh3d(
            x=verts[:, 2],
            y=verts[:, 1],
            z=verts[:, 0],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            opacity=0.8,
            color='steelblue',
            showlegend=True,
            name='Brain Surface'
        )])
        
    except Exception as e:
        # Fallback to scatter if marching cubes fails
        coords = np.argwhere(smoothed_atlas > threshold)
        if len(coords) == 0:
            return None
        x, y, z = coords[:, 2], coords[:, 1], coords[:, 0]
        intensities = smoothed_atlas[smoothed_atlas > threshold]
        
        fig = go.Figure(data=[go.Scatter3d(
            x=x, y=y, z=z,
            mode='markers',
            marker=dict(
                size=2,
                color=intensities,
                colorscale='Viridis',
                showscale=True,
                opacity=0.8
            )
        )])
    
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="X (μm)" if show_axes else "",
            yaxis_title="Y (μm)" if show_axes else "",
            zaxis_title="Z (μm)" if show_axes else "",
            aspectmode="data",
            xaxis=dict(showgrid=show_axes),
            yaxis=dict(showgrid=show_axes),
            zaxis=dict(showgrid=show_axes),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.3))
        ),
        height=700,
        hovermode='closest',
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    return fig


def plot_cutting_plane(atlas, cut_axis='z', cut_position=0.5, blade_angle=0):
    """
    Visualize the smoothed brain with a rotatable cutting plane overlay.
    cut_axis: 'x', 'y', or 'z'
    cut_position: 0-1 normalized position along axis
    blade_angle: rotation angle of cutting plane in degrees
    """
    smoothed_atlas = create_smooth_volume(atlas, sigma=2.0)
    threshold = smoothed_atlas.max() * 0.4
    
    try:
        verts, faces, _, _ = measure.marching_cubes(smoothed_atlas, level=threshold)
        
        fig = go.Figure(data=[go.Mesh3d(
            x=verts[:, 2],
            y=verts[:, 1],
            z=verts[:, 0],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            opacity=0.7,
            color='steelblue',
            name='Brain Surface'
        )])
        
    except Exception as e:
        coords = np.argwhere(smoothed_atlas > threshold)
        if len(coords) == 0:
            return None
        x, y, z = coords[:, 2], coords[:, 1], coords[:, 0]
        intensities = smoothed_atlas[smoothed_atlas > threshold]
        
        fig = go.Figure(data=[go.Scatter3d(
            x=x, y=y, z=z,
            mode='markers',
            marker=dict(size=2, color=intensities, opacity=0.7)
        )])
    
    # Get axis dimensions
    dims = atlas.shape
    axis_map = {'z': 0, 'y': 1, 'x': 2}
    axis_idx = axis_map[cut_axis]
    plane_pos = int(cut_position * dims[axis_idx])
    
    # Create rotatable cutting plane
    angle_rad = np.radians(blade_angle)
    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    
    if cut_axis == 'z':
        # Plane perpendicular to Z, rotatable in XY plane
        plane_x = [0, dims[2], dims[2], 0, 0]
        plane_y = [0, 0, dims[1], dims[1], 0]
        plane_z = [plane_pos] * 5
        
        # Rotate plane around center
        cx, cy = dims[2] / 2, dims[1] / 2
        rotated_x = [cx + (x - cx) * cos_a - (y - cy) * sin_a for x, y in zip(plane_x, plane_y)]
        rotated_y = [cy + (x - cx) * sin_a + (y - cy) * cos_a for x, y in zip(plane_x, plane_y)]
        plane_x, plane_y = rotated_x, rotated_y
        
    elif cut_axis == 'y':
        plane_x = [0, dims[2], dims[2], 0, 0]
        plane_y = [plane_pos] * 5
        plane_z = [0, 0, dims[0], dims[0], 0]
        
        cz, cx = dims[0] / 2, dims[2] / 2
        rotated_z = [cz + (z - cz) * cos_a - (x - cx) * sin_a for z, x in zip(plane_z, plane_x)]
        rotated_x = [cx + (z - cz) * sin_a + (x - cx) * cos_a for z, x in zip(plane_z, plane_x)]
        plane_z, plane_x = rotated_z, rotated_x
        
    else:  # cut_axis == 'x'
        plane_x = [plane_pos] * 5
        plane_y = [0, dims[1], dims[1], 0, 0]
        plane_z = [0, 0, dims[0], dims[0], 0]
        
        cy, cz = dims[1] / 2, dims[0] / 2
        rotated_y = [cy + (y - cy) * cos_a - (z - cz) * sin_a for y, z in zip(plane_y, plane_z)]
        rotated_z = [cz + (y - cy) * sin_a + (z - cz) * cos_a for y, z in zip(plane_y, plane_z)]
        plane_y, plane_z = rotated_y, rotated_z
    
    fig.add_trace(go.Scatter3d(
        x=plane_x, y=plane_y, z=plane_z,
        mode='lines',
        line=dict(color='red', width=5),
        name=f'Blade (angle: {blade_angle}°)'
    ))
    
    fig.update_layout(
        title="3D Brain with Cutting Blade",
        scene=dict(aspectmode="data"),
        height=700,
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    return fig
