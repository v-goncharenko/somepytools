from .typing import Array, Bbox, Number, OpencvFlag, Optional, Sequence


try:
    import cv2
except ModuleNotFoundError:
    pass


try:
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    pass


def resize(
    image: Array,
    inter: Optional[OpencvFlag] = None,
    *,
    height: Optional[Number] = None,
    width: Optional[Number] = None,
) -> Array:
    """Smart resizing with OpenCV under the hood

    Args:
        interp: Interpolation flags, [see here](https://docs.opencv.org/4.5.5/da/d54/group__imgproc__transform.html#ga5bb5a1fea74ea38e1a5445ca803ff121)

    Retruns:
        resized image (new one)
    """
    inter = inter or cv2.INTER_AREA
    orig_height, orig_width = image.shape[:2]

    if width is not None and height is not None:
        dsize = (width, height)
    elif height is not None:
        ratio = height / float(orig_height)
        dsize = (int(orig_width * ratio), height)
    elif width is not None:
        ratio = width / float(orig_width)
        dsize = (width, int(orig_height * ratio))
    else:
        raise ValueError("At least one of `height` and `width` must be specified!")

    return cv2.resize(image, dsize, interpolation=inter)


def plot_image(
    image: "Array",
    title: str = "",
    boxes: Sequence[Bbox] = (),
    figsize: tuple = (20, 5),
    opencv_format: bool = False,
    extra_operations=lambda: None,
):
    """Plots image with optional bboxes on it

    Args:
        boxes: list of bboxes in 'tlbr' format
            remember that matplotlib's coordinates x is horizontal, y is vertical
        opencv_format: channels sequence from opencv (BGR), so it need to be reversed
        extra_operations: lambda with everything you want to do to plt
    """
    if opencv_format:  # to reverse colours from BGR
        image = image[..., ::-1]

    plt.figure(figsize=figsize, constrained_layout=True)
    plt.imshow(image)
    plt.title(title)
    for box in boxes:
        rect = patches.Rectangle(
            (box[0], box[1]),
            box[2] - box[0],
            box[3] - box[1],
            linewidth=1,
            edgecolor="r",
            facecolor="none",
        )
        plt.gca().add_patch(rect)
    extra_operations()
    plt.show()
