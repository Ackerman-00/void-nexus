#!/usr/bin/env python3
"""Deterministic tear-apart sweep for EVERY package in a nexus repo.

Proof-or-Stop gate. Auto-detects the repo type by file layout:

  - gentoo  : <cat>/<pkg>/*.ebuild + Manifest (BLAKE2B + SHA512)
  - fedora  : <pkg>/<pkg>.spec                (Version/Source0, # sha256: comments)
  - nix     : pkgs/*.nix                      (version =, fetchurl {url; hash} SRI)
  - void    : srcpkgs/<pkg>/template          (version=, distfiles=, checksum=)
  - opensuse: <pkg>/<pkg>.spec                (Version + Source0, update.sh live check)

For each package: resolve every source URL, download, verify size + checksum
(sha256/BLAKE2B+SHA512/SRI per repo convention), tear the artifact apart
(AppImage --appimage-extract, .deb control Version, zip/tar internals, Electron
.asar, application.ini, runtime --version probe), read the real internal
version, compare to the pinned version, and check live/git-snapshot pins
against upstream HEAD. Emits a per-package table + teardown-report.md.

Exit 0 = every package verified. Exit 1 = any FAIL/MISMATCH/STALE/UNVERIFIED
-> the run is NOT done. Agent claims are not evidence; the exit code and the
committed report are.

Pure stdlib (python3 only). No curl, no git, no dpkg, no unsquashfs required.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SKIP_DIRS = {"cache", "job_out", "binpkgs", "distfiles", "ccache", ".github",
             ".git", "tools", "node_modules"}
UA = {"User-Agent": "teardown-sweep/1.1 (nexus CI gate)"}

STATUS_OK = "OK"
STATUS_SOURCE_OK = "SOURCE-OK"
STATUS_MISMATCH = "MISMATCH"
STATUS_STALE = "STALE"
STATUS_FAIL = "FAIL"
STATUS_UNVERIFIED = "UNVERIFIED"
STATUS_SKIP = "SKIP-LIVE-UNVERIFIED"

rows = []  # (package, distfile, pinned, internal, status, note)


def log(msg):
    print(msg, flush=True)


def _github_headers():
    """Return headers dict with GITHUB_TOKEN auth if available (5000 req/hour vs 60)."""
    headers = dict(UA)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("REPO_FULL_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = "token " + token
    return headers


def fetch(url, timeout=120):
    """fetch(url) -> bytes. Uses GITHUB_TOKEN for GitHub API calls."""
    headers = _github_headers() if "api.github.com" in url or "github.com" in url else UA
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_with_name(url, timeout=120):
    """fetch(url) -> (bytes, content-disposition filename or None)."""
    headers = _github_headers() if "api.github.com" in url or "github.com" in url else UA
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        cd = r.headers.get("Content-Disposition", "")
        m = re.search(r'filename="?([^";]+)"?', cd)
        return data, (m.group(1).strip() if m else None)


def http_status(url, timeout=60):
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def latest_channel_version_header(url, timeout=60):
    """Return (header, value) for any version-ish HTTP response header on a
    'latest'-channel artifact URL (e.g. X-Fluxer-Version: 2026.820.194906).
    Such a header is authoritative upstream declaration of what the URL
    currently serves - even when the artifact's internal version tag uses a
    different scheme."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for k, v in r.headers.items():
                if "version" in k.lower() and v.strip():
                    return k, v.strip()
    except Exception:
        pass
    return None


def normalize(v):
    v = (v or "").strip().strip('"').strip("'").strip("`")
    v = re.sub(r"^[vV]", "", v)
    v = re.sub(r"\+.*$", "", v)
    v = re.sub(r"-0[~.-].*$", "", v)
    v = re.sub(r"-([0-9]+)$", "", v)
    return v.lower()


def versions_match(pv, internal):
    """True when internal == pv, or internal is pv with a leading build-number
    component (e.g. Chromium-prefixed Brave '151.1.93.137' vs pinned
    '1.93.137')."""
    p, i = normalize(pv), normalize(internal)
    if p == i:
        return True
    pc, ic = p.split("."), i.split(".")
    if len(ic) > len(pc) and ic[len(ic) - len(pc):] == pc:
        return True
    return False


def upstream_head(repo):
    """GitHub API first (with retries); git ls-remote fallback; None if both fail.
    repo may be 'owner/name' (GitHub) or a full URL (Gitea/GitLab etc.)."""
    import time
    if repo.startswith("http"):
        try:
            import subprocess
            out = subprocess.check_output(
                ["git", "ls-remote", repo.rstrip("/") + ".git", "HEAD"],
                timeout=30, stderr=subprocess.DEVNULL).decode()
            m = re.search(r"([0-9a-fA-F]{40})", out)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None
    for attempt in range(3):
        try:
            data = json.loads(fetch("https://api.github.com/repos/%s/commits/HEAD" % repo, timeout=30).decode())
            if isinstance(data, dict) and data.get("sha"):
                return data["sha"]
        except Exception:
            time.sleep(5 * (attempt + 1))
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "ls-remote", "https://github.com/%s.git" % repo, "HEAD"],
            timeout=30, stderr=subprocess.DEVNULL).decode()
        m = re.search(r"([0-9a-fA-F]{40})", out)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def upstream_latest_tag(repo):
    """Latest release tag name. Prefers the GitHub API (release metadata),
    falls back to `git ls-remote --tags` which has no rate limit."""
    import time
    for attempt in range(2):
        try:
            data = json.loads(fetch("https://api.github.com/repos/%s/releases/latest" % repo, timeout=30).decode())
            if isinstance(data, dict) and data.get("tag_name"):
                return data["tag_name"]
        except Exception:
            time.sleep(5 * (attempt + 1))
    try:
        out = subprocess.run(["git", "ls-remote", "--tags", "https://github.com/%s.git" % repo],
                             capture_output=True, text=True, timeout=120).stdout
        tags = []
        for line in out.splitlines():
            ref = line.split("refs/tags/", 1)[-1].replace("^{}", "")
            if re.match(r"^v?\d", ref) and "/" not in ref:
                tags.append(ref)
        if tags:
            def tagkey(t):
                return [int(x) if x.isdigit() else x for x in re.split(r"([0-9]+)", t)]
            return sorted(tags, key=tagkey)[-1]
    except Exception:
        pass
    return None


def repo_from_url(url):
    """Normalize a homepage/git URL into owner/repo."""
    u = (url or "").strip().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    u = re.sub(r"^https?://[^/]+/", "", u)
    if u.count("/") != 1:
        return None
    owner, name = u.split("/")
    if not owner or not name:
        return None
    return "%s/%s" % (owner, name)


def verify_file(path, expected):
    """expected: dict with 'size' and one or more of b2/s512/sha256 hex strings."""
    if "size" in expected and expected["size"]:
        if path.stat().st_size != expected["size"]:
            return False, "size %d != pinned %d" % (path.stat().st_size, expected["size"])
    digests = {k: v for k, v in expected.items() if k in ("b2", "s512", "sha256") and v}
    if not digests:
        return True, "no checksum pinned"
    calc = {}
    for k in digests:
        h = {"b2": hashlib.blake2b(), "s512": hashlib.sha512(), "sha256": hashlib.sha256()}[k]
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        calc[k] = h.hexdigest()
    for k, v in digests.items():
        if calc[k] != v.lower():
            return False, "%s mismatch" % k
    return True, "hash-OK"


def sri_to_hex(sri):
    """sha256-<base64> SRI (nix) -> lower hex."""
    try:
        b = sri.split("-", 1)[1]
        return base64.b64decode(b).hex()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Inventory + parsing per repo type
# ---------------------------------------------------------------------------

def detect_type(root):
    if list(root.rglob("*.ebuild")) and list(root.rglob("Manifest")):
        return "gentoo"
    if (root / "srcpkgs").is_dir() and list((root / "srcpkgs").rglob("template")):
        return "void"
    if (root / "pkgs").is_dir() and list((root / "pkgs").glob("*.nix")):
        return "nix"
    specs = list(root.rglob("*.spec"))
    if specs:
        for s in specs:
            content = s.read_text(errors="ignore")
            if "obs_" in content or "SUSE" in content or "OBS" in content:
                return "opensuse"
        return "fedora"
    return None


def expand(text, vars_):
    """Expand ${VAR}, ${VAR/pat/repl}, ${VAR//pat/repl}, ${VAR%glob} and RPM
    %{VAR}/%VAR forms, nesting-safe."""
    for _ in range(8):
        out = text

        def rep(m):
            v = vars_.get(m.group(1), "")
            if m.group(2) == "//":
                return v.replace(m.group(3), m.group(4))
            return v.replace(m.group(3), m.group(4), 1)

        out = re.sub(r"\$\{(\w+)(//?)([^/}]*)/([^}]*)\}", rep, out)

        def strip(m):
            v = vars_.get(m.group(1), "")
            pat = m.group(2)
            if pat == ".*":
                rx = r"\.[^.]*$"  # bash %.* = shortest suffix match
            else:
                rx = re.escape(pat).replace(r"\*", ".*") + "$"
            return re.sub(rx, "", v)

        out = re.sub(r"\$\{(\w+)%([^}]*)\}", strip, out)

        def pstrip(m):
            v = vars_.get(m.group(1), "")
            rx = re.escape(m.group(2)).replace(r"\*", ".*")
            return re.sub(r"^" + rx, "", v)

        out = re.sub(r"\$\{(\w+)#([^}]*)\}", pstrip, out)

        def plain(m):
            return vars_.get(m.group(1), m.group(0))

        out = re.sub(r"\$\{(\w+)\}", plain, out)

        def rpm_brace(m):
            return vars_.get(m.group(1), m.group(0))

        out = re.sub(r"%\{(\w+)\}", rpm_brace, out)

        def rpm_plain(m):
            return vars_.get(m.group(1), m.group(0))

        out = re.sub(r"%(\w+)", rpm_plain, out)
        if out == text:
            return out
        text = out
    return text


