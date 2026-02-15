# Turbo Apply

Paste a job posting link, get a folder with everything you need to apply — your resume template, AI prompts to tailor it, and a cover letter prompt. One click.

---

## Getting Started (Windows)

### Step 1 — Download

Click the green **Code** button on this page → **Download ZIP**. Extract the folder anywhere (Desktop is fine).

### Step 2 — Run

Double-click **`TurboApply.cmd`** inside the folder.

That's it. The script will automatically install everything your computer needs (Python, LaTeX tools, etc.) and open the app. This only happens the first time — after that it just opens instantly.

> If Windows shows a "Windows protected your PC" popup, click **More info** → **Run anyway**. This is normal for downloaded scripts.

### Step 3 — Use the App

The app opens with three modes at the top. Pick the one you need:

#### 🌐 Scrape a Job Posting
1. Copy the job URL from LinkedIn, Indeed, or any job site
2. Paste it into the URL box
3. Pick where you want the folder created (Output Dir)
4. Click **⚡ Generate**
5. A folder is created with your resume template + AI prompts ready to go

#### 📁 Create an Empty Template
1. Switch to **Empty Template** mode
2. Type a name for the folder (e.g. "Google-SWE")
3. Click **⚡ Generate**

#### 📄 Compile Your Resume to PDF
1. Switch to **Compile LaTeX** mode
2. Click **Browse** and pick your `.tex` file
3. Click **📄 Compile PDF**
4. Your `Resume.pdf` appears next to the `.tex` file

### Options

- **🇫🇷 French mode** — Check this box to get prompts in French
- **Open in VS Code** — Automatically opens the new folder in VS Code after generating

### What You Get

After generating, your folder looks like this:

```
Software-Eng-Google/
├── Software-Eng-Google.txt     ← the job description
├── prompt.txt                  ← give this to ChatGPT/Copilot to tailor your resume
├── prompt-cover.txt            ← give this to ChatGPT/Copilot to write a cover letter
└── resume-template.tex         ← your resume template, ready to edit
```

### Scraping Tips

- **LinkedIn/Indeed blocking you?** Save the job page as an HTML file (Ctrl+S in your browser), then use the **Browse** button to select it instead of pasting the URL.
- **Need cookies?** Install [Cookie-Editor](https://cookie-editor.com/) in your browser, export cookies as `cookies.txt` (Netscape format), and drop the file in the Turbo Apply folder.

---
---

# README for Devs

Everything below is for developers who want to understand the codebase, use the CLI, or contribute.

## Requirements

- **Python 3.10+** (uses walrus operator and modern syntax)
- **tkinter** — included with Python on Windows; on Linux install with `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora)
- No other third-party packages required — uses only the Python standard library
- **Optional:** `pdflatex` on PATH for LaTeX → PDF compilation — install [MiKTeX](https://miktex.org/download) (Windows) or TeX Live (`sudo apt install texlive-latex-base` on Linux)
- **Optional:** `cookies.txt` (Netscape format) in the project root for authenticated scraping — export cookies using [Cookie-Editor](https://cookie-editor.com/)

## How It Works

1. **Scrape** — Extracts job title, company, and full description from a URL. Supports **LinkedIn**, **Indeed**, any site with [JSON-LD `JobPosting`](https://schema.org/JobPosting) markup, and local `.html` files.
2. **Generate** — Creates a folder named `<Title>-<Company>/` with:
   | File | Purpose |
   |---|---|
   | `<folder>.txt` | Job description text + source URL |
   | `prompt.txt` | AI prompt for tailoring `resume-template.tex` to the posting |
   | `prompt-cover.txt` | AI prompt for generating a cover letter from `Resume.pdf` |
   | `resume-template.tex` | Copy of your LaTeX resume template, ready to edit |
3. **Open** — Auto-opens the folder in VS Code (when `code` is on PATH).
4. **Build** — Compiles `.tex` → `Resume.pdf` via `pdflatex` (auto-finds MiKTeX even if not on PATH).

## CLI Usage

```bash
# Via the unified launcher (GUI if no args, CLI if args given)
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

## GUI Launch

```bash
python run.py           # auto-opens GUI when no arguments given
python gui.py            # launch GUI directly
```

**Windows one-click:** Double-click `TurboApply.cmd` — auto-installs Python, MiKTeX, and pip packages if missing, then launches the GUI. Requires [winget](https://aka.ms/getwinget) (built into Windows 10/11).

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
TurboApply.cmd       # One-click Windows installer + launcher
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

- **Windows:** Paths and Windows-reserved names (CON, PRN, etc.) are automatically handled. `pdflatex` is auto-discovered in common MiKTeX/TeX Live install directories even if not on PATH.
- **Linux / macOS:** Ensure `pdflatex` is installed (`sudo apt install texlive-latex-base` or equivalent) for PDF builds. VS Code auto-open works when the `code` CLI is available.

