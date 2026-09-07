#!/usr/bin/env python3
"""
CipherLink & Chat App — Unified Multi-Application Runner
=========================================================
Runs both applications (CipherLink and Chat App), including their backends
and frontends, using a single Python command.

Usage:
  python run.py                 # Run both applications (all 4 services)
  python run.py --app cipherlink # Run only CipherLink (BE + FE)
  python run.py --app chat       # Run only Chat App (BE + FE)
  python run.py --backend-only   # Run only backends
  python run.py --frontend-only  # Run only frontends
  python run.py --windows        # Launch each service in separate terminal windows
  python run.py --stop           # Terminate all running services on ports 8000, 8001, 3000, 5173
  python run.py --status         # Check status of ports and services
"""

import argparse
import ctypes
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Ensure UTF-8 output encoding across Windows / Linux / macOS
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --- Terminal Colors & Styling ---
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    # Enable ANSI escape codes in Windows Console
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Colors
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
WHITE = "\033[97m"

PROJECT_ROOT = Path(__file__).resolve().parent

# --- Service Definitions ---
SERVICES = {
    "cipherlink_backend": {
        "name": "CipherLink Backend",
        "tag": "CipherLink-BE",
        "color": CYAN,
        "app": "cipherlink",
        "role": "backend",
        "port": 8001,
        "url": "http://localhost:8001",
        "docs_url": "http://localhost:8001/docs",
        "cwd": PROJECT_ROOT / "cipherlink" / "backend",
        "venv_candidates": [
            PROJECT_ROOT / "cipherlink" / "backend" / "venv",
            PROJECT_ROOT / "cipherlink" / "backend" / "env",
        ],
        "cmd_args": ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        "type": "python",
    },
    "cipherlink_frontend": {
        "name": "CipherLink Frontend",
        "tag": "CipherLink-FE",
        "color": BLUE,
        "app": "cipherlink",
        "role": "frontend",
        "port": 5173,
        "url": "http://localhost:5173",
        "docs_url": None,
        "cwd": PROJECT_ROOT / "cipherlink" / "frontend",
        "cmd_args": ["run", "dev"],
        "type": "npm",
    },
    "chat_backend": {
        "name": "Chat App Backend",
        "tag": "ChatApp-BE   ",
        "color": GREEN,
        "app": "chat",
        "role": "backend",
        "port": 8000,
        "url": "http://localhost:8000",
        "docs_url": "http://localhost:8000/docs",
        "cwd": PROJECT_ROOT / "chat_app" / "backend",
        "venv_candidates": [
            PROJECT_ROOT / "chat_app" / "backend" / "env",
            PROJECT_ROOT / "chat_app" / "backend" / "venv",
        ],
        "cmd_args": ["-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        "type": "python",
    },
    "chat_frontend": {
        "name": "Chat App Frontend",
        "tag": "ChatApp-FE   ",
        "color": YELLOW,
        "app": "chat",
        "role": "frontend",
        "port": 3000,
        "url": "http://localhost:3000",
        "docs_url": None,
        "cwd": PROJECT_ROOT / "chat_app" / "frontend",
        "cmd_args": ["run", "dev"],
        "type": "npm",
    },
}

ALL_PORTS = [s["port"] for s in SERVICES.values()]

# Global list of running child processes
running_processes = []
shutdown_initiated = False


def print_banner():
    banner = f"""
{BOLD}{CYAN}===================================================================={RESET}
{BOLD}{CYAN}      [#] CipherLink & Chat App — Unified Multi-App Runner          {RESET}
{BOLD}{CYAN}===================================================================={RESET}"""
    print(banner)


def find_python_executable(candidates):
    """Finds the python executable from a list of venv candidate directories."""
    for cand in candidates:
        if IS_WINDOWS:
            exe = cand / "Scripts" / "python.exe"
        else:
            exe = cand / "bin" / "python"
        if exe.exists():
            return str(exe)
    # Fallback to current system python
    return sys.executable


def find_npm_executable():
    """Locates npm on Windows or Unix."""
    npm_path = shutil.which("npm.cmd") if IS_WINDOWS else shutil.which("npm")
    if not npm_path:
        npm_path = shutil.which("npm")
    return npm_path


def is_port_in_use(port: int) -> bool:
    """Checks whether a TCP port is currently open and bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_pids_for_port(port: int) -> list[int]:
    """Retrieves process IDs listening on a specific port."""
    pids = set()
    if IS_WINDOWS:
        try:
            output = subprocess.check_output(
                ["netstat", "-ano", "-p", "TCP"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in output.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0].upper() == "TCP":
                    local_addr = parts[1]
                    state = parts[3].upper()
                    pid_str = parts[4]
                    if (local_addr.endswith(f":{port}") or local_addr.endswith(f"]:{port}")) and state in ("LISTENING", "ESTABLISHED"):
                        try:
                            pids.add(int(pid_str))
                        except ValueError:
                            pass
        except Exception:
            pass
    else:
        try:
            output = subprocess.check_output(
                ["lsof", "-t", f"-i:{port}"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in output.strip().split():
                try:
                    pids.add(int(line))
                except ValueError:
                    pass
        except Exception:
            pass
    return list(pids)


def kill_process_tree(pid: int):
    """Forcefully and cleanly terminates a process and all its children."""
    if pid <= 0:
        return
    if IS_WINDOWS:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass


def free_port(port: int, service_name: str = ""):
    """Terminates any process using the specified port."""
    pids = get_pids_for_port(port)
    if not pids:
        return False

    name_label = f" ({service_name})" if service_name else ""
    for pid in pids:
        print(f"{YELLOW}[!] Port {port}{name_label} occupied by PID {pid}. Freeing...{RESET}")
        kill_process_tree(pid)

    # Wait up to 2 seconds for port to clear
    for _ in range(10):
        time.sleep(0.2)
        if not is_port_in_use(port):
            print(f"{GREEN}[OK] Port {port} freed successfully.{RESET}")
            return True

    return not is_port_in_use(port)


def stop_all_services():
    """Stops all running services on ports 8000, 8001, 3000, 5173."""
    print(f"\n{BOLD}{YELLOW}Stopping all services across ports {ALL_PORTS}...{RESET}")
    any_stopped = False
    for s_key, s_info in SERVICES.items():
        port = s_info["port"]
        pids = get_pids_for_port(port)
        if pids:
            any_stopped = True
            for pid in pids:
                print(f"  {RED}Stopping {s_info['name']} (PID: {pid}) on port {port}...{RESET}")
                kill_process_tree(pid)
        else:
            print(f"  {DIM}Port {port} ({s_info['name']}) is already free.{RESET}")

    if any_stopped:
        print(f"\n{BOLD}{GREEN}[OK] All targeted services stopped.{RESET}\n")
    else:
        print(f"\n{BOLD}{GREEN}[OK] No running services found on target ports.{RESET}\n")


def show_status():
    """Prints current status of each service port."""
    print(f"\n{BOLD}Service Status Overview:{RESET}")
    print(f"{'Service':<25} {'Port':<8} {'Status':<12} {'PIDs':<15} {'URL'}")
    print("-" * 75)
    for s_info in SERVICES.values():
        port = s_info["port"]
        pids = get_pids_for_port(port)
        if pids:
            status_str = f"{GREEN}ONLINE{RESET}"
            pids_str = ", ".join(map(str, pids))
        else:
            status_str = f"{DIM}OFFLINE{RESET}"
            pids_str = "-"
        print(f"{s_info['name']:<25} {port:<8} {status_str:<21} {pids_str:<15} {s_info['url']}")
    print()


def stream_logs(process, tag: str, color: str):
    """Reads stdout from child process and prints with colored prefix."""
    prefix = f"{color}{BOLD}[{tag}]{RESET} "
    try:
        for line in iter(process.stdout.readline, ""):
            if shutdown_initiated:
                break
            if line:
                print(f"{prefix}{line.rstrip()}")
    except (ValueError, IOError):
        pass


def launch_in_separate_windows(selected_services, npm_path):
    """Launches each service in its own dedicated command window."""
    print(f"\n{BOLD}{GREEN}Launching services in separate terminal windows...{RESET}\n")
    for s_key, s_info in selected_services.items():
        cwd = s_info["cwd"]
        port = s_info["port"]
        title = f"{s_info['name']} (:{port})"

        if s_info["type"] == "python":
            py_exe = find_python_executable(s_info["venv_candidates"])
            cmd_list = [py_exe] + s_info["cmd_args"]
            cmd_str = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd_list)
        else:
            cmd_str = f'"{npm_path}" {" ".join(s_info["cmd_args"])}'

        print(f"  Launching {s_info['color']}{title}{RESET}...")
        if IS_WINDOWS:
            # Use cmd.exe /k to keep window open with the title
            full_cmd = f'start "{title}" cmd /k "cd /d "{cwd}" && {cmd_str}"'
            subprocess.Popen(full_cmd, shell=True)
        else:
            # On Linux/macOS, spawn background process
            subprocess.Popen(cmd_str, cwd=cwd, shell=True)

    print(f"\n{BOLD}{GREEN}[OK] All {len(selected_services)} services launched in separate windows.{RESET}")
    print(f"{DIM}Use 'python run.py --stop' to terminate them at any time.{RESET}\n")


def launch_unified(selected_services, npm_path):
    """Launches all selected services and streams output to current terminal."""
    global running_processes, shutdown_initiated

    threads = []

    print(f"\n{BOLD}{GREEN}Starting {len(selected_services)} services in unified log stream...{RESET}\n")

    for s_key, s_info in selected_services.items():
        cwd = s_info["cwd"]
        tag = s_info["tag"]
        color = s_info["color"]

        if s_info["type"] == "python":
            py_exe = find_python_executable(s_info["venv_candidates"])
            cmd = [py_exe] + s_info["cmd_args"]
            display_info = f"Python ({Path(py_exe).parent.parent.name}) -> port {s_info['port']}"
        else:
            cmd = [npm_path] + s_info["cmd_args"]
            display_info = f"NPM dev server -> port {s_info['port']}"

        print(f"  Starting {color}{s_info['name']:<22}{RESET} [{display_info}]")

        try:
            # Set creationflags on Windows to create a new process group for clean tree killing
            creationflags = 0
            if IS_WINDOWS:
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
            running_processes.append((s_info, proc))

            # Start background reader thread
            t = threading.Thread(target=stream_logs, args=(proc, tag, color), daemon=True)
            t.start()
            threads.append(t)

        except Exception as e:
            print(f"{RED}[ERROR] Failed to start {s_info['name']}: {e}{RESET}")

    # Display endpoints dashboard
    print("\n" + f"{BOLD}{WHITE}--------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{WHITE}  >> Service Dashboards & Endpoints:{RESET}")
    for s_info, proc in running_processes:
        tag_str = f"{s_info['color']}{s_info['name']}{RESET}"
        url_str = f"{WHITE}{BOLD}{s_info['url']}{RESET}"
        docs_str = f" {DIM}(Docs: {s_info['docs_url']}){RESET}" if s_info.get("docs_url") else ""
        print(f"   * {tag_str:<32} -> {url_str}{docs_str}")
    print(f"{BOLD}{WHITE}--------------------------------------------------------------------{RESET}")
    print(f"{YELLOW}Press Ctrl+C at any time to gracefully terminate all services.{RESET}\n")

    # Monitor loop
    try:
        while True:
            time.sleep(0.5)
            # Check if all processes terminated
            all_dead = all(proc.poll() is not None for _, proc in running_processes)
            if all_dead and running_processes:
                print(f"\n{YELLOW}[!] All processes have exited.{RESET}")
                break
    except KeyboardInterrupt:
        print(f"\n\n{BOLD}{YELLOW}Received shutdown signal (Ctrl+C). Terminating all services...{RESET}")
    finally:
        shutdown_initiated = True
        for s_info, proc in running_processes:
            if proc.poll() is None:
                print(f"  {DIM}Stopping {s_info['name']} (PID: {proc.pid})...{RESET}")
                kill_process_tree(proc.pid)

        # Final sweep on ports to prevent any lingering orphan sockets
        time.sleep(0.5)
        for s_info, _ in running_processes:
            pids = get_pids_for_port(s_info["port"])
            for pid in pids:
                kill_process_tree(pid)

        print(f"{BOLD}{GREEN}[OK] All services cleanly stopped.{RESET}\n")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Unified runner for CipherLink & Chat App applications.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                   # Run both applications (all 4 services)
  python run.py --app cipherlink   # Run only CipherLink (BE + FE)
  python run.py --app chat         # Run only Chat App (BE + FE)
  python run.py --backend-only     # Run backends only (port 8000 & 8001)
  python run.py --frontend-only    # Run frontends only (port 3000 & 5173)
  python run.py --windows          # Launch each service in its own terminal window
  python run.py --status           # Check which services/ports are running
  python run.py --stop             # Stop all services on ports 8000, 8001, 3000, 5173
        """,
    )
    parser.add_argument(
        "-a", "--app",
        choices=["all", "cipherlink", "chat"],
        default="all",
        help="Choose which application to run (default: all)",
    )
    parser.add_argument(
        "-b", "--backend-only",
        action="store_true",
        help="Run only backend services (FastAPI / Uvicorn)",
    )
    parser.add_argument(
        "-f", "--frontend-only",
        action="store_true",
        help="Run only frontend services (Vite / NPM)",
    )
    parser.add_argument(
        "-w", "--windows",
        action="store_true",
        help="Launch each service in a separate terminal window instead of multiplexing logs",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop all running services on ports 8000, 8001, 3000, 5173 and exit",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show online/offline status of all services and ports",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved commands, paths, and environments without launching them",
    )
    parser.add_argument(
        "--no-kill",
        action="store_true",
        help="Do not automatically kill existing processes holding target ports before starting",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    print_banner()

    if args.stop:
        stop_all_services()
        return

    if args.status:
        show_status()
        return

    # Check for npm
    npm_path = find_npm_executable()
    if not npm_path and not args.backend_only:
        print(f"{RED}[ERROR] 'npm' was not found in your PATH. Please install Node.js/npm.{RESET}")
        sys.exit(1)

    # Filter services based on CLI options
    selected = {}
    for key, info in SERVICES.items():
        # Filter by app
        if args.app != "all" and info["app"] != args.app:
            continue
        # Filter by role
        if args.backend_only and info["role"] != "backend":
            continue
        if args.frontend_only and info["role"] != "frontend":
            continue
        selected[key] = info

    if not selected:
        print(f"{RED}[ERROR] No services matched the specified criteria.{RESET}")
        sys.exit(1)

    if args.dry_run:
        print(f"\n{BOLD}Dry Run Preview ({len(selected)} services selected):{RESET}")
        print("-" * 75)
        for s_key, s_info in selected.items():
            if s_info["type"] == "python":
                py_exe = find_python_executable(s_info["venv_candidates"])
                cmd = [py_exe] + s_info["cmd_args"]
            else:
                cmd = [npm_path] + s_info["cmd_args"]
            print(f"  {s_info['color']}{BOLD}{s_info['name']}{RESET} (Port: {s_info['port']})")
            print(f"    Directory : {s_info['cwd']}")
            print(f"    Command   : {' '.join(str(c) for c in cmd)}")
            print(f"    URL       : {s_info['url']}")
            print()
        return

    # Free existing ports before launching unless --no-kill is set
    if not args.no_kill:
        for s_key, s_info in selected.items():
            port = s_info["port"]
            if is_port_in_use(port):
                free_port(port, s_info["name"])

    # Launch services
    if args.windows:
        launch_in_separate_windows(selected, npm_path)
    else:
        launch_unified(selected, npm_path)


if __name__ == "__main__":
    main()
