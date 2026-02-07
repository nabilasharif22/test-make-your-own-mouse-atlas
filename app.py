"""
app.py
------
Interactive 3D Brain Slicer
Run with: streamlit run app.py
"""

import os
import streamlit as st
import numpy as np

from atlas_loader import load_mock_atlas
from brain_3d import plot_3d_brain, plot_cutting_plane
from blade_cutter import simulate_blade_cut, extract_slice_at_position
from utils import summarize_slice
from exporter import save_slice_png, save_slices_pdf

st.set_page_config(layout="wide", page_title="3D Brain Slicer")
st.title("🧠 Interactive 3D Brain Slicer")

# Rendering settings (sidebar)
st.sidebar.header("Rendering Settings")
# Default: slightly less smoothing for crisper boundaries, skip small regions by default
sigma = st.sidebar.slider("Surface smoothing (sigma)", 0.2, 3.0, 0.7, step=0.1)
min_voxels = st.sidebar.number_input("Min voxels per structure", min_value=1, max_value=2000, value=50, step=1)
opacity = st.sidebar.slider("Structure opacity", 0.1, 1.0, 0.9, step=0.05)
camera_x = st.sidebar.slider("Camera X", -5.0, 5.0, 1.5, step=0.1)
camera_y = st.sidebar.slider("Camera Y", -5.0, 5.0, 1.5, step=0.1)
camera_z = st.sidebar.slider("Camera Z", -5.0, 5.0, 1.3, step=0.1)
cache_info = st.sidebar.checkbox("Use Allen API cache", value=True)

if "atlas" not in st.session_state:
    st.session_state.atlas = load_mock_atlas()
    st.session_state.brain_placed = False
    st.session_state.generated_slices = []
    st.session_state.current_slice_idx = 0
    st.session_state.cut_axis = "z"
    st.session_state.cut_position = 0.5

os.makedirs("exports", exist_ok=True)

tab1, tab2, tab3 = st.tabs(["View Brain", "Make Cut", "Browse Slices"])

with tab1:
    st.header("View 3D Brain")
    fig_3d = plot_3d_brain(
        st.session_state.atlas,
        smooth_sigma=sigma,
        min_voxels=min_voxels,
        opacity=opacity,
        camera_eye=(camera_x, camera_y, camera_z)
    )
    st.plotly_chart(fig_3d, width='stretch')
    
    if st.button("Place Brain"):
        st.session_state.brain_placed = True
        st.success("Brain placed!")

with tab2:
    if not st.session_state.brain_placed:
        st.warning("Place brain first in View Brain tab")
    else:
        st.header("Make Cut")
        col1, col2 = st.columns([3, 1])
        
        with col2:
            axis = st.radio("Axis:", ["z", "y", "x"])
            position = st.slider("Position", 0.0, 1.0, 0.5)
            angle = st.slider("Angle", 0, 360, 0)
        
        with col1:
            fig_cut = plot_cutting_plane(
                st.session_state.atlas,
                cut_axis=axis,
                cut_position=position,
                blade_angle=angle,
                smooth_sigma=sigma,
                min_voxels=min_voxels,
                opacity=opacity,
                camera_eye=(camera_x, camera_y, camera_z)
            )
            st.plotly_chart(fig_cut, width='stretch')
        
        if st.button("Make Cut"):
            piece1, _ = simulate_blade_cut(st.session_state.atlas, cut_axis=axis, cut_position=position)
            st.session_state.generated_slices = [piece1[i, :, :] for i in range(piece1.shape[0])]
            st.success(f"Generated {len(st.session_state.generated_slices)} slices")

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
                        st.write(f"**Color:** {info.get('color_hex_triplet', 'N/A')}")
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
