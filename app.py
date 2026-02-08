"""
app.py
------
Interactive 3D Brain Slicer
Run with: streamlit run app.py
"""

import os
import streamlit as st
import numpy as np
from scipy import stats

from atlas_loader import load_mock_atlas
from brain_3d import plot_3d_brain, plot_cutting_plane
from blade_cutter import simulate_blade_cut, extract_slice_at_position
from utils import summarize_slice
from exporter import save_slice_png, save_slices_pdf

st.set_page_config(layout="wide", page_title="3D Brain Slicer")
st.title(" Interactive 3D Mouse Brain Slicer")

# Rendering settings (sidebar)
st.sidebar.header("Rendering Settings")
# Default: slightly less smoothing for crisper boundaries. We no longer filter small regions so
# users can preserve small anatomical details in the 3D view.
sigma = st.sidebar.slider("Surface smoothing (sigma)", 0.2, 3.0, 0.7, step=0.1)
# Keep all structures in the 3D view by default (user requested removing the min-voxels control)
min_voxels = 0
opacity = st.sidebar.slider("Structure opacity", 0.1, 1.0, 0.9, step=0.05)
camera_x = st.sidebar.slider("Camera X", -5.0, 5.0, 1.5, step=0.1)
camera_y = st.sidebar.slider("Camera Y", -5.0, 5.0, 1.5, step=0.1)
camera_z = st.sidebar.slider("Camera Z", -5.0, 5.0, 1.3, step=0.1)
cache_info = st.sidebar.checkbox("Use Allen API cache", value=True)
# Option to keep the current camera/orientation between updates
keep_camera = st.sidebar.checkbox("Keep camera between updates", value=True)

if "atlas" not in st.session_state:
    atlas, voxel_size = load_mock_atlas()
    st.session_state.atlas = atlas
    st.session_state.voxel_size = voxel_size
    st.session_state.generated_slices = []
    st.session_state.current_slice_idx = 0
    st.session_state.cut_axis = "z"
    st.session_state.cut_position = 0.5
    # initialize camera state from sidebar defaults
    st.session_state.camera = {"x": camera_x, "y": camera_y, "z": camera_z}

if "camera" not in st.session_state:
    st.session_state.camera = {"x": camera_x, "y": camera_y, "z": camera_z}

os.makedirs("exports", exist_ok=True)

tab1, tab2, tab3 = st.tabs(["View Brain", "Make Cut", "Browse Slices"])

with tab1:
    st.header("View 3D Brain")
    # Choose camera: preserve stored camera if user wants to keep orientation
    if keep_camera:
        cam = st.session_state.camera
    else:
        cam = {"x": camera_x, "y": camera_y, "z": camera_z}

    fig_3d = plot_3d_brain(
        st.session_state.atlas,
        smooth_sigma=sigma,
        min_voxels=min_voxels,
        opacity=opacity,
        camera=cam,
        voxel_size=st.session_state.voxel_size
    )
    st.plotly_chart(fig_3d, width='stretch')
    
    
    # Camera controls
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Apply camera sliders to view"):
            st.session_state.camera = {"x": camera_x, "y": camera_y, "z": camera_z}
            st.success("Updated stored camera from sliders")
    with c2:
        if st.button("Reset view"):
            st.session_state.camera = {"x": 1.5, "y": 1.5, "z": 1.3}
            st.success("Reset view to default")

