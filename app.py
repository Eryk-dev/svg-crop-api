#!/usr/bin/env python3
"""
SVG Crop API

FastAPI service that processes SVG files, extracts images, creates masks,
and returns precisely cropped images as a ZIP file encoded in base64 format.
"""

import asyncio
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any
import shutil
import uuid
import base64

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import uvicorn

from svg_processor import SVGProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="SVG Crop API",
    description="API for processing SVG files and extracting precisely cropped images",
    version="1.0.0"
)

# Request models
class SVGProcessRequest(BaseModel):
    svg_url: HttpUrl
    output_format: str = "png"  # png or jpeg

# Global processor instance
processor = SVGProcessor()

def cleanup_temp_dir(temp_dir: Path):
    """Clean up temporary directory in background"""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Failed to cleanup {temp_dir}: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "svg-crop-api"}

@app.post("/crop-svg")
async def crop_svg(request: SVGProcessRequest, background_tasks: BackgroundTasks):
    """Process SVG URL and return ZIP file with cropped images encoded in base64."""
    # Create unique temporary directory
    temp_id = str(uuid.uuid4())[:8]
    temp_dir = Path(tempfile.gettempdir()) / f"svg_crop_{temp_id}"
    
    try:
        # Create temporary directory
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Processing SVG: {request.svg_url}")
        logger.info(f"Temporary directory: {temp_dir}")
        
        # Process SVG
        result = await processor.process_svg_async(
            str(request.svg_url),
            temp_dir,
            request.output_format
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Create ZIP file
        zip_path = temp_dir / f"cropped_images_{temp_id}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all cropped images to ZIP
            crop_files = list(temp_dir.glob(f"crop_region*.{request.output_format}"))
            mask_files = list(temp_dir.glob("mask_region*.png"))
            
            for file_path in crop_files + mask_files:
                zipf.write(file_path, file_path.name)
                logger.info(f"Added to ZIP: {file_path.name}")
        
        if not crop_files:
            raise HTTPException(status_code=400, detail="No cropped images were generated")
        
        zip_size = zip_path.stat().st_size
        logger.info(f"Created ZIP file: {zip_path} ({zip_size} bytes)")
        
        # Read ZIP file and encode to base64
        with open(zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()
            zip_base64 = base64.b64encode(zip_content).decode('utf-8')
        
        # Schedule cleanup for after response is sent
        background_tasks.add_task(cleanup_temp_dir, temp_dir)
        
        # Return ZIP file as base64
        return JSONResponse(
            content={
                "success": True,
                "filename": "cropped_images.zip",
                "file_base64": zip_base64,
                "file_size": zip_size,
                "regions_processed": result["regions_processed"],
                "images_downloaded": result["images_downloaded"]
            },
            headers={
                "Content-Type": "application/json"
            }
        )
        
    except HTTPException:
        cleanup_temp_dir(temp_dir)
        raise
    except Exception as e:
        logger.error(f"Error processing SVG: {e}")
        cleanup_temp_dir(temp_dir)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "SVG Crop API",
        "version": "1.0.0",
        "endpoints": {
            "POST /crop-svg": "Process SVG and return cropped images as ZIP in base64 format",
            "GET /health": "Health check"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
