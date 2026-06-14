#!/usr/bin/env python3
"""Compile a LaTeX resume file to Resume.pdf."""

import argparse
import platform
import re
import shutil
import subprocess
import webbrowser
from pathlib import Path

_MIKTEX_PACKAGES = ("geometry", "parskip", "enumitem", "hyperref", "ec", "cm-super")


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


def _find_initexmf(pdflatex=None):
    found = shutil.which("initexmf")
    if found:
        return found

    if pdflatex:
        candidate = Path(pdflatex).with_name("initexmf.exe")
        if candidate.exists():
            return str(candidate)

    return None


def _find_mpm(pdflatex=None):
    found = shutil.which("mpm")
    if found:
        return found

    if pdflatex:
        candidate = Path(pdflatex).with_name("mpm.exe")
        if candidate.exists():
            return str(candidate)

    return None


def _enable_miktex_installer(pdflatex=None):
    if platform.system() != "Windows":
        return

    initexmf = _find_initexmf(pdflatex)
    if not initexmf:
        return

    subprocess.run(
        [initexmf, "--enable-installer"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _install_miktex_packages(pdflatex=None):
    if platform.system() != "Windows":
        return

    mpm = _find_mpm(pdflatex)
    if not mpm:
        return

    for package in _MIKTEX_PACKAGES:
        subprocess.run(
            [mpm, f"--install={package}", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _refresh_miktex_fonts(pdflatex=None):
    if platform.system() != "Windows":
        return

    initexmf = _find_initexmf(pdflatex)
    if not initexmf:
        return

    for option in ("--update-fndb", "--mkmaps"):
        subprocess.run(
            [initexmf, option],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _prepare_miktex(pdflatex=None):
    _enable_miktex_installer(pdflatex)
    _install_miktex_packages(pdflatex)
    _refresh_miktex_fonts(pdflatex)


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
    )


def compile_resume(tex_path, output_stem="Resume"):
    path = Path(tex_path).expanduser().resolve()
    if path.suffix.lower() != ".tex" or not path.is_file():
        raise ValueError(f"Invalid .tex file: {path}")

    pdflatex = _find_pdflatex()
    if not pdflatex:
        raise RuntimeError(
            "pdflatex not found. Install MiKTeX or TeX Live, then rerun this script."
        )

    _prepare_miktex(pdflatex)
    _cleanup_aux(path.parent, output_stem)
    command = [pdflatex, "-interaction=nonstopmode", f"-jobname={output_stem}", path.name]
    if platform.system() == "Windows":
        command.insert(1, "--enable-installer")

    try:
        result = _run_pdflatex(command, path.parent)
        output = result.stdout or result.stderr
        if result.returncode != 0 and (_missing_latex_file(output) or _missing_latex_font(output)):
            _prepare_miktex(pdflatex)
            result = _run_pdflatex(command, path.parent)
    finally:
        _cleanup_aux(path.parent, output_stem)

    if result.returncode != 0:
        output = (result.stdout or result.stderr or "").strip()
        missing_file = _missing_latex_file(output)
        if missing_file:
            raise RuntimeError(
                f"pdflatex failed because MiKTeX is missing {missing_file}.\n"
                "This is a LaTeX installation issue, not a resume-template.tex "
                "content issue. Install or update MiKTeX packages, then rerun "
                "this script. Do not remove LaTeX packages or rewrite the "
                "template preamble to work around this."
            )
        missing_font = _missing_latex_font(output)
        if missing_font:
            raise RuntimeError(
                f"pdflatex failed because MiKTeX is missing font data for {missing_font}.\n"
                "This is a MiKTeX package/font-map issue, not a resume-template.tex "
                "content issue. Run TurboApply.cmd again to prepare LaTeX packages, "
                "then rerun this script. Do not remove LaTeX packages or rewrite "
                "the template preamble to work around this."
            )
        raise RuntimeError(f"pdflatex failed:\n{output}")

    return path.parent / f"{output_stem}.pdf"


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
