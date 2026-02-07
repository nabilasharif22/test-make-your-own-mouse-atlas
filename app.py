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
    fig_3d = plot_3d_brain(st.session_state.atlas)
    st.plotly_chart(fig_3d, use_container_width=True)
    
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
            fig_cut = plot_cutting_plane(st.session_state.atlas, cut_axis=axis, cut_position=position, blade_angle=angle)
            st.plotly_chart(fig_cut, use_container_width=True)
        
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
        st.image((current / current.max() * 255).astype(np.uint8), width=400)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save PNG"):
                save_slice_png(current, f"exports/slice_{idx}.png")
                st.success("Saved!")
        with col2:
            if st.button("Save PDF"):
                save_slices_pdf(st.session_state.generated_slices, "exports/brain.pdf")
                st.success("Saved!")
