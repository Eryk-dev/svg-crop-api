#!/usr/bin/env python3
"""
SVG Processor Module

Core processing logic adapted from create_masks_from_svg.py
Provides async interface for API usage with temporary file handling.
"""

import asyncio
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Any
import aiohttp
import aiofiles

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class SVGProcessor:
    """Processes SVG files to extract and crop images with precise coordinate transformation."""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def parse_transform(self, transform_str: str) -> Tuple[float, float]:
        """Extract translation (tx, ty) from a matrix transform string."""
        match = re.search(r"matrix\(([^)]+)\)", transform_str)
        if match:
            parts = [float(p) for p in match.group(1).replace(",", " ").split()]
            if len(parts) == 6:
                return parts[4], parts[5]
        return 0.0, 0.0

    def parse_matrix(self, transform_str: str) -> Tuple[float, float, float, float, float, float]:
        """Parse transformation matrix from SVG transform attribute."""
        match = re.search(r"matrix\(([^)]+)\)", transform_str)
        if match:
            parts = [float(p) for p in match.group(1).replace(",", " ").split()]
            if len(parts) == 6:
                return tuple(parts)
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    def build_parent_map(self, root):
        """Build a mapping from child elements to their parent elements."""
        parent_map = {}
        for parent in root.iter():
            for child in parent:
                parent_map[child] = parent
        return parent_map

    def find_transform_for_image(self, image_el, parent_map):
        """Find the transformation matrix for an image element by traversing up the tree."""
        current = image_el
        while current is not None:
            parent = parent_map.get(current)
            if parent is not None and parent.tag.endswith('}g'):
                transform_str = parent.get('transform', '')
                if transform_str and 'matrix' in transform_str:
                    return self.parse_matrix(transform_str)
            current = parent
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    async def download_file(self, url: str, dest_path: Path) -> bool:
        """Download a file from URL to destination path."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url) as response:
                response.raise_for_status()
                content = await response.read()
                
                async with aiofiles.open(dest_path, 'wb') as f:
                    await f.write(content)
                
                logger.debug(f"Downloaded: {dest_path.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False

    async def download_svg(self, url: str, dest: Path) -> bool:
        """Download SVG from URL and fix common formatting issues."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                
                # Fix malformed XML declaration
                if content.startswith('<!--?xml'):
                    content = content.replace('<!--?xml', '<?xml', 1)
                    if content.startswith('<?xml version="1.0" encoding="UTF-8" standalone="no" ?-->'):
                        content = content.replace('?-->', '?>', 1)
                
                async with aiofiles.open(dest, 'w', encoding='utf-8') as f:
                    await f.write(content)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to download SVG: {e}")
            return False

    def extract_image_urls(self, svg_path: Path) -> List[str]:
        """Extract all image URLs from the SVG file."""
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Failed to parse SVG file: {e}")
            return []

        ns = {
            "svg": "http://www.w3.org/2000/svg",
            "xlink": "http://www.w3.org/1999/xlink"
        }
        
        image_urls = []
        for img_el in root.findall(".//svg:image", ns):
            href = img_el.get("{http://www.w3.org/1999/xlink}href")
            if href and href.startswith("http"):
                image_urls.append(href)
        
        return image_urls

    def extract_filename_from_url(self, url: str) -> str:
        """Extract a reasonable filename from an image URL."""
        parsed = urllib.parse.urlparse(url)
        path_parts = parsed.path.split('/')
        for part in reversed(path_parts):
            if '.' in part and any(ext in part.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                return part
        
        if path_parts and path_parts[-1]:
            return path_parts[-1] + '.jpeg'
        
        return 'image.jpeg'

    async def download_all_images(self, image_urls: List[str], out_dir: Path) -> int:
        """Download all images from the URL list to the output directory."""
        if not image_urls:
            return 0
        
        downloaded_count = 0
        
        for i, url in enumerate(image_urls):
            filename = self.extract_filename_from_url(url)
            
            # Avoid filename conflicts
            dest_path = out_dir / filename
            if dest_path.exists():
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    filename = f"{name_parts[0]}_{i}.{name_parts[1]}"
                else:
                    filename = f"{filename}_{i}"
                dest_path = out_dir / filename
            
            if await self.download_file(url, dest_path):
                downloaded_count += 1
        
        return downloaded_count

    def update_svg_with_local_images(self, svg_path: Path, image_urls: List[str], out_dir: Path) -> None:
        """Replace remote image URLs in the SVG with local file references."""
        try:
            content = svg_path.read_text(encoding='utf-8')
            
            for i, url in enumerate(image_urls):
                filename = self.extract_filename_from_url(url)
                
                # Handle potential filename conflicts
                local_path = out_dir / filename
                if not local_path.exists():
                    name_parts = filename.rsplit('.', 1)
                    if len(name_parts) == 2:
                        test_filename = f"{name_parts[0]}_{i}.{name_parts[1]}"
                    else:
                        test_filename = f"{filename}_{i}"
                    test_path = out_dir / test_filename
                    if test_path.exists():
                        filename = test_filename
                
                content = content.replace(url, filename)
            
            svg_path.write_text(content, encoding='utf-8')
            
        except Exception as e:
            logger.error(f"Failed to update SVG with local images: {e}")

    def precise_crop_image(self, image_filename: str, out_dir: Path, 
                          clip_rect: Tuple[float, float, float, float], 
                          transform_matrix: Tuple[float, float, float, float, float, float],
                          image_attrs: Tuple[float, float, float, float], 
                          region_idx: int, output_format: str = "png") -> bool:
        """Precisely crop an image based on SVG clipping coordinates and transformation matrix."""
        try:
            image_path = out_dir / image_filename
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                return False
            
            clip_x, clip_y, clip_w, clip_h = clip_rect
            a, b, c, d, tx, ty = transform_matrix
            img_x, img_y, img_width, img_height = image_attrs
            
            # Transform coordinates
            group_clip_x = (clip_x - tx) / a
            group_clip_y = (clip_y - ty) / d
            group_clip_w = clip_w / a
            group_clip_h = clip_h / d
            
            img_crop_x = group_clip_x - img_x
            img_crop_y = group_clip_y - img_y
            
            with Image.open(image_path) as img:
                orig_width, orig_height = img.size
                
                scale_x = orig_width / img_width
                scale_y = orig_height / img_height
                
                final_x = img_crop_x * scale_x
                final_y = img_crop_y * scale_y
                final_w = group_clip_w * scale_x
                final_h = group_clip_h * scale_y
                
                x1 = max(0, int(final_x))
                y1 = max(0, int(final_y))
                x2 = min(orig_width, int(final_x + final_w))
                y2 = min(orig_height, int(final_y + final_h))
                
                if x2 <= x1 or y2 <= y1:
                    logger.warning(f"Invalid crop coordinates for {image_filename}")
                    return False
                
                cropped = img.crop((x1, y1, x2, y2))
                
                file_ext = "png" if output_format == "png" else "jpeg"
                crop_filename = f"crop_region{region_idx}_{image_filename.rsplit('.', 1)[0]}.{file_ext}"
                crop_path = out_dir / crop_filename
                
                if output_format == "png":
                    cropped.save(crop_path, format="PNG")
                else:
                    cropped.save(crop_path, format="JPEG", quality=95)
                
                logger.info(f"Cropped: {crop_filename}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to crop image {image_filename}: {e}")
            return False

    def extract_masks_and_crop_images(self, svg_path: Path, out_dir: Path, output_format: str = "png") -> int:
        """Extract masks and crop images from SVG."""
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Failed to parse SVG file: {e}")
            return 0

        ns = {"svg": "http://www.w3.org/2000/svg", "xlink": "http://www.w3.org/1999/xlink"}
        parent_map = self.build_parent_map(root)
        
        # Get SVG dimensions
        viewbox = root.get("viewBox")
        if viewbox:
            _, _, w, h = map(float, viewbox.split())
        else:
            w = float(root.get("width", 1000))
            h = float(root.get("height", 1000))
        svg_dims = (int(h), int(w))

        # Find clipPaths
        clip_paths: Dict[str, Tuple[float, float, float, float]] = {}
        for clip_path_el in root.findall(".//svg:clipPath", ns):
            clip_id = clip_path_el.get("id")
            rect_el = clip_path_el.find("svg:rect", ns)
            if clip_id and rect_el is not None:
                try:
                    x = float(rect_el.get("x", 0))
                    y = float(rect_el.get("y", 0))
                    width = float(rect_el.get("width"))
                    height = float(rect_el.get("height"))
                    
                    transform = rect_el.get("transform", "")
                    tx, ty = self.parse_transform(transform)
                    
                    abs_x = x + tx
                    abs_y = y + ty
                    
                    clip_paths[clip_id] = (abs_x, abs_y, width, height)
                except (ValueError, TypeError):
                    continue

        # Process elements with clip-path
        mask_count = 0
        elements_with_clip_path = root.findall(".//*[@clip-path]", ns)

        for el in elements_with_clip_path:
            clip_path_url = el.get("clip-path", "")
            match = re.search(r"url\(#([^)]+)\)", clip_path_url)
            if match:
                clip_id = match.group(1)
                if clip_id in clip_paths:
                    clip_x, clip_y, clip_w, clip_h = clip_paths[clip_id]
                    
                    # Create mask
                    mask = np.zeros(svg_dims, dtype=np.uint8)
                    pt1 = (int(round(clip_x)), int(round(clip_y)))
                    pt2 = (int(round(clip_x + clip_w)), int(round(clip_y + clip_h)))
                    cv2.rectangle(mask, pt1, pt2, (255), thickness=-1)
                    
                    mask_path = out_dir / f"mask_region{mask_count}.png"
                    cv2.imwrite(str(mask_path), mask)
                    
                    # Find associated image
                    image_el = el.find(".//svg:image", ns)
                    if image_el is not None:
                        image_href = image_el.get("{http://www.w3.org/1999/xlink}href", "")
                        if image_href:
                            img_x = float(image_el.get("x", 0))
                            img_y = float(image_el.get("y", 0))
                            img_width = float(image_el.get("width", 0))
                            img_height = float(image_el.get("height", 0))
                            
                            transform_matrix = self.find_transform_for_image(image_el, parent_map)
                            
                            self.precise_crop_image(
                                image_href, out_dir, 
                                (clip_x, clip_y, clip_w, clip_h),
                                transform_matrix,
                                (img_x, img_y, img_width, img_height),
                                mask_count,
                                output_format
                            )
                    
                    mask_count += 1
        
        return mask_count

    async def process_svg_async(self, svg_url: str, temp_dir: Path, output_format: str = "png") -> Dict[str, Any]:
        """Main async processing function."""
        try:
            svg_path = temp_dir / "view.svg"
            
            # Download SVG
            if not await self.download_svg(svg_url, svg_path):
                return {"success": False, "error": "Failed to download SVG"}
            
            # Extract image URLs
            image_urls = self.extract_image_urls(svg_path)
            if not image_urls:
                return {"success": False, "error": "No images found in SVG"}
            
            # Download images
            images_downloaded = await self.download_all_images(image_urls, temp_dir)
            if images_downloaded == 0:
                return {"success": False, "error": "Failed to download any images"}
            
            # Update SVG with local references
            self.update_svg_with_local_images(svg_path, image_urls, temp_dir)
            
            # Extract masks and crop images
            regions_processed = self.extract_masks_and_crop_images(svg_path, temp_dir, output_format)
            
            if regions_processed == 0:
                return {"success": False, "error": "No regions processed"}
            
            return {
                "success": True,
                "regions_processed": regions_processed,
                "images_downloaded": images_downloaded
            }
            
        except Exception as e:
            logger.error(f"Error in process_svg_async: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if self.session:
                await self.session.close()
                self.session = None 