with tab2:
    st.header("Make Cut")
    col1, col2 = st.columns([3, 1])
    
    with col2:
        axis = st.radio("Axis:", ["z", "y", "x"])
        position = st.slider("Position", 0.0, 1.0, 0.5)
        angle = st.slider("Angle", 0, 360, 0)
        # Slice thickness in micrometers (affects how many voxel-layers are grouped into one slice)
        # Default to the voxel size along Z (or overall first entry) so the default is one voxel thick
        voxel_defaults = st.session_state.voxel_size if "voxel_size" in st.session_state else (25.0, 25.0, 25.0)
        thickness_um = st.slider("Slice thickness (μm)", 1.0, 1000.0, float(voxel_defaults[0]), step=1.0)
    
    with col1:
        # Compute a preview highlight mask limited to a slab around the cut plane
        axis_map = {"z": 0, "y": 1, "x": 2}
        ax = axis_map.get(axis, 0)
        voxel_z, voxel_y, voxel_x = st.session_state.voxel_size
        voxel_along_axis = (voxel_z, voxel_y, voxel_x)[ax]
        slab_vox = max(1, int(round(thickness_um / float(voxel_along_axis))))
        full_axis_len = st.session_state.atlas.shape[ax]
        cut_idx = int(position * full_axis_len)
        half = slab_vox // 2
        start = max(0, cut_idx - half)
        end = min(full_axis_len, start + slab_vox)

        highlight_mask_preview = None
        try:
            # build a boolean mask marking the removed side within the slab window
            mask = np.zeros_like(st.session_state.atlas, dtype=np.uint8)
            if ax == 0:
                removed_start = cut_idx
                removed_end = end
                if removed_start < removed_end:
                    mask[removed_start:removed_end, :, :] = 1
            elif ax == 1:
                removed_start = cut_idx
                removed_end = end
                if removed_start < removed_end:
                    mask[:, removed_start:removed_end, :] = 1
            else:
                removed_start = cut_idx
                removed_end = end
                if removed_start < removed_end:
                    mask[:, :, removed_start:removed_end] = 1
            highlight_mask_preview = mask
        except Exception:
            highlight_mask_preview = None

        cam_for_cut = st.session_state.camera if keep_camera else {"x": camera_x, "y": camera_y, "z": camera_z}

        fig_cut = plot_cutting_plane(
            st.session_state.atlas,
            cut_axis=axis,
            cut_position=position,
            blade_angle=angle,
            smooth_sigma=sigma,
            min_voxels=min_voxels,
            opacity=opacity,
            camera=cam_for_cut,
            highlight_mask=highlight_mask_preview,
            highlight_color="#ff4444",
            highlight_opacity=0.35,
            voxel_size=st.session_state.voxel_size
        )
        st.plotly_chart(fig_cut, width='stretch')
    
    if st.button("Make Cut"):
        piece1, piece2 = simulate_blade_cut(st.session_state.atlas, cut_axis=axis, cut_position=position)
        # Slab-only extraction: compute a window around the cut plane limited to requested thickness (μm)
        axis_map = {"z": 0, "y": 1, "x": 2}
        ax = axis_map.get(axis, 0)
        voxel_z, voxel_y, voxel_x = st.session_state.voxel_size
        voxel_along_axis = (voxel_z, voxel_y, voxel_x)[ax]

        slab_vox = max(1, int(round(thickness_um / float(voxel_along_axis))))
        full_axis_len = st.session_state.atlas.shape[ax]
        cut_idx = int(position * full_axis_len)
        half = slab_vox // 2
        start = max(0, cut_idx - half)
        end = min(full_axis_len, start + slab_vox)

        # Extract the windowed volume (move axis to front for easy slicing)
        vol_full = np.moveaxis(st.session_state.atlas, ax, 0)  # shape (S, A, B)
        vol_window = vol_full[start:end]  # shape (slab_vox, A, B)

        # Produce one output slice per voxel-layer within the slab (mode across single-layer -> same labels)
        grouped_slices = []
        for i in range(vol_window.shape[0]):
            layer = vol_window[i]
            grouped_slices.append(layer)

        # Save generated slab slices back to session
        st.session_state.generated_slices = [s for s in grouped_slices]
        st.success(f"Generated {len(st.session_state.generated_slices)} slab slices (total slab {thickness_um} μm)")

        # Build highlight mask limited to removed side within the slab window for preview/reporting
        highlight_mask = np.zeros_like(st.session_state.atlas, dtype=np.uint8)
        if ax == 0:  # z
            removed_start = cut_idx
            removed_end = end
            if removed_start < removed_end:
                highlight_mask[removed_start:removed_end, :, :] = 1
        elif ax == 1:  # y
            removed_start = cut_idx
            removed_end = end
            if removed_start < removed_end:
                highlight_mask[:, removed_start:removed_end, :] = 1
        else:  # x
            removed_start = cut_idx
            removed_end = end
            if removed_start < removed_end:
                highlight_mask[:, :, removed_start:removed_end] = 1

        # Report which structures were removed (in the cut-off piece)
        kept_ids = set(np.unique(piece1))
        removed_ids = set(np.unique(piece2))
        # remove background id 0
        kept_ids.discard(0)
        removed_ids.discard(0)

        from allen_api import get_structure_info

        voxel_z, voxel_y, voxel_x = st.session_state.voxel_size

        with st.expander("Cut result: structures kept vs removed"):
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Kept piece (visible slices)**")
                if kept_ids:
                    for sid in sorted(kept_ids):
                        info = get_structure_info(int(sid))
                        name = info.get('name') if info else f"Structure {sid}"
                        st.write(f"- ID {sid}: {name}")
                else:
                    st.write("No structures retained (background only)")

            with c2:
                st.write("**Removed piece (cut off)**")
                if removed_ids:
                    for sid in sorted(removed_ids):
                        info = get_structure_info(int(sid))
                        name = info.get('name') if info else f"Structure {sid}"
                        count = int((piece2 == sid).sum())
                        voxel_volume_um3 = count * (voxel_z * voxel_y * voxel_x)
                        voxel_volume_mm3 = voxel_volume_um3 / 1e9

                        # bounding box extents (in voxels) and convert to um
                        coords = np.argwhere(piece2 == sid)
                        if coords.size:
                            zmin, ymin, xmin = coords.min(axis=0)
                            zmax, ymax, xmax = coords.max(axis=0)
                            dz = (zmax - zmin + 1) * voxel_z
                            dy = (ymax - ymin + 1) * voxel_y
                            dx = (xmax - xmin + 1) * voxel_x
                            extent_str = f"extent (μm): x={dx:.1f}, y={dy:.1f}, z={dz:.1f}"
                        else:
                            extent_str = "extent: N/A"

                        st.write(f"- ID {sid}: {name} — voxels: {count}, volume: {voxel_volume_um3:.0f} μm³ ({voxel_volume_mm3:.4f} mm³) — {extent_str}")
                else:
                    st.write("No structures were cut off (background only)")

