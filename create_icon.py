from PIL import Image, ImageDraw, ImageFont
import os

def create_simple_icon():
    """Create a simple app icon"""
    # Create 256x256 image
    img = Image.new('RGBA', (256, 256), (70, 130, 180, 255))  # Steel blue background
    draw = ImageDraw.Draw(img)
    
    # Draw a simple "ALT" text
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text = "LocZ"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (256 - text_width) // 2
    y = (256 - text_height) // 2
    
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # Add a border
    draw.rectangle([10, 10, 245, 245], outline=(255, 255, 255), width=3)
    
    # Save as ICO
    img.save('app_icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (256,256)])
    print("✅ Icon created: app_icon.ico")

if __name__ == "__main__":
    create_simple_icon()
