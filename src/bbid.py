#!/usr/bin/env python3
import argparse
import hashlib

import os
import pickle
import posixpath
import re
import signal
import socket
import ssl
import threading
import time
import urllib.parse
import urllib.request
from io import BytesIO
from PIL import Image

import filetype


# config
socket.setdefaulttimeout(10)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

output_dir = 'data/bing'  # default output dir
tried_urls = []
image_md5s = {}
in_progress = 0
urlopenheader = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.bing.com/'
}


# Naive URL encoding
def _encode_url(url):
    scheme, netloc, path, query, fragment = list(urllib.parse.urlsplit(url))

    path = urllib.parse.quote(path)  # path
    query = urllib.parse.quote_plus(query)  # query
    fragment = urllib.parse.quote(fragment)  # fragment

    encoded_url = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))

    return encoded_url


def download(pool_sema: threading.Semaphore, img_sema: threading.Semaphore, url: str, output_dir: str, limit: int, prefix: str = None):
    global tried_urls
    global image_md5s
    global in_progress
    global urlopenheader
    
    # Early out if limit reached before this thread even acquires processing power
    if limit is not None and len(tried_urls) >= limit:
        return
        
    if url in tried_urls:
        print('SKIP: Already checked url, skipping')
        return
    pool_sema.acquire()
    in_progress += 1
    acquired_img_sema = False

    path = urllib.parse.urlsplit(url).path
    name, _ = os.path.splitext(posixpath.basename(path))
    if not name:
        # if path and name are empty (e.g. https://sample.domain/abcd/?query)
        name = hashlib.md5(url.encode('utf-8')).hexdigest()
    name = name.strip()[:36].strip()

    try:
        url.encode('ascii')
    except UnicodeEncodeError:  # the url contains non-ascii characters
        url = _encode_url(url)

    try:
        request = urllib.request.Request(url, None, urlopenheader)
        image = urllib.request.urlopen(request, context=ctx).read()
        
        kind = filetype.guess(image)
        if kind is None:
            print('SKIP: Invalid image, not saving ' + name)
            return

        # Attach a file extension based on an image header
        ext = kind.extension
        if ext == 'jpeg':
            ext = 'jpg'

        md5_key = hashlib.md5(image).hexdigest()
        if md5_key in image_md5s:
            print('SKIP: Image is a duplicate of ' + image_md5s[md5_key] + ', not saving ' + md5_key)
            return

        img_sema.acquire()
        acquired_img_sema = True
        
        if limit is not None and len(tried_urls) >= limit:
            return

        if prefix is not None:
            i = 1
            filename = f"{prefix}_1_{i}.jpg"
            while os.path.exists(os.path.join(output_dir, filename)):
                if hashlib.md5(open(os.path.join(output_dir, filename), 'rb').read()).hexdigest() == md5_key:
                    print('SKIP: Already downloaded ' + filename + ', not saving')
                    return
                i += 1
                filename = f"{prefix}_1_{i}.jpg"
        else:
            filename = name + '.jpg'
            i = 0
            while os.path.exists(os.path.join(output_dir, filename)):
                if hashlib.md5(open(os.path.join(output_dir, filename), 'rb').read()).hexdigest() == md5_key:
                    print('SKIP: Already downloaded ' + filename + ', not saving')
                    return
                i += 1
                filename = "%s-%d.jpg" % (name, i)

        image_md5s[md5_key] = filename

        out_path = os.path.join(output_dir, filename)
        pil_image = Image.open(BytesIO(image))
        
        if pil_image.mode in ("RGBA", "P"):
            pil_image = pil_image.convert("RGB")
            
        pil_image.save(out_path, format="JPEG", quality=95)
        
        print(" OK : " + filename)
        tried_urls.append(url)
    except Exception as e:
        print("FAIL: " + name, str(e))
    finally:
        pool_sema.release()
        if acquired_img_sema:
            img_sema.release()
        in_progress -= 1


