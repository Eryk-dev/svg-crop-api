#!/usr/bin/env python3
"""
SVG Crop API (Flask version)

Service that processes SVG files, extracts images, creates masks,
and returns precisely cropped images as a ZIP file encoded in base64.
"""

import asyncio
import logging
import tempfile
import zipfile
from pathlib import Path
import shutil
import uuid
import base64

from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest

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


def cleanup_temp_dir(temp_dir: Path):
    """Remove a temporary directory recursively."""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.info("Cleaned up temporary directory: %s", temp_dir)
    except Exception as exc:
        logger.error("Failed to cleanup %s: %s", temp_dir, exc)


@app.route('/health', methods=['GET'])
def health_check():
    """Health-check endpoint."""
    return {"status": "healthy", "service": "svg-crop-api"}


@app.route('/crop-svg', methods=['POST'])
def crop_svg():
    """Process SVG URL and return ZIP file (base64 encoded)."""
    data = request.get_json(force=True, silent=True)
    if not data or 'svg_url' not in data:
        raise BadRequest('JSON body must include "svg_url".')

    svg_url = data['svg_url']
    output_format = data.get('output_format', 'png').lower()
    if output_format not in ('png', 'jpeg'):
        raise BadRequest('output_format must be "png" or "jpeg"')

    temp_id = str(uuid.uuid4())[:8]
    temp_dir = Path(tempfile.gettempdir()) / f"svg_crop_{temp_id}"

    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Processing SVG: %s", svg_url)
        logger.info("Temporary directory: %s", temp_dir)

        # Run async SVG processing in a synchronous context
        result = asyncio.run(
            processor.process_svg_async(svg_url, temp_dir, output_format)
        )

        if not result["success"]:
            cleanup_temp_dir(temp_dir)
            return jsonify({"success": False, "error": result["error"]}), 400

        zip_path = temp_dir / f"cropped_images_{temp_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            crop_files = list(temp_dir.glob(f"crop_region*.{output_format}"))
            mask_files = list(temp_dir.glob("mask_region*.png"))

            for file_path in crop_files + mask_files:
                zipf.write(file_path, file_path.name)
                logger.info("Added to ZIP: %s", file_path.name)

        if not crop_files:
            cleanup_temp_dir(temp_dir)
            return jsonify({"success": False, "error": "No cropped images generated"}), 400

        zip_size = zip_path.stat().st_size
        with zip_path.open('rb') as f_zip:
            zip_base64 = base64.b64encode(f_zip.read()).decode('utf-8')

        # Build response
        response_body = {
            "success": True,
            "filename": "cropped_images.zip",
            "file_base64": zip_base64,
            "file_size": zip_size,
            "regions_processed": result["regions_processed"],
            "images_downloaded": result["images_downloaded"],
        }

        return jsonify(response_body)

    except BadRequest:
        raise  # Propagate to Flask error handler
    except Exception as exc:
        logger.error("Error processing SVG: %s", exc)
        return jsonify({"success": False, "error": "Internal server error"}), 500
    finally:
        cleanup_temp_dir(temp_dir)


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return {
        "service": "SVG Crop API",
        "version": "1.0.0",
        "endpoints": {
            "POST /crop-svg": "Process SVG and return cropped images as ZIP in base64 format",
            "GET /health": "Health check"
        }
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8877, debug=False)
