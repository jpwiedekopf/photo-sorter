from tqdm import tqdm
from exif import Image
import argparse
from patharg import PathType
from glob import glob
from pathlib import Path
from typing import List
from datetime import datetime
from shutil import copyfile
from sys import stderr


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
    target_directory: Path
    copy_filenames: List[Path]
    copy_raw: List[Path]

    def __init__(self, original_jpg, original_raw, datetime, target_directory):
        self.original_jpg_path = original_jpg
        self.original_raw_path = original_raw
        self.datetime = datetime
        self.target_directory = target_directory
        self.copy_jpg = []
        self.copy_raw = []

    def __str__(self):
        return f"FoundFile(jpg={self.original_jpg_path}, raw={self.original_raw_path}, dt={self.datetime}, target={self.target_directory}, copy_jpg={self.copy_jpg}, copy_raw={self.copy_raw})"
    
    def __repr__(self):
        return str(self)

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
        for raw_ext in raw_extensions:
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
        try:
            my_image = Image(image_file)
        except Exception as e:
            print(f"Failed to read EXIF data from {path}: {e}")
            exit(1)
    dt_original = my_image.datetime_original
    dt_format = datetime.strptime(dt_original, exif_dt_format)
    return dt_format

def format_output_path(dt: datetime) -> Path:
    return Path(str(dt.year)).joinpath(dt.strftime("%Y-%m-%d"))

def gather_files(jpg_list: List[Path], raw_list: List[Path]):
    found_files: List[FoundFile] = []
    jpg_tqdm = tqdm(jpg_list)
    jpg_tqdm.write("Scanning JPG files")
    for jpg in jpg_tqdm:
        jpg_datetime = read_exif_datetime(jpg)
        matching_raw = [r for r in raw_list if r.stem == jpg.stem and r.parent == jpg.parent]
        found_raw = None
        if len(matching_raw) > 1:
            raise Exception(f"Found multiple RAW files matching {jpg}, how is that possible?")
        elif len(matching_raw) == 1:
            found_raw = matching_raw[0]
            raw_list.remove(found_raw) # Remove the matching RAW file from the list, since the match is 1:1
        out_dir = format_output_path(jpg_datetime)
        found_files.append(FoundFile(jpg, found_raw, jpg_datetime, out_dir))

    if len(raw_list) > 0:
        raw_tqdm = tqdm(raw_list)
        raw_tqdm.write("Scanning remaining RAW files")
        for raw in raw_tqdm:
            raw_datetime = read_exif_datetime(raw)
            out_dir = format_output_path(raw_datetime)
            found_files.append(FoundFile(None, raw, raw_datetime, out_dir))
    print("Scanned all files.")
    return found_files

def scan_output_dirs(args: argparse.Namespace, file_list: List[FoundFile]):
    """
    Scan the output directories to see if they exist, and if not, create them.
    This method also considers that the directories for each day may also be renamed
    containing a suffix, e.g. "2020-01-01_Whatever happened on that day".
    """
    required_output_dirs = set([f.target_directory for f in file_list])
    print("Creating yearly directories, where they don't exist yet.")
    year_dir_map = {}
    all_years = set([r.parent for r in required_output_dirs])
    if args.split_raw:
        # TODO
        raise NotImplementedError("Splitting RAW files is not yet implemented.")
    else:
        for year in all_years:
            if args.split_raw:
                for out_dir in [Path(o) for o in args.output]:
                    year_dir = out_dir.joinpath(year)
                    if not year_dir.exists():
                        print(f"Creating directory {year_dir}")
                        year_dir.mkdir(parents=False, exist_ok=False)
                        year_dir_map[year_dir] = []
                    else:
                        year_dir_map[year_dir] = list([f for f in year_dir.iterdir() if f.is_dir()])

            for out_dir in [Path(o) for o in args.output]:
                year_dir = out_dir.joinpath(year)
                if not year_dir.exists():
                    print(f"Creating directory {year_dir}")
                    year_dir.mkdir(parents=False, exist_ok=False)
                    year_dir_map[year_dir] = []
                else:
                    year_dir_map[year_dir] = list([f for f in year_dir.iterdir() if f.is_dir()])
    
    output_map = {}

    dir_tqdm = tqdm(required_output_dirs)
    dir_tqdm.write("Scanning output directories")
    out_basedirs = list(Path(o) for o in args.output)
    new_filelist: List[FoundFile] = []
    for required_dir in dir_tqdm:
        year = required_dir.parent
        for out_dir in out_basedirs:
            year_dir = out_dir.joinpath(year)
            target_dir = out_dir.joinpath(required_dir)
            matching_dirs = [d for d in year_dir_map.get(year_dir) if d is not None and d.name.startswith(required_dir.name)]
            if len(matching_dirs) == 1:
                output_map[target_dir] = matching_dirs[0]
            elif len(matching_dirs) == 0:
                target_dir = out_dir.joinpath(required_dir)
                dir_tqdm.write(f"Creating directory {target_dir}")
                target_dir.mkdir(parents=False, exist_ok=False)
                output_map[target_dir] = target_dir
            else:
                raise Exception(f"found multiple matching directories for {required_dir} in {year_dir}, please fix manually.")

    files_tqdm = tqdm(file_list)
    files_tqdm.write("Generating file copy jobs")
    for file in files_tqdm:
        copy_to_dirs = []
        for out_dir in out_basedirs:
            requested_output_dir = out_dir.joinpath(file.target_directory)
            copy_to_dirs.append(output_map.get(requested_output_dir))
        copy_jpg = None
        copy_raw = None
        for target_dir in copy_to_dirs:
            if args.rename_files:
                if file.original_jpg_path is not None:
                    copy_jpg = f"{file.datetime.strftime('%Y-%m-%d_%H-%M-%S')}-{file.original_jpg_path.name}"
                    file.copy_jpg.append(target_dir.joinpath(copy_jpg))
                if file.original_raw_path is not None:
                    copy_raw = f"{file.datetime.strftime('%Y-%m-%d_%H-%M-%S')}-{file.original_raw_path.name}"
                    file.copy_raw.append(target_dir.joinpath(copy_raw))
            else:
                if file.original_jpg_path is not None:
                    copy_jpg = file.original_jpg_path.name
                    file.copy_jpg.append(target_dir.joinpath(copy_jpg))
                if file.original_raw_path is not None:
                    copy_raw = file.original_raw_path.name
                    file.copy_raw.append(target_dir.joinpath(copy_raw))

        new_filelist.append(file)

    return new_filelist

def copy_files(filelist: List[FoundFile]):
    job_tqdm = tqdm(filelist)
    job_tqdm.write("Copying files")
    skipped_files = []
    for job in job_tqdm:
        for target_jpg in job.copy_jpg:
            if target_jpg.exists():
                skipped_files.append(target_jpg)
                job_tqdm.write(f"Skipping {target_jpg}, already exists")
            else:
                copyfile(job.original_jpg_path, target_jpg)
        for raw in job.copy_raw:
            if raw.exists():
                skipped_files.append(raw)
            else:
                copyfile(job.original_raw_path, raw)
    
    if len(skipped_files) > 0:
        print("Skipped files:", file=stderr)
        for skipped in skipped_files:
            print(skipped, file=stderr)


if __name__ == "__main__":
    args = parse_args()
    (jpg_list, raw_list) = scan_input_dirs(args)
    file_list = gather_files(jpg_list, raw_list)
    copy_jobs = scan_output_dirs(args, file_list)
    copy_files(copy_jobs)
    print("Done.")