def fetch_images_from_keyword(pool_sema: threading.Semaphore, img_sema: threading.Semaphore, keyword: str,
                              output_dir: str, filters: str, limit: int, prefix: str = None):
    global tried_urls
    global image_md5s
    global in_progress
    global urlopenheader
    current = 1
    last = ''
    active_threads = []
    
    while True:
        time.sleep(0.1)

        request_url = 'https://www.bing.com/images/async?q=' + urllib.parse.quote_plus(keyword) + '&first=' + str(
            current) + '&count=35&qft=' + ('' if filters is None else filters)
        request = urllib.request.Request(request_url, None, headers=urlopenheader)
        response = urllib.request.urlopen(request, context=ctx)
        html = response.read().decode('utf8')
        links = re.findall('murl&quot;:&quot;(.*?)&quot;', html)
        try:
            for index, link in enumerate(links):
                if limit is not None and len(tried_urls) >= limit:
                    break
                t = threading.Thread(target=download, args=(pool_sema, img_sema, link, output_dir, limit, prefix))
                t.start()
                active_threads.append(t)
                current += 1
                
            if limit is not None and len(tried_urls) >= limit:
                break
                
            if not links or links[-1] == last:
                break
            last = links[-1]
            
        except IndexError:
            print('FAIL: No search results for "{0}"'.format(keyword))
            break
            
    for t in active_threads:
        t.join()


def backup_history(*args):
    global output_dir
    global tried_urls
    global image_md5s
    global in_progress
    global urlopenheader
    download_history = open(os.path.join(output_dir, 'download_history.pickle'), 'wb')
    pickle.dump(tried_urls, download_history)
    copied_image_md5s = dict(
        image_md5s)  # We are working with the copy, because length of input variable for pickle must not be changed during dumping
    pickle.dump(copied_image_md5s, download_history)
    download_history.close()
    print('history_dumped')
    if args:
        exit(0)


def main():
    global output_dir
    global tried_urls
    global image_md5s
    global in_progress
    global urlopenheader
    parser = argparse.ArgumentParser(description='Bing image bulk downloader')
    parser.add_argument('search_string', nargs="+", help='Keyword to search')
    parser.add_argument('-f', '--search-file', action='store_true', help='use search-string as a path to a file containing search strings line by line',
                        required=False)
    parser.add_argument('-o', '--output', help='Output directory', required=False)
    parser.add_argument('-a', '--adult-filter-off', help='Disable adult filter', action='store_true', required=False)
    parser.add_argument('--filters',
                        help='Any query based filters you want to append when searching for images, e.g. +filterui:license-L1', default='',
                        required=False)
    parser.add_argument('--limit', help='Make sure not to search for more than specified amount of images.',
                        required=False, type=int)
    parser.add_argument('-t', '--threads', help='Number of threads', type=int, default=10)
    args = parser.parse_args()
    print(vars(args))
    args.search_string = ' '.join(args.search_string)

    if args.output:
        output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_dir_origin = output_dir
    signal.signal(signal.SIGINT, backup_history)
    try:
        download_history = open(os.path.join(output_dir, 'download_history.pickle'), 'rb')
        tried_urls = pickle.load(download_history)
        image_md5s = pickle.load(download_history)
        download_history.close()
    except (OSError, IOError):
        tried_urls = []
    if args.adult_filter_off:
        urlopenheader['Cookie'] = 'SRCHHPGUSR=ADLT=OFF'
    pool_sema = threading.BoundedSemaphore(args.threads)
    img_sema = threading.Semaphore()

    
    if not args.search_file:
        fetch_images_from_keyword(pool_sema, img_sema, args.search_string, output_dir, args.filters, args.limit)
    else:
        import csv
        try:
            with open(args.search_string, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None) # skip header
                for row in reader:
                    breed = row[0].strip()
                    prefix = row[1].strip()
                    
                    # folder matching Stanford Dogs Annotation style
                    folder_name = f"{prefix}-{breed.capitalize()}"
                    output_sub_dir = os.path.join(output_dir_origin, folder_name)
                    
                    if not os.path.exists(output_sub_dir):
                        os.makedirs(output_sub_dir)
                        
                    # search using a more descriptive keyword
                    # Replacing underscores with spaces, appending ' dog' can help Bing find specific breeds
                    search_term = breed.replace('_', ' ') + " dog photo"
                    
                    # reset the tried_urls state per keyword to not stop after the very first limit is hit
                    tried_urls = []
                    
                    print(f"\nFetching images for: {search_term} -> {output_sub_dir}")
                    fetch_images_from_keyword(pool_sema, img_sema, search_term, output_sub_dir, args.filters, args.limit, prefix)
                    backup_history()
                    time.sleep(2)
        except (OSError, IOError) as e:
            print("FAIL: Couldn't open or process file {}: {}".format(args.search_string, e))
            exit(1)


if __name__ == "__main__":
    main()
