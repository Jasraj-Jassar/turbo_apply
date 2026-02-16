#!/usr/bin/env bash
# One-click Linux setup and launcher for Turbo Apply.

set -u
set -o pipefail

PROJECT_NAME="Turbo Apply"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
COOKIES_FILE="$SCRIPT_DIR/cookies.txt"
APT_UPDATED=0
PKG_MGR=""
PYTHON_BIN=""
VENV_PY=""

info() { printf "  [INFO] %s\n" "$*"; }
warn() { printf "  [WARN] %s\n" "$*"; }
error() { printf "  [ERROR] %s\n" "$*" >&2; }

restart_as_user_if_needed() {
  # Running GUI apps as root via sudo usually fails on Wayland/X11 auth.
  if [[ "$(id -u)" -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    local user_home
    user_home="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
    [[ -n "$user_home" ]] || user_home="/home/$SUDO_USER"

    warn "This script was started with sudo. Restarting as user '$SUDO_USER' for GUI compatibility..."

    if command -v runuser >/dev/null 2>&1; then
      exec runuser -u "$SUDO_USER" -- \
        env HOME="$user_home" \
            DISPLAY="${DISPLAY:-}" \
            WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
            XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/${SUDO_UID:-}}" \
            bash "$SCRIPT_DIR/TurboApply.sh" "$@"
    fi

    error "runuser is unavailable. Please run this without sudo:"
    error "  ./TurboApply.sh"
    exit 1
  fi
}

run_as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    return 127
  fi
}

detect_pkg_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    PKG_MGR="apt"
  elif command -v pacman >/dev/null 2>&1; then
    PKG_MGR="pacman"
  elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
  elif command -v zypper >/dev/null 2>&1; then
    PKG_MGR="zypper"
  else
    PKG_MGR=""
  fi
}

install_packages() {
  if [[ $# -eq 0 ]]; then
    return 0
  fi
  if [[ -z "$PKG_MGR" ]]; then
    return 1
  fi

  case "$PKG_MGR" in
    apt)
      if [[ "$APT_UPDATED" -eq 0 ]]; then
        run_as_root apt-get update || return 1
        APT_UPDATED=1
      fi
      run_as_root apt-get install -y "$@"
      ;;
    pacman)
      run_as_root pacman -Sy --noconfirm "$@"
      ;;
    dnf)
      run_as_root dnf install -y "$@"
      ;;
    zypper)
      run_as_root zypper --non-interactive install "$@"
      ;;
    *)
      return 1
      ;;
  esac
}

install_python_stack() {
  case "$PKG_MGR" in
    apt)
      install_packages python3 python3-pip python3-venv python3-tk
      ;;
    pacman)
      install_packages python python-pip tk
      ;;
    dnf)
      install_packages python3 python3-pip python3-tkinter
      ;;
    zypper)
      install_packages python3 python3-pip python3-virtualenv python3-tk
      ;;
    *)
      return 1
      ;;
  esac
}

install_tk() {
  case "$PKG_MGR" in
    apt) install_packages python3-tk ;;
    pacman) install_packages tk ;;
    dnf) install_packages python3-tkinter ;;
    zypper) install_packages python3-tk ;;
    *) return 1 ;;
  esac
}

install_pdflatex() {
  case "$PKG_MGR" in
    apt) install_packages texlive-latex-base ;;
    pacman) install_packages texlive-basic ;;
    dnf) install_packages texlive-scheme-basic ;;
    zypper) install_packages texlive ;;
    *) return 1 ;;
  esac
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    return 0
  fi
  if command -v python >/dev/null 2>&1 &&
     python -c "import sys; raise SystemExit(0 if sys.version_info.major == 3 else 1)" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
    return 0
  fi
  return 1
}

ensure_python() {
  info "[1/5] Checking Python..."
  if find_python; then
    info "Using: $("$PYTHON_BIN" --version 2>&1)"
    return 0
  fi

  warn "Python 3 not found. Attempting to install..."
  if ! install_python_stack; then
    error "Could not install Python automatically."
    error "Install Python 3 manually, then rerun: ./TurboApply.sh"
    return 1
  fi

  if ! find_python; then
    error "Python installation finished but python3 is still unavailable."
    return 1
  fi
  info "Using: $("$PYTHON_BIN" --version 2>&1)"
}

