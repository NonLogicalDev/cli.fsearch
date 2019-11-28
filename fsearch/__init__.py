import sys
import argparse

from .dirops import DirOps

from .constants import CONF_DIR_PATH, CONF_FILE_PATH


class App(object):
    def __init__(self, parser: argparse.ArgumentParser):
        self.parser = self._register_args(parser)

    @staticmethod
    def _register_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--list", "-l", action="store_true")

        commands = parser.add_subparsers(dest='command')

        c = commands.add_parser('conf')
        g = c.add_mutually_exclusive_group()
        g.add_argument("--path", "-p", action='store_true',
                       help="print the expected location of the configuration file.")
        g.add_argument("--init", action='store_true',
                       help="initialize cofiguration with an example.")

        commands.add_parser('parent-dirs', aliases=["pd"])
        commands.add_parser('parent-files', aliases=["pf"])
        commands.add_parser('content-dirs', aliases=["cd"])
        commands.add_parser('content-files', aliases=["cf"])

        c = commands.add_parser('projects', aliases=["p"])
        c.add_argument("prefilter", nargs="*")

        return parser

    def _parse_args(self, args) -> argparse.Namespace:
        args = self.parser.parse_args(args)
        setattr(args, "conf_dir_path", CONF_DIR_PATH)
        setattr(args, "conf_path", CONF_FILE_PATH)
        return args

    def run(self, args):
        args = self._parse_args(args)
        ops = DirOps(DirOps.parse_config(), output=sys.stdout)

        if args.command == 'conf':
            ops.cmd__conf(write=args.init, path=args.path)
        elif args.command in ['parent-dirs', 'pd']:
            ops.cmd__list_parent_dirs()
        elif args.command in ['parent-files', 'pf']:
            ops.cmd__list_parent_files()
        elif args.command in ['content-dirs', 'cd']:
            ops.cmd__list_content_dirs()
        elif args.command in ['content-files', 'cf']:
            ops.cmd__list_content_files()
        elif args.command in ['projects', 'p']:
            ops.cmd__list_projects()
        else:
            self.parser.print_help()
