from pathlib import Path

import somepytools
from somepytools.io import read_toml


curr_dir = Path(__file__).resolve().parent


def test_version():
    pyproject = read_toml(curr_dir / "../pyproject.toml")

    assert somepytools.__version__ == pyproject["tool"]["poetry"]["version"]
