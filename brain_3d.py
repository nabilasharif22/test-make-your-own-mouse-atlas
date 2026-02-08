"""
brain_3d.py
-----------
3D brain visualization with smooth surface rendering using marching cubes.
"""

import numpy as np
import plotly.graph_objects as go
from scipy.ndimage import gaussian_filter
from skimage import measure
from allen_api import get_structure_info
import os
import hashlib


_MESH_CACHE_DIR = ".cache/meshes"


def _mesh_cache_key(sid, smooth_sigma, mask_sum, shape):
    """Create a short key for caching based on structure id and parameters."""
    key_raw = f"{sid}_{smooth_sigma}_{int(mask_sum)}_{shape[0]}x{shape[1]}x{shape[2]}"
    return hashlib.sha1(key_raw.encode("utf-8")).hexdigest()


def _mesh_cache_path(key):
    os.makedirs(_MESH_CACHE_DIR, exist_ok=True)
    return os.path.join(_MESH_CACHE_DIR, f"{key}.npz")


def _mesh_cache_load(key):
    path = _mesh_cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        data = np.load(path)
        return data["verts"], data["faces"]
    except Exception:
        return None


def _mesh_cache_save(key, verts, faces):
    path = _mesh_cache_path(key)
    try:
        np.savez_compressed(path, verts=verts, faces=faces)
    except Exception:
        pass


