import pathlib
import shutil
import sys
import os
import hashlib

sys.path.insert(0, 'src')
from _version import __version__  # noqa:E402

tools_dir = pathlib.Path('tools')
build_dir = pathlib.Path('build')
build_out = build_dir / 'RestoreWindowPos'
dist_dir = pathlib.Path('dist')
dist_out = dist_dir / 'choco'
installer_src = dist_dir / 'RestoreWindowPos_install.exe'

installer_hash = hashlib.sha256(open(installer_src, 'rb').read()).hexdigest()

if build_out.exists():
    shutil.rmtree(build_out)
dist_dir.mkdir(exist_ok=True)
shutil.copytree(tools_dir / 'choco_template', build_out)

for root, _, files in os.walk(build_out):
    for file in files:
        if not file.endswith(('.ps1', '.nuspec')):
            continue
        file = os.path.join(root, file)
        with open(file, 'r', encoding='utf-8') as f:
            contents = f.read()
        with open(file, 'w', encoding='utf-8') as f:
            f.write(
                contents.replace(
                    '@@InstallerChecksum@@', installer_hash
                ).replace(
                    '@@PackageVersion@@', __version__
                )
            )


shutil.copyfile(installer_src,
                f'{build_out}/tools/RestoreWindowPos_install.exe')
shutil.copyfile('LICENSE', f'{build_out}/tools/LICENSE.txt')

os.system(
    f'choco pack {build_dir}/RestoreWindowPos/restorewindowpos.nuspec --outdir {dist_dir}')
