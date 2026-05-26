import sys
import os
from .app import main as app_main

def main():
    if os.geteuid() != 0:
        # Re-launch with pkexec, preserving GUI environment variables
        print("Not running as root. Escalating privileges via pkexec...")
        
        env_vars = []
        for var in ['DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY']:
            if var in os.environ:
                env_vars.append(f"{var}={os.environ[var]}")
        
        # Ensure the root process can find the module if it's installed in user site-packages
        python_path = os.environ.get("PYTHONPATH", "")
        if python_path:
            python_path += ":" + ":".join(sys.path)
        else:
            python_path = ":".join(sys.path)
        env_vars.append(f"PYTHONPATH={python_path}")
                
        args = ["pkexec", "env"] + env_vars + [sys.executable, "-m", "wireguard_gui"]
        os.execvp("pkexec", args)
    
    sys.exit(app_main())

if __name__ == '__main__':
    main()
