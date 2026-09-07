"""The junk files the gate must skip, each tagged with its skip reason.

Scattered next to good files as well as under junk/, per the brief, so the
gate is exercised in realistic locations, not one quarantine folder.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen import canvas as canvas_mod

from corpus.manifest import Manifest
from corpus.rng import make_rng

TINY_IMAGES = 60
BAD_PDF = 12
ENCRYPTED_PDF = 5
BINARY_BLOBS = 36
OVERSIZE_BYTES = 210 * 1024 * 1024

SCATTER_DIRS = ["notes", "screenshots", "reports", "decks", "junk"]
BLOB_EXTENSIONS = [".bin", ".dylib", ".zip", ".sqlite"]

# screen_path settles type before it ever looks at size, so a file has to carry
# a supported extension to reach the empty or the oversized rule at all. An
# unsupported one is refused as unsupported_type whatever its size, which is
# why each of these lists is paired with the reason the gate will actually give.
EMPTY_SUPPORTED = [".txt", ".md", ".pdf", ".png"]
EMPTY_UNSUPPORTED = [".log", ".json"]
ZERO_BYTE_SUPPORTED = 15
ZERO_BYTE_UNSUPPORTED = 10

OVERSIZE_FILES = [
    ("reports", "scan-archive-2019.pdf", "oversized"),
    ("junk", "camera-roll-export.bin", "unsupported_type"),
    ("screenshots", "timelapse-raw.zip", "unsupported_type"),
]


def _scatter_dir(root: Path, index: int) -> Path:
    d = root / SCATTER_DIRS[index % len(SCATTER_DIRS)]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tiny_images(root: Path, manifest: Manifest, rng: random.Random) -> int:
    sizes = [(1, 1), (16, 16), (32, 32), (48, 48), (64, 64), (120, 90), (180, 40)]
    for i in range(TINY_IMAGES):
        w, h = sizes[i % len(sizes)]
        img = Image.new("RGB", (w, h), (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
        d = _scatter_dir(root, i)
        path = d / f"icon-{w}x{h}-{i}.png"
        img.save(path)
        manifest.add_skipped(path, "junk", "image_too_small")
    return TINY_IMAGES


def _zero_byte(root: Path, manifest: Manifest) -> int:
    plan = [
        (EMPTY_SUPPORTED[i % len(EMPTY_SUPPORTED)], "empty") for i in range(ZERO_BYTE_SUPPORTED)
    ]
    plan += [
        (EMPTY_UNSUPPORTED[i % len(EMPTY_UNSUPPORTED)], "unsupported_type")
        for i in range(ZERO_BYTE_UNSUPPORTED)
    ]
    for i, (ext, reason) in enumerate(plan):
        d = _scatter_dir(root, i + 3)
        path = d / f"empty-{i}{ext}"
        path.touch()
        manifest.add_skipped(path, "junk", reason)
    return len(plan)


def _bad_pdf(root: Path, manifest: Manifest) -> int:
    for i in range(BAD_PDF):
        d = _scatter_dir(root, i + 1)
        path = d / f"draft-report-{i}.pdf"
        path.write_bytes(b"This looks like a pdf but is not.\n")
        manifest.add_skipped(path, "junk", "corrupt")
    return BAD_PDF


def _encrypted_pdf(root: Path, manifest: Manifest) -> int:
    out_dir = root / "junk" / "protected"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(ENCRYPTED_PDF):
        path = out_dir / f"confidential-{i}.pdf"
        enc = StandardEncryption(f"user{i}", f"owner{i}", canPrint=0)
        c = canvas_mod.Canvas(str(path), pagesize=letter, encrypt=enc, invariant=1)
        c.drawString(72, 700, "This document is protected.")
        c.save()
        manifest.add_skipped(path, "junk", "encrypted")
    return ENCRYPTED_PDF


def _binary_blobs(root: Path, manifest: Manifest, rng: random.Random) -> int:
    for i in range(BINARY_BLOBS):
        ext = BLOB_EXTENSIONS[i % len(BLOB_EXTENSIONS)]
        d = _scatter_dir(root, i + 2)
        path = d / f"artifact-{i}{ext}"
        path.write_bytes(rng.randbytes(rng.randint(512, 4096)))
        manifest.add_skipped(path, "junk", "unsupported_type")
    return BINARY_BLOBS


def _ignored_paths(root: Path, manifest: Manifest) -> int:
    count = 0
    for d in ["screenshots", "notes", "junk"]:
        path = root / d / ".DS_Store"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x00\x00\x00\x01Bud1" + b"\x00" * 28)
        # Not excluded_path. The gate excludes hidden directories, not hidden
        # files, so that a user's own .notes.md stays findable. A .DS_Store is
        # refused for having no indexable type, like any other binary blob.
        manifest.add_skipped(path, "junk", "unsupported_type")
        count += 1

    nm = root / "junk" / "node_modules"
    (nm / "lodash").mkdir(parents=True, exist_ok=True)
    (nm / ".bin").mkdir(parents=True, exist_ok=True)
    for rel, content in [
        ("lodash/package.json", '{"name": "lodash", "version": "4.17.21"}\n'),
        ("lodash/index.js", "module.exports = {};\n"),
        ("lodash/README.md", "# lodash\n"),
        (".bin/eslint", "#!/bin/sh\necho eslint\n"),
    ]:
        path = nm / rel
        path.write_text(content)
        manifest.add_skipped(path, "junk", "excluded_path")
        count += 1

    git = root / "junk" / ".git"
    (git / "objects" / "ab").mkdir(parents=True, exist_ok=True)
    for rel, content in [
        ("HEAD", "ref: refs/heads/main\n"),
        ("config", "[core]\n\trepositoryformatversion = 0\n"),
        ("description", "Unnamed repository\n"),
        ("objects/ab/cdef1234deadbeef", "\x78\x9c\x03\x00\x00\x00\x00\x01"),
    ]:
        path = git / rel
        if rel.endswith("cdef1234deadbeef"):
            path.write_bytes(content.encode("latin1"))
        else:
            path.write_text(content)
        manifest.add_skipped(path, "junk", "excluded_path")
        count += 1
    return count


def _oversized(root: Path, manifest: Manifest) -> int:
    for dirname, name, reason in OVERSIZE_FILES:
        d = root / dirname
        d.mkdir(parents=True, exist_ok=True)
        path = d / name
        # Sparse. Seeking past the end and writing one byte makes stat report
        # the full size while the filesystem allocates a single block.
        with path.open("wb") as f:
            f.seek(OVERSIZE_BYTES - 1)
            f.write(b"\0")
        assert path.stat().st_size == OVERSIZE_BYTES
        manifest.add_skipped(path, "junk", reason)
    return len(OVERSIZE_FILES)


def generate(seed: int, root: Path, manifest: Manifest) -> int:
    rng = make_rng(seed, "junk")
    (root / "junk").mkdir(parents=True, exist_ok=True)
    total = 0
    total += _tiny_images(root, manifest, rng)
    total += _zero_byte(root, manifest)
    total += _bad_pdf(root, manifest)
    total += _encrypted_pdf(root, manifest)
    total += _binary_blobs(root, manifest, rng)
    total += _ignored_paths(root, manifest)
    total += _oversized(root, manifest)
    return total