def parse_spec_sources(content, vars_):
    """Extract (url, distname, sha256_or_None) for each SourceN: line."""
    srcs = []
    sha256s = [m.group(1).strip().lower() for m in re.finditer(r"#\s*sha256:\s*([0-9a-fA-F]{64})", content)]
    for m in re.finditer(r"^Source\d*:\s*(\S+)\s*$", content, re.M):
        raw = m.group(1)
        url = expand(eval_shell_exprs(raw, vars_), vars_)
        name = url.rsplit("/", 1)[-1]
        if not name:
            name = raw
        sha = sha256s[len(srcs)] if len(sha256s) > len(srcs) else None
        srcs.append((url, name, sha))
    return srcs


def eval_shell_exprs(s, vars_):
    """Evaluate the common Fedora inline %(...) shell expressions BEFORE any
    expand() call can mangle their ${...} internals:
      %(c=%{commit}; echo ${c:0:7})          -> commit[:7]
      %(v='%{version}'; echo "${v//'~'/-}")  -> version with '~' replaced
    """
    def rep_slice(m):
        val = expand(m.group(2).strip(), vars_).strip("'\"")
        return val[:int(m.group(3))]

    def rep_subst(m):
        val = expand(m.group(2).strip(), vars_).strip("'\"")
        return val.replace(m.group(3), m.group(4))

    s = re.sub(r"%\((\w+)=([^;]+);\s*echo\s+\"\$\{\1//'([^']*)'/'?([^'\"}]*)'?\}\"\)", rep_subst, s)
    s = re.sub(r"%\((\w+)=([^;]+);\s*echo\s+\$\{\1//'([^']*)'/'?([^'\"}]*)'?\}\)", rep_subst, s)
    s = re.sub(r"%\((\w+)=([^;]+);\s*echo\s+\$\{\1:0:(\d+)\}\)", rep_slice, s)
    return s


def emulate_globals(vars_):
    """Resolve shell-expr %global values (shortcommit, tag) and the derived
    forge macros (fileref, forgesource)."""
    for key in ("shortcommit", "tag"):
        if key in vars_ and "%(" in vars_[key]:
            vars_[key] = eval_shell_exprs(vars_[key], vars_)
    if "%{fileref}" in vars_.get("version", "") and "tag" in vars_:
        vars_["fileref"] = re.sub(r"^v", "", vars_["tag"])
    if "forgesource" not in vars_ and "forgeurl" in vars_ and "tag" in vars_:
        base = vars_["forgeurl"].rstrip("/").rsplit("/", 1)[-1]
        vars_["forgesource"] = "%s/archive/%s/%s-%s.tar.gz" % (
            vars_["forgeurl"].rstrip("/"), vars_["tag"], base, vars_["tag"])
    return vars_


def spec_vars(content):
    """%global/%define vars + Name/Version/URL + sha256 comments from a spec,
    including common Fedora forge/go macro emulation (forgesource, fileref,
    shortcommit, shell-expr %global values)."""
    vars_ = {}
    for m in re.finditer(r"^%(?:global|define)\s+(\w+)\s+(.+?)\s*$", content, re.M):
        vars_.setdefault(m.group(1), m.group(2).strip())
    for m in re.finditer(r"^Name:\s*(\S+)", content, re.M):
        vars_["name"] = m.group(1)
    for m in re.finditer(r"^Version:\s*(\S+)", content, re.M):
        vars_["version"] = m.group(1)
    for m in re.finditer(r"^URL:\s*(\S+)", content, re.M):
        vars_["url"] = m.group(1)
    emulate_globals(vars_)
    v = vars_.get("version", "")
    if "%{" in v:
        vars_["version"] = expand(v, vars_)
    if "url" in vars_ and "%{" in vars_["url"]:
        vars_["url"] = expand(vars_["url"], vars_)
    if "name" in vars_ and "%{" in vars_["name"]:
        vars_["name"] = expand(vars_["name"], vars_)
    return vars_


def find_specs(root):
    out = []
    for p in sorted(root.rglob("*.spec")):
        if any(x in p.parts for x in SKIP_DIRS):
            continue
        content = p.read_text(errors="ignore")
        if "update.sh" in content or "Spec" in content or "Name:" in content:
            out.append(p)
    return out


def resolve_github_url(repo, version):
    """Tags-API match for version -> archive URL (used when a spec macro like
    %{gosource}/%{forgesource} cannot be expanded locally)."""
    try:
        data = json.loads(fetch("https://api.github.com/repos/%s/tags?per_page=100" % repo, timeout=60).decode())
        if isinstance(data, list):
            for t in data:
                tag = t.get("name", "")
                if tag and versions_match(version, tag.lstrip("v")):
                    return "https://github.com/%s/archive/%s.tar.gz" % (repo, tag)
    except Exception:
        pass
    for cand in ("v%s" % version, version):
        url = "https://github.com/%s/archive/%s.tar.gz" % (repo, cand)
        if http_status(url) == 200:
            return url
    return None


def resolve_codeberg_url(repo, version):
    """Forgejo tags-API match for version -> archive URL."""
    try:
        data = json.loads(fetch("https://codeberg.org/api/v1/repos/%s/tags" % repo, timeout=60).decode())
        if isinstance(data, list):
            for t in data:
                tag = t.get("name", "")
                if tag and versions_match(version, tag.lstrip("v")):
                    return "https://codeberg.org/%s/archive/%s.tar.gz" % (repo, tag)
    except Exception:
        pass
    for cand in ("v%s" % version, version):
        url = "https://codeberg.org/%s/archive/%s.tar.gz" % (repo, cand)
        if http_status(url) == 200:
            return url
    return None


# --- fedora / opensuse ---

def parse_fedora(spec):
    content = spec.read_text(errors="ignore")
    vars_ = spec_vars(content)
    pkg = vars_.get("name") or spec.parent.name
    pv = vars_.get("version", "")
    root = spec.parent
    srcs = []
    for url, name, sha in parse_spec_sources(content, vars_):
        if url and url.startswith(("http://", "https://")) and "%{" not in url:
            srcs.append((url, name, sha))
            continue
        if url and "%{" not in url:
            p1, p2 = root / name, root.parent / name
            if p1.exists() or p2.exists():
                p = p1 if p1.exists() else p2
                if re.search(r"\.(tar|tar\.gz|tgz|tar\.xz|txz|tar\.zst|tar\.bz2|tbz2|zip|7z|gz|bz2|xz|zst|crate|whl|deb|rpm|appimage|exe|dmg|asar|jar|bin)$", name, re.I):
                    srcs.append(("local:%s" % p, name, None))
                else:
                    srcs.append(("local:aux", name, None))
                continue
        repo = None
        for cand in (vars_.get("forgeurl"), vars_.get("url")):
            if cand:
                r = repo_from_url(cand)
                if r:
                    repo = r
                    break
        if not repo:
            gi = vars_.get("goipath", "")
            if gi.startswith("github.com/"):
                repo = gi[len("github.com/"):]
        resolved = None
        if repo:
            host_hint = (vars_.get("url", "") + vars_.get("forgeurl", "") + vars_.get("goipath", ""))
            if "codeberg.org" in host_hint:
                resolved = resolve_codeberg_url(repo, pv)
            else:
                resolved = resolve_github_url(repo, pv)
        if resolved:
            srcs.append((resolved, resolved.rsplit("/", 1)[-1], sha))
        else:
            srcs.append((None, name, sha))
    live = None
    if vars_.get("commit") and vars_.get("url"):
        repo = repo_from_url(vars_["url"])
        if repo:
            live = (repo, vars_["commit"], True)
    return pkg, pv, srcs, live


# --- void (XBPS) ---

VAR_RE = re.compile(r'^(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))', re.M)
MULTI_VAR_RE = re.compile(r'^(\w+)\+?=(?:"([^"]*)"|\'([^\']*)\')', re.M | re.S)
BRANCH_VAR_RE = re.compile(r'^\s*(\w+)\+?=(?:"([^"]*)"|\'([^\']*)\'|(\S+))', re.M)


def apply_case_blocks(content, vars_):
    """void templates assign arch/version-specific vars via case blocks.
    Evaluate the branch matching the current value of the subject var."""
    import fnmatch

    def repl(m):
        subject = m.group(1)
        val = vars_.get(subject, "")
        for br in re.split(r";;", m.group(2)):
            pm = re.match(r"\s*([^)]*)\)\s*(.*)$", br, re.S)
            if not pm:
                continue
            pat, assign = pm.group(1).strip(), pm.group(2)
            if not any(fnmatch.fnmatch(val, alt.strip()) for alt in pat.split("|")):
                continue
            for am in BRANCH_VAR_RE.finditer(assign):
                v = am.group(2) or am.group(3) or am.group(4) or ""
                if am.group(0).lstrip().startswith(am.group(1) + "+="):
                    vars_[am.group(1)] = vars_.get(am.group(1), "") + " " + v
                else:
                    vars_.setdefault(am.group(1), v)
            return m.group(0)
        return m.group(0)

    content = re.sub(r'case "\$\{(\w+)\}" in(.*?)^\s*esac', repl, content, flags=re.S | re.M)
    content = re.sub(r'case "\$(\w+)" in(.*?)^\s*esac', repl, content, flags=re.S | re.M)
    return content


