#!/usr/bin/env python3
"""CLI for creating job application folders from job postings."""

import argparse
import platform
import shutil
import subprocess
from pathlib import Path

import latex_to_pdf
import processor
import scraper

_CODEX_START_PROMPT = (
    "Follow both prompts: read prompt.txt and prompt-cover.txt. Only edit "
    "resume-template.tex and create cover-letter.txt. Use the existing "
    "latex_to_pdf.py to create Resume.pdf. Do not create, edit, or replace "
    "scripts or any other files. Do not change the LaTeX preamble, "
    "documentclass, or usepackage lines. If the converter reports a missing "
    "LaTeX package or font, stop and report it."
)


def _compile_resume(tex_arg):
    return latex_to_pdf.compile_resume(tex_arg)


def _open_pdf_in_browser(pdf_path):
    return latex_to_pdf.open_pdf_in_browser(pdf_path)


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
            if platform.system() == "Windows":
                _popen_silent([
                    "cmd.exe", "/c", "start", "Codex CLI", "/D", str(path),
                    codex, "-C", str(path), _CODEX_START_PROMPT,
                ])
            else:
                _popen_silent([codex, "-C", str(path), _CODEX_START_PROMPT])
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
    return "Codex CLI", _open_in_codex(path)


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
        if _open_pdf_in_browser(pdf):
            print("Opened PDF in browser")
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
