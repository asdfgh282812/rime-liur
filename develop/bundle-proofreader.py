#!/usr/bin/env python3
"""Bundle the checker runtime and data into an unsigned Squirrel app."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def bundle(app, work, python, model, rime):
    helpers = app / 'Contents/Helpers'
    shutil.rmtree(helpers, ignore_errors=True)
    helpers.mkdir()
    freeze = work / 'freeze'
    freeze.mkdir(exist_ok=True)
    command = [python, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
               '--name', 'LiurChecker', '--distpath', str(freeze / 'dist'),
               '--workpath', str(freeze / 'build'), '--specpath', str(freeze),
               '--collect-binaries', 'onnxruntime', '--copy-metadata', 'numpy',
               '--copy-metadata', 'onnxruntime']
    for name in ('torch', 'tensorflow', 'pandas', 'matplotlib', 'scipy', 'onnx', 'transformers', 'IPython', 'pytest'):
        command += ['--exclude-module', name]
    subprocess.run([*map(str, command), str(ROOT / 'proofreader/service.py')], check=True)
    runtime = app / 'Contents/Resources/LiurChecker'
    shutil.rmtree(runtime, ignore_errors=True)
    shutil.copytree(freeze / 'dist/LiurChecker', runtime, symlinks=True)
    subprocess.run(['xcrun', 'clang', '-O2', '-Wall', '-Wextra', '-Werror',
                    str(ROOT / 'proofreader/client.c'), '-o', str(helpers / 'liur_proofread_client')], check=True)
    data = app / 'Contents/SharedSupport/proofreader'
    shutil.rmtree(data, ignore_errors=True)
    (data / 'model').mkdir(parents=True)
    provenance = json.loads((model / 'provenance.json').read_text())
    for name in ('model.onnx', 'vocab.txt'):
        if hashlib.sha256((model / name).read_bytes()).hexdigest() != provenance['sha256'][name]:
            raise RuntimeError(f'Model hash mismatch: {name}')
    for name in ('model.onnx', 'vocab.txt', 'provenance.json'):
        shutil.copy2(model / name, data / 'model' / name)
    shutil.copy2(model / 'original/README.md', data / 'model/README.md')
    for name in ('essay.txt', 'terra_pinyin.dict.yaml'):
        shutil.copy2(rime / name, data / name)
    shutil.copy2(ROOT / 'Rime/lua/liur_proofreader.lua', data)
    shutil.copy2(ROOT / 'Rime/liur.schema.yaml', data)
    shutil.copy2(ROOT / 'proofreader/service.py', data / 'service-source.py')
    shutil.copy2(ROOT / 'develop/activate-builtin-proofreader.sh', data / 'activate.sh')
    # Keep the runtime's bundled licenses and copy build distribution notices too.
    licenses = data / 'licenses'
    licenses.mkdir()
    for name in ('numpy', 'onnxruntime', 'pyinstaller'):
        result = subprocess.check_output([str(python), '-c',
            'import importlib.metadata, json; d=importlib.metadata.distribution(' + repr(name) + '); '
            'print(json.dumps({"version":d.version,"files":[str(d.locate_file(f)) for f in d.files '
            'if "license" in str(f).lower() or "notice" in str(f).lower()]}))'], text=True)
        info = json.loads(result)
        target = licenses / name
        target.mkdir()
        for i, filename in enumerate(info['files']):
            path = Path(filename)
            if path.is_file(): shutil.copy2(path, target / f'{i}-{path.name}')
        (target / 'version.txt').write_text(info['version'] + '\n')
    manifest = {str(p.relative_to(data)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(data.rglob('*')) if p.is_file()}
    (data / 'bundle-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return data
