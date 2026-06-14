#!/usr/bin/env python3
"""CLI for creating job application folders from job postings."""

import argparse
import platform
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import processor
import scraper

_CODEX_START_PROMPT = "follow both promts"


def _find_pdflatex():
    """Locate pdflatex on PATH or in common install directories."""
    import platform as _plat
    found = shutil.which("pdflatex")
    if found:
        return found
    if _plat.system() == "Windows":
        candidates = [
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
            Path("C:/Program Files/MiKTeX/miktex/bin/x64/pdflatex.exe"),
            Path("C:/Program Files (x86)/MiKTeX/miktex/bin/x64/pdflatex.exe"),
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/pdflatex.exe",
        ]
        texlive = Path("C:/texlive")
        if texlive.exists():
            for year_dir in sorted(texlive.iterdir(), reverse=True):
                cand = year_dir / "bin/windows/pdflatex.exe"
                if cand.exists():
                    return str(cand)
        for c in candidates:
            if c.exists():
                return str(c)
    return None


def _compile_resume(tex_arg):
    path = _parse_path(tex_arg)
    if path.suffix.lower() != ".tex" or not path.is_file():
        raise ValueError(f"Invalid .tex file: {path}")

    stem = "Resume"
    _cleanup_aux(path.parent, stem)

    pdflatex = _find_pdflatex()
    if not pdflatex:
        raise RuntimeError(
            "pdflatex not found. Install MiKTeX (https://miktex.org/download) "
            "or TeX Live, then restart this application."
        )

    try:
        result = subprocess.run(
            [pdflatex, "--enable-installer", "-interaction=nonstopmode",
             f"-jobname={stem}", path.name],
            cwd=path.parent, capture_output=True, text=True
        )
    finally:
        _cleanup_aux(path.parent, stem)

    if result.returncode != 0:
        raise RuntimeError(f"pdflatex failed:\n{result.stdout}")

    return path.parent / f"{stem}.pdf"


def _parse_path(value):
    if value.lower().startswith("file://"):
        parsed = urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in ("", "localhost"):
            path = f"//{parsed.netloc}{path}"
        value = url2pathname(path)
    return Path(value).expanduser().resolve()


def _cleanup_aux(directory, stem):
    for ext in (".aux", ".log", ".out", ".toc", ".nav", ".snm", ".fls", ".fdb_latexmk", ".synctex.gz"):
        try:
            (directory / f"{stem}{ext}").unlink()
        except OSError:
            pass


def _which_first(*names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _popen_silent(args):
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if platform.system() == "Windows" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(args, **kwargs)


def _open_in_codex(path):
    names = ("codex.cmd", "codex.exe", "codex") if platform.system() == "Windows" else ("codex",)
    codex = _which_first(*names)
    if codex:
        try:
            _popen_silent([codex, "app", str(path)])
            _send_codex_start_prompt()
            return True
        except OSError:
            pass
    return False


def _open_in_vscode(path):
    names = ("code.cmd", "code.exe", "code") if platform.system() == "Windows" else ("code",)
    code = _which_first(*names)
    if code:
        try:
            _popen_silent([code, str(path)])
            return True
        except OSError:
            pass
    return False


def _open_workspace(path, opener):
    if opener == "none":
        return "None", True
    if opener == "vscode":
        return "VS Code", _open_in_vscode(path)
    return "Codex", _open_in_codex(path)


def _send_codex_start_prompt():
    if platform.system() != "Windows":
        return

    script = (
        f"$prompt = '{_CODEX_START_PROMPT}'; "
        "Start-Sleep -Seconds 3; "
        "$shell = New-Object -ComObject WScript.Shell; "
        "for ($i = 0; $i -lt 20; $i++) { "
        "if ($shell.AppActivate('Codex')) { "
        "Start-Sleep -Milliseconds 300; "
        "$shell.SendKeys($prompt + '{ENTER}'); "
        "exit 0 "
        "} "
        "Start-Sleep -Milliseconds 500 "
        "}"
    )
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "ByPass",
             "-WindowStyle", "Hidden", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Create job folder from posting URL or compile .tex resume.")
    parser.add_argument("url", nargs="?", help="Job posting URL or .tex file path")
    parser.add_argument("-vf", action="store_true", help="French mode")
    parser.add_argument("-e", type=str, help="Empty template folder")
    parser.add_argument(
        "--open-with", choices=("codex", "vscode", "none"), default="codex",
        help="Open generated folders with Codex, VS Code, or not at all (default: codex)",
    )
    args = parser.parse_args()

    # if empty folder, skip whole process
    if args.e:
        try:
            result = processor.process_empty_job(args.e.strip(), Path.cwd(), french=args.vf)
        except ValueError as e:
            parser.error(str(e))
        print(f"Created: {result['folder_path']}")
        if args.open_with != "none":
            opener_name, opened = _open_workspace(result["folder_path"], args.open_with)
            print(f"Opened in {opener_name}" if opened else f"Could not open in {opener_name}")
        if tpl := result.get("resume_template_path"):
            print(f"Template: {tpl}")
        if script := result.get("latex_script_path"):
            print(f"Script: {script}")
        print("Ended")
        return

    target = (args.url or "").strip()
    if not target:
        try:
            target = input("Job posting link or .tex path: ").strip()
        except EOFError:
            pass

    if not target:
        parser.error("URL or .tex path required.")

    # .tex file → compile PDF
    if target.lower().endswith(".tex") and not target.lower().startswith(("http://", "https://")):
        try:
            pdf = _compile_resume(target)
        except Exception as e:
            raise SystemExit(str(e)) from e
        print(f"Created: {pdf}")
        return

    # URL → scrape and process
    job = scraper.scrape_job(target)
    result = processor.process_job(job, Path.cwd(), target, french=args.vf)

    print(f"Created: {result['folder_path']}")
    if args.open_with != "none":
        opener_name, opened = _open_workspace(result["folder_path"], args.open_with)
        print(f"Opened in {opener_name}" if opened else f"Could not open in {opener_name}")
    if tpl := result.get("resume_template_path"):
        print(f"Template: {tpl}")
    if script := result.get("latex_script_path"):
        print(f"Script: {script}")


if __name__ == "__main__":
    main()
