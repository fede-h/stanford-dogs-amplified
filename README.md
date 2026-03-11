# Stanford Dogs Augmentation

### Bing Image Filters Cheatsheet
You can use these filters with the `--filters` argument (e.g., `--filters "+filterui:photo-photo +filterui:imagesize-large"`):

**Image Type:**
* `+filterui:photo-photo` : Photograph (Highly recommended for datasets)
* `+filterui:photo-clipart` : Clipart
* `+filterui:photo-lineart` : Line drawing
* `+filterui:photo-transparent`: Transparent background

**Aspect Ratio:**
* `+filterui:aspect-square` : Square (1:1)
* `+filterui:aspect-wide`   : Wide landscape (16:9, etc.)
* `+filterui:aspect-tall`   : Tall portrait

**Image Size:**
* `+filterui:imagesize-large`  : Large
* `+filterui:imagesize-medium` : Medium
* `+filterui:imagesize-small`  : Small

**Color:**
* `+filterui:color2-color` : Only color images
* `+filterui:color2-bw`    : Only black & white images

***

suggested bbid command:

.venv/bin/python3 src/bbid.py -f data/classes.csv -o data/bing --limit 1000 --filters "+filterui:photo-photo"
