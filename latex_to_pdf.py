#!/usr/bin/env python3
"""Compile a LaTeX resume file to Resume.pdf."""

import argparse
import platform
import re
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname


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


def _parse_path(value):
    value = str(value)
    if value.lower().startswith("file://"):
        parsed = urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in ("", "localhost"):
            path = f"//{parsed.netloc}{path}"
        value = url2pathname(path)
    return Path(value).expanduser().resolve()


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


def _missing_latex_file(output):
    match = re.search(r"(?:LaTeX Error:\s*)?File [`']([^`']+\.(?:sty|cls))[`'] not found", output or "")
    return match.group(1) if match else None


def _missing_latex_font(output):
    match = re.search(r"!pdfTeX error:\s*pdflatex\.EXE \(file ([^)]+)\): Font .* not found", output or "")
    return match.group(1) if match else None


def _run_pdflatex(command, directory):
    return subprocess.run(
        command,
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def compile_resume(tex_path, output_stem="Resume"):
    path = _parse_path(tex_path)
    if path.suffix.lower() != ".tex" or not path.is_file():
        raise ValueError(f"Invalid .tex file: {path}")

    pdflatex = _find_pdflatex()
    if not pdflatex:
        raise RuntimeError(
            "pdflatex not found. Install MiKTeX or TeX Live, then rerun this script."
        )

    output_pdf = path.parent / f"{output_stem}.pdf"
    try:
        output_pdf.unlink()
    except OSError:
        pass

    _cleanup_aux(path.parent, output_stem)
    command = [pdflatex, "-interaction=nonstopmode", f"-jobname={output_stem}", path.name]

    try:
        try:
            result = _run_pdflatex(command, path.parent)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                "pdflatex timed out after 120 seconds. This is a LaTeX/MiKTeX "
                "setup issue, not permission to rewrite the resume template. "
                "Close other MiKTeX/LaTeX processes, run TurboApply.cmd once to "
                "prepare required packages and fonts, then rerun this script."
            ) from e

        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    finally:
        _cleanup_aux(path.parent, output_stem)

    if result.returncode != 0:
        output = (result.stdout or result.stderr or "").strip()
        missing_file = _missing_latex_file(output)
        if missing_file:
            raise RuntimeError(
                f"pdflatex failed because MiKTeX is missing {missing_file}.\n"
                "This is a LaTeX installation issue, not a resume-template.tex "
                "content issue. Run TurboApply.cmd once to install required "
                "LaTeX packages, then rerun this script. Do not remove LaTeX "
                "packages or rewrite the template preamble to work around this."
            )
        missing_font = _missing_latex_font(output)
        if missing_font:
            raise RuntimeError(
                f"pdflatex failed because MiKTeX is missing font data for {missing_font}.\n"
                "This is a MiKTeX package/font-map issue, not a resume-template.tex "
                "content issue. Run TurboApply.cmd once to prepare LaTeX packages, "
                "then rerun this script. Do not remove LaTeX packages or rewrite "
                "the template preamble to work around this."
            )
        raise RuntimeError(f"pdflatex failed:\n{output}")

    if not output_pdf.is_file() or output_pdf.stat().st_size == 0:
        raise RuntimeError(f"pdflatex finished but did not create {output_pdf.name}.")

    return output_pdf


def open_pdf_in_browser(pdf_path):
    path = Path(pdf_path).resolve()
    uri = path.as_uri()
    try:
        if webbrowser.open(uri, new=2):
            return True
    except Exception:
        pass

    if platform.system() == "Windows":
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", uri],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            return True
        except OSError:
            pass

    return False


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
    if open_pdf_in_browser(pdf):
        print("Opened in browser")
    else:
        print("Created PDF, but could not open it in browser.")


if __name__ == "__main__":
    main()
