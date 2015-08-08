import io
import base64
import random
import requests
import config
from glob import glob
from PIL import Image
from urllib import request, parse, error
from collections import namedtuple

# http://freeimages.pictures/api
image_url = 'http://freeimages.pictures/api/user/{}/'.format(config.IMAGES_API_KEY)
masks = glob('data/masks/*.png')


def image(name, url_only=False, force_mixture=False, mixture_size=(400,250)):
    # First try the entire name as the query
    url = fetch_image(name)
    if url is not None and not force_mixture:
        return url

    # Otherwise, blend an image from separate queries
    else:
        parts = [fetch_image(p) for p in name.split(' ')]
        parts = [p for p in parts if p is not None]

        if not parts:
            return '#'

        elif len(parts) == 1:
            img = parts[0]
            mask = Image.open(random.choice(masks))
            mimg = mask_images(img, img, mask, mixture_size)
            data = img_to_b64(mimg)

        else:
            parts = random.sample(parts, 2)
            mask = Image.open(random.choice(masks))
            mimg = mask_images(*parts, mask=mask, target_size=mixture_size)
            data = img_to_b64(mimg)

        if url_only:
            return upload_b64(data, title=name)

        return 'data:image/jpeg;base64,{}'.format(data)


def fetch_image(name):
    q = parse.quote(name)
    res = requests.get(image_url, headers={'User-Agent': 'Chrome'}, params={
        'keyword': q,
        'sources': 'flickr|wikimedia|pixabay|morguefile|google'
    })
    results = sum([d['result'] for d in res.json()['sources']], [])

    # Try results until we get an available image
    while results:
        url = results.pop()['preview_url'] # could also use url or thumb_url
        req = request.Request(url, headers={'User-Agent': 'Chrome'})
        try:
            request.urlopen(req)
            return url
        except error.HTTPError:
            continue


def download_image(url):
    req = request.Request(url, headers={'User-Agent': 'Chrome'})
    resp = request.urlopen(req)
    data = io.BytesIO(resp.read())
    return Image.open(data)


def blend_images(url1, url2, target_size=(400, 250)):
    images = []
    for url in [url1, url2]:
        img = download_image(url)
        img = img.convert('RGBA')
        images.append(img)

    cimages = []
    for img in images:
        img = resize_image(img, target_size)
        cimages.append(img)

    return Image.blend(cimages[0], cimages[1], 0.5)


def resize_image(img, target_size):
    Point = namedtuple('Point', ['x', 'y'])

    size = Point(*img.size)
    target_size = Point(*target_size)

    # Scale as needed
    x_scale = target_size.x/size.x
    y_scale = target_size.y/size.y
    scale_factor = max(x_scale, y_scale)
    scaled_size = Point(*[int(d*scale_factor) for d in size])
    img = img.resize(scaled_size)

    # Crop as needed
    if scaled_size.x == target_size.x:
        l, r = 0, target_size.x
    else:
        x_center = scaled_size.x/2
        l = int(x_center - target_size.x/2)
        r = int(x_center + target_size.x/2)

    if scaled_size.y == target_size.y:
        u, d = 0, target_size.y
    else:
        y_center = scaled_size.y/2
        u = int(y_center - target_size.y/2)
        d = int(y_center + target_size.y/2)

    return img.crop((l,u,r,d))


def mask_images(url1, url2, mask, target_size=(400, 250)):
    """
    Combine two images, then apply a mask onto a transparent background.
    """
    images = []
    for url in [url1, url2]:
        img = download_image(url)
        img = img.convert('RGBA')
        images.append(img)

    cimages = []
    for img in images:
        img = resize_image(img, target_size)
        cimages.append(img)

    mask = mask.convert('RGBA')
    mask = resize_image(mask, target_size)

    bimg = Image.blend(cimages[0], cimages[1], 0.5)
    back = Image.new('RGBA', target_size, color=1)

    return Image.composite(bimg, back, mask)



def img_to_b64(img, format='png'):
    buff = io.BytesIO()
    img.save(buff, format=format)
    return base64.b64encode(buff.getvalue())


def upload_b64(b64_data, title=''):
    res = requests.post('https://api.imgur.com/3/image',
                        headers={'Authorization': 'Client-ID {}'.format(config.IMGUR_CLIENT_ID)},
                        data={'image': b64_data, 'title': title})

    return res.json()['data']['link']
