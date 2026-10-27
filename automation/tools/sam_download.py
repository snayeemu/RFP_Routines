#!/usr/bin/env python3
"""Download all attachments of a SAM.gov opportunity without a browser.

  sam_download.py <sam-url-or-opportunity-id> <out-dir>

1. Notice: saves the notice metadata and description text to <out-dir>/notice.txt (the
   description is part of the solicitation, often the whole of it).
2. Zip API: GET /opps/v3/opportunities/<id>/resources/download/zip -> {"location": signed S3
   URL valid ~9 s} -> download immediately -> unzip. A null location means no files.
3. Fallback: list /resources (excluding deleted) and download each file by resourceId.
   Per-file downloads can fail with "resource has been deleted" after the effective delete
   date even though the zip still works, which is why the zip is tried first.
External "link" resources are always listed in the manifest; follow them like a portal.
Writes <out-dir>/manifest.json and prints it. status: ok | partial | no-attachments | failed.
"""
import html
import json
import os
import re
import subprocess
import sys
import zipfile

API = "https://sam.gov/api/prod/opps"
UA = "Mozilla/5.0"
MAX_ZIP_BYTES = 500 * 1024 * 1024  # expanded size limit for untrusted archives
MAX_ZIP_MEMBERS = 500


def get(url, timeout=120):
    """Return (http_status, body). curl, not urllib: this Python build cannot verify HTTPS here."""
    out = subprocess.run(["curl", "-sSL", "--max-time", str(timeout), "-A", UA, "-w", "\n%{http_code}", url],
                         capture_output=True, timeout=timeout + 30)
    if out.returncode:
        raise RuntimeError(f"curl: {out.stderr.decode('utf-8', 'replace').strip()}")
    body, _, code = out.stdout.rpartition(b"\n")
    return int(code or 0), body


def get_json(url):
    code, body = get(url)
    if code != 200:
        raise RuntimeError(f"HTTP {code}: {body[:200].decode('utf-8', 'replace')}")
    return json.loads(body)


def opp_id(arg):
    m = re.search(r"([0-9a-f]{32})", arg)
    if not m:
        sys.exit(f"no 32-hex opportunity id in {arg!r}")
    return m.group(1)


def unique_path(folder, name):
    name = re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "file"
    base, ext = os.path.splitext(name)
    path, n = os.path.join(folder, name), 2
    while os.path.exists(path):
        path, n = os.path.join(folder, f"{base}_{n}{ext}"), n + 1
    return path


def save_notice(oid, out):
    d = get_json(f"{API}/v2/opportunities/{oid}?api_key=null")
    d2 = d.get("data2") or {}
    sol = d2.get("solicitation") or {}
    info = {"title": d2.get("title"), "solicitationNumber": d2.get("solicitationNumber"),
            "type": d2.get("type"), "naics": d2.get("naics"), "setAside": sol.get("setAside"),
            "responseDeadline": (sol.get("deadlines") or {}).get("response"),
            "postedDate": d.get("postedDate"), "archived": d.get("archived"), "cancelled": d.get("cancelled")}
    bodies = [x.get("body", "") for x in (d.get("description") or [])]
    text = html.unescape(re.sub(r"<[^>]+>", " ", "\n\n".join(bodies)))
    with open(os.path.join(out, "notice.txt"), "w", encoding="utf-8") as f:
        f.write(json.dumps(info, indent=2, default=str) + "\n\n=== Description ===\n" + text.strip() + "\n")
    return info


def list_resources(oid):
    d = get_json(f"{API}/v3/opportunities/{oid}/resources?api_key=null&excludeDeleted=true")
    files, links = [], []
    for group in d.get("_embedded", {}).get("opportunityAttachmentList", []):
        for a in group.get("attachments", []):
            if str(a.get("deletedFlag")) == "1":
                continue
            if a.get("type") == "link":
                links.append({"name": a.get("name"), "url": a.get("uri")})
            else:
                files.append(a)
    return files, links


def via_zip(oid, out):
    loc = get_json(f"{API}/v3/opportunities/{oid}/resources/download/zip?api_key=null").get("location")
    if not loc:
        return None  # SAM has no files for this notice
    code, data = get(loc)
    if code != 200 or data[:2] != b"PK":
        raise RuntimeError(f"zip download HTTP {code}")
    zpath = os.path.join(out, "_all_attachments.zip")
    with open(zpath, "wb") as f:
        f.write(data)
    names = []
    with zipfile.ZipFile(zpath) as z:
        members = [i for i in z.infolist() if not i.is_dir()]
        if len(members) > MAX_ZIP_MEMBERS or sum(i.file_size for i in members) > MAX_ZIP_BYTES:
            raise RuntimeError("zip exceeds size/member limits; not extracted")
        for info in members:
            target = unique_path(out, os.path.basename(info.filename))
            with z.open(info) as src, open(target, "wb") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
            names.append(os.path.basename(target))
    return names


def via_files(attachments, out):
    files, errors = [], []
    for a in attachments:
        name = a.get("name") or a["resourceId"]
        try:
            code, data = get(f"{API}/v3/opportunities/resources/files/{a['resourceId']}/download?api_key=null&token=")
            if code != 200:
                raise RuntimeError(f"HTTP {code}: {data[:200].decode('utf-8', 'replace')}")
            target = unique_path(out, name)
            with open(target, "wb") as f:
                f.write(data)
            files.append(os.path.basename(target))
        except Exception as e:
            errors.append(f"{name}: {e}")
    return files, errors


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    oid, out = opp_id(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    m = {"opportunity_id": oid, "sam_url": f"https://sam.gov/opp/{oid}/view", "notice": None,
         "method": None, "expected_files": None, "files": [], "links": [], "errors": []}
    try:
        m["notice"] = save_notice(oid, out)
    except Exception as e:
        m["errors"].append(f"notice: {e}")
    attachments = None
    try:
        attachments, m["links"] = list_resources(oid)
        m["expected_files"] = len(attachments)
    except Exception as e:
        m["errors"].append(f"resources: {e}")
    try:
        names = via_zip(oid, out)
        if names is not None:
            m["files"], m["method"] = names, "zip"
    except Exception as e:
        m["errors"].append(f"zip: {e}")
    if not m["files"] and attachments:
        m["files"], errs = via_files(attachments, out)
        m["errors"] += errs
        m["method"] = "per-file" if m["files"] else None

    real = [f for f in m["files"] if f != "Deleted Attachments.txt"]
    expected = m["expected_files"]
    file_errors = [e for e in m["errors"] if not e.startswith(("zip:", "notice:", "resources:"))]
    if real:
        complete = (expected is None or len(real) >= expected) and not file_errors
        m["status"] = "ok" if complete else "partial"
    elif expected == 0:
        m["status"] = "no-attachments"  # notice.txt (and any links) is the whole solicitation
    else:
        m["status"] = "failed"
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(m, f, indent=2, default=str)
    print(json.dumps(m, indent=2, default=str))


if __name__ == "__main__":
    main()