def create_smooth_volume(atlas, sigma=2.0):
    """
    Create a smooth 3D volume by applying Gaussian filtering.
    Returns a 3D array suitable for isosurface rendering.
    """
    smoothed = gaussian_filter(atlas.astype(float), sigma=sigma)
    return smoothed


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-1 scale)."""
    if not hex_color or len(hex_color) != 6:
        return (0.5, 0.5, 0.5)  # Default gray
    try:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)
    except:
        return (0.5, 0.5, 0.5)


def get_structure_color(struct_id, color_cache):
    """Get RGB color for a structure from cache or API."""
    if struct_id in color_cache:
        return color_cache[struct_id]
    
    info = get_structure_info(int(struct_id))
    if info and info.get('color_hex_triplet'):
        rgb = hex_to_rgb(info['color_hex_triplet'])
    else:
        rgb = (0.5, 0.5, 0.5)  # Default gray
    
    color_cache[struct_id] = rgb
    return rgb


def plot_3d_brain(atlas, title="3D Brain Atlas", show_axes=True, smooth_sigma=1.0, min_voxels=20, opacity=0.9, camera_eye=(1.5,1.5,1.3), camera=None, voxel_size=(25.0, 25.0, 25.0)):
    """
    Create an interactive 3D brain visualization with color-coded structures.
    Uses marching cubes algorithm for true surface rendering.
    Shows structure info on hover with Allen API colors.
    """
    # Render each structure as its own smoothed mesh. This produces distinct,
    # colored surfaces (instead of a single blended blob) similar to the
    # Allen 3D viewer.
    structure_ids = np.unique(atlas[atlas > 0])
    fig = go.Figure()

    # lighting defaults for nicer surface appearance
    lighting = dict(ambient=0.6, diffuse=0.8, roughness=0.5, specular=0.5)

    for sid in structure_ids:
        sid = int(sid)
        mask = (atlas == sid).astype(float)
        # skip tiny regions
        if mask.sum() < min_voxels:
            continue

        # smooth binary mask to create clean surface
        smooth_mask = gaussian_filter(mask, sigma=smooth_sigma)

        # Try loading cached mesh first
        cache_key = _mesh_cache_key(sid, smooth_sigma, mask.sum(), atlas.shape)
        cached = _mesh_cache_load(cache_key)
        if cached is not None:
            verts, faces = cached
        else:
            try:
                verts, faces, _, _ = measure.marching_cubes(smooth_mask, level=0.5)
            except Exception:
                continue
            # save to cache (best-effort)
            _mesh_cache_save(cache_key, verts, faces)

        # Get color and name from Allen API
        info = get_structure_info(sid)
        if info and info.get('color_hex_triplet'):
            color_hex = f"#{info.get('color_hex_triplet')}"
        else:
            color_hex = "#808080"
        name = info.get('name', f'Structure {sid}') if info else f'Structure {sid}'

        # Prepare hover text per-vertex (same name for all)
        hover_text = [name] * len(verts)

        # Create mesh for this structure (note: verts are z,y,x)
        vz, vy, vx = voxel_size
        mesh = go.Mesh3d(
            x=verts[:, 2] * vx,
            y=verts[:, 1] * vy,
            z=verts[:, 0] * vz,
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            color=color_hex,
            opacity=opacity,
            name=name,
            hovertext=hover_text,
            hoverinfo='text',
            lighting=lighting,
            flatshading=False
        )

        fig.add_trace(mesh)

    # If no structure meshes were added, fallback to smoothed volume scatter
    if not fig.data:
        smoothed_atlas = create_smooth_volume(atlas, sigma=2.0)
        threshold = smoothed_atlas.max() * 0.4
        coords = np.argwhere(smoothed_atlas > threshold)
        if len(coords) == 0:
            return None
        vz, vy, vx = voxel_size
        x, y, z = coords[:, 2] * vx, coords[:, 1] * vy, coords[:, 0] * vz
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='markers',
            marker=dict(size=2, color='lightgray', opacity=0.8)
        ))
    
    # If caller provided a camera dict, use it; otherwise fall back to camera_eye tuple
    scene_camera = dict(eye=dict(x=camera_eye[0], y=camera_eye[1], z=camera_eye[2]))
    if camera and isinstance(camera, dict):
        # Expecting {'x':.., 'y':.., 'z':..} or Plotly camera dict
        if 'eye' in camera and isinstance(camera['eye'], dict):
            scene_camera = camera
        else:
            scene_camera = dict(eye=dict(x=float(camera.get('x', camera_eye[0])), y=float(camera.get('y', camera_eye[1])), z=float(camera.get('z', camera_eye[2]))))

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
            camera=scene_camera.get('camera', scene_camera) if isinstance(scene_camera, dict) else scene_camera
        ),
        height=700,
        hovermode='closest',
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    return fig


def plot_cutting_plane(atlas, cut_axis='z', cut_position=0.5, blade_angle=0, smooth_sigma=1.0, min_voxels=20, opacity=0.8, camera_eye=(1.5,1.5,1.3), camera=None, highlight_mask=None, highlight_color="#ff3333", highlight_opacity=0.35, voxel_size=(25.0,25.0,25.0)):
    """
    Visualize the smoothed brain with a rotatable cutting plane overlay.
    Uses color-coded structures from Allen Atlas.
    cut_axis: 'x', 'y', or 'z'
    cut_position: 0-1 normalized position along axis
    blade_angle: rotation angle of cutting plane in degrees
    """
    # Render per-structure meshes like `plot_3d_brain`, but keep room for the
    # cutting plane overlay.
    fig = go.Figure()
    lighting = dict(ambient=0.6, diffuse=0.8, roughness=0.5, specular=0.5)

    structure_ids = np.unique(atlas[atlas > 0])
    for sid in structure_ids:
        sid = int(sid)
        mask = (atlas == sid).astype(float)
        if mask.sum() < min_voxels:
            continue
        smooth_mask = gaussian_filter(mask, sigma=smooth_sigma)
        # Try mesh cache
        cache_key = _mesh_cache_key(sid, smooth_sigma, mask.sum(), atlas.shape)
        cached = _mesh_cache_load(cache_key)
        if cached is not None:
            verts, faces = cached
        else:
            try:
                verts, faces, _, _ = measure.marching_cubes(smooth_mask, level=0.5)
            except Exception:
                continue
            _mesh_cache_save(cache_key, verts, faces)

        info = get_structure_info(sid)
        if info and info.get('color_hex_triplet'):
            color_hex = f"#{info.get('color_hex_triplet')}"
        else:
            color_hex = "#808080"
        name = info.get('name', f'Structure {sid}') if info else f'Structure {sid}'

        vz, vy, vx = voxel_size
        mesh = go.Mesh3d(
            x=verts[:, 2] * vx, y=verts[:, 1] * vy, z=verts[:, 0] * vz,
            i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
            color=color_hex, opacity=opacity, name=name,
            hovertext=[name] * len(verts), hoverinfo='text',
            lighting=lighting, flatshading=False
        )
        fig.add_trace(mesh)
    
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

        # Rotate plane around center (voxel coords)
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
    
    # Scale plane coordinates into micrometers
    vz, vy, vx = voxel_size
    # convert voxel coords to micrometers matching axis
    if cut_axis == 'z':
        sx = [px * vx for px in plane_x]
        sy = [py * vy for py in plane_y]
        sz = [pz * vz for pz in plane_z]
    elif cut_axis == 'y':
        sx = [px * vx for px in plane_x]
        sy = [py * vy for py in plane_y]
        sz = [pz * vz for pz in plane_z]
    else:
        sx = [px * vx for px in plane_x]
        sy = [py * vy for py in plane_y]
        sz = [pz * vz for pz in plane_z]

    fig.add_trace(go.Scatter3d(
        x=sx, y=sy, z=sz,
        mode='lines',
        line=dict(color='red', width=5),
        name=f'Blade (angle: {blade_angle}°)'
    ))

    # If a highlight mask was provided (boolean mask of voxels to highlight), render its surface
    if highlight_mask is not None:
        try:
            # Smooth and extract surface for highlighted region
            hmask = (highlight_mask > 0).astype(float)
            if hmask.sum() > 0:
                h_smooth = gaussian_filter(hmask, sigma=max(1.0, smooth_sigma))
                verts, faces, _, _ = measure.marching_cubes(h_smooth, level=0.5)
                # Add highlight mesh (note: make it semi-transparent and on top)
                # scale highlight verts by voxel size
                vz, vy, vx = voxel_size
                highlight_mesh = go.Mesh3d(
                    x=verts[:, 2] * vx, y=verts[:, 1] * vy, z=verts[:, 0] * vz,
                    i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
                    color=highlight_color, opacity=highlight_opacity, name='To be cut',
                    hovertext=['To be cut'] * len(verts), hoverinfo='text',
                    lighting=dict(ambient=0.6, diffuse=0.4, roughness=0.9, specular=0.2),
                    flatshading=True
                )
                fig.add_trace(highlight_mesh)
        except Exception:
            pass
    
    # Respect provided camera if available
    scene_camera = dict(eye=dict(x=camera_eye[0], y=camera_eye[1], z=camera_eye[2]))
    if camera and isinstance(camera, dict):
        if 'eye' in camera and isinstance(camera['eye'], dict):
            scene_camera = camera
        else:
            scene_camera = dict(eye=dict(x=float(camera.get('x', camera_eye[0])), y=float(camera.get('y', camera_eye[1])), z=float(camera.get('z', camera_eye[2]))))

    fig.update_layout(
        title="3D Brain with Cutting Blade",
        scene=dict(aspectmode="data", camera=scene_camera.get('camera', scene_camera) if isinstance(scene_camera, dict) else scene_camera),
        height=700,
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    return fig
