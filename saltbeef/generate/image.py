import io
import json
import base64
import random
import requests
import config
from PIL import Image
from urllib import request, parse, error
from collections import namedtuple

# https://developers.google.com/image-search/v1/jsondevguide?hl=en
image_url = 'https://ajax.googleapis.com/ajax/services/search/images?v=1.0&safe=active&q='


def image(name, url_only=False, force_mixture=False):
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
            return parts[0]

        else:
            parts = random.sample(parts, 2)
            data = blend_images(*parts)

            if url_only:
                res = requests.post('https://api.imgur.com/3/image',
                                    headers={'Authorization': 'Client-ID {}'.format(config.IMGUR_CLIENT_ID)},
                                    data={'image': data, 'title': name})

                return res.json()['data']['link']

            return 'data:image/jpeg;base64,{}'.format(data)


def fetch_image(name):
    q = parse.quote(name)
    url = image_url + q
    req = request.Request(url, headers={'User-Agent': 'Chrome'})
    resp = request.urlopen(req)
    body = resp.read()
    results = json.loads(body.decode('utf-8'))['responseData']['results']

    # Try results until we get an available image
    while results:
        url = results.pop()['url']
        req = request.Request(url, headers={'User-Agent': 'Chrome'})
        try:
            resp = request.urlopen(req)
            return url
        except error.HTTPError:
            continue


def blend_images(url1, url2):
    # TO DO clean this up
    Point = namedtuple('Point', ['x', 'y'])

    images = []
    for url in [url1, url2]:
        req = request.Request(url, headers={'User-Agent': 'Chrome'})
        resp = request.urlopen(req)
        data = io.BytesIO(resp.read())
        img = Image.open(data)
        images.append(img)

    cimages = []
    for img in images:
        size = Point(*img.size)
        target_size = Point(400, 250)

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

        img = img.crop((l,u,r,d))
        cimages.append(img)

    cimages[0] = cimages[0].convert('RGBA')
    cimages[1] = cimages[1].convert('RGBA')
    fimg = Image.blend(cimages[0], cimages[1], 0.5)
    buff = io.BytesIO()
    fimg.save(buff, format='jpeg')
    return base64.b64encode(buff.getvalue())
