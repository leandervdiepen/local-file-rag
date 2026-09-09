# PyInstaller build of the sidecar, as one directory next to the app bundle.
#
# onedir, not onefile: onefile unpacks a gigabyte of torch to a temp directory
# on every launch, which turns a 1.5 s start into 20 s and writes the whole
# model runtime to disk each time the user opens the app.

from PyInstaller.utils.hooks import collect_all, collect_submodules

# These four decide at import time what to load, so nothing static finds their
# pieces: torch dispatches to backend libraries, transformers and
# sentence_transformers resolve model classes by name from config JSON, and
# lance ships a compiled extension with its own data.
BUNDLED = ("torch", "torchvision", "transformers", "sentence_transformers", "lance", "lancedb", "pypdfium2")

datas, binaries, hiddenimports = [], [], []
for package in BUNDLED:
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

# Vision and Quartz are reached through pyobjc's lazy framework loader, which
# imports by string, so the OCR path is invisible to the analysis.
hiddenimports += collect_submodules("objc")
hiddenimports += ["Vision", "Quartz", "CoreFoundation", "Foundation"]

# waitress serves the app and flask finds nothing that imports it.
hiddenimports += ["waitress", "waitress.server"]

analysis = Analysis(
    ["src/sidecar/interface/cli.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Nothing here is imported by the sidecar, and each drags in tens of
    # megabytes through torch's optional integrations.
    excludes=[
        "tkinter",
        "matplotlib",
        "pytest",
        "IPython",
        "notebook",
        "torch.distributed",
        "torch.testing",
        "tensorboard",
    ],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="sidecar",
    console=True,
    # The handshake is a line on stdout, so nothing may buffer it.
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    target_arch="arm64",
)

COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="sidecar",
)
