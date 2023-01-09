import os
import sys

import pyinstaller_versionfile

sys.path.insert(0, 'src')
from _version import __version__  # noqa: E402

if not os.path.isdir('build'):
    os.mkdir('build')

pyinstaller_versionfile.create_versionfile(
    output_file="build/versionfile.txt",
    version=f'{__version__}.0',
    file_description="RestoreWindowPos",
    legal_copyright="© Crozzers (github.com/Crozzers) 2023",
    product_name="RestoreWindowPos"
)
