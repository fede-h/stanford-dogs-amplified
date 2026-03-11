import urllib.request
import tarfile
import sys
from pathlib import Path

def reporthook(n, b, t):
    if t > 0:
        sys.stdout.write(f"\rDownloading... {min(100, int(n * b * 100 / t))}%")
        sys.stdout.flush()

def load_data(base_dir):
    target_dir = base_dir / "data/stanford_dogs"
    target_dir.mkdir(parents=True, exist_ok=True)
    base_url = "http://vision.stanford.edu/aditya86/ImageNetDogs/{}"
    
    for f in ["images.tar", "annotation.tar"]:
        p = target_dir / f
        if not p.exists():
            print(f"\nDownloading {f}...")
            urllib.request.urlretrieve(base_url.format(f), p, reporthook)
            print()
        print(f"Extracting {f}...")
        with tarfile.open(p) as tar:
            tar.extractall(target_dir)
        print(f"Cleaning up {f}...")
        p.unlink()

def main():
    base_dir = Path(__file__).resolve().parent.parent
    load_data(base_dir)

if __name__ == "__main__":
    main()
