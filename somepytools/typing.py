"""Single place to define (and redefine) custom types"""

from numbers import Number
from pathlib import Path
from typing import *  # noqa: F403
from typing import Any, Dict, Generic, List, TypeVar, Union


# Path wich is expected to be directory (dir.is_dir() == True)
Directory = Path
# Path wich is expected to be file (dir.is_dir() == False)
File = Path

# No exact type for this, so use crutch, more info: https://github.com/python/typing/issues/182
JsonSerializable = Union[List[Any], Dict[Any, Any]]

# This is supposed to be some data type for multidimensional array libraries as numpy or torch
Dtype = TypeVar("Dtype")

try:
    import numpy as np

    class Array(np.ndarray, Generic[Dtype]):
        """Numpy array of type `Dtype`

        `Dtype` can be any regular numeric type such as `int`, `bool` or numpy types as `np.float32`
        """

        pass

except ModuleNotFoundError:
    pass

try:
    import torch

    # Hardware type for torch
    Device = torch.device
    # Weakened version accepting string as well as Device
    LooseDevice = Union[str, torch.device]
    Model = torch.nn.Module

    class Tensor(torch.Tensor, Generic[Dtype]):
        """Torch tensor of type `Dtype`

        `Dtype` can be any regular numeric type such as `int`, `bool` or torch types as `torch.float32`
        """

        pass

except ModuleNotFoundError:
    pass
