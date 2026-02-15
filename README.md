# Turbo Apply

A cross-platform desktop app (GUI + CLI) that turns a job posting URL into a ready-to-work application folder — complete with the job description, AI-ready prompts for tailoring your resume and writing a cover letter, and a copy of your LaTeX resume template.

Works on **Windows** and **Linux**. Zero third-party dependencies — built entirely on Python's standard library (tkinter).

## Requirements

- **Python 3.10+** (uses walrus operator and modern syntax)
- **tkinter** — included with Python on Windows; on Linux install with `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora)
- No other third-party packages required — uses only the Python standard library
- **Optional:** `pdflatex` on PATH for LaTeX → PDF compilation
- **Optional:** `cookies.txt` (Netscape format) in the project root for authenticated scraping — export cookies using [Cookie-Editor](https://cookie-editor.com/)

## How It Works

1. **Scrape** — Give it a job URL (or a saved HTML file). The scraper extracts the job title, company, and full description. Supports **LinkedIn**, **Indeed**, any site that embeds [JSON-LD `JobPosting`](https://schema.org/JobPosting) markup, and local `.html` files as a fallback.
2. **Generate** — Creates a clean, OS-safe folder named `<Title>-<Company>/` and populates it with:
   | File | Purpose |
   |---|---|
   | `<folder>.txt` | Job description text + source URL |
   | `prompt.txt` | AI prompt for tailoring `resume-template.tex` to the posting |
   | `prompt-cover.txt` | AI prompt for generating a cover letter from `Resume.pdf` |
   | `resume-template.tex` | Copy of your LaTeX resume template, ready to edit |
3. **Open** — Automatically opens the new folder in VS Code (when `code` is on PATH).
4. **Build** — Pass a `.tex` file instead of a URL to compile it to `Resume.pdf` via `pdflatex`.

The generated prompts are designed to be fed directly to an AI assistant (ChatGPT, Copilot, etc.) along with the job description so it can tailor your resume and draft a cover letter for each application.

## GUI — Quick Start

Launch the graphical interface:

```bash
python run.py           # auto-opens GUI when no arguments given
python gui.py            # launch GUI directly
```

The GUI provides three modes accessible via radio buttons:

| Mode | What it does |
|---|---|
| **🌐 Scrape URL / HTML** | Paste a job URL or browse for a local HTML file → generates the full folder |
| **📁 Empty Template** | Enter a folder name → creates a skeleton folder with prompts and template |
| **📄 Compile LaTeX** | Browse for a `.tex` file → compiles it to `Resume.pdf` via `pdflatex` |

Features:
- **Output directory picker** — choose where folders are created
- **French mode toggle** — generates French prompts
- **Open in VS Code** — auto-opens the new folder after generation
- **Open Folder button** — opens the result in your file explorer
- **Live output log** — colour-coded progress and error messages
- **Threaded execution** — GUI stays responsive during scraping

## CLI — Quick Start

Pass arguments to use the command-line interface:

```bash
# Via the unified launcher
python run.py "<job_url>"
python run.py -vf "<job_url>"
python run.py -e "My-Job-Name"
python run.py /path/to/resume.tex

# Or directly
python job_tool.py "<job_url>"
python job_tool.py "/path/to/page.html"
python job_tool.py /path/to/resume.tex
python job_tool.py -vf "<job_url>"
python job_tool.py -e "My-Job-Name"
```

> **Tip:** Quote long URLs so shell characters (like `&`) don't break the command.

## Output Snapshot

```
Software-Eng-Acme-Corp/
├── Software-Eng-Acme-Corp.txt      # job description + source URL
├── prompt.txt                       # resume-tailoring prompt
├── prompt-cover.txt                 # cover-letter prompt
└── resume-template.tex              # your LaTeX template copy
```

## Scraping Details

| Source | Strategy |
|---|---|
| Any site with JSON-LD | Extracts `JobPosting` structured data |
| LinkedIn | Parses Open Graph meta tags + HTML patterns |
| Indeed | Custom HTML parser for title, company, and description |
| Local HTML | Reads the file directly — best fallback when sites block requests |

The scraper uses browser-like headers, optional cookie files (`cookies.txt` in Netscape format), retry logic, and detects CAPTCHAs and auth walls with actionable error messages.

## Project Structure

```
run.py               # Unified launcher — GUI (no args) or CLI (with args)
gui.py               # Cross-platform GUI application (tkinter)
job_tool.py          # CLI entry point — dispatches scrape, process, or compile
scraper.py           # Fetches & parses job postings (LinkedIn, Indeed, JSON-LD, HTML)
processor.py         # Builds folder name, creates folder, writes files
prompt_creator.py    # Loads prompt templates from templates/ or templates_vf/
file_ops.py          # File I/O helpers (write, copy, text wrapping)
templates/           # English prompt templates + LaTeX resume template
templates_vf/        # French prompt templates + LaTeX resume template
```

## French Mode (`-vf`)

Pass `-vf` to use French prompt templates from `templates_vf/`. The resume-tailoring and cover-letter prompts will be generated in French.

```bash
python job_tool.py -vf "<job_url>"
python job_tool.py -vf -e "Mon-Poste"
```

## Platform Notes

- **Windows:** Use `py -3 job_tool.py "<job_url>"` or `python ...`. Paths and Windows-reserved names (CON, PRN, etc.) are automatically handled. Install [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/) and ensure `pdflatex.exe` is on PATH for PDF builds.
- **Linux / macOS:** Ensure `pdflatex` is installed (`sudo apt install texlive-latex-base` or equivalent) for PDF builds. VS Code auto-open works when the `code` CLI is available.