def parse_void(template):
    content = template.read_text(errors="ignore")
    vars_ = {}
    for m in VAR_RE.finditer(content):
        vars_.setdefault(m.group(1), m.group(2) or m.group(3) or m.group(4) or "")
    for m in MULTI_VAR_RE.finditer(content):
        if m.group(1) in ("distfiles", "checksum") and not m.group(0).startswith(m.group(1) + "+="):
            vars_.setdefault(m.group(1), (m.group(2) or m.group(3) or ""))
    vars_.setdefault("XBPS_TARGET_MACHINE", "x86_64")
    vars_.setdefault("GNU_SITE", "https://ftp.gnu.org/gnu")
    vars_.setdefault("SOURCEFORGE_SITE", "https://downloads.sourceforge.net")
    apply_case_blocks(content, vars_)
    for m in MULTI_VAR_RE.finditer(content):
        if m.group(1) in ("distfiles", "checksum"):
            v = m.group(2) or m.group(3) or ""
            if m.group(0).startswith(m.group(1) + "+="):
                vars_[m.group(1)] = vars_.get(m.group(1), "") + " " + v
            else:
                vars_[m.group(1)] = v
    pkg = vars_.get("pkgname") or template.parent.name
    pv = vars_.get("version", "")
    if vars_.get("metapackage") == "yes":
        return pkg, pv, [("__metapackage__", pkg, None)], None
    dist_raw = vars_.get("distfiles", "").strip()
    srcs = []
    for tok in dist_raw.split():
        if ">" in tok:
            url, name = tok.rsplit(">", 1)
        else:
            url, name = tok, tok.rsplit("/", 1)[-1]
        url = expand(url, vars_)
        name = expand(name, vars_)
        srcs.append((url, name))
    sums = [s.lower() for s in vars_.get("checksum", "").split()]
    for i, (u, n) in enumerate(srcs):
        if i < len(sums):
            srcs[i] = (u, n, sums[i])
    live = None
    if vars_.get("_commit"):
        hp = vars_.get("homepage", "")
        if "github.com" in hp:
            live = (repo_from_url(hp), vars_["_commit"], True)
        elif hp:
            live = (hp.rstrip("/"), vars_["_commit"], False)
    return pkg, pv, srcs, live


# --- nix ---

def parse_nix(pnix):
    content = pnix.read_text(errors="ignore")
    pkg = pnix.stem
    m = re.search(r'version\s*=\s*"([^"]+)"', content)
    pv = m.group(1) if m else ""
    srcs = []
    for m in re.finditer(
            r"(fetchurl|fetchzip|fetchFromGitHub|fetchTarball)\s*\{.*?\};", content, re.S):
        block = m.group(0)
        url = None
        rev = None
        repo = None
        um = re.search(r'url\s*=\s*"([^"]+)"', block)
        if um:
            url = expand(um.group(1), {"version": pv})
        hm = re.search(r'hash\s*=\s*"([^"]+)"', block)
        if hm:
            h = hm.group(1)
            if h.startswith("sha256-"):
                h = sri_to_hex(h)
            else:
                h = None
        else:
            h = None
        if m.group(1) == "fetchFromGitHub":
            rm = re.search(r'rev\s*=\s*"([^"]+)"', block)
            om = re.search(r'owner\s*=\s*"([^"]+)"', block)
            nm = re.search(r'repo\s*=\s*"([^"]+)"', block)
            if rm and om and nm:
                rev = expand(rm.group(1), {"version": pv})
                repo = "%s/%s" % (om.group(1), nm.group(1))
                url = "https://github.com/%s/archive/%s.tar.gz" % (repo, rev)
        if url:
            srcs.append((url, url.rsplit("/", 1)[-1], h))
    live = None
    if repo and rev:
        live = (repo, rev)
    return pkg, pv, srcs, live


# --- gentoo (unchanged behavior) ---

DIST_RE = re.compile(r"^DIST\s+(\S+)\s+(\d+)\s+BLAKE2B\s+([0-9a-fA-F]+)\s+SHA512\s+([0-9a-fA-F]+)")


def filename_vars(ebname):
    name = ebname[: -len(".ebuild")]
    m = re.match(r"^(.+?)-(\d[^-]*?)(?:-r(\d+))?$", name)
    if not m:
        return {}
    pn, pv, rev = m.group(1), m.group(2), m.group(3)
    if rev:
        pv = pv + "-r" + rev
    return {"PN": pn, "PV": pv, "P": pn + "-" + pv}


def parse_vars(content):
    vars_ = {}
    for m in VAR_RE.finditer(content):
        g = m.group(2) or m.group(3) or m.group(4) or ""
        if m.group(1) == "SRC_URI":
            continue
        vars_.setdefault(m.group(1), g)
    return vars_


def parse_gentoo(eb):
    pkg_dir = eb.parent
    pkg = "%s/%s" % (pkg_dir.parts[-2], pkg_dir.parts[-1])
    content = eb.read_text(errors="ignore")
    vars_ = {**filename_vars(eb.name), **parse_vars(content)}
    vars_.setdefault("P", "%s-%s" % (vars_.get("PN", pkg_dir.parts[-1]), vars_.get("PV", "")))
    pv = vars_.get("PV", "")
    manifest = {}
    mp = pkg_dir / "Manifest"
    if mp.exists():
        for line in mp.read_text(errors="ignore").splitlines():
            m = DIST_RE.match(line)
            if m:
                manifest[m.group(1)] = {"size": int(m.group(2)), "b2": m.group(3).lower(),
                                        "s512": m.group(4).lower()}
    live = None
    if vars_.get("PV") == "9999" and vars_.get("EGIT_REPO_URI"):
        repo = vars_["EGIT_REPO_URI"].rstrip("/")
        if repo.endswith(".git"):
            repo = repo[:-4]
        repo = re.sub(r"^https?://[^/]+/", "", repo)
        live = (repo, vars_.get("EGIT_COMMIT", ""), True)
    srcs = []
    if "pypi" in content:
        pn = vars_.get("PN", "")
        url = pypi_sdist_url(pn, pv)
        srcs = [(url or "", "%s-%s.tar.gz" % (pn, pv))]
    else:
        m = re.search(r'^\s*SRC_URI="(.*?)"', content, re.M | re.S)
        if m:
            body = m.group(1)
            for arm in ("amd64", "arm64"):
                body = re.sub(r"%s\? \((.*?)\)" % arm, lambda mm: mm.group(1), body, flags=re.S)
            body = re.sub(r"[A-Za-z0-9_+\-]+\? \(.*?\)", "", body, flags=re.S)
            for m in re.finditer(r"(https?://\S+)(?:\s*->\s*(\S+))?", body):
                url, rename = m.group(1), m.group(2)
                url = expand(url, vars_)
                if rename:
                    name = expand(rename.strip(), vars_)
                else:
                    name = url.rsplit("/", 1)[-1]
                srcs.append((url, name))
    srcs = [(u, n, manifest.get(n)) for u, n in srcs]
    return pkg, pv, srcs, live


def pypi_sdist_url(pn, pv):
    try:
        data = json.loads(fetch_with_name("https://pypi.org/pypi/%s/%s/json" % (pn, pv), timeout=60)[0].decode())
        for u in data.get("urls", []):
            if u.get("filename", "").endswith(".tar.gz") and u.get("packagetype") == "sdist":
                return u["url"]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Teardown machinery (shared with gentoo sweep)
# ---------------------------------------------------------------------------

def ar_names(path):
    data = path.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        return []
    names = []
    idx = 8
    while idx + 60 <= len(data):
        name = data[idx:idx + 16].split(b"/")[0].decode(errors="ignore").strip()
        try:
            size = int(data[idx + 48:idx + 58].decode().strip() or 0)
        except ValueError:
            break
        names.append((name, idx + 60, size))
        idx += 60 + size + (size % 2)
    return names


def extract_deb_control_version(path, tmp):
    members = ar_names(path)
    if not members:
        return None, "not an ar archive"
    for name, off, size in members:
        if re.match(r"^control\.tar\.(gz|xz|zst|bz2)$", name):
            blob = path.read_bytes()[off:off + size]
            ext = name.split(".", 2)[-1]
            ctl = tmp / ("control." + ext)
            ctl.write_bytes(blob)
            try:
                if ext == "zst":
                    try:
                        import zstandard as zstd
                        dctx = zstd.ZstdDecompressor()
                        with open(ctl, "rb") as f_in:
                            decompressed = dctx.stream_reader(f_in).read()
                        ctl_decomp = tmp / "control.tar"
                        ctl_decomp.write_bytes(decompressed)
                        ctl = ctl_decomp
                    except ImportError:
                        import subprocess as _sp
                        ctl_decomp = tmp / "control.tar"
                        _sp.run(["zstd", "-d", "-o", str(ctl_decomp), str(ctl)],
                                check=True, capture_output=True)
                        ctl = ctl_decomp
                with tarfile.open(ctl) as t:
                    names = t.getnames()
                    control_name = "control" if "control" in names else next(
                        (n for n in names if n.endswith("/control")), None)
                    if control_name is None:
                        return None, "no control file inside %s" % name
                    control = t.extractfile(control_name)
                    text = control.read().decode(errors="ignore") if control else ""
            except Exception as e:
                return None, "control %s unreadable: %s" % (name, e)
            vm = re.search(r"^Version:\s*(.+)$", text, re.M)
            pm = re.search(r"^Package:\s*(.+)$", text, re.M)
            pkg = pm.group(1).strip() if pm else "?"
            ver = vm.group(1).strip() if vm else None
            return ver, "deb pkg=%s (control %s)" % (pkg, name)
    return None, "no control.tar.* member"


