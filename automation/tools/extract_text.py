#!/usr/bin/env python3
"""Extract readable text from every document in a folder (recursive).

  extract_text.py <folder>

Writes <folder>/_text/<file>.txt for each PDF / DOCX / DOC / XLSX / TXT / HTML file and
prints a JSON summary. PDF text is split with "=== Page N ===" markers so findings can be
cited by page. Files that yield almost no text (scanned PDFs, images) are flagged
"low_text": read those directly with the Read tool instead.
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile

LOW_TEXT = 200


def run(cmd, timeout):
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if out.returncode:
        raise RuntimeError(f"{cmd[0]} exit {out.returncode}: {out.stderr.strip()[:200]}")
    return out


def pdf(path):
    out = run(["pdftotext", "-layout", path, "-"], 300)
    pages = out.stdout.split("\f")
    return "\n".join(f"=== Page {i} ===\n{p}" for i, p in enumerate(pages, 1) if p.strip())


def docx(path):
    import docx as d
    doc = d.Document(path)
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(parts)


def textutil(path):
    return run(["textutil", "-convert", "txt", "-stdout", path], 120).stdout


def xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"=== Sheet {ws.title} ===")
        for row in ws.iter_rows(values_only=True):
            if any(v not in (None, "") for v in row):
                parts.append(" | ".join("" if v is None else str(v) for v in row))
    return "\n".join(parts)


def plain(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


HANDLERS = {".pdf": pdf, ".docx": docx, ".doc": textutil, ".rtf": textutil, ".xlsx": xlsx,
            ".xlsm": xlsx, ".txt": plain, ".csv": plain, ".htm": textutil, ".html": textutil}


MAX_ZIP_BYTES = 500 * 1024 * 1024
MAX_ZIP_DEPTH = 3


def expand_archives(root, summary):
    """Unzip archives into sibling folders, repeating for nested zips (bounded)."""
    done = set()
    for _ in range(MAX_ZIP_DEPTH):
        found = False
        for dirpath, _, names in os.walk(root):
            if "_text" in dirpath.split(os.sep):
                continue
            for n in names:
                src = os.path.join(dirpath, n)
                if not n.lower().endswith(".zip") or n.startswith("_all_attachments") or src in done:
                    continue
                done.add(src)
                found = True
                try:
                    with zipfile.ZipFile(src) as z:
                        if sum(i.file_size for i in z.infolist()) > MAX_ZIP_BYTES:
                            raise RuntimeError("archive exceeds size limit; not extracted")
                        dest = os.path.realpath(os.path.join(dirpath, n[:-4]))
                        for info in z.infolist():
                            target = os.path.realpath(os.path.join(dest, info.filename))
                            if not target.startswith(dest + os.sep):
                                raise RuntimeError(f"unsafe path in archive: {info.filename}")
                        z.extractall(dest)
                except Exception as e:
                    summary.append({"file": os.path.relpath(src, root), "error": str(e)})
        if not found:
            break


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    summary = []
    expand_archives(root, summary)
    outdir = os.path.join(root, "_text")
    shutil.rmtree(outdir, ignore_errors=True)  # never leave stale text from an earlier run
    os.makedirs(outdir)
    used = set()
    for dirpath, _, names in os.walk(root):
        if "_text" in dirpath.split(os.sep):
            continue
        for n in sorted(names):
            ext = os.path.splitext(n)[1].lower()
            if ext not in HANDLERS:
                continue
            src = os.path.join(dirpath, n)
            rel = os.path.relpath(src, root)
            try:
                text = HANDLERS[ext](src)
                stem, k = rel.replace(os.sep, "__"), 2
                dest_name = stem + ".txt"
                while dest_name in used:
                    dest_name, k = f"{stem}_{k}.txt", k + 1
                used.add(dest_name)
                dest = os.path.join(outdir, dest_name)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(text)
                summary.append({"file": rel, "text": os.path.relpath(dest, root), "chars": len(text),
                                "low_text": len(text.strip()) < LOW_TEXT})
            except Exception as e:
                summary.append({"file": rel, "error": str(e)})
    print(json.dumps(summary, indent=2))
    if any("error" in s for s in summary):
        sys.exit(2)  # summary still printed; failed files have no text and must be reported


if __name__ == "__main__":
    main()
