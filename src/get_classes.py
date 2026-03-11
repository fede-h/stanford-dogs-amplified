import csv
from pathlib import Path


def main():
    base_dir = Path(__file__).resolve().parent.parent
    annotation_dir = base_dir / "data" / "stanford_dogs" / "Annotation"
    output_path = base_dir / "data" / "classes.csv"

    rows = []
    for folder in sorted(annotation_dir.iterdir()):
        if not folder.is_dir():
            continue
        # folder name format: n02085620-Chihuahua
        prefix, breed = folder.name.split("-", maxsplit=1)
        file_count = sum(1 for f in folder.iterdir() if f.is_file())
        rows.append((breed.lower(), prefix, file_count))

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["breed", "prefix", "file_count"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} breeds to {output_path}")


if __name__ == "__main__":
    main()
