import shutil
from functools import wraps
from inspect import getfullargspec
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from .constants import SIZE_CONSTANTS
from .typing import Any, Directory, File, get_args


def str2pathlib(func):
    """Decorator to convert string inputs to Path when they are annotated as Path

    Allows to write decorated function as if you always have Path object as input
        but use this function with string input variables (see Example section).

    Under the hood it converts all input variables annotated as Path
        and having type str to Path objects.

    Example:
        from pathlib import Path

        @str2pathlib
        def my_func(source: Path):
            dest = source / "my_dir"
            dest.mkdir()
            return dest

        my_func("~/home/user")

        >>> PosixPath('~/home/user/my_dir')
    """

    def str_to_path(item: Any) -> Any:
        if isinstance(item, str):
            return Path(item)
        return item

    full_arg_spec = getfullargspec(func)
    all_defaults = full_arg_spec.defaults or ()

    path_args = []
    for arg_name, arg_type in full_arg_spec.annotations.items():
        if (arg_type != Path and Path not in get_args(arg_type)) or arg_name == "return":
            continue

        if arg_name in full_arg_spec.kwonlyargs:
            index = float("inf")
            needs_default = True
            default = full_arg_spec.kwonlydefaults[arg_name]
        else:
            index = full_arg_spec.args.index(arg_name)
            def_index = index - len(full_arg_spec.args) + len(all_defaults)
            needs_default = def_index >= 0
            default = full_arg_spec.defaults[def_index] if needs_default else None

        path_args.append((index, arg_name, needs_default, str_to_path(default)))

    @wraps(func)
    def wrapper(*args, **kwargs):
        args = list(args)

        for index, arg_name, needs_default, default in path_args:
            if arg_name in kwargs:
                kwargs[arg_name] = str_to_path(kwargs[arg_name])
            elif index < len(args):  # this was passed as arg
                args[index] = str_to_path(args[index])
            elif needs_default:
                kwargs[arg_name] = default

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
