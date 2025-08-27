#!/usr/bin/env python3
"""
Debug script to test coordinate transformations step by step
"""

import numpy as np
import math

def matrix_inverse_2x2(a, b, c, d):
    """Calculate inverse of 2x2 transformation matrix"""
    det = a * d - b * c
    if abs(det) < 1e-10:
        raise ValueError(f"Matrix is singular (det={det})")
    
    inv_a = d / det
    inv_b = -b / det
    inv_c = -c / det
    inv_d = a / det
    
    return inv_a, inv_b, inv_c, inv_d

def transform_point(x, y, matrix):
    """Transform a point using matrix [a, b, c, d, tx, ty]"""
    a, b, c, d, tx, ty = matrix
    x_new = a * x + c * y + tx
    y_new = b * x + d * y + ty
    return x_new, y_new

def inverse_transform_point(x, y, matrix):
    """Inverse transform a point"""
    a, b, c, d, tx, ty = matrix
    
    # First subtract translation
    x_trans = x - tx
    y_trans = y - ty
    
    # Then apply inverse of rotation/scale matrix
    try:
        inv_a, inv_b, inv_c, inv_d = matrix_inverse_2x2(a, b, c, d)
        x_orig = inv_a * x_trans + inv_c * y_trans
        y_orig = inv_b * x_trans + inv_d * y_trans
        return x_orig, y_orig
    except ValueError as e:
        print(f"Cannot invert matrix: {e}")
        return None, None

def debug_transformation_step_by_step():
    """Debug the transformation for our specific SVG"""
    
    print("=== STEP-BY-STEP TRANSFORMATION DEBUG ===\n")
    
    # Data from our SVG analysis
    test_cases = [
        {
            "name": "Image 1 (DFC9A2C6)",
            "clip_coords": (559.3, 218.3, 376.3, 564.5),  # Final clipPath coords
            "image_matrix": [0.0, 0.14, -0.14, 0.0, 735.8847898796978, 500.0],
            "image_coords": (-2048.0, -1536.0, 4096.0, 3072.0),  # x, y, w, h in SVG
            "expected_aspect": 4096/3072  # Original image aspect ratio
        }
    ]
    
    for case in test_cases:
        print(f"--- {case['name']} ---")
        
        clip_x, clip_y, clip_w, clip_h = case['clip_coords']
        matrix = case['image_matrix']
        img_x, img_y, img_w, img_h = case['image_coords']
        
        print(f"ClipPath coords: ({clip_x:.1f}, {clip_y:.1f}, {clip_w:.1f}, {clip_h:.1f})")
        print(f"Image matrix: {matrix}")
        print(f"Image SVG coords: x={img_x}, y={img_y}, w={img_w}, h={img_h}")
        
        # Step 1: Calculate clip corners in SVG space
        clip_corners = [
            (clip_x, clip_y),                    # Top-left
            (clip_x + clip_w, clip_y),           # Top-right  
            (clip_x, clip_y + clip_h),           # Bottom-left
            (clip_x + clip_w, clip_y + clip_h)   # Bottom-right
        ]
        print(f"Clip corners in SVG: {clip_corners}")
        
        # Step 2: Transform clip corners to image coordinate system
        print("\nTransforming clip corners to image space:")
        image_corners = []
        for i, (cx, cy) in enumerate(clip_corners):
            ix, iy = inverse_transform_point(cx, cy, matrix)
            if ix is not None:
                image_corners.append((ix, iy))
                print(f"  Corner {i+1}: SVG({cx:.1f}, {cy:.1f}) -> Image({ix:.1f}, {iy:.1f})")
        
        if len(image_corners) == 4:
            # Step 3: Calculate bounding box in image space
            min_x = min(corner[0] for corner in image_corners)
            max_x = max(corner[0] for corner in image_corners)
            min_y = min(corner[1] for corner in image_corners)
            max_y = max(corner[1] for corner in image_corners)
            
            print(f"\nImage space bounding box:")
            print(f"  X range: {min_x:.1f} to {max_x:.1f} (width: {max_x-min_x:.1f})")
            print(f"  Y range: {min_y:.1f} to {max_y:.1f} (height: {max_y-min_y:.1f})")
            
            # Step 4: Adjust for image offset and calculate crop coordinates
            crop_x = min_x - img_x
            crop_y = min_y - img_y
            crop_w = max_x - min_x
            crop_h = max_y - min_y
            
            print(f"\nCrop coordinates relative to image:")
            print(f"  Crop: x={crop_x:.1f}, y={crop_y:.1f}, w={crop_w:.1f}, h={crop_h:.1f}")
            print(f"  Aspect ratio: {crop_w/crop_h:.3f}")
            print(f"  Expected aspect: {case['expected_aspect']:.3f}")
            
            # Step 5: Calculate what this means in terms of actual pixel crop
            # (This would be scaled by the actual image dimensions)
            print(f"\nActual image dimensions in SVG: {img_w} x {img_h}")
            
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    debug_transformation_step_by_step()