import os

import pyinstaller_versionfile

if not os.path.isdir('build'):
    os.mkdir('build')

pyinstaller_versionfile.create_versionfile(
    output_file="build/versionfile.txt",
    version="0.4.0.0",
    file_description="RestoreWindowPos",
    legal_copyright="© Crozzers (github.com/Crozzers) 2023",
    product_name="RestoreWindowPos"
)
