#!/usr/bin/env python3
"""Cross-platform GUI for Turbo Apply — job application folder generator."""

import os
import platform
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse
from urllib.request import url2pathname

import processor
import scraper

# ── Colours & Theme ─────────────────────────────────────────────────────────

_BG = "#1e1e2e"
_BG_LIGHT = "#2a2a3c"
_BG_INPUT = "#313145"
_FG = "#cdd6f4"
_FG_DIM = "#7f849c"
_ACCENT = "#89b4fa"
_ACCENT_HOVER = "#74c7ec"
_SUCCESS = "#a6e3a1"
_ERROR = "#f38ba8"
_WARN = "#f9e2af"
_BORDER = "#45475a"
_FONT = ("Segoe UI", 11) if platform.system() == "Windows" else ("Helvetica", 11)
_FONT_SM = (_FONT[0], 9)
_FONT_LG = (_FONT[0], 14, "bold")
_FONT_MONO = ("Consolas", 10) if platform.system() == "Windows" else ("Monospace", 10)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _parse_path(value):
    if value.lower().startswith("file://"):
        parsed = urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in ("", "localhost"):
            path = f"//{parsed.netloc}{path}"
        value = url2pathname(path)
    return Path(value).expanduser().resolve()


def _cleanup_aux(directory, stem):
    for ext in (".aux", ".log", ".out", ".toc", ".nav", ".snm",
                ".fls", ".fdb_latexmk", ".synctex.gz"):
        try:
            (directory / f"{stem}{ext}").unlink()
        except OSError:
            pass


def _compile_resume(tex_arg):
    path = _parse_path(tex_arg)
    if path.suffix.lower() != ".tex" or not path.is_file():
        raise ValueError(f"Invalid .tex file: {path}")
    stem = "Resume"
    _cleanup_aux(path.parent, stem)
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", f"-jobname={stem}", path.name],
            cwd=path.parent, capture_output=True, text=True,
        )
    except FileNotFoundError:
        raise RuntimeError("pdflatex not found. Install TeX Live / MiKTeX.") from None
    finally:
        _cleanup_aux(path.parent, stem)
    if result.returncode != 0:
        raise RuntimeError(f"pdflatex failed:\n{result.stdout}")
    return path.parent / f"{stem}.pdf"


