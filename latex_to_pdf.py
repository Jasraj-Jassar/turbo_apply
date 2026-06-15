#!/usr/bin/env python3
"""Compile a LaTeX resume file to Resume.pdf."""

import argparse
import os
import platform
import re
import shutil
import subprocess
import tempfile
import webbrowser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

_WINDOWS_MIKTEX_TOOLS = {
    "pdflatex": "pdflatex.exe",
    "initexmf": "initexmf.exe",
    "mpm": "mpm.exe",
}


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


def _env_int(name, default, minimum):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(value, minimum)


def _run_quiet(command, cwd=None, timeout=60):
    flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" and hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=timeout,
            creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _find_tool(name):
    found = shutil.which(name)
    if found:
        return found

    if platform.system() == "Windows":
        exe_name = _WINDOWS_MIKTEX_TOOLS.get(name, name)
        candidates = [
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64" / exe_name,
            Path("C:/Program Files/MiKTeX/miktex/bin/x64") / exe_name,
            Path("C:/Program Files (x86)/MiKTeX/miktex/bin/x64") / exe_name,
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin" / exe_name,
        ]

        if name == "pdflatex" and (texlive := Path("C:/texlive")).exists():
            for year_dir in sorted(texlive.iterdir(), reverse=True):
                candidate = year_dir / "bin/windows/pdflatex.exe"
                if candidate.exists():
                    return str(candidate)

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

    return None


def _find_pdflatex():
    return _find_tool("pdflatex")


def _is_miktex_binary(path):
    return platform.system() == "Windows" and "miktex" in str(path).lower()


def _prepare_miktex():
    if platform.system() != "Windows":
        return

    initexmf = _find_tool("initexmf")
    if initexmf:
        for args in (
            [initexmf, "--set-config-value=[MPM]AutoInstall=1"],
            [initexmf, "--enable-installer"],
            [initexmf, "--update-fndb"],
        ):
            _run_quiet(args, timeout=90)


def _refresh_miktex_fonts():
    if platform.system() != "Windows":
        return
    initexmf = _find_tool("initexmf")
    if initexmf:
        _run_quiet([initexmf, "--mkmaps"], timeout=120)


def _try_install_miktex_package(package):
    if platform.system() != "Windows" or not package:
        return
    mpm = _find_tool("mpm")
    if mpm:
        _run_quiet([mpm, f"--install={package}", "--quiet"], timeout=180)


def _missing_latex_file(output):
    match = re.search(r"(?:LaTeX Error:\s*)?File [`']([^`']+\.(?:sty|cls))[`'] not found", output or "")
    return match.group(1) if match else None


def _missing_latex_font(output):
    match = re.search(r"!pdfTeX error:\s*pdflatex\.EXE \(file ([^)]+)\): Font .* not found", output or "")
    return match.group(1) if match else None


def _run_pdflatex(command, directory, timeout):
    return subprocess.run(
        command,
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
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
    using_miktex = _is_miktex_binary(pdflatex)
    if using_miktex:
        _prepare_miktex()

    command = [pdflatex]
    if using_miktex:
        command.append("-enable-installer")
    command.extend(["-interaction=nonstopmode", "-halt-on-error", f"-jobname={output_stem}", path.name])

    timeout = _env_int("TURBO_APPLY_PDFLATEX_TIMEOUT", 300, 60)
    result = None
    output = ""
    attempts = 2 if using_miktex else 1

    try:
        for attempt in range(attempts):
            try:
                result = _run_pdflatex(command, path.parent, timeout=timeout)
            except subprocess.TimeoutExpired as e:
                _cleanup_aux(path.parent, output_stem)
                if attempt + 1 < attempts:
                    _prepare_miktex()
                    continue
                raise RuntimeError(
                    f"pdflatex timed out after {timeout} seconds even after "
                    "enabling MiKTeX automatic package installation. This is a "
                    "LaTeX/MiKTeX setup issue, not permission to rewrite the "
                    "resume template. From the main Turbo Apply folder, run "
                    "TurboApply.cmd --check-only once, then rerun this script."
                ) from e

            output = "\n".join(part for part in (result.stdout, result.stderr) if part)
            if result.returncode == 0:
                break

            missing_file = _missing_latex_file(output)
            missing_font = _missing_latex_font(output)
            if attempt + 1 < attempts and missing_file:
                _try_install_miktex_package(Path(missing_file).stem)
                continue
            if attempt + 1 < attempts and missing_font:
                _try_install_miktex_package("cm-super")
                _refresh_miktex_fonts()
                continue
            break
    finally:
        _cleanup_aux(path.parent, output_stem)

    if result is None or result.returncode != 0:
        output = output or ((result.stdout or result.stderr or "").strip() if result else "")
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


def self_test():
    with tempfile.TemporaryDirectory(prefix="turbo-apply-latex-") as tmp:
        tex_path = Path(tmp) / "smoke.tex"
        tex_path.write_text(
            r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{parskip}
\usepackage{enumitem}
\usepackage[colorlinks=true,linkcolor=black,urlcolor=blue]{hyperref}
\begin{document}
\begin{itemize}[leftmargin=*,nosep]
    \item Turbo Apply LaTeX smoke test.
\end{itemize}
\href{https://example.com}{example.com}
\end{document}
""",
            encoding="utf-8",
        )
        compile_resume(tex_path, output_stem="TurboApplySmoke")
        return True


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
        "--self-test",
        action="store_true",
        help="Verify the local LaTeX/MiKTeX setup using the Turbo Apply template packages.",
    )
    parser.add_argument(
        "tex_file",
        nargs="?",
        default="resume-template.tex",
        help="LaTeX file to compile (default: resume-template.tex)",
    )
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("LaTeX self-test passed.")
        return

    pdf = compile_resume(args.tex_file)
    print(f"Created: {pdf}")
    if open_pdf_in_browser(pdf):
        print("Opened in browser")
    else:
        print("Created PDF, but could not open it in browser.")


if __name__ == "__main__":
    main()
