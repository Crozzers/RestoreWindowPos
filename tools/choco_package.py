import pathlib
import shutil
import sys
import os
import hashlib

sys.path.insert(0, 'src')
from _version import __version__  # noqa:E402

build_dir = pathlib.Path('build')
build_out = build_dir / 'RestoreWindowPos'
dist_dir = pathlib.Path('dist')
dist_out = dist_dir / 'choco'
installer_src = dist_dir / 'RestoreWindowPos_install.exe'

installer_hash = hashlib.sha256(open(installer_src, 'rb').read()).hexdigest()
# pull some shenanigans because choco doesn't let you specify a local path for a template
template = os.path.relpath('./tools/choco_template', r'C:\ProgramData\chocolatey\templates')

os.system((
    f'choco new RestoreWindowPos --force --outdir {build_dir}'
    f' -t "{template}"'
    ' maintainername="Crozzers" maintainerrepo="https://github.com/Crozzers/RestoreWindowPos"'
    f' InstallerType=exe packageversion="{__version__}" SilentArgs="\'/S\'"'
    # custom params
    ' GithubPage="https://github.com/Crozzers/RestoreWindowPos"'
    ' IconUrl="https://raw.githubusercontent.com/Crozzers/RestoreWindowPos/main/assets/icon256.ico"'
    ' LicenseUrl="https://raw.githubusercontent.com/Crozzers/RestoreWindowPos/main/LICENSE"'
    f' InstallerHash="{installer_hash}"'
))


shutil.copyfile(installer_src,
                f'{build_out}/tools/RestoreWindowPos_install.exe')
shutil.copyfile('LICENSE', f'{build_out}/tools/LICENSE.txt')

os.system(f'choco pack {build_dir}/RestoreWindowPos/restorewindowpos.nuspec --outdir {dist_dir}')
