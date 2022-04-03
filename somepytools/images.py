from contextlib import contextmanager
from pathlib import Path

from .general import str2pathlib
from .typing import Array, File, Iterable, List, Union


try:
    import cv2

except ModuleNotFoundError:
    pass


@contextmanager
@str2pathlib
def open_video(video_path: File, mode: str = "r", *args):
    """Context manager to work with cv2 videos

    Mimics python's standard `open` function

    Args:
        video_path: path to video to open
        mode: either 'r' for read or 'w' write
        args: additional arguments passed to Capture or Writer
            according to OpenCV documentation

    Returns:
        cv2.VideoCapture or cv2.VideoWriter depending on mode

    Example of writing:
        open_video(
            out_path,
            'w',
            cv2.VideoWriter_fourcc(*'XVID'), # fourcc
            15, # fps
            (width, height), # frame size
        )
    """
    if mode == "r":
        video = cv2.VideoCapture(video_path.as_posix(), *args)
    elif mode == "w":
        video = cv2.VideoWriter(video_path.as_posix(), *args)
    else:
        raise ValueError(f'Incorrect open mode "{mode}"; "r" or "w" expected!')

    if not video.isOpened():
        raise ValueError(f"Video {video_path} is not opened!")

    try:
        yield video
    finally:
        video.release()


@str2pathlib
def write_video(
    images: List[Array],
    video_path: File,
    codec_code: str = "XVID",
    fps: int = 2,
    is_color=True,
):
    """

    Args:
        images: List of RGB or binary images.
        video_path: The name of the file to save the video to.
        codec_code: FourCC - a 4-byte code used to specify the video codec.
        fps: Framerate of the created video stream.
        is_color: RGB images or not.

    """
    fourcc = cv2.VideoWriter_fourcc(*codec_code)
    height, width, channels = images[0].shape
    with open_video(video_path, "w", fourcc, fps, (width, height), is_color) as capture:
        for frame in images:
            if is_color:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            capture.write(frame)


@str2pathlib
def frames(video: Union[File, cv2.VideoCapture], rgb: bool = True) -> Iterable[Array]:
    """Generator of frames of the video provided

    Args:
        video: either Path or Video capture to read frames from
            in former case file will be opened with :py:funct:`.open_video`
        rgb: if True returns RGB image, else BGR - native to opencv format

    Yields:
        Frames of video in (H, W, C) format
    """
    if isinstance(video, Path) or isinstance(video, str):
        with open_video(video) as capture:
            yield from frames(capture, rgb)
    else:
        while True:
            retval, frame = video.read()
            if not retval:
                break
            if rgb:
                frame = frame[:, :, ::-1]
            yield frame
