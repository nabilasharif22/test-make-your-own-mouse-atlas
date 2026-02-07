"""
exporter.py
-----------
Handles PNG and PDF export of slices.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image


def normalize_slice(slice_2d):
    """
    Normalize slice data to 0-255 range.
    """
    slice_min = slice_2d.min()
    slice_max = slice_2d.max()
    if slice_max > slice_min:
        return ((slice_2d - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
    return slice_2d.astype(np.uint8)


def save_slice_png(slice_2d, filename):
    """
    Save a single slice as a PNG image.
    """
    normalized = normalize_slice(slice_2d)
    
    plt.figure()
    plt.imshow(normalized, cmap='gray')
    plt.axis("off")
    plt.savefig(filename, bbox_inches="tight", pad_inches=0)
    plt.close()


def save_slices_pdf(slices, filename):
    """
    Save all slices into one PDF.
    """
    images = []

    for slice_2d in slices:
        normalized = normalize_slice(slice_2d)
        
        fig, ax = plt.subplots()
        ax.imshow(normalized, cmap='gray')
        ax.axis("off")

        temp_file = "temp_slice.png"
        plt.savefig(temp_file, bbox_inches="tight", pad_inches=0)
        plt.close()

        images.append(Image.open(temp_file).convert("RGB"))

    if images:
        images[0].save(
            filename,
            save_all=True,
            append_images=images[1:] if len(images) > 1 else []
        )

    if os.path.exists("temp_slice.png"):
        os.remove("temp_slice.png")
