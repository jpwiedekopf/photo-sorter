import argparse
from patharg import PathType

parser = argparse.ArgumentParser()
parser.add_argument("--input", "-i", type=PathType(type='dir', abs=True, exists=True), nargs="+", required=True)
parser.add_argument("--output", "-o", type=PathType(type='dir', abs=True, exists=True), nargs="+", required=True),
parser.add_argument('--split-raw', "-s", default=True, action='store_true')
parser.add_argument("--no-split-raw", "-n", action='store_false', dest="split_raw"),
parser.add_argument("--jpg-dir", default="JPG", type=str)
parser.add_argument("--raw-dir", default="RAW", type=str)

args = parser.parse_args()
print(args)