#!/usr/bin/env python3
import os
import pathlib
import yaml

ROOT = pathlib.Path(".")
NB_ROOT = ROOT / "notebooks"      # directory to scan
TOC_PATH = ROOT / "_toc.yml"
BOOK_ROOT = "index"               # you need index.md or index.ipynb at repo root

# Return repo-relative stem path without extension, using forward slashes
def stem_path(p: pathlib.Path) -> str:
    rel = p.relative_to(ROOT)
    return str(rel.with_suffix("")).replace("\\", "/")

# Collect notebooks
all_nbs = sorted([p for p in NB_ROOT.rglob("*.ipynb")])

# Group by immediate subdirectory under notebooks/
chapters = []
by_dir = {}
for nb in all_nbs:
    # skip a top-level book root if someone put notebooks/index.* (avoid duplication)
    if nb.with_suffix("").name == "index" and nb.parent == ROOT:
        continue
    # group key: first segment after notebooks/
    try:
        key = nb.relative_to(NB_ROOT).parts[0]
    except ValueError:
        continue
    by_dir.setdefault(key, []).append(nb)

for dirname in sorted(by_dir):
    files = sorted(by_dir[dirname])
    # chapter file: if the folder has its own index.* use that; else first notebook
    folder = NB_ROOT / dirname
    folder_index = None
    for cand in [folder / "index.ipynb", folder / "index.md"]:
        if cand.exists():
            folder_index = cand
            break
    chapter_file = folder_index if folder_index else files[0]

    # sections: all other notebooks in that folder (exclude the chapter file)
    sections = []
    for f in files:
        if f.resolve() == chapter_file.resolve():
            continue
        sections.append({"file": stem_path(f)})

    chapter = {"file": stem_path(chapter_file)}
    if sections:
        chapter["sections"] = sections
    chapters.append(chapter)

toc = {
    "format": "jb-book",
    "root": BOOK_ROOT,
    "chapters": chapters
}

with open(TOC_PATH, "w", encoding="utf-8") as f:
    yaml.dump(toc, f, sort_keys=False, allow_unicode=True)

print(f"Wrote {TOC_PATH} with {sum(len(c.get('sections', [])) + 1 for c in chapters)} entries.")

