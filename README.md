# Stanford Dogs Augmentation

A complete computer vision data pipeline to fetch, clean, and augment the Stanford Dogs dataset using automated web scraping and YOLO-based bounding box detection. 

The goal of this project is to allow for the dynamic expansion of the [Stanford Dogs dataset](http://vision.stanford.edu/aditya86/ImageNetDogs/) by downloading new images from Bing, filtering out bad/fake images using YOLO, and injecting the survivors into the dataset with formatted Pascal VOC XML annotations, as in the original dataset. Original train and test splits are deprecated.

## Workflow pipeline and manual

### 1. Download the Base Dataset
Initialize the project by downloading the base Stanford Dogs dataset. This builds the fundamental folder structure (`data/stanford_dogs/...`) and extracts `images.tar` and `annotation.tar`.
```bash
python src/load_dataset.py
```

### 2. Generate Classes CSV
Parse the Annotations directory to catalog every breed and their respective ImageNet ID prefix into a CSV file. `bbid.py` uses this CSV to know what to search for.
```bash
python src/get_classes.py
```
*Output: `data/classes.csv`*

### 3. Bulk Scraping with `bbid.py`
Download new images from Bing based on the CSV. The script requests specific search terms (e.g., `'[breed] dog photo'`), standardizes the downloads into strict RGB JPGs (resolving alpha channels and `webp`/`avif` formats), and places them into categorized folders (e.g., `data/bing/n02085620-Chihuahua`).

**Suggested command:**
```bash
python src/bbid.py -f data/classes.csv -o data/bing --limit 200 --filters "+filterui:photo-photo"
```
The limit parameter is the amount of raw new images that are downloaded for each breed. In this case the limit is set to 200, but you can try with more agressive approaches. The downside of this is expected poorer quality data.
The filters are set to only download photos (detected format for BING).

### 4. YOLO Object Detection & Data Injection
Process the newly downloaded bulk images. `yolo_clean.py` loops through `data/bing/` and infers bounding boxes using YOLO26m object detection model.

If a bounding box for a "Dog" is found with a confidence score > 0.3:
1. The image is officially admitted and copied back into the dataset structure (`data/stanford_dogs/Images`).
2. A strict Pascal VOC formatting XML annotation is generated mirroring the Stanford structural layout (`<annotation>...<bndbox>...</bndbox>...</annotation>`).
3. The XML is uploaded directly alongside the original tags in `data/stanford_dogs/Annotation`.

```bash
python src/yolo_clean.py
```
*Any image that fails to trigger a positive dog detection is automatically skipped and kept out of the clean dataset.*
