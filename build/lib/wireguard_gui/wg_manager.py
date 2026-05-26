import subprocess
import os
import re

WG_DIR = "/etc/wireguard"

def _run_cmd(cmd: list) -> subprocess.CompletedProcess:
    """Run a command directly (app is already running as root)."""
    return subprocess.run(cmd, capture_output=True, text=True)

def list_profiles() -> list:
    """List available wireguard profiles in /etc/wireguard/."""
    try:
        files = os.listdir(WG_DIR)
    except FileNotFoundError:
        return []
    except PermissionError:
        return []
    
    profiles = []
    for f in files:
        if f.endswith(".conf"):
            profiles.append(f[:-5])
    return profiles

def get_active_interfaces() -> list:
    """Get a list of currently active wireguard interfaces."""
    result = _run_cmd(["wg", "show", "interfaces"])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().split()
    return []

def toggle_connection(profile: str, connect: bool) -> tuple[bool, str]:
    """Turn a wireguard profile on or off."""
    cmd = "up" if connect else "down"
    result = _run_cmd(["wg-quick", cmd, profile])
    success = result.returncode == 0
    return success, result.stderr or result.stdout

def get_status(profile: str) -> dict:
    """Get status and stats for a specific profile."""
    active = get_active_interfaces()
    if profile not in active:
        return {"status": "disconnected"}
    
    result = _run_cmd(["wg", "show", profile])
    if result.returncode != 0:
        return {"status": "error", "message": result.stderr}
    
    output = result.stdout
    stats = {"status": "connected", "peers": []}
    
    current_peer = None
    for line in output.split('\n'):
        line = line.strip()
        if line.startswith("peer:"):
            current_peer = {"id": line.split(" ")[1]}
            stats["peers"].append(current_peer)
        elif current_peer:
            if "endpoint:" in line:
                current_peer["endpoint"] = line.split(":", 1)[1].strip()
            elif "latest handshake:" in line:
                current_peer["latest_handshake"] = line.split(":", 1)[1].strip()
            elif "transfer:" in line:
                current_peer["transfer"] = line.split(":", 1)[1].strip()
                
    return stats

def import_profile(filepath: str) -> tuple[bool, str]:
    """Copy a .conf file into /etc/wireguard/."""
    if not os.path.isfile(filepath):
        return False, "File does not exist."
    if not filepath.endswith(".conf"):
        return False, "File must be a .conf file."
    
    basename = os.path.basename(filepath)
    dest = os.path.join(WG_DIR, basename)
    
    # We're root, so we can just copy and set permissions directly using Python
    try:
        import shutil
        shutil.copy2(filepath, dest)
        os.chmod(dest, 0o600)
        return True, "Profile imported successfully."
    except Exception as e:
        return False, f"Error: {e}"

def save_config(name: str, content: str) -> tuple[bool, str]:
    """Save a pasted config to /etc/wireguard/."""
    if not name:
        return False, "Profile name cannot be empty."
    
    if not name.endswith(".conf"):
        name += ".conf"
        
    dest = os.path.join(WG_DIR, name)
    try:
        with open(dest, "w") as f:
            f.write(content)
        os.chmod(dest, 0o600)
        return True, "Profile saved successfully."
    except Exception as e:
        return False, f"Error: {e}"
