import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from ultralytics import YOLO

def create_pascal_voc_xml(folder, filename, db_source, width, height, depth, objects):
    """
    Creates an XML string mimicking the Stanford Dogs Pascal VOC format
    """
    annotation = ET.Element('annotation')
    
    ET.SubElement(annotation, 'folder').text = str(folder)
    ET.SubElement(annotation, 'filename').text = str(filename)
    
    source = ET.SubElement(annotation, 'source')
    ET.SubElement(source, 'database').text = str(db_source)
    
    size = ET.SubElement(annotation, 'size')
    ET.SubElement(size, 'width').text = str(width)
    ET.SubElement(size, 'height').text = str(height)
    ET.SubElement(size, 'depth').text = str(depth)
    
    ET.SubElement(annotation, 'segment').text = '0'
    
    for obj in objects:
        object_elem = ET.SubElement(annotation, 'object')
        ET.SubElement(object_elem, 'name').text = str(obj['name'])
        ET.SubElement(object_elem, 'pose').text = 'Unspecified'
        ET.SubElement(object_elem, 'truncated').text = '0'
        ET.SubElement(object_elem, 'difficult').text = '0'
        
        bndbox = ET.SubElement(object_elem, 'bndbox')
        ET.SubElement(bndbox, 'xmin').text = str(int(obj['xmin']))
        ET.SubElement(bndbox, 'ymin').text = str(int(obj['ymin']))
        ET.SubElement(bndbox, 'xmax').text = str(int(obj['xmax']))
        ET.SubElement(bndbox, 'ymax').text = str(int(obj['ymax']))
        
    # Pretty print
    ET.indent(annotation, space="    ", level=0)
    return ET.tostring(annotation, encoding='unicode')

def process_images():
    base_dir = Path(__file__).resolve().parent.parent
    input_dir = base_dir / "data" / "bing"
    
    output_images_dir = base_dir / "data" / "stanford_dogs" / "Images"
    output_annotations_dir = base_dir / "data" / "stanford_dogs" / "Annotation"
    
    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_annotations_dir.mkdir(parents=True, exist_ok=True)
    
    # Load YOLO Model
    print("Loading YOLO model...")
    model = YOLO('yolo26m.pt')
    
    if not input_dir.exists():
        print(f"Error: Directory {input_dir} not found. Run bbid.py first.")
        return

    folders = sorted([f for f in input_dir.iterdir() if f.is_dir()])
    
    for folder_path in folders:
        folder_name = folder_path.name
        
        # Extrapolate prefix and breed from folder "n02085620-Chihuahua"
        if "-" not in folder_name:
            continue
        prefix, breed = folder_name.split("-", 1)
        
        # Make mirrored structure in the new dataset
        out_img_sub = output_images_dir / folder_name
        out_ann_sub = output_annotations_dir / folder_name
        out_img_sub.mkdir(parents=True, exist_ok=True)
        out_ann_sub.mkdir(parents=True, exist_ok=True)
        
        images = list(folder_path.glob("*.jpg"))
        if not images:
            continue
            
        print(f"\nProcessing {len(images)} images in {folder_name}...")
        
        for img_path in images:
            try:
                # Get inferences: classes=[16] isolates 'dog'
                results = model.predict(source=str(img_path), classes=[16], conf=0.3, verbose=False)
                result = results[0]
                
                # If no dogs found, skip
                if len(result.boxes) == 0:
                    print(f"  [SKIP] No dogs detected over 0.3: {img_path.name}")
                    continue
                
                # Image metadata
                img_width, img_height = result.orig_shape[1], result.orig_shape[0]  # YOLO orig_shape is (H, W)
                filename_no_ext = img_path.stem
                
                # Objects list for XML formatting
                detected_objects = []
                for box in result.boxes.xyxy:  # Extract absolute coordinates
                    xmin, ymin, xmax, ymax = box.tolist()
                    detected_objects.append({
                        'name': breed.capitalize(),
                        'xmin': xmin,
                        'ymin': ymin,
                        'xmax': xmax,
                        'ymax': ymax
                    })
                
                # Generate XML
                xml_content = create_pascal_voc_xml(
                    folder=prefix,
                    filename=filename_no_ext,
                    db_source="ImageNet database",
                    width=img_width,
                    height=img_height,
                    depth=3, # PIL RGB assumed
                    objects=detected_objects
                )
                
                # Save XML
                ann_file = out_ann_sub / filename_no_ext
                with open(ann_file, "w") as f:
                    f.write(xml_content)
                
                # Copy Image
                shutil.copy2(img_path, out_img_sub / img_path.name)
                
                print(f"  [OK] Saved {len(detected_objects)} dog(s): {img_path.name}")
                
            except Exception as e:
                print(f"  [ERROR] Failed to process {img_path.name}: {e}")

if __name__ == "__main__":
    process_images()
