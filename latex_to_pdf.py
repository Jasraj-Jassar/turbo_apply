#!/usr/bin/env python3
"""Compile a LaTeX resume file to Resume.pdf."""

import argparse
import platform
import shutil
import subprocess
from pathlib import Path


def _cleanup_aux(directory, stem):
    for ext in (
        ".aux",
        ".log",
        ".out",
        ".toc",
        ".nav",
        ".snm",
        ".fls",
        ".fdb_latexmk",
        ".synctex.gz",
    ):
        try:
            (directory / f"{stem}{ext}").unlink()
        except OSError:
            pass


def _find_pdflatex():
    found = shutil.which("pdflatex")
    if found:
        return found

    if platform.system() == "Windows":
        candidates = [
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
            Path("C:/Program Files/MiKTeX/miktex/bin/x64/pdflatex.exe"),
            Path("C:/Program Files (x86)/MiKTeX/miktex/bin/x64/pdflatex.exe"),
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/pdflatex.exe",
        ]

        texlive = Path("C:/texlive")
        if texlive.exists():
            for year_dir in sorted(texlive.iterdir(), reverse=True):
                candidate = year_dir / "bin/windows/pdflatex.exe"
                if candidate.exists():
                    return str(candidate)

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

    return None


def compile_resume(tex_path, output_stem="Resume"):
    path = Path(tex_path).expanduser().resolve()
    if path.suffix.lower() != ".tex" or not path.is_file():
        raise ValueError(f"Invalid .tex file: {path}")

    pdflatex = _find_pdflatex()
    if not pdflatex:
        raise RuntimeError(
            "pdflatex not found. Install MiKTeX or TeX Live, then rerun this script."
        )

    _cleanup_aux(path.parent, output_stem)
    command = [pdflatex, "-interaction=nonstopmode", f"-jobname={output_stem}", path.name]
    if platform.system() == "Windows":
        command.insert(1, "--enable-installer")

    try:
        result = subprocess.run(
            command,
            cwd=path.parent,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        _cleanup_aux(path.parent, output_stem)

    if result.returncode != 0:
        output = (result.stdout or result.stderr or "").strip()
        raise RuntimeError(f"pdflatex failed:\n{output}")

    return path.parent / f"{output_stem}.pdf"


def main():
    parser = argparse.ArgumentParser(description="Compile a .tex resume into Resume.pdf.")
    parser.add_argument(
        "tex_file",
        nargs="?",
        default="resume-template.tex",
        help="LaTeX file to compile (default: resume-template.tex)",
    )
    args = parser.parse_args()

    pdf = compile_resume(args.tex_file)
    print(f"Created: {pdf}")


if __name__ == "__main__":
    main()
