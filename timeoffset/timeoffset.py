from tqdm import tqdm
from exif import Image
import argparse
from patharg import PathType
from glob import glob
from sys import stderr
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple
from shutil import copyfile
from os import path


jpg_extensions = ["JPG", "JPEG", "JFIF"]
raw_extensions = ["RAW", "RAF", "DNG", "DXF"]
all_extensions = jpg_extensions + raw_extensions
exif_dt_format = "%Y:%m:%d %H:%M:%S"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i",
                        action="append", required=True,
                        type=PathType(type='dir', abs=True, exists=True))
    parser.add_argument("--in-place", "-p",
                        default=True, action='store_true')
    parser.add_argument("--keep-original", "-k",
                        action='store_false', dest='in_place')
    parser.add_argument("--out-dir", "-o",
                        type=PathType(type='dir', abs=True, exists=True))
    parser.add_argument("--hours",
                        required=True,
                        type=str)
    parser.add_argument("--minutes",
                        default="0",
                        type=str)

    args = parser.parse_args()
    print(args)
    if not args.in_place:
        if args.out_dir is None:
            print("The output directory isn't set, but --keep-original was presented on the command line.")
            exit(1)
    args.hours=int(args.hours)
    args.minutes=int(args.minutes)

    print(f"Using a time offset of ({args.hours}h):({args.minutes})min")

    return args


def read_exif_datetime(path: Path) -> Tuple[datetime, Image]:
    with open(path, 'rb') as image_file:
        try:
            my_image = Image(image_file)
        except Exception as e:
            print(f"Failed to read EXIF data from {path}: {e}")
            exit(1)
    dt_original = my_image.datetime_original
    dt_format = datetime.strptime(dt_original, exif_dt_format)
    return (dt_format, my_image)


def scan_input_dirs(args: argparse.Namespace) -> List[Path]:
    found_files = []
    pbar = tqdm([Path(i) for i in args.input])
    for input_dir in pbar:
        pbar.write(f"Scanning input directory: {input_dir}")
        for ext in all_extensions:
            g = glob(pathname=f"**/*.{ext}", root_dir=input_dir, recursive=True)
            found_files.extend([input_dir.joinpath(f) for f in g])
    print(f"Found {len(found_files)} files")
    return sorted(found_files)


def apply_offset(args: argparse.Namespace, files: List[Path]):
    pbar = tqdm(files)
    offset = timedelta(hours=args.hours, minutes=args.minutes)
    for f in pbar:
        (photo_dt, exif) = read_exif_datetime(f)
        modified_dt = photo_dt + offset
        exif.datetime_original = modified_dt.strftime(exif_dt_format)
        if args.in_place:
            out_file = f
            pbar.write(f"{f}: {photo_dt} -> {modified_dt}")
        else:
            out_file = path.join(args.out_dir, f.name)
            pbar.write(f"{f}: {photo_dt} -> {modified_dt} [{out_file}]")
        with open(out_file, 'wb') as of:
            of.write(exif.get_file())

if __name__ == "__main__":
    args = parse_args()
    file_list = scan_input_dirs(args)
    apply_offset(args, file_list)
