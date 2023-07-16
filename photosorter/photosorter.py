from tqdm import tqdm
from exif import Image
import argparse
from patharg import PathType
from glob import glob
from pathlib import Path
from typing import List
from datetime import datetime


jpg_extensions = ["JPG", "JPEG", "JFIF"]
raw_extensions = ["RAW", "RAF", "DNG", "DXF"]
exif_dt_format = "%Y:%m:%d %H:%M:%S"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", action="append", required=True, type=PathType(type='dir', abs=True, exists=True))
    parser.add_argument("--output", "-o", action="append", required=True, type=PathType(type='dir', abs=True, exists=True)),
    parser.add_argument('--split-raw', "-s", default=True, action='store_true')
    parser.add_argument("--no-split-raw", "-n", action='store_false', dest="split_raw"),
    parser.add_argument("--jpg-dir", default="JPG", type=str)
    parser.add_argument("--raw-dir", default="RAW", type=str)
    parser.add_argument("--rename-files", default=True, action='store_true')
    parser.add_argument("--no-rename-files", dest="rename_files", action='store_false')
    args = parser.parse_args()
    print(args)
    return args

class FoundFile:
    original_jpg_path: Path
    original_raw_path: Path
    datetime: str
    target_directory: str

    def __init__(self, original_jpg, original_raw, datetime, target_directory):
        self.original_jpg_path = original_jpg
        self.original_raw_path = original_raw
        self.datetime = datetime
        self.target_directory = target_directory

def scan_input_dirs(args: argparse.Namespace):
    found_jpg = []
    found_raw = []
    pbar = tqdm([Path(i) for i in args.input])
    for input_dir in pbar:
        pbar.write(f"Scanning input directory: {input_dir}")
        jpg_list = []
        for jpg_ext in jpg_extensions:
            g = glob(pathname=f"**/*.{jpg_ext}", root_dir=input_dir, recursive=True)
            jpg_list.extend([input_dir.joinpath(f) for f in g])
        raw_list = []
        for raw_ext in jpg_extensions:
            g = glob(pathname=f"**/*.{raw_ext}", root_dir=input_dir, recursive=True)
            raw_list.extend([input_dir.joinpath(f) for f in g])
        pbar.write(f"Found {len(jpg_list)} JPGs and {len(raw_list)} RAWs")

        found_jpg.extend(jpg_list)
        found_jpg.sort()

        found_raw.extend(raw_list)
        found_raw.sort()

    print(f"In total, found {len(found_jpg)} JPGs and {len(found_jpg)} RAWs")
    return (found_jpg, found_raw)

def read_exif_datetime(path: Path) -> datetime:
    with open(path, 'rb') as image_file:
        my_image = Image(image_file)
    dt_original = my_image.datetime_original
    dt_format = datetime.strptime(dt_original, exif_dt_format)
    return dt_format

def gather_files(jpg_list: List[Path], raw_list: List[Path]):
    found_files: List[FoundFile] = []
    jpg_tqdm = tqdm(jpg_list)
    jpg_tqdm.write("Scanning JPG files")
    for jpg in jpg_tqdm:
        found_jpg_item = {}
        jpg_datetime = read_exif_datetime(jpg)
        matching_raw = [r for r in raw_list if r.stem == jpg.stem and r.parent == jpg.parent]
        if len(matching_raw) == 1:
            out_dir = f"{jpg_datetime.year}"{jpg_datetime.month:02d}"
            found_files.append(FoundFile(jpg, matching_raw[0], jpg_datetime, "test"))
            raw_list.remove(matching_raw[0]) # Remove the matching RAW file from the list, since the match is 1:1
        else:
            pass



if __name__ == "__main__":
    args = parse_args()
    (jpg_list, raw_list) = scan_input_dirs(args)
    file_list = gather_files(jpg_list, raw_list)