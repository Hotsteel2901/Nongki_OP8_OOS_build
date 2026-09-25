#!/usr/bin/env python3
"""Apply Drivers/manifest.xml: place the out-of-tree Qualcomm driver sources into the
kernel tree before it is compiled (symlinks / copies / kbuild glue / overlays).

Only the Python standard library is used, so it runs on any CI image as-is.
"""

import argparse
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


class Fatal(Exception):
    pass


def log(prefix, message):
    print("%s %s" % (prefix, message), flush=True)


def expand(text):
    """Resolve the \\t / \\n escapes used in the manifest."""
    return text.replace("\\t", "\t").replace("\\n", "\n")


def norm(text):
    return " ".join(text.split())


class Origins:
    """Resolves an origin id to a directory, cloning git origins on first use."""

    def __init__(self, workspace, manifest, cache_root):
        self.workspace = workspace
        self.cache_root = cache_root
        self.local = {}
        self.git = {}
        self.cloned = set()
        for origin in manifest.findall("./origins/origin"):
            oid = origin.get("id")
            if origin.get("kind", "local") == "git":
                self.git[oid] = origin
            else:
                self.local[oid] = os.path.join(workspace, origin.get("root"))

    def root(self, oid):
        if oid in self.local:
            return self.local[oid], False
        if oid not in self.git:
            raise Fatal("entry refers to unknown origin '%s'" % oid)
        return self._clone(oid), True

    def _clone(self, oid):
        origin = self.git[oid]
        root = os.path.join(self.cache_root, oid)
        if oid not in self.cloned:
            if not os.path.isdir(os.path.join(root, ".git")):
                if os.path.exists(root):
                    shutil.rmtree(root)
                os.makedirs(os.path.dirname(os.path.abspath(root)) or ".", exist_ok=True)
                cmd = ["git", "clone", "--filter=blob:none", "--depth=1"]
                if origin.get("sparse"):
                    cmd.append("--sparse")
                cmd += ["-b", origin.get("branch"), origin.get("repo"), root]
                log("[+]", "fallback origin '%s': %s" % (oid, " ".join(cmd[1:])))
                subprocess.check_call(cmd)
                if origin.get("sparse"):
                    subprocess.check_call(
                        ["git", "-C", root, "sparse-checkout", "set"] + origin.get("sparse").split())
            self.cloned.add(oid)
        return root


def pick_source(origins, entry):
    """First <source> whose path exists wins; git origins force a copy."""
    tried = []
    for source in entry.findall("source"):
        oid, rel = source.get("origin"), source.get("path")
        root, is_git = origins.root(oid)
        path = os.path.join(root, rel)
        tried.append("%s:%s" % (oid, rel))
        if os.path.exists(path):
            return path, oid, rel, is_git
    raise Fatal("no source found for '%s' (tried %s)" % (entry.get("name"), ", ".join(tried)))


def prepare_dst(dst, expect_symlink):
    """Clear the destination so it can be recreated; refuses to delete real content."""
    if os.path.islink(dst):
        os.remove(dst)
    elif os.path.isfile(dst):
        os.remove(dst)
    elif os.path.isdir(dst):
        if expect_symlink and os.listdir(dst):
            raise Fatal("%s exists as a directory, refusing to replace it with a symlink" % dst)
        shutil.rmtree(dst)


def apply_glue(entry, kernel):
    for glue in entry.findall("glue"):
        path = os.path.join(kernel, glue.get("file"))
        if not os.path.isfile(path):
            raise Fatal("glue target %s does not exist" % path)
        want = expand(glue.get("line"))
        lines = open(path).read().splitlines(keepends=True)
        if any(norm(line) == norm(want) for line in lines):
            log("[=]", "%s: already in %s" % (entry.get("name"), glue.get("file")))
            continue
        if not want.endswith("\n"):
            want += "\n"
        anchor = glue.get("before")
        if anchor:
            index = next((i for i, line in enumerate(lines) if norm(line).startswith(norm(anchor))), None)
            if index is None:
                raise Fatal("anchor '%s' not found in %s" % (anchor, path))
            lines.insert(index, want)
        else:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(want)
        open(path, "w").writelines(lines)
        log("[+]", "%s: added to %s" % (entry.get("name"), glue.get("file")))


def apply_overlay(entry, workspace, kernel):
    for overlay in entry.findall("overlay"):
        src_root = os.path.join(workspace, overlay.get("dir"))
        dst_root = os.path.join(kernel, overlay.get("dst"))
        if not os.path.isdir(src_root):
            raise Fatal("overlay %s does not exist" % src_root)
        copied = 0
        for dirpath, _dirs, files in os.walk(src_root):
            rel = os.path.relpath(dirpath, src_root)
            target = dst_root if rel == "." else os.path.join(dst_root, rel)
            os.makedirs(target, exist_ok=True)
            for name in files:
                shutil.copy2(os.path.join(dirpath, name), os.path.join(target, name))
                copied += 1
        log("[+]", "%s: overlaid %d file(s) from %s" % (entry.get("name"), copied, overlay.get("dir")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="Drivers/manifest.xml")
    parser.add_argument("--workspace", default=os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
    parser.add_argument("--kernel", default="kernel/msm-4.19",
                        help="kernel tree, relative to the workspace")
    parser.add_argument("--fallback-cache", default="/tmp/driver_map_cache",
                        help="directory a git origin is cloned into when it is needed")
    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    kernel = os.path.join(workspace, args.kernel)
    if not os.path.isdir(kernel):
        log("[-]", "kernel tree %s not found" % kernel)
        return 1

    tree = ET.parse(os.path.join(workspace, args.manifest))
    manifest = tree.getroot()
    origins = Origins(workspace, manifest, args.fallback_cache)

    applied = skipped = 0
    for entry in manifest.findall("./map/entry"):
        name = entry.get("name")
        if entry.get("enabled", "true") != "true":
            log("[=]", "%s: declared in %s, not enabled (%s)"
                % (name, "manifest.xml", entry.get("note", "")))
            skipped += 1
            continue

        src, origin_id, rel, is_git = pick_source(origins, entry)
        dst = os.path.join(kernel, entry.get("dst"))
        mode = "copy" if is_git else entry.get("mode", "symlink")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        prepare_dst(dst, expect_symlink=(mode == "symlink"))
        if mode == "symlink":
            os.symlink(os.path.relpath(src, os.path.dirname(dst)), dst)
        else:
            shutil.copytree(src, dst, symlinks=True)
        if not os.path.exists(dst):
            raise Fatal("%s does not resolve after applying" % dst)
        log("[+]", "%s: %s -> %s (%s from %s)" % (name, rel, entry.get("dst"), mode, origin_id))
        apply_overlay(entry, workspace, kernel)
        apply_glue(entry, kernel)
        applied += 1

    for path in manifest.findall("./require/path"):
        target = os.path.join(workspace, path.get("value"))
        if not os.path.exists(target):
            raise Fatal("%s cannot resolve, the OOS layout is incomplete" % path.get("value"))
        log("[+]", "%s -> %s" % (path.get("value"), os.path.realpath(target)))

    log("[+]", "driver map applied: %d entry(ies) wired, %d declared" % (applied, skipped))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Fatal, ET.ParseError, subprocess.CalledProcessError) as error:
        log("[-]", str(error))
        sys.exit(1)