ensure_venv() {
  info "[2/5] Creating/updating virtual environment..."

  if [[ -e "$VENV_DIR" && ! -w "$VENV_DIR" ]]; then
    warn ".venv is not writable (possibly created with sudo). Fixing ownership..."
    run_as_root chown -R "$(id -u):$(id -g)" "$VENV_DIR" || {
      error "Could not fix ownership for $VENV_DIR"
      error "Run manually: sudo chown -R $(id -u):$(id -g) \"$VENV_DIR\""
      return 1
    }
  fi

  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    if ! "$PYTHON_BIN" -m venv "$VENV_DIR" >/dev/null 2>&1; then
      warn "venv module unavailable. Attempting to install missing Python components..."
      install_python_stack || true
      "$PYTHON_BIN" -m venv "$VENV_DIR" >/dev/null 2>&1 || {
        error "Failed to create virtual environment at $VENV_DIR"
        return 1
      }
    fi
  fi

  VENV_PY="$VENV_DIR/bin/python"
  "$VENV_PY" -m pip --version >/dev/null 2>&1 || {
    error "pip is unavailable in virtual environment."
    return 1
  }

  if [[ -f "$REQUIREMENTS_FILE" ]]; then
    "$VENV_PY" -m pip install --upgrade pip >/dev/null 2>&1 || true
    if ! "$VENV_PY" -m pip install -r "$REQUIREMENTS_FILE"; then
      warn "Some pip packages failed to install. Continuing (core app still works)."
    fi
  else
    warn "requirements.txt not found, skipping pip install."
  fi
}

ensure_tkinter() {
  info "[3/5] Checking tkinter..."
  if "$VENV_PY" -c "import tkinter" >/dev/null 2>&1; then
    info "tkinter OK."
    return 0
  fi

  warn "tkinter is missing. Attempting to install..."
  install_tk || true
  if ! "$VENV_PY" -c "import tkinter" >/dev/null 2>&1; then
    error "tkinter still unavailable."
    case "$PKG_MGR" in
      apt) error "Install manually: sudo apt-get install python3-tk" ;;
      pacman) error "Install manually: sudo pacman -S tk" ;;
      dnf) error "Install manually: sudo dnf install python3-tkinter" ;;
      zypper) error "Install manually: sudo zypper install python3-tk" ;;
      *) error "Install your distro's python tkinter package, then rerun." ;;
    esac
    return 1
  fi
  info "tkinter OK."
}

ensure_pdflatex() {
  info "[4/5] Checking pdflatex..."
  if command -v pdflatex >/dev/null 2>&1; then
    info "pdflatex OK."
    return 0
  fi

  warn "pdflatex not found. Attempting to install (optional for PDF compile)..."
  if install_pdflatex && command -v pdflatex >/dev/null 2>&1; then
    info "pdflatex installed."
  else
    warn "Could not install pdflatex automatically. Resume PDF compile may fail until TeX Live is installed."
  fi
}

ensure_cookies_file() {
  if [[ -f "$COOKIES_FILE" ]]; then
    return 0
  fi
  cat >"$COOKIES_FILE" <<'EOF'
# Netscape HTTP Cookie File
# https://cookie-editor.com/ - Export cookies in Netscape format and paste them here.
# One cookie per line. Lines starting with # are comments.
EOF
  info "Created empty cookies.txt."
}

launch_app() {
  info "[5/5] Launching ${PROJECT_NAME}..."
  cd "$SCRIPT_DIR" || return 1
  exec "$VENV_PY" "$SCRIPT_DIR/run.py"
}

main() {
  restart_as_user_if_needed "$@"

  printf "\n"
  printf " ========================================\n"
  printf "   %s - Linux Setup & Launch\n" "$PROJECT_NAME"
  printf " ========================================\n\n"

  detect_pkg_manager
  if [[ -n "$PKG_MGR" ]]; then
    info "Detected package manager: $PKG_MGR"
  else
    warn "No supported package manager detected; auto-install may be limited."
  fi

  ensure_python || exit 1
  ensure_venv || exit 1
  ensure_tkinter || exit 1
  ensure_pdflatex || true
  ensure_cookies_file
  launch_app || exit 1
}

main "$@"
