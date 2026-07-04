#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# SEC Non-Mandated Scraper — Runner Script
# ──────────────────────────────────────────────────────────────────────────────
# Creates/is inside the UV venv, installs deps if needed, then runs the
# Python scraper in the background. Logs output to scraper.log.
#
# Usage:
#   ./run-sec-scraper.sh              # Run in foreground
#   ./run-sec-scraper.sh --background  # Run in background (daemon)
#   ./run-sec-scraper.sh --status      # Check if running
#   ./run-sec-scraper.sh --stop        # Stop background process
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SCRAPER="$SCRIPT_DIR/sec-scraper.py"
LOG="$SCRIPT_DIR/scraper.log"
PID_FILE="$SCRIPT_DIR/.scraper.pid"

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Status check ──
check_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# ── Stop ──
stop_scraper() {
    local pid
    if pid=$(check_running); then
        info "Stopping scraper (PID $pid)..."
        kill "$pid" 2>/dev/null || true
        # Wait up to 10 seconds for graceful shutdown
        for i in $(seq 1 10); do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            warn "Force killing..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
        info "Stopped."
    else
        warn "No scraper running."
    fi
}

    # ── Detect Xvfb ──
if [ -z "${DISPLAY:-}" ] && command -v xvfb-run &>/dev/null; then
    XVFB=(xvfb-run -a --auto-servernum)
    info "No display — using xvfb-run (virtual framebuffer)"
else
    XVFB=()
fi

# ── Run the scraper (foreground) ──
run_scraper() {
    info "Setting up environment..."

    # Create venv if missing
    if [ ! -d "$VENV_DIR" ]; then
        info "Creating virtual environment..."
        uv venv "$VENV_DIR" --python 3.11
    fi

    # Activate
    source "$VENV_DIR/bin/activate"

    # Install dependencies
    info "Installing dependencies..."
    uv pip install --quiet nodriver requests

    info "Starting scraper..."
    echo "─────────────────────────────────────────────────────"
    "${XVFB[@]}" uv run sec-scraper.py 2>&1
    exit_code=$?
    echo "─────────────────────────────────────────────────────"

    if [ $exit_code -eq 0 ]; then
        info "Scraper finished successfully."
    else
        error "Scraper exited with code $exit_code. Check $LOG for details."
    fi

    return $exit_code
}

# ── Run in background ──
run_background() {
    if pid=$(check_running); then
        error "Scraper is already running (PID $pid). Use --stop first."
        exit 1
    fi

    # Use nohup and redirect output
    nohup bash "$0" > "$LOG" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Wait a moment then check
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        info "Scraper started in background (PID $pid)."
        info "Monitor: tail -f $LOG"
        info "Stop:    $0 --stop"
    else
        error "Scraper failed to start. Check $LOG"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# ── Main ──
case "${1:-}" in
    --background|-b)
        run_background
        ;;
    --stop)
        stop_scraper
        ;;
    --status|-s)
        if pid=$(check_running); then
            info "Scraper is running (PID $pid)."
        else
            warn "No scraper running."
        fi
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  (none)        Run scraper in foreground"
        echo "  --background  Run scraper in background (daemon)"
        echo "  --stop        Stop background scraper"
        echo "  --status      Check if scraper is running"
        echo "  --help        Show this help"
        ;;
    *)
        run_scraper
        ;;
esac
