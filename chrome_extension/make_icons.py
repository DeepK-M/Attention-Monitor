from PIL import Image, ImageDraw

def make_icon(size, path):
    img  = Image.new('RGBA', (size, size), (13, 15, 26, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size//2, size//2
    r = int(size * 0.35)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(0, 229, 160, 255))
    img.save(path)
    print(f'Created {path}')

make_icon(16,  'icon16.png')
make_icon(48,  'icon48.png')
make_icon(128, 'icon128.png')
print('All icons created!')