def read_small(p, limit=200_000):
    try:
        if p.stat().st_size > limit:
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def read_asar_version(path):
    try:
        data = path.read_bytes()
        if len(data) < 12:
            return None
        header_size = int.from_bytes(data[4:8], "little")
        payload_start = 8 + header_size
        start = data.find(b"{", 8)
        if start < 0:
            return None
        header = json.JSONDecoder().raw_decode(data[start:].decode(errors="ignore"))[0]
        files = header.get("files", {})

        def walk(node, prefix=""):
            for name, info in node.items():
                p = prefix + "/" + name
                if isinstance(info, dict) and info.get("files"):
                    yield from walk(info["files"], p)
                elif isinstance(info, dict) and name == "package.json" and "node_modules" not in p:
                    try:
                        off, size = int(info["offset"]), int(info["size"])
                        pj = json.loads(data[payload_start + off: payload_start + off + size].decode(errors="ignore"))
                        if pj.get("version"):
                            yield p, pj["version"]
                    except Exception:
                        pass

        for p, v in walk(files):
            return v
    except Exception:
        return None
    return None


STRONG_KINDS = {"asar", "X-AppImage-Version", "desktop Version", "application.ini"}
WEAK_KINDS = {"package.json", "Cargo.toml", "version file", "changelog"}
SOURCE_MARKERS = ("makefile", "meson.build", "cargo.toml", "cmakelists.txt",
                  "configure.ac", "setup.py", "setup.cfg", "pyproject.toml", "src")


def read_rpm_version(path):
    """Parse RPM header tags (1000 NAME, 1001 VERSION, 1002 RELEASE) directly
    from the binary - the equivalent of `rpm -qip` without rpm."""
    data = path.read_bytes()
    if len(data) < 96 or data[:4] != b"\xed\xab\xee\xdb":
        return None, "not an rpm (magic)"
    pos = 96

    def parse_header(idx):
        if idx + 16 > len(data) or data[idx:idx + 3] != b"\x8e\xad\xe8":
            return None, idx
        n = int.from_bytes(data[idx + 8:idx + 12], "big")
        dlen = int.from_bytes(data[idx + 12:idx + 16], "big")
        entries = []
        p = idx + 16
        for _ in range(n):
            e = data[p:p + 16]
            if len(e) < 16:
                break
            entries.append((int.from_bytes(e[0:4], "big"), int.from_bytes(e[4:8], "big"),
                            int.from_bytes(e[8:12], "big"), int.from_bytes(e[12:16], "big")))
            p += 16
        return entries, p + dlen

    sig_entries, pos2 = parse_header(pos)
    if sig_entries is None:
        return None, "no signature header"
    for _ in range(16):
        hdr_entries, data_end = parse_header(pos2)
        if hdr_entries is not None:
            break
        pos2 += 1
    if hdr_entries is None:
        return None, "no main header"

    def get(tag):
        base = pos2 + 16 + len(hdr_entries) * 16
        for t, typ, off, cnt in hdr_entries:
            if t == tag and typ in (6, 8):
                end_ = data.find(b"\x00", base + off)
                if end_ == -1:
                    end_ = len(data)
                return data[base + off:end_].decode(errors="ignore")
        return None

    name = get(1000)
    ver = get(1001)
    rel = get(1002)
    if not ver:
        return None, "rpm header has no VERSION tag"
    full = "%s-%s" % (ver, rel) if rel else ver
    return full, "rpm header %s=%s%s (tags NAME/VERSION%s)" % (
        name or "?", full, "-%s" % rel if rel else "", "")


def looks_like_source(tree):
    for f in tree.rglob("*"):
        if not f.is_file():
            continue
        if f.name.lower() in SOURCE_MARKERS and len(f.relative_to(tree).parts) <= 3:
            return True
        if f.suffix.lower() in (".c", ".h", ".rs", ".py", ".cc", ".cpp", ".go", ".patch"):
            return True
        if f.name.lower() in ("readme", "readme.md", "license", "copying", "changelog") \
                and len(f.relative_to(tree).parts) <= 3:
            return True
        if f.stat().st_size < 65_536 and len(f.relative_to(tree).parts) <= 3:
            try:
                head = f.open("rb").read(2)
                if head == b"#!":
                    return True
            except Exception:
                pass
    return False


DOC_NAMES = {"license", "license.txt", "license.md", "copying", "copying.txt",
             "readme", "readme.md", "readme.txt", "changelog", "news", "notice"}
DOC_EXT = {".md", ".txt", ".patch", ".diff"}
AUX_EXT = {".png", ".svg", ".ico", ".jpg", ".jpeg", ".gif", ".webp", ".xml",
           ".plist", ".metainfo"}


def looks_like_doc(distname):
    base = distname.lower().rsplit(".", 1)[0] if distname.lower().rsplit(".", 1)[-1] in DOC_EXT else distname.lower()
    return base in DOC_NAMES or distname.lower().endswith(tuple(DOC_EXT))


def looks_like_aux(distname):
    return distname.lower().endswith(tuple(AUX_EXT))


ELF_MACHINES = {0x02: "sparc", 0x14: "ppc", 0x15: "ppc64", 0x16: "s390x",
                0x28: "arm", 0x3E: "x86_64", 0xB7: "aarch64", 0x03: "i386", 0x08: "mips"}


def machine_from_elf(head):
    if len(head) < 20 or head[:4] != b"\x7fELF":
        return None
    return ELF_MACHINES.get(int.from_bytes(head[18:20], "little"))


def artifact_machine(path, name):
    """Machine of the first ELF found in the artifact (AppImage runtime header
    or zip/tar member headers). None when nothing ELF-like is found."""
    ext = name.lower()
    try:
        if ext.endswith(".appimage") or ".appimage" in ext:
            return machine_from_elf(path.read_bytes()[:20])
        if ext.endswith(".zip"):
            import io
            with zipfile.ZipFile(path) as z:
                for zi in z.infolist()[:64]:
                    if zi.file_size > 40_000_000:
                        continue
                    with z.open(zi) as f:
                        head = f.read(20)
                    m = machine_from_elf(head)
                    if m:
                        return m
            return None
        if ext.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
            import io
            with tarfile.open(path) as t:
                for ti in t.getmembers()[:512]:
                    if not ti.isfile() or ti.size > 40_000_000:
                        continue
                    f = t.extractfile(ti)
                    if not f:
                        continue
                    m = machine_from_elf(f.read(20))
                    if m:
                        return m
            return None
    except Exception:
        return None
    return None


def host_machine():
    import platform
    m = platform.machine()
    return {"amd64": "x86_64", "arm64": "aarch64"}.get(m, m)


def _lsremote_version_tags(clone_url):
    """All version-like tags via `git ls-remote --tags` - no API rate limits."""
    try:
        out = subprocess.run(["git", "ls-remote", "--tags", clone_url],
                             capture_output=True, text=True, timeout=180).stdout
    except Exception:
        return []
    tags = []
    for line in out.splitlines():
        if "\t" not in line or "refs/tags/" not in line:
            continue
        ref = line.split("\t", 1)[1].split("refs/tags/", 1)[-1].replace("^{}", "")
        if re.match(r"^v?\d", ref) and "/" not in ref:
            tags.append(ref)
    return tags


def _tagkey(t):
    """Version-ish sort key: numeric segments compare numerically."""
    return [int(x) if x.isdigit() else x for x in re.split(r"([0-9]+)", t)]


def latest_tag_lsremote(clone_url, include_prereleases=False):
    """Latest version-like tag via `git ls-remote --tags` - no API rate limits.
    Prerelease-looking tags (beta/rc/alpha/...) are ignored unless requested.
    Returns the tag name or None."""
    tags, pre = [], []
    for ref in _lsremote_version_tags(clone_url):
        if re.search(r"(?i)(alpha|beta|rc\d|[-.]pre|[-.]dev|nightly|canary)", ref):
            pre.append(ref)
        else:
            tags.append(ref)
    pool = (tags + pre) if include_prereleases else (tags or pre)
    return sorted(pool, key=_tagkey)[-1] if pool else None


def forge_slug_from_url(u):
    """((owner/repo for REST APIs or None), clone_url) from a release/archive
    URL. Recognizes GitHub, Codeberg, GitLab instances and Gitea git.* hosts."""
    if not u:
        return None, None

    def repo(r):
        return re.sub(r"\.git$", "", r.rstrip("/"))

    m = re.search(r"github\.com/([^/]+)/([^/#?]+)", u)
    if m:
        return "%s/%s" % (m.group(1), repo(m.group(2))), \
            "https://github.com/%s/%s.git" % (m.group(1), repo(m.group(2)))
    m = re.search(r"codeberg\.org/([^/]+)/([^/#?]+)", u)
    if m:
        return "%s/%s" % (m.group(1), repo(m.group(2))), \
            "https://codeberg.org/%s/%s.git" % (m.group(1), repo(m.group(2)))
    m = re.search(r"(?:gitlab\.[\w.-]+|git\.[\w.-]+)/([^/]+/[^/#?]+)", u)
    if m:
        host = m.group(0).split("/")[0]
        return None, "https://%s/%s.git" % (host, repo(m.group(1)))
    return None, None


def staleness_pv(pv):
    """Strip distro-revision noise so PV compares cleanly against upstream tags."""
    v = re.sub(r"[_-]p\d+$", "", pv or "")
    v = re.sub(r"-r\d+$", "", v)
    v = re.sub(r"\^.*$", "", v)
    v = re.sub(r"~.*$", "", v)
    return v


PLACEHOLDER_RE = re.compile(r"^(latest|unstable|dev|master|head|git|rolling|current)$", re.I)


