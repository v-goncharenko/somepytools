import importlib
import os
import shutil
import zipfile
from enum import StrEnum
from pathlib import Path
from types import ModuleType

from .typing import Directory, File, PathLike


class DriveBackend(StrEnum):
    Google = "google"
    Yandex = "yandex"


def _require(module: str, backend: str) -> ModuleType:
    """Import an optional ``module`` or raise an actionable ImportError.

    Both `gdown` and `yadisk` are optional dependencies (extras), so we import them
    lazily and only when a particular backend is actually used.

    Args:
        module: Name of the module to import (e.g. ``"gdown"``).
        backend: Human-readable backend name used in the error message.
    """
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise ImportError(
            f"The {backend!r} drive backend requires the optional `{module}` package, "
            f"which is not installed. Install it with `pip install {module}` "
            f"or pull all optional drive backends via `pip install 'somepytools[all]'`."
        ) from exc


def _download_from_google(
    file_id: str,
    root_dir: Directory,
    *,
    quiet: bool,
    use_cookies: bool,
) -> File:
    gdown = _require("gdown", DriveBackend.Google.value)
    # Passing output as a directory with a trailing separator tells gdown
    # to preserve the filename obtained from Google Drive.
    downloaded_path = gdown.download(
        id=file_id,
        output=str(root_dir) + os.sep,
        quiet=quiet,
        use_cookies=use_cookies,
    )

    if downloaded_path is None:
        raise RuntimeError(
            "gdown did not return a downloaded file path. "
            "Check file permissions: the Drive file should be public / shared by link."
        )

    return Path(downloaded_path).expanduser().resolve()


def _download_from_yandex(public_key: str, root_dir: Directory) -> File:
    yadisk = _require("yadisk", DriveBackend.Yandex.value)
    with yadisk.Client() as client:
        meta = client.get_public_meta(public_key)
        name = meta.name
        if not name:
            raise RuntimeError(
                f"Could not determine filename for Yandex public resource: {public_key!r}. "
                "Make sure the link points to a file (not a folder) and is public."
            )
        target_path = (root_dir / name).resolve()
        client.download_public(public_key, str(target_path))

    return target_path


def _prepare_extract_dir(zip_path: File, *, overwrite_extract_dir: bool) -> Directory:
    extracted_dir = zip_path.with_suffix("")

    if not extracted_dir.exists():
        return extracted_dir

    if not extracted_dir.is_dir():
        raise FileExistsError(
            f"Extraction target exists and is not a directory: {extracted_dir}"
        )

    existing_items = list(extracted_dir.iterdir())
    if not existing_items:
        return extracted_dir

    if not overwrite_extract_dir:
        raise FileExistsError(
            f"Extraction directory already exists and is non-empty: {extracted_dir}. "
            "Pass overwrite_extract_dir=True to replace it."
        )

    for item in existing_items:
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    return extracted_dir


_BYTES_PER_KIB = 1024
_PROGRESS_MIN_ENTRIES = 4


def _human_size(n_bytes: int) -> str:
    size = float(n_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < _BYTES_PER_KIB:
            return f"{size:.1f} {unit}"
        size /= _BYTES_PER_KIB
    return f"{size:.1f} PiB"


def unzip(zip_path: File, extract_dir: Directory, verbose: bool) -> None:
    """Extract ZIP archive into extract_dir, rejecting members that would escape it.

    This protects against path traversal entries such as ../../some_file.

    Args:
        zip_path: path to an existing .zip file
        extract_dir: directory to extract zip file to
        verbose: to print status messages or not
    """
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_root = extract_dir.resolve()

    with zipfile.ZipFile(zip_path, mode="r") as zf:
        if verbose:
            print(f"Verifying integrity of {zip_path.name} ...")
        bad_member = zf.testzip()
        if bad_member is not None:
            raise ValueError(f"Corrupted ZIP member detected: {bad_member!r}")

        members = zf.infolist()
        for member in members:
            target_path = (extract_dir / member.filename).resolve()

            if target_path != extract_root and extract_root not in target_path.parents:
                raise ValueError(
                    f"Unsafe ZIP member path: {member.filename!r}. "
                    "Archive extraction was aborted."
                )

        total = len(members)
        total_size = sum(m.file_size for m in members)
        if verbose:
            print(
                f"Extracting {total} entries ({_human_size(total_size)}) "
                f"from {zip_path.name} to {extract_dir} ..."
            )

        # Medium density: print at 25/50/75% boundaries (skipped for tiny archives).
        checkpoints = (
            {max(1, total * pct // 100) for pct in (25, 50, 75)}
            if verbose and total >= _PROGRESS_MIN_ENTRIES
            else set()
        )

        for i, member in enumerate(members, start=1):
            zf.extract(member, extract_dir)
            if i in checkpoints:
                print(f"  ... {i}/{total} entries extracted ({i * 100 // total}%)")

        if verbose:
            print(f"Done: extracted {total} entries to {extract_dir}")


def download_and_unpack(
    file_id: str,
    root_dir: PathLike = ".",
    *,
    backend: DriveBackend = DriveBackend.Google,
    quiet: bool = False,
    use_cookies: bool = True,
    overwrite_extract_dir: bool = False,
) -> tuple[Path, Path]:
    """Download a public ZIP file from a cloud drive and unpack it.

    For Google Drive uses `gdown`, for Yandex Disk - `yadisk[sync-defaults]`.

    Args:
        file_id: Public file identifier. For ``backend="google"`` it is the Google Drive
            file ID or shared URL; for ``backend="yandex"`` it is the Yandex Disk public
            key or public URL (e.g. ``https://disk.yandex.ru/d/...``).
        root_dir: Directory where the ZIP archive and extracted directory will be stored.
        backend: Source to download the file from. One of :class:`DriveBackend` values.
        quiet: If True, suppress progress output (passed to ``gdown.download()`` for the
            Google backend, and used to silence extraction progress in :func:`unzip`).
        use_cookies: Passed to ``gdown.download()``. Keeping this True is usually useful
            for Google Drive throttling / confirmation flows. Ignored for the Yandex
            backend.
        overwrite_extract_dir:
            If True, delete existing files in the extraction directory before extraction.
            If False, raise FileExistsError when the extraction directory already exists
            and is non-empty.

    Returns:
        zip_path: downloaded zip file path
        extracted_dir: dir where zip is extracted
    """
    root_dir = Path(root_dir).expanduser().resolve()
    root_dir.mkdir(parents=True, exist_ok=True)

    backend = DriveBackend(backend)
    if backend is DriveBackend.Google:
        zip_path = _download_from_google(
            file_id, root_dir, quiet=quiet, use_cookies=use_cookies
        )
    elif backend is DriveBackend.Yandex:
        zip_path = _download_from_yandex(file_id, root_dir)
    else:
        raise ValueError(f"Unsupported drive backend: {backend!r}")

    if not zip_path.exists():
        raise FileNotFoundError(f"Downloaded path does not exist: {zip_path}")

    if zip_path.suffix.lower() != ".zip":
        raise ValueError(f"Downloaded file is not a .zip archive: {zip_path.name}")

    extracted_dir = _prepare_extract_dir(zip_path, overwrite_extract_dir=overwrite_extract_dir)

    unzip(zip_path=zip_path, extract_dir=extracted_dir, verbose=not quiet)

    return zip_path, extracted_dir
