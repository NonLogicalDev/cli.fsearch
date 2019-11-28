import json
import os
import subprocess
import time
import sys

from functools import reduce

from fsearch.constants import CONF_DIR_PATH, CONF_FILE_PATH, DEFAULT_CONF
from fsearch.utils import path_resolve


class DirOps:

    def __init__(self, conf, output=sys.stdout):
        self.conf = conf
        self.output = output

    @classmethod
    def parse_config(cls):
        out = {}

        if os.path.exists(CONF_FILE_PATH):
            with open(CONF_FILE_PATH) as f:
                out.update(json.load(f))

        z_file_path = path_resolve(out.get("z_jump_file", ""))
        if os.path.exists(z_file_path):
            t = time.time()
            path_stats = {}

            with open(z_file_path) as f:
                for line in f.readlines():
                    path, freq, ts = line.split("|")
                    rfreq = float(freq)
                    rts = t - int(ts)
                    rank = rfreq * (3600 / rts)
                    path_stats[path] = {
                        "freq": rfreq, "ts": rts, "rank": rank,
                    }
            out.update({
                "path_stats": path_stats
            })

        return out

    # { Commands }

    def cmd__conf(self, write=False, path=False):
        if write:
            if not os.path.exists(CONF_FILE_PATH):
                _ensure_dir(CONF_DIR_PATH)
                with open(CONF_FILE_PATH, "w+") as conf_file:
                    conf_file.write(json.dumps(DEFAULT_CONF, indent=4))
                    conf_file.write("\n")
                self.output.write("Initialized Config...\n")
                return 0

        if path:
            self.output.write(self.CONF_FILE_PATH)
            return 0

        self.output.write(json.dumps(self.DEFAULT_CONF, indent=4))
        self.output.write("\n")
        return 0

    def cmd__list_parent_dirs(self):
        stream = self.output

        cwd = os.getcwd()
        cur_dir = cwd
        dir_list = list()
        while True:
            cur_dir_parent = os.path.dirname(cur_dir)
            if cur_dir == cur_dir_parent:
                break
            dir_list.append(cur_dir_parent)
            cur_dir = cur_dir_parent

        for dir in dir_list:
            stream.write(dir)
            stream.write("\n")

    def cmd__list_parent_files(self):
        stream = self.output

        cwd = os.getcwd()
        cur_dir = os.path.join(cwd, ".")
        dir_list = list()

        while True:
            cur_dir_parent = os.path.dirname(cur_dir)
            if cur_dir == cur_dir_parent:
                break

            dir_list.append(cur_dir_parent)
            cur_dir = cur_dir_parent

        for dir in dir_list:
            pfiles = _find(dir, ['-maxdepth', '1'])
            for file in pfiles:
                stream.write(file)
                stream.write("\n")

    def cmd__list_content_dirs(self):
        stream = self.output

        cwd = os.getcwd()
        dirs = _find(cwd, ['-type', 'd'], prune=["*/.git"])

        for dir in dirs:
            if dir == cwd:
                continue

            stream.write(_exclude_common(cwd, dir))
            stream.write("\n")

    def cmd__list_content_files(self):
        stream = self.output
        cwd = os.getcwd()
        # files = cls.find(cwd, [
        #     # Exclude Git Folders
        #     '-path', '*/.git/*', '-path', '*/.git',
        #
        #     # Prune Path
        #     '-prune', '-o', '-type', 'f', '-print',
        # ])
        # files = _cmd(['rg', '-l', '^'])
        files = _find(cwd, ['-type', 'f'], prune=["*/.git"])
        for file in files:
            stream.write(_exclude_common(cwd, file))
            stream.write("\n")

    def cmd__list_projects(self):
        stream = self.output
        files = []

        for e in self.conf.get("project_roots", []):
            path_spec = e.get("path", "")
            path = path_resolve(path_spec)

            if path == "":
                return []

            find_args = []

            search_spec = e.get("search", {})
            for param, val in search_spec.items():
                find_args.extend(["-" + param, val])

            mindepth = e.get("min", None)
            if mindepth is not None:
                find_args.extend(["-mindepth", mindepth])

            maxdepth = e.get("max", None)
            if maxdepth is not None:
                find_args.extend(["-maxdepth", maxdepth])

            if e.get("parent", False):
                found_files = map(
                    lambda p: os.path.dirname(p).replace(path, path_spec),
                    _find(path, find_args)
                )
            else:
                found_files = _find(path, find_args)

            files.extend([f.replace(path, path_spec) for f in found_files])

        files = set(files)
        for file in self._z_path_order(files):
            stream.write(file)
            stream.write("\n")

    # { Private Utility Methods }

    def _z_path_order(self, paths):
        path_stats = self.conf.get("path_stats", {})

        def sort_order(path):
            path = path_resolve(path)
            out = (0, path)
            if path in path_stats:
                stats = path_stats[path]
                out = (0 - stats["rank"], path)
            return out

        return sorted(paths, key=sort_order)
        # return sorted(map(lambda x: sort_order(x), paths), key=lambda x: x[0])


def _ensure_dir(self, path):
    if not os.path.exists(path):
        os.mkdir(path)


def _cmd(cmd):
    out = subprocess.Popen([str(c) for c in cmd], stdout=subprocess.PIPE)
    while not out.stdout.closed:
        line = out.stdout.readline().decode('utf-8')
        if len(line) != 0:
            yield line.strip()
        else:
            break


def _find(dir, args, prune=None):
    find_args = []
    if prune is not None:
        prune_args = []
        for path in prune:
            prune_args.extend(["-path", path])
        find_args.extend([
            '(', *prune_args, '-prune', ')', '-o'
        ])
    find_args.extend(args)
    return _cmd(['find', '-L', dir, *find_args])


def _designate_dir(path):
    if os.path.isdir(path) and path != '/':
        path = '{}/'.format(path)
    return '{}'.format(path)


def _format_path(path):
    return '"{}"'.format(_designate_dir(path))


def _exclude_common(patha, pathb):
    return pathb.replace(_designate_dir(patha), "")
