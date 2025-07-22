#!/usr/bin/env python3
"""
SVG Crop API

Flask service that processes SVG files, extracts images, creates masks,
and returns precisely cropped images as a ZIP file encoded in base64 format.
"""

import asyncio
import logging
import tempfile
import zipfile
from pathlib import Path
import shutil
import uuid
import base64
from functools import wraps

from flask import Flask, request, jsonify

from svg_processor import SVGProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Global processor instance
processor = SVGProcessor()

def async_action(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

def cleanup_temp_dir(temp_dir: Path):
    """Clean up temporary directory"""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Failed to cleanup {temp_dir}: {e}")

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "svg-crop-api"})

@app.route("/crop-svg", methods=["POST"])
@async_action
async def crop_svg():
    """Process SVG URL and return ZIP file with cropped images encoded in base64."""
    if not request.json or "svg_url" not in request.json:
        return jsonify({"error": "Missing svg_url in request"}), 400

    svg_url = request.json["svg_url"]
    output_format = request.json.get("output_format", "png")

    # Create unique temporary directory
    temp_id = str(uuid.uuid4())[:8]
    temp_dir = Path(tempfile.gettempdir()) / f"svg_crop_{temp_id}"
    
    try:
        # Create temporary directory
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Processing SVG: {svg_url}")
        logger.info(f"Temporary directory: {temp_dir}")
        
        # Process SVG
        result = await processor.process_svg_async(
            svg_url,
            temp_dir,
            output_format
        )
        
        if not result["success"]:
            return jsonify({"error": result["error"]}), 400
        
        # Create ZIP file
        zip_path = temp_dir / f"cropped_images_{temp_id}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            crop_files = list(temp_dir.glob(f"crop_region*.{output_format}"))
            mask_files = list(temp_dir.glob("mask_region*.png"))
            
            for file_path in crop_files + mask_files:
                zipf.write(file_path, file_path.name)
                logger.info(f"Added to ZIP: {file_path.name}")
        
        if not crop_files:
            return jsonify({"error": "No cropped images were generated"}), 400
        
        zip_size = zip_path.stat().st_size
        logger.info(f"Created ZIP file: {zip_path} ({zip_size} bytes)")
        
        # Read ZIP file and encode to base64
        with open(zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()
            zip_base64 = base64.b64encode(zip_content).decode('utf-8')
        
        # Cleanup temporary directory
        cleanup_temp_dir(temp_dir)
        
        # Return ZIP file as base64
        return jsonify({
            "success": True,
            "filename": "cropped_images.zip",
            "file_base64": zip_base64,
            "file_size": zip_size,
            "regions_processed": result["regions_processed"],
            "images_downloaded": result["images_downloaded"]
        })
        
    except Exception as e:
        logger.error(f"Error processing SVG: {e}")
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API information"""
    return jsonify({
        "service": "SVG Crop API",
        "version": "1.0.0",
        "framework": "Flask",
        "endpoints": {
            "POST /crop-svg": "Process SVG and return cropped images as ZIP in base64 format",
            "GET /health": "Health check"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8877)
