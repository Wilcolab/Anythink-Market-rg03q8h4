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
import random
import numpy as np

# Get the base directory using the current file's location
BASE_DIR = Path(__file__).resolve().parent

# In-memory image storage using a dictionary
# Keys are unique IDs, values are base64 encoded image data
IMAGE_STORE = {}

def apply_black_white_filter(image: Image.Image) -> Image.Image:
    """
    Apply a true black and white conversion using proper luminance weighting.
    
    Args:
        image (Image.Image): Input PIL Image to be converted
        
    Returns:
        Image.Image: Black and white version of the input image
    """
    rgb_img = image.convert('RGB')
    width, height = rgb_img.size
    pixels = rgb_img.load()
    
    for py in range(height):
        for px in range(width):
            r, g, b = rgb_img.getpixel((px, py))
            # Use luminance formula for better black and white conversion
            # This gives more weight to green and less to blue, matching human perception
            luminance = int(0.299 * r + 0.587 * g + 0.114 * b)
            pixels[px, py] = (luminance, luminance, luminance)
    
    return rgb_img

def apply_vintage_filter(image: Image.Image) -> Image.Image:
    """
    Apply a vintage film effect with warm tones and vignette.
    
    Args:
        image (Image.Image): Input PIL Image to be processed
        
    Returns:
        Image.Image: Vintage-styled version of the input image
    """
    rgb_img = image.convert('RGB')
    width, height = rgb_img.size
    pixels = rgb_img.load()
    
    for py in range(height):
        for px in range(width):
            r, g, b = rgb_img.getpixel((px, py))
            
            # Add warm tone
            tr = int(r * 1.1)  # Increase red
            tg = int(g * 0.9)  # Decrease green
            tb = int(b * 0.8)  # Decrease blue
            
            # Add slight sepia tone
            tr = int(0.393 * tr + 0.769 * tg + 0.189 * tb)
            tg = int(0.349 * tr + 0.686 * tg + 0.168 * tb)
            tb = int(0.272 * tr + 0.534 * tg + 0.131 * tb)
            
            # Add vignette effect
            center_x = width / 2
            center_y = height / 2
            distance = ((px - center_x) ** 2 + (py - center_y) ** 2) ** 0.5
            max_distance = ((width/2) ** 2 + (height/2) ** 2) ** 0.5
            vignette = 1 - (distance / max_distance) * 0.5
            
            # Apply vignette
            tr = int(tr * vignette)
            tg = int(tg * vignette)
            tb = int(tb * vignette)
            
            # Ensure values don't exceed 255
            tr = min(255, max(0, tr))
            tg = min(255, max(0, tg))
            tb = min(255, max(0, tb))
            
            pixels[px, py] = (tr, tg, tb)
    
    return rgb_img

def apply_glitch_filter(image: Image.Image) -> Image.Image:
    """
    Apply a digital glitch effect with color channel shifting and noise.
    
    Args:
        image (Image.Image): Input PIL Image to be processed
        
    Returns:
        Image.Image: Glitch-styled version of the input image
    """
    rgb_img = image.convert('RGB')
    img_array = np.array(rgb_img)
    
    # Randomly shift color channels
    shift_amount = random.randint(5, 15)
    direction = random.choice(['left', 'right'])
    
    if direction == 'left':
        img_array[:, shift_amount:, :] = img_array[:, :-shift_amount, :]
    else:
        img_array[:, :-shift_amount, :] = img_array[:, shift_amount:, :]
    
    # Add random noise
    noise = np.random.normal(0, 25, img_array.shape).astype(np.uint8)
    img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    
    # Randomly shift some rows
    for i in range(0, img_array.shape[0], random.randint(10, 30)):
        shift = random.randint(-20, 20)
        if shift > 0:
            img_array[i, shift:, :] = img_array[i, :-shift, :]
        else:
            img_array[i, :shift, :] = img_array[i, -shift:, :]
    
    return Image.fromarray(img_array)

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
    "sepia": "Sepia tone effect",
    "black_white": "True black and white conversion",
    "vintage": "Vintage film effect",
    "glitch": "Digital glitch effect"
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
                pixels[px, py] = (255 - r, 255 - g, 255 - b)
        
        filtered_img = rgb_img
    elif selected_filter == "sepia":
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
                tr = min(255, tr)
                tg = min(255, tg)
                tb = min(255, tb)
                
                pixels[px, py] = (tr, tg, tb)
        
        filtered_img = rgb_img
    elif selected_filter == "black_white":
        filtered_img = apply_black_white_filter(img)
    elif selected_filter == "vintage":
        filtered_img = apply_vintage_filter(img)
    elif selected_filter == "glitch":
        filtered_img = apply_glitch_filter(img)
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