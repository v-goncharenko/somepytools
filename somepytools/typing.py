"""Single place to define (and redefine) custom types."""

import os
from collections.abc import Sequence
from numbers import Number
from pathlib import Path
from typing import Any, TypeVar

import numpy as np

# Path which is expected to be directory (dir.is_dir() == True)
Directory = Path
# Path which is expected to be file (dir.is_dir() == False)
File = Path
# Something that looks like a path on OS
PathLike = str | os.PathLike

# No exact type for this, so use crutch, more info: https://github.com/python/typing/issues/182
JsonSerializable = list[Any] | dict[Any, Any]

# Format to annotate flags coming from OpenCV (not usual integers)
OpencvFlag = int

# This is supposed to be some data type for multidimensional array libraries as numpy or torch
Dtype = TypeVar("Dtype")

Bbox = Sequence[Number]
"""Numpy array of type `Dtype`.

`Dtype` can be any regular numeric type such as `int`, `bool` or numpy types as `np.float32`
"""

Array = np.ndarray

try:
    import torch

    # Hardware type for torch
    Device = torch.device
    # Weakened version accepting string as well as Device
    LooseDevice = str | torch.device
    Model = torch.nn.Module
    """Torch tensor of type `Dtype`.

    `Dtype` can be any regular numeric type such as `int`, `bool` or torch types as
    `torch.float32`
    """

    Tensor = torch.Tensor

except ModuleNotFoundError:
    Device = None
    LooseDevice = None
    Model = None
    Tensor = None