with tab3:
    if not st.session_state.generated_slices:
        st.info("Generate slices in Make Cut tab")
    else:
        st.header("Browse Slices")
        idx = st.slider("Slice", 0, len(st.session_state.generated_slices) - 1)
        
        current = st.session_state.generated_slices[idx]
        
        # Create colored version of slice based on structure IDs
        # Map structure IDs to colors from Allen API
        colored_slice = np.zeros((*current.shape, 3), dtype=np.uint8)
        
        # Get structure colors
        from allen_api import get_structure_info
        unique_ids = np.unique(current[current > 0])
        struct_colors = {}
        
        for struct_id in unique_ids:
            info = get_structure_info(int(struct_id))
            if info and info.get('color_hex_triplet'):
                hex_color = info['color_hex_triplet']
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                struct_colors[int(struct_id)] = (r, g, b)
            else:
                struct_colors[int(struct_id)] = (128, 128, 128)  # Default gray
        
        # Paint the slice
        for struct_id, color in struct_colors.items():
            mask = current == struct_id
            colored_slice[mask] = color
        
        st.image(colored_slice, width=400)
        
        # Display structures in this slice
        st.subheader("Structures in this slice:")
        structures = summarize_slice(current)
        
        if structures:
            for sid, info in structures.items():
                if info:
                    with st.expander(f"ID {sid}: {info.get('name', 'Unknown')} ({info.get('acronym', '?')})"):
                        st.write(f"**Name:** {info.get('name', 'N/A')}")
                        st.write(f"**Acronym:** {info.get('acronym', 'N/A')}")
                        color_hex = info.get('color_hex_triplet', None)
                        if color_hex and len(color_hex) == 6:
                            color_css = f"#{color_hex}"
                            st.markdown(
                                f"""
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <div style="width:16px; height:16px; background:{color_css}; border:1px solid #333;"></div>
                                    <span>Color: {color_css}</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            st.write("**Color:** N/A")
                        st.write(f"**Parent ID:** {info.get('parent_structure_id', 'N/A')}")
                else:
                    st.write(f"ID {sid}: Could not fetch info from Allen API")
        else:
            st.info("No structures found in this slice (background only)")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save PNG"):
                save_slice_png(current, f"exports/slice_{idx}.png")
                st.success("Saved!")
        with col2:
            if st.button("Save PDF"):
                save_slices_pdf(st.session_state.generated_slices, "exports/brain.pdf")
                st.success("Saved!")