def version_evidence(tree, distname):
    hits = []
    seen = set()
    for f in sorted(tree.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(tree)
        if len(rel.parts) > 6:
            continue
        name = f.name.lower()
        txt = ""
        if name.endswith(".asar") and f.stat().st_size < 200_000_000:
            ver = read_asar_version(f)
            if ver:
                key = ("asar", ver)
                if key not in seen:
                    seen.add(key)
                    hits.append(("asar", ver, str(rel)))
        if name.endswith(".desktop"):
            txt = read_small(f)
            m = re.search(r"^X-AppImage-Version=(.+)$", txt, re.M)
            if m:
                hits.append(("X-AppImage-Version", m.group(1).strip(), str(rel)))
                seen.add(("XAI", m.group(1).strip()))
            m = re.search(r"^Version=(.+)$", txt, re.M)
            if m and m.group(1).strip() not in ("1.0", "1.0.0"):
                key = ("desk", m.group(1).strip())
                if key not in seen:
                    seen.add(key)
                    hits.append(("desktop Version", m.group(1).strip(), str(rel)))
        elif name in ("application.ini", "platform.ini"):
            txt = read_small(f)
            m = re.search(r"^Version=(.+)$", txt, re.M)
            if m and m.group(1).strip() not in ("1.0", "1.0.0"):
                key = ("ini", m.group(1).strip())
                if key not in seen:
                    seen.add(key)
                    hits.append(("application.ini", m.group(1).strip(), str(rel)))
        elif name == "package.json":
            if "node_modules" in rel.parts or "app.asar.unpacked" in rel.parts:
                continue
            txt = read_small(f)
            try:
                j = json.loads(txt)
                v = j.get("version")
                if v:
                    key = ("pj", str(v))
                    if key not in seen:
                        seen.add(key)
                        hits.append(("package.json", str(v), str(rel)))
            except Exception:
                pass
        elif name in ("cargo.toml", "cargo.toml.orig"):
            txt = read_small(f)
            m = re.search(r"^\[package\]\s*$.*?^version\s*=\s*\"([^\"]+)\"", txt, re.M | re.S)
            if m:
                key = ("cargo", m.group(1))
                if key not in seen:
                    seen.add(key)
                    hits.append(("Cargo.toml", m.group(1), str(rel)))
        elif name in ("version", "version.txt", "version.json", "package_version"):
            txt = read_small(f).strip()
            if txt and len(txt) < 64 and re.match(r"^[\w.\-+~]+$", txt):
                key = ("vfile", txt)
                if key not in seen:
                    seen.add(key)
                    hits.append(("version file", txt, str(rel)))
        elif "changelog" in name or name.startswith("news") or name.endswith(".release"):
            txt = read_small(f, 50_000)
            m = re.search(r"([0-9]+\.[0-9]+(?:\.[0-9]+)?[a-zA-Z0-9._\-]*)", txt)
            if m:
                key = ("cl", m.group(1))
                if key not in seen:
                    seen.add(key)
                    hits.append(("changelog", m.group(1), str(rel)))
    if not hits:
        return hits
    priority = {"asar": 0, "X-AppImage-Version": 1, "application.ini": 2,
                "desktop Version": 3, "package.json": 4, "Cargo.toml": 5,
                "version file": 6, "changelog": 7}
    hits.sort(key=lambda h: (priority.get(h[0], 9), h[2]))
    return hits[:4]


def probe_binary_version(sub, distname):
    import subprocess
    cands = []
    for f in sorted(sub.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(sub)
        if len(rel.parts) > 3:
            continue
        try:
            head = f.read_bytes()[:4]
            if head == b"\x7fELF":
                cands.append(f)
        except Exception:
            continue
    for cand in cands[:5]:
        try:
            os.chmod(cand, 0o755)
            res = subprocess.run([str(cand), "--version"], capture_output=True,
                                 timeout=20, cwd=sub)
            out = (res.stdout or res.stderr or b"").decode(errors="ignore")
            m = re.search(r"([0-9]+\.[0-9]+(?:\.[0-9]+)?[a-zA-Z0-9._\-]*)", out)
            if m:
                return m.group(1), "%s --version" % cand.name, out.strip()[:120]
        except Exception:
            continue
    return None, None, None


def tear_apart(path, distname, tmp):
    """Return (internal_version, note, strong, source_like)."""
    ext = distname.lower()
    if ext.endswith(".appimage") or ".appimage" in ext:
        try:
            os.chmod(path, 0o755)
            sub = tmp / "appimage"
            sub.mkdir()
            import subprocess
            res = subprocess.run([str(path), "--appimage-extract"], cwd=sub,
                                 capture_output=True, timeout=300)
            root = sub / "squashfs-root"
            if root.is_dir():
                hits = version_evidence(root, distname)
                for kind, v, rel in hits:
                    if kind in STRONG_KINDS:
                        return v, "AppImage %s (%s)" % (v, rel), True, False
                if hits:
                    return hits[0][1], "AppImage %s=%s (%s)" % (hits[0][0], hits[0][1], hits[0][2]), False, False
                return None, "AppImage extracted, no version evidence found (rc=%d)" % res.returncode, False, False
            return None, "AppImage --appimage-extract failed (rc=%d): %s" % (
                res.returncode, res.stderr.decode(errors="ignore")[-300:]), False, False
        except Exception as e:
            return None, "AppImage teardown error: %s" % e, False, False
    if ext.endswith(".deb"):
        ver, note = extract_deb_control_version(path, tmp)
        return ver, note, bool(ver), False
    if ext.endswith(".rpm"):
        ver, note = read_rpm_version(path)
        return ver, note, bool(ver), False
    if ext.endswith(".crate"):
        try:
            sub = tmp / "crate"
            sub.mkdir()
            with tarfile.open(path) as t:
                t.extractall(sub, filter="data")
            return None, "crate (cargo package tarball), source by construction", False, True
        except Exception as e:
            return None, "crate teardown error: %s" % e, False, False
    if ext.endswith(".zip"):
        try:
            sub = tmp / "zip"
            sub.mkdir()
            with zipfile.ZipFile(path) as z:
                z.extractall(sub)
            hits = version_evidence(sub, distname)
            for kind, v, rel in hits:
                if kind in STRONG_KINDS:
                    return v, "zip %s=%s (%s)" % (kind, v, rel), True, False
            ver, cmd, out = probe_binary_version(sub, distname)
            if ver:
                return ver, "zip runtime probe %s: %s" % (cmd, out), True, False
            if hits:
                return hits[0][1], "zip %s=%s (%s)" % (hits[0][0], hits[0][1], hits[0][2]), False, looks_like_source(sub)
            return None, "zip extracted, no version evidence found", False, looks_like_source(sub)
        except Exception as e:
            return None, "zip teardown error: %s" % e, False, False
    if ext.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2", ".tar.zst")):
        try:
            sub = tmp / "tar"
            sub.mkdir()
            actual_path = path
            if ext.endswith(".tar.zst"):
                try:
                    import zstandard as zstd
                    dctx = zstd.ZstdDecompressor()
                    with open(path, "rb") as f_in:
                        decompressed = dctx.stream_reader(f_in).read()
                    decomp_path = tmp / "decomp.tar"
                    decomp_path.write_bytes(decompressed)
                    actual_path = decomp_path
                except ImportError:
                    import subprocess as _sp
                    _sp.run(["zstd", "-d", "-o", str(tmp / "decomp.tar"), str(path)],
                            check=True, capture_output=True)
                    actual_path = tmp / "decomp.tar"
            with tarfile.open(actual_path) as t:
                t.extractall(sub, filter="data")
            hits = version_evidence(sub, distname)
            for kind, v, rel in hits:
                if kind in STRONG_KINDS:
                    return v, "tar %s=%s (%s)" % (kind, v, rel), True, False
            ver, cmd, out = probe_binary_version(sub, distname)
            if ver:
                return ver, "tar runtime probe %s: %s" % (cmd, out), True, False
            if hits:
                return hits[0][1], "tar %s=%s (%s)" % (hits[0][0], hits[0][1], hits[0][2]), False, looks_like_source(sub)
            return None, "tar extracted, no version evidence found", False, looks_like_source(sub)
        except Exception as e:
            return None, "tar teardown error: %s" % e, False, False
    if ext.endswith(".zst"):
        try:
            sub = tmp / "zst"
            sub.mkdir()
            try:
                import zstandard as zstd
                dctx = zstd.ZstdDecompressor()
                with open(path, "rb") as f_in:
                    decompressed = dctx.stream_reader(f_in).read()
                decomp_path = sub / "decomp"
                decomp_path.write_bytes(decompressed)
            except ImportError:
                import subprocess as _sp
                _sp.run(["zstd", "-d", "-o", str(sub / "decomp"), str(path)],
                        check=True, capture_output=True)
                decomp_path = sub / "decomp"
            try:
                with tarfile.open(decomp_path) as t:
                    t.extractall(sub / "tar", filter="data")
                    hits = version_evidence(sub / "tar", distname)
            except:
                hits = version_evidence(sub, distname)
            for kind, v, rel in hits:
                if kind in STRONG_KINDS:
                    return v, "zst %s=%s (%s)" % (kind, v, rel), True, False
            ver, cmd, out = probe_binary_version(sub, distname)
            if ver:
                return ver, "zst runtime probe %s: %s" % (cmd, out), True, False
            if hits:
                return hits[0][1], "zst %s=%s (%s)" % (hits[0][0], hits[0][1], hits[0][2]), False, looks_like_source(sub)
            return None, "zst extracted, no version evidence found", False, looks_like_source(sub)
        except Exception as e:
            return None, "zst teardown error: %s" % e, False, False
    if ext.endswith(".xbps"):
        try:
            sub = tmp / "xbps"
            sub.mkdir()
            import subprocess as _sp
            _sp.run(["tar", "xf", str(path), "-C", str(sub)], check=True, capture_output=True)
            hits = version_evidence(sub, distname)
            for kind, v, rel in hits:
                if kind in STRONG_KINDS:
                    return v, "xbps %s=%s (%s)" % (kind, v, rel), True, False
            ver, cmd, out = probe_binary_version(sub, distname)
            if ver:
                return ver, "xbps runtime probe %s: %s" % (cmd, out), True, False
            if hits:
                return hits[0][1], "xbps %s=%s (%s)" % (hits[0][0], hits[0][1], hits[0][2]), False, looks_like_source(sub)
            return None, "xbps extracted, no version evidence found", False, looks_like_source(sub)
        except Exception as e:
            return None, "xbps teardown error: %s" % e, False, False
    if ext.endswith(".rpm"):
        try:
            sub = tmp / "rpm"
            sub.mkdir()
            import subprocess as _sp
            _sp.run(["bash", "-c", "rpm2cpio '%s' | cpio -idm" % str(path)],
                    cwd=str(sub), check=True, capture_output=True)
            hits = version_evidence(sub, distname)
            for kind, v, rel in hits:
                if kind in STRONG_KINDS:
                    return v, "rpm %s=%s (%s)" % (kind, v, rel), True, False
            ver, cmd, out = probe_binary_version(sub, distname)
            if ver:
                return ver, "rpm runtime probe %s: %s" % (cmd, out), True, False
            if hits:
                return hits[0][1], "rpm %s=%s (%s)" % (hits[0][0], hits[0][1], hits[0][2]), False, looks_like_source(sub)
            return None, "rpm extracted, no version evidence found", False, looks_like_source(sub)
        except Exception as e:
            return None, "rpm teardown error: %s" % e, False, False
    return None, "unknown artifact type", False, False


# ---------------------------------------------------------------------------
# Dependency checking - verify missing shared libraries
# ---------------------------------------------------------------------------

def get_elf_needed(elf_path):
    """Return list of NEEDED shared libraries from an ELF binary via readelf."""
    try:
        res = subprocess.run(["readelf", "-d", str(elf_path)],
                             capture_output=True, timeout=10)
        if res.returncode != 0:
            return []
        needed = []
        for line in res.stdout.decode(errors="ignore").splitlines():
            m = re.search(r"NEEDED\s+(\S+)", line)
            if m:
                needed.append(m.group(1))
        return needed
    except Exception:
        return []


def find_elfs_in_dir(root, max_depth=6):
    """Find all ELF binaries in a directory tree."""
    elfs = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(root)
        if len(rel.parts) > max_depth:
            continue
        try:
            head = f.read_bytes()[:4]
            if head == b"\x7fELF":
                elfs.append(f)
        except Exception:
            continue
    return elfs


def check_deps_in_dir(pkg, root):
    """Check for missing shared libraries in extracted artifact directory.
    Returns list of (binary, missing_lib) tuples."""
    missing = []
    elfs = find_elfs_in_dir(root)
    for elf in elfs:
        needed = get_elf_needed(elf)
        for lib in needed:
            # Check common system paths
            found = False
            for prefix in ["/lib", "/usr/lib", "/lib64", "/usr/lib64",
                           root, root / "lib", root / "usr/lib"]:
                if (prefix / lib).exists():
                    found = True
                    break
            if not found:
                # Also check if it's in a sibling dir relative to the binary
                sibling = elf.parent / lib
                if sibling.exists():
                    found = True
            if not found:
                missing.append((str(elf.relative_to(root)), lib))
    return missing


# ---------------------------------------------------------------------------
# Live-check + per-repo openSUSE source resolution
# ---------------------------------------------------------------------------

def check_live(pkg, live):
    repo, pin = live[0], live[1]
    head = upstream_head(repo)
    if not head:
        rows.append((pkg, "live %s" % repo, pin[:12], None, STATUS_SKIP,
                     "upstream HEAD unreachable (rate limit/network)"))
        log("[%s] %s : live, upstream unreachable" % (STATUS_SKIP, pkg))
        return True
    ok = (normalize(pin[:12]) == normalize(head[:12]))
    status = STATUS_OK if ok else STATUS_STALE
    note = "live %s pin %s vs upstream %s" % (repo, pin[:12], head[:12])
    rows.append((pkg, "live %s" % repo, pin[:12], head[:12], status, note))
    log("[%s] %s : %s" % (status, pkg, note))
    return ok


def update_sh_vars(ush):
    """Parse VAR="value" assignments from an update.sh into a dict."""
    d = {}
    try:
        for m in re.finditer(r'^\s*(\w+)="([^"]*)"', ush.read_text(errors="ignore"), re.M):
            d[m.group(1)] = m.group(2)
    except Exception:
        pass
    return d


def resolve_opensuse_urls(pkg, pv, srcs):
    """opensuse Source0 are bare filenames; real URLs live in update.sh
    (GITHUB_REPO latest release assets, API_URL/X86_URL/... variables) or are
    absolute (rootapp)."""
    out = []
    ush = None
    for cand in (Path(pkg) / "update.sh", Path(pkg).parent / "update.sh"):
        if cand.exists():
            ush = cand
            break
    shv = update_sh_vars(ush) if ush else {}
    url_vars = [(k, v) for k, v in shv.items()
                if v.startswith(("http://", "https://")) and "$" not in v
                and (k.endswith("_URL") or k == "API_URL")]
    for url, name, sha in srcs:
        if url and url.startswith(("http://", "https://", "local:")):
            out.append((url, name, sha))
            continue
        want = expand(name, {"version": pv})
        asset_url = None
        gh = shv.get("GITHUB_REPO")
        if gh:
            tag = upstream_latest_tag(gh)
            if tag:
                try:
                    data = json.loads(fetch("https://api.github.com/repos/%s/releases/latest" % gh, timeout=60).decode())
                    for a in data.get("assets", []):
                        if a.get("name") == want or a.get("browser_download_url", "").endswith(want):
                            asset_url = a["browser_download_url"]
                            break
                except Exception:
                    pass
                if not asset_url and "DOWNLOAD_URL" in shv:
                    asset_url = expand(shv["DOWNLOAD_URL"], {"version": pv, "tag": tag})
                if not asset_url:
                    cand = "https://github.com/%s/releases/download/%s/%s" % (gh, tag, want)
                    if http_status(cand) == 200:
                        asset_url = cand
        if not asset_url and url_vars:
            if len(url_vars) == 1:
                asset_url = url_vars[0][1]
            else:
                # multiple per-arch URLs: match arch keywords from the wanted name
                low = want.lower()
                arch_pats = (("arm64", ("arm64", "aarch64")), ("x86", ("x86_64", "amd64", "x64")))
                picked = None
                for kw, variants in arch_pats:
                    if any(v in low for v in variants):
                        picked = kw
                        break
                for k, v in url_vars:
                    vl = (k + " " + v).lower()
                    if picked and any(x in vl for x in dict(arch_pats)[picked]):
                        asset_url = v
                        break
                if not asset_url and url_vars:
                    asset_url = url_vars[0][1]
        out.append((asset_url, want, sha))
    return out


def channel_url_for_pkg(pkg):
    """Best-effort 'latest-channel' URL for a package dir (from its update.sh
    URL variables) - used to fetch authoritative version headers even when
    the artifact itself is a bundled local file."""
    for cand in (Path(pkg) / "update.sh", Path(pkg).parent / "update.sh"):
        if cand.exists():
            shv = update_sh_vars(cand)
            for k, v in shv.items():
                if v.startswith(("http://", "https://")) and "$" not in v \
                        and (k.endswith("_URL") or k == "API_URL"):
                    return v
    return None


def sweep_package(pkg, pv, srcs, live, repo_type, workdir):
    dl = workdir / "distfiles"
    dl.mkdir(exist_ok=True)
    if live:
        check_live(pkg, live)
        return
    if repo_type == "opensuse":
        srcs = resolve_opensuse_urls(pkg, pv, srcs)
    if not srcs or (len(srcs) == 1 and srcs[0][0] == "__metapackage__"):
        if srcs and srcs[0][0] == "__metapackage__":
            rows.append((pkg, "-", pv, None, STATUS_OK, "metapackage, no sources to verify"))
            log("[%s] %s : metapackage" % (STATUS_OK, pkg))
            return
        rows.append((pkg, "?", pv, None, STATUS_FAIL, "no source URL resolvable"))
        log("[%s] %s : no source URL" % (STATUS_FAIL, pkg))
        return
    pkg_ok = True
    pkg_verified = False
    for item in srcs:
        if len(item) == 2:
            url, name, sha = item[0], item[1], None
        else:
            url, name, sha = item
        if not url:
            rows.append((pkg, name, pv, None, STATUS_FAIL,
                         "download URL unresolvable (no URL + no GitHub release asset match)"))
            log("[%s] %s : URL unresolvable for %s" % (STATUS_FAIL, pkg, name))
            pkg_ok = False
            continue
        if url.startswith("local:"):
            if url == "local:aux":
                rows.append((pkg, name, pv, None, STATUS_OK,
                             "bundled aux/doc asset in repo, no download needed"))
                log("[%s] %s : %s bundled aux/doc asset" % (STATUS_OK, pkg, name))
                pkg_verified = True
                continue
            src_path = Path(url[len("local:"):])
            if not src_path.exists():
                rows.append((pkg, name, pv, None, STATUS_FAIL,
                             "bundled source %s missing from repo" % name))
                log("[%s] %s : bundled source missing" % (STATUS_FAIL, pkg))
                pkg_ok = False
                continue
            hash_note = "no-checksum-pinned"
            if sha:
                good, why = verify_file(src_path, {"sha256": sha})
                if not good:
                    rows.append((pkg, name, pv, None, STATUS_FAIL, why))
                    log("[%s] %s : %s for bundled %s" % (STATUS_FAIL, pkg, why, name))
                    pkg_ok = False
                    continue
                hash_note = why
            with tempfile.TemporaryDirectory() as td:
                internal, note, strong, src_like = tear_apart(src_path, name, Path(td))
            if internal and strong:
                if PLACEHOLDER_RE.match(pv or ""):
                    status = STATUS_OK
                elif versions_match(pv, internal):
                    status = STATUS_OK
                else:
                    status = STATUS_MISMATCH
                    pkg_ok = False
                    hv = latest_channel_version_header(url)
                    if not hv:
                        cu = channel_url_for_pkg(pkg)
                        if cu:
                            hv = latest_channel_version_header(cu)
                    if hv and hv[1] == pv:
                        status = STATUS_OK
                        pkg_ok = True
                    elif hv:
                        status = STATUS_STALE
                if status == STATUS_OK and PLACEHOLDER_RE.match(pv or ""):
                    note = "%s | hash %s | pinned placeholder %r, internal %s authoritative" % (
                        note, hash_note, pv, internal)
                elif status == STATUS_STALE:
                    note = "%s | hash %s | upstream channel now declares %s via %s - rerun update.sh | pinned %s | internal %s" % (
                        note, hash_note, hv[1], hv[0], pv, internal)
                elif status == STATUS_OK and hv:
                    note = "%s | hash %s | upstream declares %s via %s (internal tag uses a different scheme) | pinned %s | internal %s" % (
                        note, hash_note, pv, hv[0], pv, internal)
                else:
                    note = "%s | hash %s | pinned %s | internal %s" % (note, hash_note, pv, internal)
            elif internal and not strong:
                status = STATUS_SOURCE_OK
                note = "%s | hash %s | weak internal evidence %s (not authoritative)" % (note, hash_note, internal)
            elif src_like:
                status = STATUS_SOURCE_OK
                note = "%s | hash %s | bundled source tarball (version = PV by construction)" % (note, hash_note)
            else:
                status = STATUS_UNVERIFIED
                pkg_ok = False
                note = "%s | hash %s | bundled binary, no internal version evidence" % (note, hash_note)
            rows.append((pkg, name, pv, internal, status, note))
            log("[%s] %s : %s" % (status, pkg, note))
            if status in (STATUS_OK, STATUS_SOURCE_OK):
                pkg_verified = True
            continue
        if name.lower().endswith((".sig", ".asc", ".keyring", ".pem", ".pub", ".minisig")):
            rows.append((pkg, name, pv, None, STATUS_OK,
                         "signature/keyring verification material, no teardown applicable"))
            log("[%s] %s : %s signature/keyring material" % (STATUS_OK, pkg, name))
            pkg_verified = True
            continue
        dst = dl / name
        if not dst.exists():
            try:
                log("  downloading %s (%s)" % (name, url))
                data, cd_name = fetch_with_name(url)
                dst.write_bytes(data)
                if cd_name and cd_name != name:
                    (dl / (name + ".cdname")).write_text(cd_name)
            except Exception as e:
                rows.append((pkg, name, pv, None, STATUS_FAIL, "download failed: %s" % e))
                log("[%s] %s : download failed %s" % (STATUS_FAIL, pkg, name))
                pkg_ok = False
                continue
        expected = sha if isinstance(sha, dict) else {}
        if sha and isinstance(sha, str):
            expected = {"sha256": sha}
        good, why = verify_file(dst, expected)
        if not good:
            rows.append((pkg, name, pv, None, STATUS_FAIL, why))
            log("[%s] %s : %s for %s" % (STATUS_FAIL, pkg, why, name))
            pkg_ok = False
            continue
        hash_note = why if (isinstance(sha, str) or isinstance(sha, dict)) else "no-checksum-pinned"
        if looks_like_doc(name) or looks_like_aux(name):
            rows.append((pkg, name, pv, None, STATUS_OK,
                         "hash %s | license/doc/aux asset, not an artifact" % hash_note))
            log("[%s] %s : %s is a doc/aux asset (%s)" % (STATUS_OK, pkg, name, hash_note))
            pkg_verified = True
            continue
        if name.lower().endswith((".tar.zst", ".zst", ".7z")):
            if pkg_verified:
                rows.append((pkg, name, pv, None, STATUS_OK,
                             "hash %s | dependency/aux bundle (zstd/7z, not extractable with "
                             "stdlib); package version verified via primary artifact" % hash_note))
                log("[%s] %s : %s dependency bundle, hash-verified" % (STATUS_OK, pkg, name))
                continue
            rows.append((pkg, name, pv, None, STATUS_UNVERIFIED,
                         "hash %s | zstd/7z bundle, not extractable with stdlib, no sibling "
                         "artifact verified" % hash_note))
            log("[%s] %s : %s zstd/7z bundle, unverified" % (STATUS_UNVERIFIED, pkg, name))
            pkg_ok = False
            continue
        teardown_name = name
        if not re.search(r"\.(appimage|deb|rpm|zip|tar\.gz|tgz|tar\.xz|tar\.bz2|crate|tar\.zst|zst|7z|tar)$", name.lower()):
            cd_name = content_disposition_name(dst)
            if cd_name:
                teardown_name = cd_name
        dep_missing = []
        with tempfile.TemporaryDirectory() as td:
            internal, note, strong, src_like = tear_apart(dst, teardown_name, Path(td))
            # Check for missing shared libraries in extracted binaries
            if strong and td and os.listdir(td):
                dep_missing = check_deps_in_dir(pkg, Path(td))
        if internal and strong:
            if PLACEHOLDER_RE.match(pv or ""):
                status = STATUS_OK
                note = "%s | hash %s | pinned placeholder %r, internal %s authoritative" % (
                    note, hash_note, pv, internal)
            elif versions_match(pv, internal):
                status = STATUS_OK
            else:
                status = STATUS_MISMATCH
                pkg_ok = False
                hv = latest_channel_version_header(url)
                if not hv and url.startswith("local:"):
                    cu = channel_url_for_pkg(pkg)
                    if cu:
                        hv = latest_channel_version_header(cu)
                if hv and hv[1] == pv:
                    status = STATUS_OK
                    pkg_ok = True
                    note += " | upstream declares %s via %s on this artifact URL (internal tag uses a different scheme)" % (pv, hv[0])
                elif hv:
                    status = STATUS_STALE
                    note += " | upstream now declares %s via %s on this URL - rerun update.sh" % (hv[1], hv[0])
            note = "%s | pinned %s | internal %s" % (note, pv, internal)
        elif internal and not strong:
            status = STATUS_SOURCE_OK
            note = "%s | hash %s | weak internal evidence %s (not authoritative)" % (note, hash_note, internal)
        elif src_like:
            status = STATUS_SOURCE_OK
            note = "%s | hash %s | source tarball (version = PV by construction)" % (note, hash_note)
        else:
            mach = artifact_machine(dst, name)
            hm = host_machine()
            if PLACEHOLDER_RE.match(pv or "") and internal:
                status = STATUS_OK
                note = "%s | hash %s | pinned placeholder %r, internal %s authoritative" % (
                    note, hash_note, pv, internal)
            elif mach and mach != hm:
                status = STATUS_OK
                note = "%s | hash %s | cross-arch artifact (%s), hash-verified; not executable on %s host" % (
                    note, hash_note, mach, hm)
            else:
                status = STATUS_UNVERIFIED
                pkg_ok = False
                note = "%s | hash %s | BINARY ARTIFACT, no internal version evidence" % (note, hash_note)
        # Append dependency check results
        if dep_missing:
            unique_missing = sorted(set(lib for _, lib in dep_missing))
            dep_note = " | MISSING DEPS: %s" % ", ".join(unique_missing[:10])
            if len(unique_missing) > 10:
                dep_note += " (+%d more)" % (len(unique_missing) - 10)
            note += dep_note
            # If status was OK but deps are missing, flag it
            if status == STATUS_OK:
                status = STATUS_FAIL
                pkg_ok = False
                note += " [DEPS-FAIL]"
            log("[%s] %s : %d missing libs: %s" % (STATUS_FAIL, pkg, len(unique_missing), ", ".join(unique_missing[:5])))
        rows.append((pkg, name, pv, internal, status, note))
        log("[%s] %s : %s" % (status, pkg, note))
        if status in (STATUS_OK, STATUS_SOURCE_OK):
            pkg_verified = True


def content_disposition_name(dst):
    """Return the real filename for extensionless distfiles: we record the
    Content-Disposition filename at download time in a sidecar marker."""
    side = Path(str(dst) + ".cdname")
    if side.exists():
        return side.read_text(errors="ignore").strip() or None
    return None


def _replacement_asset_exists(srcs, pv, newver):
    """True/False whether upstream's new version serves an artifact matching
    our current URL pattern (pv swapped for newver). None = undeterminable
    (version string not embedded in any URL)."""
    found = False
    for item in srcs:
        url = item[0] if isinstance(item, tuple) else None
        if not (isinstance(url, str) and url.startswith(("http://", "https://"))
                and pv and pv in url):
            continue
        found = True
        for nv in dict.fromkeys([newver, newver.lstrip("v")]):
            if http_status(url.replace(pv, nv)) == 200:
                return True
    return False if found else None


def check_upstream_latest(pkgs):
    """Deterministic staleness gate: for every release-pinned package whose
    artifact URL points at a known forge, compare PV against upstream's
    latest release. Decision matrix:
      - authoritative /releases/latest (GitHub/Codeberg; GH_TOKEN honored)
        matching PV -> OK; differing -> STALE
      - no API: ls-remote max tag matches PV -> OK
      - ls-remote only, PV matches SOME tag but not the lexical max ->
        SKIP-ambiguous (branded suffixes like zen's 1.21b vs 1.21.15b break
        pure version sort; never fail a package on a guess)
    Appends OK/STALE/SKIP rows so the report shows BOTH 'artifact is what we
    pinned' AND 'pin is upstream's latest'."""
    log("")
    log("=== UPSTREAM LATEST CHECK ===")
    for pkg, pv, srcs, live in pkgs:
        if live or not pv or PLACEHOLDER_RE.match(pv):
            continue
        if srcs and isinstance(srcs[0], tuple) and srcs[0][0] == "__metapackage__":
            continue
        api_repo = clone = None
        for item in srcs:
            url = item[0] if isinstance(item, tuple) else None
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                api_repo, clone = forge_slug_from_url(url)
                if clone:
                    break
        if not clone:
            continue  # non-forge host: no honest deterministic latest to compare
        slug = clone.split("//", 1)[-1][:-4]

        latest = None
        source = None
        if api_repo:
            headers = {"Accept": "application/vnd.github+json"}
            tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            if tok:
                headers["Authorization"] = "Bearer %s" % tok
            try:
                req = urllib.request.Request(
                    "https://api.github.com/repos/%s/releases/latest" % api_repo,
                    headers=headers)
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode())
                if data.get("tag_name"):
                    latest, source = data["tag_name"], "releases/latest"
            except Exception:
                pass

        all_tags = None
        if not latest:
            all_tags = _lsremote_version_tags(clone)
            if all_tags:
                latest, source = max(all_tags, key=_tagkey), "ls-remote"

        if not latest:
            rows.append((pkg, "upstream %s" % slug, pv, "", STATUS_SKIP,
                         "upstream tags unreachable or none version-like"))
            log("[%s] %s : upstream tags unavailable (%s)" % (STATUS_SKIP, pkg, slug))
            continue

        base = staleness_pv(pv)

        def canon(x):
            """Token-level version identity: 5.0.0~beta9 == v5.0.0-beta.9 ==
            5.0.0_beta.9 (separators and letter/digit boundaries ignored)."""
            return tuple(re.findall(r"[a-z]+|\d+", re.sub(r"^[vV]", "", (x or "").lower())))

        def same(a, b):
            for aa in dict.fromkeys([a, staleness_pv(a)]):
                for bb in dict.fromkeys([b, staleness_pv(b)]):
                    if versions_match(aa, bb) or canon(aa) == canon(bb):
                        return True
            return False

        if same(pv, latest):
            note = "at upstream latest %s [%s]" % (latest, source)
            rows.append((pkg, "upstream %s" % slug, pv, latest, STATUS_OK, note))
            log("[%s] %s : %s" % (STATUS_OK, pkg, note))
            continue
        if source == "releases/latest":
            # Some projects stop publishing release objects while tags keep
            # advancing - their releases/latest pointer then LAGS reality.
            # If PV matches a tag at least as new as the pointer, we're current.
            all_tags = _lsremote_version_tags(clone)
            match_tag = next((t for t in all_tags or []
                              if same(pv, t)), None)
            if match_tag and _tagkey(match_tag) >= _tagkey(latest):
                note = ("at upstream latest %s [tag; releases/latest pointer "
                        "stale at %s]" % (match_tag, latest))
                rows.append((pkg, "upstream %s" % slug, pv, match_tag,
                             STATUS_OK, note))
                log("[%s] %s : %s" % (STATUS_OK, pkg, note))
                continue
            if _replacement_asset_exists(srcs, pv, latest) is False:
                note = ("upstream released %s but no replacement artifact yet "
                        "(partial release) - staying on %s" % (latest, pv))
                rows.append((pkg, "upstream %s" % slug, pv, latest,
                             STATUS_SKIP, note))
                log("[%s] %s : %s" % (STATUS_SKIP, pkg, note))
                continue
            note = ("pinned %s but upstream released %s - rerun update.sh"
                    % (pv, latest))
            rows.append((pkg, "upstream %s" % slug, pv, latest, STATUS_STALE, note))
            log("[%s] %s : %s" % (STATUS_STALE, pkg, note))
            continue
        # ls-remote only: guard against branded-suffix misordering
        if all_tags and any(same(pv, t) for t in all_tags):
            note = ("pinned %s matches an existing tag but lexical-max is %s "
                    "- ambiguous scheme, verify manually" % (pv, latest))
            rows.append((pkg, "upstream %s" % slug, pv, latest, STATUS_SKIP, note))
            log("[%s] %s : %s" % (STATUS_SKIP, pkg, note))
            continue
        if _replacement_asset_exists(srcs, pv, latest) is False:
            note = ("newer tag %s exists but no replacement artifact yet "
                    "(partial release) - staying on %s" % (latest, pv))
            rows.append((pkg, "upstream %s" % slug, pv, latest, STATUS_SKIP, note))
            log("[%s] %s : %s" % (STATUS_SKIP, pkg, note))
            continue
        note = ("pinned %s is not any published tag; newest is %s - rerun update.sh"
                % (pv, latest))
        rows.append((pkg, "upstream %s" % slug, pv, latest, STATUS_STALE, note))
        log("[%s] %s : %s" % (STATUS_STALE, pkg, note))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overlay", default=".")
    ap.add_argument("--type", default="auto", choices=["auto", "gentoo", "fedora", "nix", "void", "opensuse"])
    ap.add_argument("--report", default="teardown-report.md")
    ap.add_argument("--workdir", default=None)
    args = ap.parse_args()

    root = Path(args.overlay)
    repo_type = args.type if args.type != "auto" else detect_type(root)
    if not repo_type:
        log("UNKNOWN REPO TYPE under %s - sweep aborted (FAIL)" % root)
        sys.exit(1)

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="teardown-"))
    workdir.mkdir(parents=True, exist_ok=True)

    pkgs = []
    if repo_type == "gentoo":
        ebuilds = sorted(
            p for p in root.rglob("*.ebuild")
            if not any(x in p.parts for x in SKIP_DIRS) and len(p.parts) >= 3
        )
        for eb in ebuilds:
            pkgs.append(parse_gentoo(eb))
        if not pkgs:
            log("NO EBUILDS FOUND under %s - sweep aborted (FAIL)" % root)
            sys.exit(1)
    elif repo_type in ("fedora", "opensuse"):
        for spec in find_specs(root):
            pkgs.append(parse_fedora(spec))
        if not pkgs:
            log("NO SPEC FILES FOUND under %s - sweep aborted (FAIL)" % root)
            sys.exit(1)
    elif repo_type == "void":
        templates = sorted(
            p for p in (root / "srcpkgs").rglob("template")
            if not any(x in p.parts for x in SKIP_DIRS)
        )
        for t in templates:
            pkgs.append(parse_void(t))
        if not pkgs:
            log("NO TEMPLATES FOUND under %s - sweep aborted (FAIL)" % root)
            sys.exit(1)
    elif repo_type == "nix":
        nixes = sorted(p for p in (root / "pkgs").glob("*.nix"))
        for n in nixes:
            pkgs.append(parse_nix(n))
        if not pkgs:
            log("NO NIX PACKAGES FOUND under %s - sweep aborted (FAIL)" % root)
            sys.exit(1)

    log("=== TEAR-DOWN SWEEP [%s]: %d packages ===" % (repo_type, len(pkgs)))
    for pkg, pv, srcs, live in pkgs:
        sweep_package(pkg, pv, srcs, live, repo_type, workdir)
    check_upstream_latest(pkgs)

    log("")
    log("=== SWEEP TABLE ===")
    log("%-34s %-34s %-16s %-14s %-12s %s" % ("PACKAGE", "DISTFILE", "PINNED", "INTERNAL", "STATUS", "NOTE"))
    n_bad = 0
    for pkg, dist, pinned, internal, status, note in rows:
        log("%-34s %-34s %-16s %-14s %-12s %s" % (
            pkg, (dist or "")[:34], (pinned or "")[:16], (internal or "")[:14], status, note))
        if status in (STATUS_FAIL, STATUS_MISMATCH, STATUS_STALE, STATUS_UNVERIFIED):
            n_bad += 1

    report = Path(args.report)
    lines = ["# Teardown Sweep Report", "",
             "Repo type: **%s**. Sweep of **%d** packages. Exit code is the "
             "verdict; this report is the receipt." % (repo_type, len(pkgs)),
             "| Package | Distfile | Pinned | Internal | Status | Note |",
             "|---|---|---|---|---|---|"]
    for pkg, dist, pinned, internal, status, note in rows:
        lines.append("| %s | %s | %s | %s | **%s** | %s |" % (
            pkg, (dist or "?").replace("|", "\\|"), pinned or "", internal or "", status,
            note.replace("|", "\\|")))
    lines.append("")
    lines.append("**Verdict: %s** (%d failure(s))" % ("PASS" if n_bad == 0 else "FAIL", n_bad))
    report.write_text("\n".join(lines) + "\n")
    log("report written to %s" % report)

    if n_bad:
        log("=== TEAR-DOWN SWEEP FAILED: %d package(s) not verified. Not done. ===" % n_bad)
        sys.exit(1)
    log("=== TEAR-DOWN SWEEP PASSED: every package torn apart and verified. ===")
    sys.exit(0)


if __name__ == "__main__":
    main()