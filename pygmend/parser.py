from pathlib import Path

from pydocstyle.parser import Parser


def parse(file_path: Path):
    return Parser().parse(file_path.open("r"), str(file_path.absolute()))
