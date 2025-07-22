# SVG Crop API

FastAPI service that processes SVG files with precise image cropping capabilities. Given an SVG URL, the API downloads the SVG and its referenced images, performs precise coordinate transformations, and returns a ZIP file containing cropped images and masks.

## Features

- ✅ **Precise Cropping**: Uses transformation matrices for pixel-perfect crops
- ✅ **Multiple Formats**: Supports PNG and JPEG output
- ✅ **Automatic Detection**: Dynamically detects any number of clipping regions
- ✅ **Temporary Processing**: No persistent storage, everything is processed in memory
- ✅ **ZIP Output**: Returns all results in a convenient ZIP file
- ✅ **Docker Ready**: Containerized for easy deployment

## Quick Start

### Local Development

1. **Clone and setup:**
```bash
git clone <repository>
cd svg-crop-api
pip install -r requirements.txt
```

2. **Run the API:**
```bash
python app.py
```

3. **Test the API:**
```bash
curl -X POST "http://localhost:8877/crop-svg" \
     -H "Content-Type: application/json" \
     -d '{"svg_url": "https://example.com/mockup.svg", "output_format": "png"}' \
     --output cropped_images.zip
```

### Docker Deployment

1. **Build the image:**
```bash
docker build -t svg-crop-api .
```

2. **Run the container:**
```bash
docker run -p 8877:8877 svg-crop-api
```

### VPS Deployment

1. **Clone on your VPS:**
```bash
git clone <repository>
cd svg-crop-api
```

2. **Build and run:**
```bash
docker build -t svg-crop-api .
docker run -d -p 8877:8877 --name svg-crop-api svg-crop-api
```

## API Endpoints

### POST /crop-svg
Process an SVG file and return cropped images as ZIP.

**Request Body:**
```json
{
  "svg_url": "https://example.com/mockup.svg",
  "output_format": "png"
}
```

**Response:** ZIP file containing cropped images and masks.

### GET /health
Health check endpoint.

### GET /
API information and usage examples.

## Usage Examples

### Python Client
```python
import requests

response = requests.post(
    "http://localhost:8877/crop-svg",
    json={
        "svg_url": "https://example.com/mockup.svg",
        "output_format": "png"
    }
)

if response.status_code == 200:
    with open("cropped_images.zip", "wb") as f:
        f.write(response.content)
    print("ZIP file saved!")
```

### JavaScript/Node.js
```javascript
const response = await fetch('http://localhost:8877/crop-svg', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    svg_url: 'https://example.com/mockup.svg',
    output_format: 'png'
  })
});

if (response.ok) {
  const blob = await response.blob();
  // Save or process the ZIP file
}
```

## License

This project is provided as-is for processing SVG mockups with precise image cropping capabilities.
