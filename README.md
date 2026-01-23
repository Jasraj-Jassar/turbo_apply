# Job Apply Organizer

Tool to automate organizing the positions I apply to. It takes a job posting
and creates a folder plus a wrapped description text file in the
directory you run it from. It can also compile a LaTeX resume to `Resume.pdf`.

## How It Works
1. Run the tool with a job URL (quote long URLs) or a saved HTML file.
2. It extracts the job title, company, and description from the page.
3. It creates a folder named from the title + company (shortened).
4. It writes `<folder>/<folder>.txt` (source URL on top), `<folder>/prompt.txt`
   (from `templates/prompt-template.txt`), and `<folder>/prompt-cover.txt`
   (from `templates/cover-letter-template.txt`).
5. It copies `templates/resume-template.tex` into the folder so you can start a
   tailored resume; build it later with `python job_tool.py <that-file>.tex`.

## Usage
```
python job_tool.py "<job_url>"
# or just run and paste when prompted (helps with URLs containing '&')
python job_tool.py
# build Resume.pdf from a LaTeX file (requires pdflatex)
python job_tool.py /path/to/resume.tex
```

Long URLs should be quoted so your shell does not split them (unquoted `&` will
background the command in many shells). If you hit a 403,
save the page as HTML and pass the file path instead:
```
python job_tool.py "/path/to/saved_page.html"
```

## Windows Notes
- Run with `py -3 job_tool.py "<job_url>"` (PowerShell/cmd) or `python job_tool.py ...`.
- Saved HTML or `.tex` files can be passed as Windows paths or `file://` URIs; the tool normalizes them.
- Folder/file names are adjusted to avoid Windows reserved device names and trailing spaces/dots.
- For resume builds, install MiKTeX (or TeX Live) and ensure `pdflatex.exe` is on your PATH; MiKTeX may prompt to install missing packages on first use.

## Output Example
Input:
- Title: `PLC Programmer`
- Company: `Automation Integrators Inc`

Output folder:
```
PLC-Prog-Automation-Integrators-Inc/
PLC-Prog-Automation-Integrators-Inc/PLC-Prog-Automation-Integrators-Inc.txt
PLC-Prog-Automation-Integrators-Inc/prompt.txt
PLC-Prog-Automation-Integrators-Inc/prompt-cover.txt
PLC-Prog-Automation-Integrators-Inc/resume-template.tex
```

When given a `.tex` file, the tool runs `pdflatex` (in that file's directory)
and writes `Resume.pdf` alongside it. LaTeX builds require `pdflatex` plus any
packages your resume uses (e.g., `marvosym` from `texlive-fontsextra` /
`texlive-fonts-extra`). Auxiliary files from the build (`.aux`, `.log`, etc.)
are cleaned up automatically after each run (even on errors); only
`Resume.pdf` remains.

## Modules
- `scraper.py`: fetches HTML and extracts job data
- `processor.py`: builds folder names and coordinates output
- `file_ops.py`: filesystem and text wrapping
- `job_tool.py`: CLI entrypoint
