#!/usr/bin/env python3
"""
Collect Docker container logs from docker-compose projects.

This script:
1. Finds docker-compose files in the current directory
2. Collects "docker compose logs" for ALL services (not just running)
3. Collects container status information
4. Produces both a folder of files AND a timestamped zip file

Output directory: .dockerlogs/
Output files:
  - docker_compose_logs.txt  (all services logs via docker compose logs)
  - _docker_info.txt         (versions + container status, line-broken)
  - <container>.log          (individual container logs)
  - mind2_docker_logs_<timestamp>.zip (archive of all the above)

Usage:
    python scripts/collect_docker_logs.py

    # Or from any directory:
    python /path/to/collect_docker_logs.py
"""

import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


def find_project_root() -> Path:
    """Find the project root by looking for docker-compose files."""
    current = Path.cwd()

    # Check current directory first
    compose_files = list(current.glob("docker-compose*.yml")) + list(current.glob("docker-compose*.yaml"))
    if compose_files:
        return current

    # Walk up the directory tree
    for parent in current.parents:
        compose_files = list(parent.glob("docker-compose*.yml")) + list(parent.glob("docker-compose*.yaml"))
        if compose_files:
            return parent

    return current


def get_project_prefix(project_root: Path) -> str:
    """Get project prefix from directory name."""
    return project_root.name.lower().replace(" ", "_").replace("-", "_")


def get_compose_containers() -> list[str]:
    """Get container names from docker-compose configuration."""
    containers = []

    try:
        # Use docker compose ps to get running containers
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0 and result.stdout.strip():
            containers = [name.strip() for name in result.stdout.strip().split("\n") if name.strip()]
    except subprocess.TimeoutExpired:
        print("Warning: docker compose ps timed out")
    except FileNotFoundError:
        print("Warning: docker command not found")
    except Exception as e:
        print(f"Warning: Error getting compose containers: {e}")

    # Fallback: try to get all running containers if compose ps fails
    if not containers:
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                containers = [name.strip() for name in result.stdout.strip().split("\n") if name.strip()]
        except Exception as e:
            print(f"Warning: Error getting docker containers: {e}")

    return containers


def get_container_logs(container_name: str, tail_lines: int = 10000) -> str:
    """Get logs from a specific container."""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail_lines), "--timestamps", container_name],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Combine stdout and stderr (docker logs outputs to both)
        logs = ""
        if result.stdout:
            logs += result.stdout
        if result.stderr:
            logs += result.stderr

        return logs
    except subprocess.TimeoutExpired:
        return f"[ERROR] Timeout while fetching logs for {container_name}\n"
    except Exception as e:
        return f"[ERROR] Failed to get logs for {container_name}: {e}\n"