def _open_in_vscode(path):
    code = shutil.which("code") or shutil.which("code.cmd")
    if code:
        try:
            subprocess.Popen([code, str(path)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            pass
    return False


def _open_folder(path):
    """Open folder in the native file explorer."""
    path = str(path)
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


# ── Custom Widgets ──────────────────────────────────────────────────────────

class PlaceholderEntry(tk.Entry):
    """Entry with greyed-out placeholder text."""

    def __init__(self, master, placeholder="", **kw):
        self._ph = placeholder
        self._ph_color = _FG_DIM
        self._fg = kw.get("fg", _FG)
        super().__init__(master, **kw)
        self._show_placeholder()
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        if not self.get():
            self.insert(0, self._ph)
            self.config(fg=self._ph_color)

    def _on_focus_in(self, _):
        if self.get() == self._ph and str(self.cget("fg")) == self._ph_color:
            self.delete(0, tk.END)
            self.config(fg=self._fg)

    def _on_focus_out(self, _):
        if not self.get():
            self._show_placeholder()

    def get_value(self):
        val = self.get()
        return "" if val == self._ph else val


class HoverButton(tk.Button):
    """Button that changes colour on hover."""

    def __init__(self, master, hover_bg=None, hover_fg=None, **kw):
        super().__init__(master, **kw)
        self._default_bg = kw.get("bg", kw.get("background", _BG_LIGHT))
        self._default_fg = kw.get("fg", kw.get("foreground", _FG))
        self._hover_bg = hover_bg or _ACCENT
        self._hover_fg = hover_fg or "#11111b"
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        self.config(bg=self._hover_bg, fg=self._hover_fg)

    def _on_leave(self, _):
        self.config(bg=self._default_bg, fg=self._default_fg)


# ── Main Application ────────────────────────────────────────────────────────

class TurboApplyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Turbo Apply")
        self.configure(bg=_BG)
        self.minsize(720, 600)
        self.geometry("780x660")
        self._set_icon()

        # State
        self._french = tk.BooleanVar(value=False)
        self._open_vscode = tk.BooleanVar(value=True)
        self._output_dir = tk.StringVar(value=str(Path.cwd()))
        self._mode = tk.StringVar(value="url")  # url | empty | tex

        self._build_ui()
        self._centre_window()

    # ── Icon ────────────────────────────────────────────────────────────

    def _set_icon(self):
        try:
            # Use a built-in icon on all platforms
            self.iconname("Turbo Apply")
        except Exception:
            pass

    def _centre_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI Build ────────────────────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        header = tk.Frame(self, bg=_BG)
        header.pack(fill=tk.X, padx=24, pady=(20, 4))
        tk.Label(header, text="⚡ Turbo Apply", font=_FONT_LG,
                 bg=_BG, fg=_ACCENT).pack(side=tk.LEFT)
        tk.Label(header, text="Job application folder generator",
                 font=_FONT_SM, bg=_BG, fg=_FG_DIM).pack(side=tk.LEFT, padx=(12, 0))

        sep = tk.Frame(self, bg=_BORDER, height=1)
        sep.pack(fill=tk.X, padx=24, pady=(8, 16))

        body = tk.Frame(self, bg=_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=24)

        # ── Mode selector ───────────────────────────────────────────
        mode_frame = tk.Frame(body, bg=_BG)
        mode_frame.pack(fill=tk.X, pady=(0, 12))
        tk.Label(mode_frame, text="Mode", font=_FONT, bg=_BG, fg=_FG).pack(side=tk.LEFT)

        for val, label in [("url", "🌐  Scrape URL / HTML"),
                           ("empty", "📁  Empty Template"),
                           ("tex", "📄  Compile LaTeX")]:
            rb = tk.Radiobutton(
                mode_frame, text=label, variable=self._mode, value=val,
                font=_FONT, bg=_BG, fg=_FG, selectcolor=_BG_INPUT,
                activebackground=_BG, activeforeground=_ACCENT,
                indicatoron=True, command=self._on_mode_change,
            )
            rb.pack(side=tk.LEFT, padx=(16, 0))

        # ── Input area ──────────────────────────────────────────────
        self._input_frame = tk.Frame(body, bg=_BG)
        self._input_frame.pack(fill=tk.X, pady=(0, 8))

        # URL / HTML input row
        self._url_frame = tk.Frame(self._input_frame, bg=_BG)
        self._url_label = tk.Label(self._url_frame, text="URL or HTML",
                                   font=_FONT, bg=_BG, fg=_FG, width=12, anchor="w")
        self._url_label.pack(side=tk.LEFT)
        self._url_entry = PlaceholderEntry(
            self._url_frame, placeholder="https://example.com/job/123  or  /path/to/page.html",
            font=_FONT, bg=_BG_INPUT, fg=_FG, insertbackground=_FG,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=_BORDER, highlightcolor=_ACCENT,
        )
        self._url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))

        self._browse_html_btn = HoverButton(
            self._url_frame, text="Browse…", font=_FONT_SM,
            bg=_BG_LIGHT, fg=_FG, relief=tk.FLAT, padx=12, pady=4,
            cursor="hand2", command=self._browse_html,
        )
        self._browse_html_btn.pack(side=tk.LEFT)
        self._url_frame.pack(fill=tk.X, pady=(0, 8))

        # Empty template name row
        self._empty_frame = tk.Frame(self._input_frame, bg=_BG)
        tk.Label(self._empty_frame, text="Folder Name",
                 font=_FONT, bg=_BG, fg=_FG, width=12, anchor="w").pack(side=tk.LEFT)
        self._empty_entry = PlaceholderEntry(
            self._empty_frame, placeholder="My-Job-Application",
            font=_FONT, bg=_BG_INPUT, fg=_FG, insertbackground=_FG,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=_BORDER, highlightcolor=_ACCENT,
        )
        self._empty_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        # .tex file input row
        self._tex_frame = tk.Frame(self._input_frame, bg=_BG)
        tk.Label(self._tex_frame, text=".tex File",
                 font=_FONT, bg=_BG, fg=_FG, width=12, anchor="w").pack(side=tk.LEFT)
        self._tex_entry = PlaceholderEntry(
            self._tex_frame, placeholder="/path/to/resume.tex",
            font=_FONT, bg=_BG_INPUT, fg=_FG, insertbackground=_FG,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=_BORDER, highlightcolor=_ACCENT,
        )
        self._tex_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self._browse_tex_btn = HoverButton(
            self._tex_frame, text="Browse…", font=_FONT_SM,
            bg=_BG_LIGHT, fg=_FG, relief=tk.FLAT, padx=12, pady=4,
            cursor="hand2", command=self._browse_tex,
        )
        self._browse_tex_btn.pack(side=tk.LEFT)

        # ── Output directory ────────────────────────────────────────
        dir_frame = tk.Frame(body, bg=_BG)
        dir_frame.pack(fill=tk.X, pady=(0, 12))
        tk.Label(dir_frame, text="Output Dir",
                 font=_FONT, bg=_BG, fg=_FG, width=12, anchor="w").pack(side=tk.LEFT)
        self._dir_entry = tk.Entry(
            dir_frame, textvariable=self._output_dir,
            font=_FONT, bg=_BG_INPUT, fg=_FG, insertbackground=_FG,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=_BORDER, highlightcolor=_ACCENT,
        )
        self._dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        HoverButton(
            dir_frame, text="Browse…", font=_FONT_SM,
            bg=_BG_LIGHT, fg=_FG, relief=tk.FLAT, padx=12, pady=4,
            cursor="hand2", command=self._browse_dir,
        ).pack(side=tk.LEFT)

        # ── Options row ─────────────────────────────────────────────
        opts = tk.Frame(body, bg=_BG)
        opts.pack(fill=tk.X, pady=(0, 16))

        tk.Checkbutton(
            opts, text="🇫🇷  French mode (-vf)", variable=self._french,
            font=_FONT, bg=_BG, fg=_FG, selectcolor=_BG_INPUT,
            activebackground=_BG, activeforeground=_ACCENT,
        ).pack(side=tk.LEFT)

        tk.Checkbutton(
            opts, text="Open in VS Code", variable=self._open_vscode,
            font=_FONT, bg=_BG, fg=_FG, selectcolor=_BG_INPUT,
            activebackground=_BG, activeforeground=_ACCENT,
        ).pack(side=tk.LEFT, padx=(24, 0))

        # ── Action button ───────────────────────────────────────────
        btn_row = tk.Frame(body, bg=_BG)
        btn_row.pack(fill=tk.X, pady=(0, 12))

        self._run_btn = HoverButton(
            btn_row, text="⚡  Generate", font=(_FONT[0], 12, "bold"),
            bg=_ACCENT, fg="#11111b", relief=tk.FLAT,
            padx=28, pady=8, cursor="hand2",
            hover_bg=_ACCENT_HOVER, hover_fg="#11111b",
            command=self._on_run,
        )
        self._run_btn.pack(side=tk.LEFT)

        self._open_folder_btn = HoverButton(
            btn_row, text="📂  Open Folder", font=_FONT,
            bg=_BG_LIGHT, fg=_FG, relief=tk.FLAT,
            padx=16, pady=6, cursor="hand2",
            command=self._on_open_folder,
        )
        self._open_folder_btn.pack(side=tk.LEFT, padx=(12, 0))
        self._open_folder_btn.config(state=tk.DISABLED)

        # ── Log output ──────────────────────────────────────────────
        log_label = tk.Frame(body, bg=_BG)
        log_label.pack(fill=tk.X, pady=(0, 4))
        tk.Label(log_label, text="Output Log", font=_FONT_SM,
                 bg=_BG, fg=_FG_DIM).pack(side=tk.LEFT)

        log_frame = tk.Frame(body, bg=_BORDER, bd=1, relief=tk.FLAT)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))
        self._log = tk.Text(
            log_frame, font=_FONT_MONO, bg=_BG_INPUT, fg=_FG,
            insertbackground=_FG, relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED, padx=10, pady=8,
        )
        scrollbar = tk.Scrollbar(log_frame, command=self._log.yview)
        self._log.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure log tag colours
        self._log.tag_config("info", foreground=_FG)
        self._log.tag_config("success", foreground=_SUCCESS)
        self._log.tag_config("error", foreground=_ERROR)
        self._log.tag_config("warn", foreground=_WARN)
        self._log.tag_config("accent", foreground=_ACCENT)

        # ── Status bar ──────────────────────────────────────────────
        self._status = tk.Label(
            self, text="Ready", font=_FONT_SM, bg=_BG_LIGHT,
            fg=_FG_DIM, anchor=tk.W, padx=12, pady=4,
        )
        self._status.pack(fill=tk.X, side=tk.BOTTOM)

        # Track last created folder for "Open Folder" button
        self._last_folder = None

        # Show correct input for initial mode
        self._on_mode_change()

    # ── Mode switching ──────────────────────────────────────────────

    def _on_mode_change(self):
        mode = self._mode.get()
        self._url_frame.pack_forget()
        self._empty_frame.pack_forget()
        self._tex_frame.pack_forget()

        if mode == "url":
            self._url_frame.pack(fill=tk.X, pady=(0, 8))
            self._run_btn.config(text="⚡  Generate")
        elif mode == "empty":
            self._empty_frame.pack(fill=tk.X, pady=(0, 8))
            self._run_btn.config(text="⚡  Generate")
        elif mode == "tex":
            self._tex_frame.pack(fill=tk.X, pady=(0, 8))
            self._run_btn.config(text="📄  Compile PDF")

    # ── File dialogs ────────────────────────────────────────────────

    def _browse_html(self):
        path = filedialog.askopenfilename(
            title="Select HTML file",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")],
        )
        if path:
            self._url_entry.delete(0, tk.END)
            self._url_entry.config(fg=_FG)
            self._url_entry.insert(0, path)

    def _browse_tex(self):
        path = filedialog.askopenfilename(
            title="Select .tex file",
            filetypes=[("LaTeX files", "*.tex"), ("All files", "*.*")],
        )
        if path:
            self._tex_entry.delete(0, tk.END)
            self._tex_entry.config(fg=_FG)
            self._tex_entry.insert(0, path)

    def _browse_dir(self):
        path = filedialog.askdirectory(title="Select output directory")
        if path:
            self._output_dir.set(path)

    # ── Logging ─────────────────────────────────────────────────────

    def _log_msg(self, msg, tag="info"):
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, msg + "\n", tag)
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)

    def _clear_log(self):
        self._log.config(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.config(state=tk.DISABLED)

    def _set_status(self, msg, colour=_FG_DIM):
        self._status.config(text=msg, fg=colour)

    # ── Run action ──────────────────────────────────────────────────

    def _on_run(self):
        mode = self._mode.get()
        self._clear_log()
        self._open_folder_btn.config(state=tk.DISABLED)
        self._last_folder = None

        if mode == "url":
            self._run_url()
        elif mode == "empty":
            self._run_empty()
        elif mode == "tex":
            self._run_tex()

    def _set_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        self._run_btn.config(state=state)
        if busy:
            self._set_status("Working…", _WARN)
        else:
            self._run_btn.config(state=tk.NORMAL)

    def _run_in_thread(self, fn):
        """Run fn in a background thread so the GUI stays responsive."""
        self._set_busy(True)

        def wrapper():
            try:
                fn()
            except Exception as e:
                self.after(0, self._log_msg, f"Error: {e}", "error")
                self.after(0, self._set_status, "Failed", _ERROR)
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=wrapper, daemon=True).start()

    # ── Scrape URL / HTML ───────────────────────────────────────────

    def _run_url(self):
        target = self._url_entry.get_value().strip()
        if not target:
            self._log_msg("Please enter a URL or HTML file path.", "warn")
            return

        base_dir = Path(self._output_dir.get())
        french = self._french.get()
        open_vs = self._open_vscode.get()

        def work():
            self.after(0, self._log_msg, f"Scraping: {target}", "accent")
            job = scraper.scrape_job(target)
            self.after(0, self._log_msg,
                       f"Found: {job.get('title', '?')} @ {job.get('company', '?')}", "info")
            self.after(0, self._log_msg, "Creating folder…", "info")

            result = processor.process_job(job, base_dir, target, french=french)
            folder = result["folder_path"]
            self._last_folder = folder

            self.after(0, self._log_msg, f"Folder:  {folder}", "success")
            if result.get("file_path"):
                self.after(0, self._log_msg, f"Description:  {result['file_path'].name}", "info")
            if result.get("prompt_path"):
                self.after(0, self._log_msg, f"Prompt:  {result['prompt_path'].name}", "info")
            if result.get("cover_prompt_path"):
                self.after(0, self._log_msg, f"Cover:   {result['cover_prompt_path'].name}", "info")
            if result.get("resume_template_path"):
                self.after(0, self._log_msg, f"Template: {result['resume_template_path'].name}", "info")

            if open_vs:
                if _open_in_vscode(folder):
                    self.after(0, self._log_msg, "Opened in VS Code", "accent")

            self.after(0, self._set_status, f"Done — {folder.name}", _SUCCESS)
            self.after(0, lambda: self._open_folder_btn.config(state=tk.NORMAL))

        self._run_in_thread(work)

    # ── Empty Template ──────────────────────────────────────────────

    def _run_empty(self):
        name = self._empty_entry.get_value().strip()
        if not name:
            self._log_msg("Please enter a folder name.", "warn")
            return

        base_dir = Path(self._output_dir.get())
        french = self._french.get()
        open_vs = self._open_vscode.get()

        def work():
            self.after(0, self._log_msg, f"Creating empty template: {name}", "accent")
            result = processor.process_empty_job(name, base_dir, french=french)
            folder = result["folder_path"]
            self._last_folder = folder

            self.after(0, self._log_msg, f"Folder: {folder}", "success")
            if result.get("resume_template_path"):
                self.after(0, self._log_msg, f"Template: {result['resume_template_path'].name}", "info")

            if open_vs:
                if _open_in_vscode(folder):
                    self.after(0, self._log_msg, "Opened in VS Code", "accent")

            self.after(0, self._set_status, f"Done — {folder.name}", _SUCCESS)
            self.after(0, lambda: self._open_folder_btn.config(state=tk.NORMAL))

        self._run_in_thread(work)

    # ── Compile LaTeX ───────────────────────────────────────────────

    def _run_tex(self):
        tex_path = self._tex_entry.get_value().strip()
        if not tex_path:
            self._log_msg("Please select a .tex file.", "warn")
            return

        def work():
            self.after(0, self._log_msg, f"Compiling: {tex_path}", "accent")
            pdf = _compile_resume(tex_path)
            self._last_folder = pdf.parent
            self.after(0, self._log_msg, f"Created: {pdf}", "success")
            self.after(0, self._set_status, f"PDF ready — {pdf.name}", _SUCCESS)
            self.after(0, lambda: self._open_folder_btn.config(state=tk.NORMAL))

        self._run_in_thread(work)

    # ── Open folder ─────────────────────────────────────────────────

    def _on_open_folder(self):
        if self._last_folder and Path(self._last_folder).exists():
            _open_folder(self._last_folder)


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    app = TurboApplyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
