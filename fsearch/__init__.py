import re
import os
import sys
import json
import argparse
import subprocess
import time

from itertools import imap


def path_resolve(*path):
    return os.path.expanduser(os.path.expandvars(os.path.join(*path)))


def natural_sort(key):
    return [
        int(c) if c.isdigit() else c.lower()
        for c in re.split(r"\d+", key)
    ]


def main_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", "-l", action="store_true")

    commands = parser.add_subparsers(dest='command')

    commands.add_parser('init-conf')
    commands.add_parser('parent-dirs')
    commands.add_parser('parent-files')
    commands.add_parser('content-dirs')
    commands.add_parser('content-files')

    cmd = commands.add_parser('projects')
    cmd.add_argument("prefilter", nargs="*")

    args = parser.parse_args(sys.argv[1:])
    setattr(args, "conf_dir_path", DirOps.CONF_DIR_PATH)
    setattr(args, "conf_path", DirOps.CONF_FILE_PATH)

    return args, parser


def main(args, parser):
    stream = sys.stdout

    ops = DirOps(DirOps.parse_config())
    try:
        if args.command == 'init-conf':
            DirOps.cmd__init_conf()
        elif args.command == 'parent-dirs':
            ops.cmd__list_parent_dirs(stream)
        elif args.command == 'parent-files':
            ops.cmd__list_parent_files(stream)
        elif args.command == 'content-dirs':
            ops.cmd__list_content_dirs(stream)
        elif args.command == 'content-files':
            ops.cmd__list_content_files(stream)
        elif args.command == 'projects':
            ops.cmd__list_projects(stream)
        else:
            parser.print_help()

    except IOError:
        pass


class DirOps:
    Z_JUMP_FILE_PATH = path_resolve("~/.z")
    CONF_DIR_PATH = path_resolve("~/.config/fsearch")
    CONF_FILE_PATH = path_resolve(CONF_DIR_PATH, "config.json")

    DEFAULT_CONF = {
        "project_roots": [
            {"path": "~", "min": 1, "max": 2, "var": "HOME"},
        ]
    }

    def __init__(self, conf):
        self.conf = conf

    @classmethod
    def cmd__init_conf(cls):
        if not os.path.exists(cls.CONF_FILE_PATH):
            if not os.path.exists(cls.CONF_DIR_PATH):
                os.mkdir(cls.CONF_DIR_PATH)
            with open(cls.CONF_FILE_PATH, "w+") as conf_file:
                conf_file.write(json.dumps(cls.DEFAULT_CONF, indent=4))
                conf_file.write("\n")
            print("Initialized Config...")
            return 0

    @classmethod
    def parse_config(cls):
        out = {}

        if os.path.exists(cls.CONF_FILE_PATH):
            with open(cls.CONF_FILE_PATH) as f:
                out.update(json.load(f))

        if os.path.exists(cls.Z_JUMP_FILE_PATH):
            t = time.time()

            path_stats = {}

            with open(cls.Z_JUMP_FILE_PATH) as f:
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

    def cmd__list_parent_dirs(self, stream):
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

    def cmd__list_parent_files(self, stream):
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
            pfiles = self._find(dir, ['-maxdepth', '1'])
            for file in pfiles:
                stream.write(file)
                stream.write("\n")

    def cmd__list_content_dirs(self, stream):
        cwd = os.getcwd()
        dirs = self._find(cwd, [
            # Exclude Git Folders
            '-path', '*/.git/*', '-path', '*/.git',

            # Prune Path
            '-prune', '-o', '-type', 'd', '-print',
        ])

        for dir in dirs:
            if dir == cwd:
                continue

            stream.write(self._exclude_common(cwd, dir))
            stream.write("\n")

    def cmd__list_content_files(self, stream):
        cwd = os.getcwd()
        # files = cls.find(cwd, [
        #     # Exclude Git Folders
        #     '-path', '*/.git/*', '-path', '*/.git',
        #
        #     # Prune Path
        #     '-prune', '-o', '-type', 'f', '-print',
        # ])
        files = self._cmdrun(['ack', '-l', '^'])
        for file in files:
            stream.write(self._exclude_common(cwd, file))
            stream.write("\n")

    def cmd__list_projects(self, stream):
        files = []

        for e in self.conf.get("project_roots", []):
            path_spec = e.get("path", "")
            path = path_resolve(path_spec)
            if path == "":
                continue

            find_args = []

            search_spec = e.get("search", {})
            if len(search_spec) > 0:
                for param, val in search_spec.iteritems():
                    find_args.extend(["-"+param, val])
            else:
                find_args.extend(["-type", "d"])

            mindepth = e.get("min", None)
            if mindepth is not None:
                find_args.extend(["-mindepth", mindepth])

            maxdepth = e.get("max", None)
            if maxdepth is not None:
                find_args.extend(["-maxdepth", maxdepth])

            found_files = imap(
                lambda p: os.path.dirname(p),
                self._find(path, find_args)
            )
            files.extend([f.replace(path, path_spec) for f in found_files])

        for file in self._z_path_order(files):
            stream.write(str(file))
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
        #return sorted(map(lambda x: sort_order(x), paths), key=lambda x: x[0])

    @classmethod
    def _exclude_common(cls, patha, pathb):
        return pathb.replace(cls._designate_dir(patha), "")

    @staticmethod
    def _designate_dir(path):
        if os.path.isdir(path) and path != '/':
            path = '{}/'.format(path)
        return '{}'.format(path)

    @classmethod
    def _format_path(cls, path):
        return '"{}"'.format(cls._designate_dir(path))

    @staticmethod
    def _cmdrun(cmd):
        out = subprocess.Popen([str(c) for c in cmd], stdout=subprocess.PIPE)
        #out.wait()
        while True:
            line = out.stdout.readline()
            if line != '':
                yield line.strip()
            else:
                break

    @classmethod
    def _find(cls, dir, args):
        find_args = ['find', '-L', dir]
        find_args.extend(args)
        return cls._cmdrun(find_args)


if __name__ == '__main__':
    try:
        main(*main_args())
    except KeyboardInterrupt:
        pass
