import shutil
from functools import wraps
from inspect import getfullargspec
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from .constants import SIZE_CONSTANTS
from .typing import Directory, File, get_args


def str2pathlib(func):
    """Decorator for wrapping loose-path function's arguments

    To escape using Path("/some/string") for all functions arguments with types
    LoseFile and LoseDirectory, decorator wraps this arguments with pathlib's Path

    Example:
        from .utils import str2pathlib
        from .types import File

        @str2pathlib
        def my_func(source: File):
            dest = source / "my_dir"
            dest.mkdir()
            return dest

        my_func("/home/user")

        >>> PosixPath('/home/user/my_dir')
    """
    full_arg_spec = getfullargspec(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        args = list(args)
        for arg_name, arg_type in full_arg_spec.annotations.items():
            if arg_name == "return":
                continue
            if arg_type == Path or Path in get_args(arg_type):
                if arg_name in kwargs:
                    if kwargs[arg_name] is None:
                        continue

                    kwargs[arg_name] = Path(kwargs[arg_name])
                else:
                    arg_index = full_arg_spec.args.index(arg_name)
                    # TODO fix default args processing
                    if len(args) > arg_index and args[arg_index]:
                        args[arg_index] = Path(args[arg_index])
        return func(*args, **kwargs)

    return wrapper


@str2pathlib
def download_url(url: str, save_path: File):
    """Downloads and saves data from url

    Args:
        url: address of file to download
        save_path: file path to save to
    """
    with urlopen(url) as response:
        with open(save_path, "wb") as file:
            file.write(response.read())


@str2pathlib
def extract_zip(zip_path: File, save_dir: Directory):
    """Unzips archive

    Args:
        zip_file_path: path to *.zip file to unzip
        save_dir:  path for files and folders to save
    """
    with ZipFile(zip_path) as zip_file:
        zip_file.extractall(save_dir)


@str2pathlib
def cp(source: Path, dest: Path, parents: bool = True) -> Path:
    """Copies file or folder to destination for both strings and pathlib objects

    Unfortunately pathlib doesn't have a native copying function =(((
    """
    if source.is_dir():
        copied = shutil.copytree(source, dest, dirs_exist_ok=True)
    else:
        if parents:
            if dest.is_dir():
                dest.mkdir(exist_ok=True, parents=True)
            else:
                dest.parent.mkdir(exist_ok=True, parents=True)
        copied = shutil.copy2(source, dest)
    return Path(copied)


@str2pathlib
def rm_r(folder: Directory):
    """Emulates `rm -r <folder>` command

    Ignores not existing directory
    """
    if not folder.exists():
        return
    shutil.rmtree(folder)


@str2pathlib
def dir_size(
    directory: Directory, units: str = "Bytes", check_softlinks: bool = True
) -> float:
    """Calculates the total size of files within the directory.

    Args:
        root: target directory
        units: size units (from .constants.SIZE_CONSTANTS.keys())
        check_softlinks: flag indicating whether to count files by links or not
    """
    total_size = 0
    for f in directory.glob("**/*"):
        if f.is_file():
            total_size += f.stat().st_size / SIZE_CONSTANTS[units]
        if check_softlinks and f.is_symlink():
            src = f.resolve()
            total_size += dir_size(src, units)
    return total_size
