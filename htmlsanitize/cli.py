"""命令行入口：净化一段 HTML。"""

import argparse
import sys

from .sanitize import SanitizeError, sanitize


def build_parser():
    parser = argparse.ArgumentParser(prog="html-sanitize", description="HTML 子集净化")
    parser.add_argument("--html", help="HTML 文本")
    parser.add_argument("--file", help="从文件读")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.file:
            with open(args.file, encoding="utf-8") as handle:
                text = handle.read()
        elif args.html is not None:
            text = args.html.replace("\\n", "\n")
        else:
            print("错误：需要 --html 或 --file", file=sys.stderr)
            return 2
        print(sanitize(text))
    except (SanitizeError, OSError) as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
