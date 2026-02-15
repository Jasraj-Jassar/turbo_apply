#!/usr/bin/env python3
"""Turbo Apply launcher — opens GUI when run without arguments, CLI otherwise."""

import sys


def main():
    # If arguments are passed (URL, -vf, -e, .tex), use CLI mode
    if len(sys.argv) > 1:
        import job_tool
        job_tool.main()
    else:
        # No arguments → launch GUI
        import gui
        gui.main()


if __name__ == "__main__":
    main()
