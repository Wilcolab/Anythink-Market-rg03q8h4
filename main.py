from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageFilter, ImageEnhance
import io
import os
import base64
from pathlib import Path
import uuid
import uvicorn

# Get the base directory using the current file's location
BASE_DIR = Path(__file__).resolve().parent

# In-memory image storage using a dictionary
# Keys are unique IDs, values are base64 encoded image data
IMAGE_STORE = {}

app = FastAPI(title="Image Filter App")

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Available filters
FILTERS = {
    "grayscale": "Convert to grayscale",
    "blur": "Blur effect",
    "contour": "Contour effect",
    "detail": "Enhance details",
    "edge_enhance": "Edge enhancement",
    "emboss": "Emboss effect",
    "sharpen": "Sharpen image",
    "smooth": "Smooth image",
    "brightness": "Increase brightness",
    "contrast": "Increase contrast",
    "invert": "Invert colors",
    "sepia": "Sepia tone effect"
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "filters": FILTERS}
    )

@app.post("/upload")
async def upload_image(request: Request, image: UploadFile = File(...)):
    # Read the image into memory
    contents = await image.read()
    
    # Generate a unique ID for the image
    image_id = str(uuid.uuid4())
    
    # Convert to PIL Image for potential resizing/optimization
    img = Image.open(io.BytesIO(contents))
    
    # Convert to RGB if not already
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    # Optional: resize large images to reduce memory usage
    max_size = 1200
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size))
    
    # Save to memory buffer and convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Store in memory dictionary
    IMAGE_STORE[image_id] = img_base64
    
    return templates.TemplateResponse(
        "filter.html", 
        {
            "request": request, 
            "filters": FILTERS, 
            "image_id": image_id,
            "image_data": f"data:image/jpeg;base64,{img_base64}"
        }
    )

@app.get("/apply-filter")
async def get_filter_page(request: Request, image_id: str):
    # Get the image data from storage
    img_base64 = IMAGE_STORE.get(image_id)
    
    if not img_base64:
        return JSONResponse({"error": "Image not found"}, status_code=404)
    
    return templates.TemplateResponse(
        "filter.html", 
        {
            "request": request, 
            "filters": FILTERS, 
            "image_id": image_id,
            "image_data": f"data:image/jpeg;base64,{img_base64}"
        }
    )

@app.post("/api/apply-filter")
async def api_apply_filter(
    image_id: str = Form(...), 
    selected_filter: str = Form(...)
):
    # Get the image data from storage
    img_base64 = IMAGE_STORE.get(image_id)
    
    if not img_base64:
        return JSONResponse({"error": "Image not found"}, status_code=404)
    
    # Convert base64 to PIL Image
    img_data = base64.b64decode(img_base64)
    img = Image.open(io.BytesIO(img_data))
    
    # Apply the selected filter
    if selected_filter == "grayscale":
        filtered_img = img.convert("L").convert("RGB")
    elif selected_filter == "blur":
        filtered_img = img.filter(ImageFilter.BLUR)
    elif selected_filter == "contour":
        filtered_img = img.filter(ImageFilter.CONTOUR)
    elif selected_filter == "detail":
        filtered_img = img.filter(ImageFilter.DETAIL)
    elif selected_filter == "edge_enhance":
        filtered_img = img.filter(ImageFilter.EDGE_ENHANCE)
    elif selected_filter == "emboss":
        filtered_img = img.filter(ImageFilter.EMBOSS)
    elif selected_filter == "sharpen":
        filtered_img = img.filter(ImageFilter.SHARPEN)
    elif selected_filter == "smooth":
        filtered_img = img.filter(ImageFilter.SMOOTH)
    elif selected_filter == "brightness":
        enhancer = ImageEnhance.Brightness(img)
        filtered_img = enhancer.enhance(1.5)
    elif selected_filter == "contrast":
        enhancer = ImageEnhance.Contrast(img)
        filtered_img = enhancer.enhance(1.5)
    elif selected_filter == "invert":
        rgb_img = img.convert('RGB')
        width, height = rgb_img.size
        pixels = rgb_img.load()
        
        for py in range(height):
            for px in range(width):
                r, g, b = rgb_img.getpixel((px, py))
                
                tr = 25 - r
                tg = 25 - g
                tb = 25 - b
                
                pixels[px, py] = (tr, tg, tb)
        
        filtered_img = rgb_img
    elif selected_filter == "sepia":
        # Convert to RGB mode if it's not already
        rgb_img = img.convert('RGB')
        width, height = rgb_img.size
        pixels = rgb_img.load()
        
        for py in range(height):
            for px in range(width):
                r, g, b = rgb_img.getpixel((px, py))
                
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                
                # Ensure values don't exceed 255
                if tr > 255:
                    tr = 255
                if tg > 255:
                    tg = 255
                if tb > 255:
                    tb = 255
                    
                pixels[px, py] = (tr, tg, tb)
        
        filtered_img = rgb_img
    else:
        # No filter or unknown filter
        filtered_img = img
    
    # Save to memory buffer instead of file
    buffered = io.BytesIO()
    filtered_img.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return JSONResponse({
        "image_data": f"data:image/jpeg;base64,{img_str}",
        "filter_name": FILTERS.get(selected_filter, "Unknown")
    })

@app.post("/download")
async def download_image(
    image_data: str = Form(...),
    filter_name: str = Form(...)
):
    # Remove prefix if present
    if "data:image/jpeg;base64," in image_data:
        image_data = image_data.replace("data:image/jpeg;base64,", "")
    
    # Decode base64 string
    try:
        image_bytes = base64.b64decode(image_data)
    except:
        return JSONResponse({"error": "Invalid image data"}, status_code=400)
    
    # Create filename
    filename = f"filtered_image_{filter_name}.jpg"
    
    # Return image data directly as a response
    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=31337, reload=True) 