def get_compose_logs_all_services() -> str:
    """
    Get docker compose logs for ALL services (not just running containers).
    This is critical audit evidence showing what happened during the compose lifecycle.
    Includes diagnostic header when output is empty or fails.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cwd = os.getcwd()

    header_parts = []
    header_parts.append("=" * 80)
    header_parts.append("DOCKER COMPOSE LOGS - ALL SERVICES")
    header_parts.append("=" * 80)
    header_parts.append(f"Timestamp: {timestamp}")
    header_parts.append(f"Working Directory: {cwd}")
    header_parts.append("")

    logs_parts = []
    services = []
    services_error = None

    # First, get list of all defined services
    try:
        result = subprocess.run(
            ["docker", "compose", "config", "--services"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            services = [s.strip() for s in result.stdout.strip().split("\n") if s.strip()]
            header_parts.append(f"Defined services: {', '.join(services)}")
        else:
            services_error = f"Return code: {result.returncode}, stderr: {result.stderr.strip() if result.stderr else 'none'}"
            header_parts.append(f"[WARNING] Could not get service list: {services_error}")
    except Exception as e:
        services_error = str(e)
        header_parts.append(f"[WARNING] Could not get service list: {e}")

    header_parts.append("")

    # Get logs from all services explicitly (includes exited containers)
    main_logs_cmd = ["docker", "compose", "logs", "--no-color", "--tail", "10000"]
    main_logs_error = None

    try:
        cmd = main_logs_cmd.copy()
        if services:
            cmd.extend(services)

        header_parts.append(f"Command executed: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        header_parts.append(f"Return code: {result.returncode}")
        header_parts.append("")

        if result.stdout:
            logs_parts.append(result.stdout)
        if result.stderr and "no such service" not in result.stderr.lower():
            logs_parts.append(result.stderr)

        if not result.stdout.strip() and not result.stderr.strip():
            main_logs_error = "Command returned empty output"

    except subprocess.TimeoutExpired:
        main_logs_error = "Timeout (120s) while fetching docker compose logs"
        header_parts.append(f"[ERROR] {main_logs_error}")
    except Exception as e:
        main_logs_error = str(e)
        header_parts.append(f"[ERROR] Failed to get compose logs: {e}")

    # Also try to get logs from specific celery workers (they may be exited)
    celery_services = ["celery-worker", "celery-worker-wf1", "celery-worker-wf2"]
    header_parts.append("-" * 80)
    header_parts.append("CELERY WORKER LOGS (explicit fetch)")
    header_parts.append("-" * 80)

    for service in celery_services:
        try:
            result = subprocess.run(
                ["docker", "compose", "logs", "--no-color", "--tail", "1000", service],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.stdout or result.stderr:
                service_logs = (result.stdout or "") + (result.stderr or "")
                if service_logs.strip() and service_logs.strip() not in "\n".join(logs_parts):
                    logs_parts.append(f"\n=== Logs from {service} ===\n{service_logs}")
                    header_parts.append(f"  {service}: logs retrieved ({len(service_logs)} chars)")
                else:
                    header_parts.append(f"  {service}: no additional logs")
            else:
                header_parts.append(f"  {service}: empty output")
        except Exception as e:
            header_parts.append(f"  {service}: error - {e}")

    header_parts.append("")
    header_parts.append("=" * 80)
    header_parts.append("LOG OUTPUT BEGINS BELOW")
    header_parts.append("=" * 80)
    header_parts.append("")

    combined_logs = "\n".join(logs_parts)

    if not combined_logs.strip():
        header_parts.append("[NO LOGS AVAILABLE]")
        header_parts.append("")
        header_parts.append("DIAGNOSTIC INFORMATION:")
        header_parts.append(f"  - Services defined: {len(services)} ({', '.join(services) if services else 'none found'})")
        header_parts.append(f"  - Main logs error: {main_logs_error or 'none'}")
        header_parts.append(f"  - Possible causes:")
        header_parts.append(f"    1. Docker services have not been started (run: docker compose up -d)")
        header_parts.append(f"    2. Services started but have no log output yet")
        header_parts.append(f"    3. docker-compose.yml not found in {cwd}")
        return "\n".join(header_parts)

    return "\n".join(header_parts) + "\n" + combined_logs


def collect_docker_info() -> str:
    """
    Collect general docker information with proper line-broken formatting.
    Each container must appear on its own line.
    Clearly distinguishes GLOBAL (all docker containers) vs PROJECT (compose-scoped).
    """
    info_parts = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cwd = os.getcwd()

    info_parts.append("=" * 80)
    info_parts.append("DOCKER ENVIRONMENT INFORMATION")
    info_parts.append("=" * 80)
    info_parts.append("")

    # Docker version
    docker_version = "Unknown"
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            docker_version = result.stdout.strip()
    except Exception:
        pass

    # Docker compose version
    compose_version = "Unknown"
    try:
        result = subprocess.run(
            ["docker", "compose", "version", "--short"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            compose_version = result.stdout.strip()
    except Exception:
        pass

    info_parts.append(f"Docker Version: {docker_version}")
    info_parts.append(f"Docker Compose Version: {compose_version}")
    info_parts.append(f"Timestamp: {timestamp}")
    info_parts.append(f"Working Directory: {cwd}")
    info_parts.append("")

    # GLOBAL: All running containers (docker ps)
    info_parts.append("=" * 80)
    info_parts.append("GLOBAL: ALL RUNNING CONTAINERS (docker ps)")
    info_parts.append("NOTE: This shows ALL containers on the system, not just this project")
    info_parts.append("=" * 80)
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            info_parts.append("NAME\tSTATUS\tIMAGE")
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    info_parts.append(line.strip())
        else:
            info_parts.append("[No running containers]")
    except Exception as e:
        info_parts.append(f"[ERROR getting container list: {e}]")

    info_parts.append("")

    # PROJECT: Compose-scoped containers (docker compose ps -a)
    info_parts.append("=" * 80)
    info_parts.append("PROJECT: COMPOSE-SCOPED CONTAINERS (docker compose ps -a)")
    info_parts.append("NOTE: This shows containers for THIS project only (including exited)")
    info_parts.append("For detailed compose ps output, see: docker_compose_ps.txt")
    info_parts.append("=" * 80)
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "-a"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                info_parts.append(line)
        else:
            info_parts.append("[No compose services found for this project]")
    except Exception as e:
        info_parts.append(f"[ERROR getting compose services: {e}]")

    return "\n".join(info_parts)


def clean_output_directory(output_dir: Path) -> None:
    """
    Clean the output directory to ensure deterministic output per run.
    Removes all files (including old logs, zips, and info files) but keeps the directory.
    """
    if output_dir.exists():
        for item in output_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    print(f"  Removed stale: {item.name}")
                elif item.is_dir():
                    # Remove subdirectories too (in case of old timestamped folders)
                    import shutil
                    shutil.rmtree(item)
                    print(f"  Removed stale dir: {item.name}")
            except Exception as e:
                print(f"  Warning: Could not remove {item.name}: {e}")


def get_compose_ps_all() -> str:
    """
    Get docker compose ps -a output (compose-scoped container list including exited).
    This is CRITICAL for audit - shows all project containers regardless of state.
    """
    header_parts = []
    header_parts.append("=" * 80)
    header_parts.append("DOCKER COMPOSE PS -A (PROJECT-SCOPED CONTAINER STATUS)")
    header_parts.append("=" * 80)
    header_parts.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    header_parts.append(f"Working Directory: {os.getcwd()}")
    header_parts.append("")

    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "-a"],
            capture_output=True,
            text=True,
            timeout=30
        )
        header_parts.append(f"Command: docker compose ps -a")
        header_parts.append(f"Return Code: {result.returncode}")
        header_parts.append("")

        if result.stdout.strip():
            header_parts.append("OUTPUT:")
            header_parts.append("-" * 80)
            header_parts.append(result.stdout)
        else:
            header_parts.append("[No output from docker compose ps -a]")

        if result.stderr.strip():
            header_parts.append("")
            header_parts.append("STDERR:")
            header_parts.append(result.stderr)

    except subprocess.TimeoutExpired:
        header_parts.append("[ERROR] Timeout while running docker compose ps -a")
    except FileNotFoundError:
        header_parts.append("[ERROR] docker command not found")
    except Exception as e:
        header_parts.append(f"[ERROR] Failed to run docker compose ps -a: {e}")

    return "\n".join(header_parts)


def main():
    """Main entry point."""
    print("Docker Log Collector")
    print("=" * 50)

    # Find project root
    project_root = find_project_root()
    os.chdir(project_root)
    print(f"Project root: {project_root}")

    # Get project prefix
    project_prefix = get_project_prefix(project_root)
    print(f"Project prefix: {project_prefix}")

    # Create output directory
    output_dir = project_root / ".dockerlogs"
    output_dir.mkdir(exist_ok=True)

    # CRITICAL: Clean output directory to ensure deterministic output per run
    print("Cleaning output directory (removing stale files)...")
    clean_output_directory(output_dir)
    print()

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    zip_filename = f"{project_prefix}_docker_logs_{timestamp}.zip"
    zip_path = output_dir / zip_filename

    print(f"Output directory: {output_dir}")
    print(f"Output ZIP: {zip_path}")
    print()

    # Collect files to write (both to folder and ZIP)
    files_to_write = {}

    # 1. Collect docker info (CRITICAL: must have proper line breaks)
    print("Collecting docker info...")
    docker_info = collect_docker_info()
    files_to_write["_docker_info.txt"] = docker_info
    print("  + _docker_info.txt")

    # 2. Collect docker compose logs for ALL services (CRITICAL for audit)
    print("Collecting docker compose logs (all services)...")
    compose_logs = get_compose_logs_all_services()
    files_to_write["docker_compose_logs.txt"] = compose_logs
    compose_size_kb = len(compose_logs.encode('utf-8')) / 1024
    print(f"  + docker_compose_logs.txt ({compose_size_kb:.1f} KB)")

    # 3. Collect docker compose ps -a (CRITICAL for audit - compose-scoped container status)
    print("Collecting docker compose ps -a (project container status)...")
    compose_ps = get_compose_ps_all()
    files_to_write["docker_compose_ps.txt"] = compose_ps
    compose_ps_size_kb = len(compose_ps.encode('utf-8')) / 1024
    print(f"  + docker_compose_ps.txt ({compose_ps_size_kb:.1f} KB)")

    # 4. Get individual container logs
    print("Finding containers...")
    containers = get_compose_containers()

    if containers:
        print(f"Found {len(containers)} container(s):")
        for container in containers:
            print(f"  - {container}")
        print()

        print("Collecting individual container logs...")
        for container in containers:
            print(f"  + {container}.log", end="", flush=True)
            logs = get_container_logs(container)

            if logs:
                files_to_write[f"{container}.log"] = logs
                size_kb = len(logs.encode('utf-8')) / 1024
                print(f" ({size_kb:.1f} KB)")
            else:
                files_to_write[f"{container}.log"] = "[No logs available]\n"
                print(" (empty)")
    else:
        print("No running containers found!")
        files_to_write["no_running_containers.txt"] = (
            f"No running containers found at {timestamp}\n"
            "Check docker_compose_logs.txt for service startup/crash information.\n"
        )

    # Write files to output directory (flat files, not just ZIP)
    print()
    print("Writing files to output directory...")
    for filename, content in files_to_write.items():
        file_path = output_dir / filename
        file_path.write_text(content, encoding='utf-8')
        print(f"  Written: {file_path}")

    # Also create ZIP archive
    print()
    print("Creating ZIP archive...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_to_write.items():
            zf.writestr(filename, content)

    # Final summary
    zip_size = zip_path.stat().st_size / 1024
    print()
    print("=" * 50)
    print(f"Done! Output directory: {output_dir}")
    print(f"Files written: {len(files_to_write)}")
    print(f"ZIP created: {zip_path}")
    print(f"ZIP size: {zip_size:.1f} KB")
    print()
    print("Key files for audit:")
    print(f"  - {output_dir / '_docker_info.txt'}")
    print(f"  - {output_dir / 'docker_compose_logs.txt'}")
    print(f"  - {output_dir / 'docker_compose_ps.txt'}")


if __name__ == "__main__":
    main()
