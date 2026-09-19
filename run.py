"""
Digital Landfill - Unified App Launcher
Launches both FastAPI Backend and Vite React Frontend concurrently.
Opens http://127.0.0.1:5173/ in your default browser.
"""

import os
import subprocess
import sys
import time
import webbrowser

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    print("=" * 60)
    print("  DIGITAL LANDFILL — Starting Unified Application")
    print("=" * 60)
    print("  [1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.api:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=root_dir,
    )

    print("  [2/2] Launching React Frontend on http://127.0.0.1:5173 ...")
    # On Windows, npm is npm.cmd
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir,
    )

    print("\n  ✓ Both servers started successfully!")
    print("  ✓ Opening http://127.0.0.1:5173/ in your browser...")
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5173/")

    print("\n  Press CTRL+C in this terminal to stop all servers.\n")
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n  Shutting down Digital Landfill servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("  Shutdown complete.")

if __name__ == "__main__":
    main()
