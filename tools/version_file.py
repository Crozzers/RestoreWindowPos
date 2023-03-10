import os
import re
import sys

import pyinstaller_versionfile
from packaging.version import Version

sys.path.insert(0, 'src')
from _version import __version__  # noqa: E402

OUTPUT_FILE = 'build/versionfile.txt'

build = 0
if os.path.isdir('build'):
    if os.path.isfile(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            ver_str = re.search(r'filevers=\((\d+,\d+,\d+),(\d+)\)', f.read(), re.M)

        last_version = Version(ver_str.group(1).replace(',', '.'))
        last_build = int(ver_str.group(2))

        if Version(__version__) == last_version:
            build = last_build + 1
else:
    os.mkdir('build')

pyinstaller_versionfile.create_versionfile(
    output_file=OUTPUT_FILE,
    version=f'{__version__}.{build}',
    file_description='RestoreWindowPos',
    legal_copyright='© Crozzers (github.com/Crozzers) 2023',
    product_name='RestoreWindowPos'
)
