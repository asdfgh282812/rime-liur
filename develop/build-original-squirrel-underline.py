#!/usr/bin/env python3
"""Build a backed-up in-place Squirrel update, preserving its input-source ID.

Requires an existing development signing identity so hardened runtime and library
validation remain enabled. Builds a local pkg; does not install it or ask for a
password. Install that pkg with macOS Installer after reviewing the backup.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import runpy
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "develop/squirrel-proofreader"
REVISION = "4381c75072bd1bb3cde0fa162aca0971b60f92ef"
OFFICIAL = Path("/Library/Input Methods/Squirrel.app")


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def prepare_source(work, source):
    if not source.exists():
        run(["git", "clone", "--depth", "1", "--branch", "0.18",
             "https://github.com/rime/squirrel.git", source])
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise RuntimeError("The source must be the pinned official Squirrel 0.18 revision")
    run(["git", "-C", source, "submodule", "update", "--init", "--depth", "1", "librime"])
    staged = work / "source"
    shutil.rmtree(staged, ignore_errors=True)  # never compile files left by an older patch
    staged.mkdir()
    # Copy pristine tracked files, so repeated builds never patch a previous build.
    tracked = subprocess.check_output(["git", "-C", str(source), "ls-tree", "--name-only", "HEAD"], text=True)
    for name in tracked.splitlines():
        path = source / name
        if path.suffix in (".m", ".h", ".pch"):
            content = subprocess.check_output(["git", "-C", str(source), "show", f"HEAD:{path.name}"])
            (staged / path.name).write_bytes(content)
    for name in ("LiurProofreadHint.h", "LiurProofreadService.h", "LiurProofreadService.m"):
        shutil.copy2(EXTENSION / name, staged)
    run(["patch", "-p1", "-i", EXTENSION / "squirrel-0.18.patch"], cwd=staged)
    main = staged / "main.m"
    text = main.read_text().replace('#import "SquirrelApplicationDelegate.h"',
        '#import "SquirrelApplicationDelegate.h"\n#import "LiurProofreadService.h"')
    text = text.replace('      [NSApp.squirrelAppDelegate setupRime];',
        '      [[LiurProofreadService shared] start];\n      [NSApp.squirrelAppDelegate setupRime];')
    text = text.replace('    rime_get_api()->finalize();',
        '    [[LiurProofreadService shared] stop];\n    rime_get_api()->finalize();')
    main.write_text(text)
    return staged


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(app):
    result = {}
    for path in sorted(app.rglob("*")):
        key = str(path.relative_to(app))
        if path.is_symlink():
            result[key] = {"link": os.readlink(path)}
        elif path.is_file():
            names = subprocess.check_output(["xattr", str(path)], text=True).splitlines()
            result[key] = {"sha256": digest(path), "signing_attributes": {
                name: hashlib.sha256(subprocess.check_output(["xattr", "-px", name, str(path)])).hexdigest()
                for name in names if name.startswith("com.apple.cs.")}}
    return result


def sign(app, identity):
    # Frozen Python extensions and interpreter must share the app's signing team.
    helpers = app / "Contents/Helpers"
    magic = {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
    for path in sorted([*helpers.rglob("*"), *(app / "Contents/Resources/LiurChecker").rglob("*")], key=lambda p: len(p.parts), reverse=True):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as stream:
                macho = stream.read(4) in magic
            if macho:
                run(["codesign", "--force", "--options", "runtime", "--sign", identity, path])
    for path in sorted((app / "Contents/Resources/LiurChecker").rglob("*.framework"), key=lambda p: len(p.parts), reverse=True):
        run(["codesign", "--force", "--options", "runtime", "--sign", identity, path])
    frameworks = app / "Contents/Frameworks"
    # Sign nested executables before their enclosing bundles, then the app.
    for path in sorted(frameworks.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_symlink():
            continue
        if path.is_dir() and path.suffix in (".app", ".xpc", ".framework"):
            run(["codesign", "--force", "--options", "runtime", "--sign", identity, path])
        elif path.is_file() and path.suffix == ".dylib":
            run(["codesign", "--force", "--options", "runtime", "--sign", identity, path])
    sparkle = frameworks / "Sparkle.framework"
    for name in ("Autoupdate", "Sparkle"):
        run(["codesign", "--force", "--options", "runtime", "--sign", identity,
             sparkle / "Versions/B" / name])
    run(["codesign", "--force", "--options", "runtime", "--sign", identity, sparkle])
    run(["codesign", "--force", "--deep", "--options", "runtime", "--sign", identity, app])
    run(["codesign", "--verify", "--deep", "--strict", app])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", required=True, help="Existing development signing identity SHA-1")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--bundle-python", type=Path, default=ROOT / ".squirrel-proofreader/bundle-tools/venv/bin/python")
    parser.add_argument("--model-dir", type=Path, default=ROOT / ".proofreader-model")
    args = parser.parse_args()
    info = plistlib.loads((OFFICIAL / "Contents/Info.plist").read_bytes())
    if info["CFBundleVersion"] != "0.18" or info["CFBundleIdentifier"] != "im.rime.inputmethod.Squirrel":
        raise RuntimeError("Expected the installed Squirrel 0.18 app")
    work = ROOT / ".squirrel-proofreader/original"
    work.mkdir(parents=True, exist_ok=True)
    source = (args.source or ROOT / ".squirrel-proofreader/upstream").resolve()
    staged = prepare_source(work, source)
    app = work / "Squirrel.app"
    if app.exists():
        shutil.rmtree(app)
    shutil.copytree(OFFICIAL, app, symlinks=True)
    shutil.rmtree(app / "Contents/_CodeSignature")
    sdk = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    flags = ["xcrun", "clang", "-fobjc-arc", "-O2", "-mmacosx-version-min=13.0",
             "-I", source / "librime/src", "-I", source / "librime/include",
             "-I", EXTENSION, "-I", f"{sdk}/System/Library/Frameworks/Tk.framework/Headers",
             "-include", staged / "Squirrel_Prefix.pch"]
    test = work / "test-hint"
    run([*flags, "-framework", "Cocoa", EXTENSION / "test-hint.m", "-o", test])
    run([test])
    frameworks = app / "Contents/Frameworks"
    flags += ["-F", frameworks]
    for name in ("Cocoa", "InputMethodKit", "Carbon", "QuartzCore", "UserNotifications", "Sparkle"):
        flags += ["-framework", name]
    libraries = [frameworks / "librime.1.dylib", *sorted((frameworks / "rime-plugins").glob("*.dylib"))]
    run([*flags, *sorted(staged.glob("*.m")),
         *[f"-Wl,-needed_library,{path}" for path in libraries],
         "-Wl,-rpath,@loader_path/../Frameworks",
         "-Wl,-rpath,@loader_path/../Frameworks/rime-plugins",
         "-o", app / "Contents/MacOS/Squirrel"])
    data = runpy.run_path(str(ROOT / "develop/bundle-proofreader.py"))["bundle"](
        app, work, args.bundle_python, args.model_dir, Path.home() / "Library/Rime")
    sign(app, args.identity)
    run([app / "Contents/Resources/LiurChecker/LiurChecker", "--model-dir", data / "model",
         "--rime-dir", data, "--self-test"], env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())})
    # This is a maintenance CLI, so it loads all libraries without starting a
    # second IMK server or opening the live user dictionary.
    run([app / "Contents/MacOS/Squirrel", "--register-input-source"])
    if (app / "Contents/Info.plist").read_bytes() != (OFFICIAL / "Contents/Info.plist").read_bytes():
        raise RuntimeError("The in-place build must preserve all input-source metadata")

    backup = Path.home() / "Library/Rime/backups" / ("squirrel-app-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True, mode=0o700)
    # ditto also retains detached signatures in script extended attributes;
    # shutil.copytree does not preserve these protected signing attributes.
    run(["ditto", "--rsrc", "--extattr", OFFICIAL, backup / "Squirrel.app"])
    original_files = fingerprint(OFFICIAL)
    if fingerprint(backup / "Squirrel.app") != original_files:
        raise RuntimeError("The original backup must match every file and signing attribute")
    (backup / "files.json").write_text(json.dumps(original_files, indent=2) + "\n")
    expected = digest(OFFICIAL / "Contents/MacOS/Squirrel")
    (backup / "manifest.json").write_text(json.dumps({
        "app": str(OFFICIAL), "original_executable_sha256": expected,
        "patched_executable_sha256": digest(app / "Contents/MacOS/Squirrel"),
        "upstream_revision": REVISION, "patch": "develop/squirrel-proofreader/squirrel-0.18.patch",
        "signing_identity": args.identity, "hardened_runtime": True,
    }, indent=2) + "\n")

    payload = work / "payload"
    if payload.exists():
        shutil.rmtree(payload)
    payload.mkdir()
    run(["ditto", "--rsrc", "--extattr", app, payload / "Squirrel.app"])
    run(["codesign", "--verify", "--deep", "--strict", payload / "Squirrel.app"])
    component = work / "component.plist"
    run(["pkgbuild", "--analyze", "--root", payload, component])
    components = plistlib.loads(component.read_bytes())
    def configure_components(entries):
        for entry in entries:
            entry["BundleIsRelocatable"] = False
            entry["BundleIsVersionChecked"] = False
            entry["BundleOverwriteAction"] = "upgrade"
            configure_components(entry.get("ChildBundles", []))
    configure_components(components)
    component.write_bytes(plistlib.dumps(components))
    scripts = work / "scripts"
    scripts.mkdir(exist_ok=True)
    # Abort if the original has changed since the verified backup was made.
    preinstall = scripts / "preinstall"
    executable = shlex.quote(str(OFFICIAL / "Contents/MacOS/Squirrel"))
    preinstall.write_text('#!/bin/sh\nset -eu\n'
        f'actual=$(/usr/bin/shasum -a 256 {executable} | /usr/bin/awk \'{{print $1}}\')\n'
        f'[ "$actual" = "{expected}" ] || {{ echo "Squirrel changed after backup; rebuild the package." >&2; exit 1; }}\n')
    preinstall.chmod(0o755)
    package = work / "Squirrel-Liur-Builtin.pkg"
    run(["pkgbuild", "--root", payload, "--component-plist", component,
         "--scripts", scripts, "--install-location", "/Library/Input Methods",
         "--identifier", "org.rime-liur.squirrel-underline", "--version", "0.18.2", package])
    (work / "installation.json").write_text(json.dumps({"package": str(package), "backup": str(backup)}, indent=2) + "\n")
    print(f"Verified original backup: {backup}")
    print(f"Package ready for macOS Installer: {package}")
    print("Installing requires administrator authentication in macOS. Never send a password to chat.")


if __name__ == "__main__":
    main()
