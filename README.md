# SVG Crop API (Flask Version)

FastAPI service that processes SVG files, extracts images, creates masks, and returns precisely cropped images as a ZIP file encoded in base64 format. The service is built with Flask and can be run with Docker.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [How to Run](#how-to-run)
  - [1. Using Docker (Recommended)](#1-using-docker-recommended)
  - [2. Running Locally](#2-running-locally)
- [API Usage](#api-usage)
  - [Endpoint: `POST /crop-svg`](#endpoint-post-crop-svg)
  - [Request Body](#request-body)
  - [Response Body](#response-body)
- [Examples](#examples)
  - [cURL](#curl)
  - [Python](#python)
  - [JavaScript/Node.js](#javascriptnodejs)

## Features

- **SVG Processing**: Downloads an SVG from a URL and parses its content.
- **Image Extraction**: Automatically downloads all remote images (`<image>`) referenced in the SVG.
- **Precise Cropping**: Uses `clipPath` coordinates and matrix transformations from the SVG to perform precise, pixel-perfect crops on the images.
- **Mask Generation**: Creates black and white masks corresponding to each cropped region.
- **Base64 ZIP Output**: Returns a single ZIP file containing all cropped images and masks, encoded in base64 for easy handling in JSON.
- **Async Processing**: Leverages `asyncio` and `aiohttp` for non-blocking download of images.
- **Dockerized**: Comes with a `Dockerfile` for easy deployment.

## Requirements

- Python 3.9+
- Docker (optional, but recommended)

## How to Run

### 1. Using Docker (Recommended)
This is the easiest way to run the API.

1.  **Build the Docker image:**
    ```bash
    docker build -t svg-crop-api .
    ```
2.  **Run the container:**
    ```bash
    docker run -d -p 8877:8877 --name svg-crop-api svg-crop-api
    ```
3.  **Test the API:**
    ```bash
    curl -X POST "http://localhost:8877/crop-svg" \
         -H "Content-Type: application/json" \
         -d '{"svg_url": "YOUR_SVG_URL_HERE"}'
    ```

### 2. Running Locally

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Flask app:**
    For development:
    ```bash
    flask run --host=0.0.0.0 --port=8877
    ```
    For production (with Gunicorn):
    ```bash
    gunicorn --bind 0.0.0.0:8877 --workers 4 app:app
    ```

## API Usage

### Endpoint: `POST /crop-svg`
Processes an SVG from a URL and returns a ZIP file with cropped images.

-   **Method**: `POST`
-   **URL**: `/crop-svg`
-   **Content-Type**: `application/json`

### Request Body
```json
{
  "svg_url": "https://example.com/path/to/your/image.svg",
  "output_format": "png"
}
```
-   `svg_url` (string, required): The public URL of the SVG file to process.
-   `output_format` (string, optional): The output format for cropped images. Can be `"png"` or `"jpeg"`. Defaults to `"png"`.

### Response Body
On success (`200 OK`), the API returns a JSON object:
```json
{
    "success": true,
    "filename": "cropped_images.zip",
    "file_base64": "UEsDBBQAAAAIAM... (base64 encoded string)",
    "file_size": 12345,
    "regions_processed": 5,
    "images_downloaded": 3
}
```

## Examples

### cURL
```bash
curl -X POST "http://localhost:8877/crop-svg" \
     -H "Content-Type: application/json" \
     -d '{"svg_url": "https://example.com/your-svg.svg", "output_format": "jpeg"}'
```

### Python
```python
import requests
import base64

response = requests.post(
    "http://localhost:8877/crop-svg",
    json={
        "svg_url": "https://example.com/your-svg.svg",
        "output_format": "png"
    }
)

if response.status_code == 200:
    data = response.json()
    zip_content = base64.b64decode(data["file_base64"])
    with open("cropped_images.zip", "wb") as f:
        f.write(zip_content)
    print("ZIP file saved successfully.")
else:
    print(f"Error: {response.text}")
```

### JavaScript/Node.js
```javascript
const fetch = require('node-fetch');
const fs = require('fs');

async function getCroppedImages() {
    const response = await fetch('http://localhost:8877/crop-svg', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ svg_url: 'https://example.com/your-svg.svg' })
    });
    
    const data = await response.json();
    
    if (data.success) {
        const buffer = Buffer.from(data.file_base64, 'base64');
        fs.writeFileSync('cropped_images.zip', buffer);
        console.log('ZIP file saved.');
    } else {
        console.error('API Error:', data.error);
    }
}

getCroppedImages();
```
