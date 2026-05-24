"""
PDF MCQ Extraction Tool - Launcher
Starts both Node.js server and Python UI automatically
"""

import subprocess
import sys
import os
import time
import shutil

# Fix Unicode/emoji output on Windows terminals (cp1252 doesn't support emoji)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def find_python():
    """Find Python executable on the system"""
    # Try common Python commands
    for cmd in ["python", "python3", "py"]:
        python_path = shutil.which(cmd)
        if python_path:
            return python_path
    return None

def main():
    # Get the directory where the script is located
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        script_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        script_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(script_dir)
    
    print("=" * 50)
    print("🚀 PDF MCQ Extraction Tool - Launcher")
    print("=" * 50)
    
    node_process = None
    python_process = None
    
    try:
        # Find Python executable
        if getattr(sys, 'frozen', False):
            # Running as .exe - need to find system Python
            python_exe = find_python()
            if not python_exe:
                print("❌ Error: Python not found in PATH!")
                print("Please make sure Python is installed and added to PATH.")
                input("Press Enter to exit...")
                return
            print(f"🐍 Using Python: {python_exe}")
        else:
            # Running as script - use current interpreter
            python_exe = sys.executable
            
        # Cleanup any existing zombie node processes on port 3000 before starting
        print("\n🧹 Cleaning up any existing background processes...")
        try:
            result = subprocess.run('netstat -ano | findstr :3000', shell=True, capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /F /T /PID {pid}', shell=True, capture_output=True)
        except:
            pass
        
        # Start Node.js server (hidden window)
        print("\n📦 Starting Node.js server...")
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        
        node_process = subprocess.Popen(
            ["node", "server.js"],
            cwd=script_dir,
            shell=False,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        )
        
        # Wait a moment for the server to start
        print("⏳ Waiting for server to initialize...")
        time.sleep(3)
        
        # Start Python UI
        print("\n🖥️  Starting Python UI...")
        ui_main_path = os.path.join(script_dir, "ui_main.py")
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        python_process = subprocess.Popen(
            [python_exe, ui_main_path],
            cwd=script_dir,
            env=env
        )
        
        print("\n✅ Both services started successfully!")
        print("📝 Close the UI window to stop the application.\n")
        
        # Wait for Python UI to close
        python_process.wait()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        input("Press Enter to exit...")
    
    finally:
        # Cleanup: Stop Node.js server when UI closes
        print("\n🛑 Shutting down...")
        
        if node_process:
            try:
                # Kill the node process and its children
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(node_process.pid)],
                    shell=True,
                    capture_output=True
                )
                
                # Backup cleanup just in case
                try:
                    result = subprocess.run('netstat -ano | findstr :3000', shell=True, capture_output=True, text=True)
                    for line in result.stdout.strip().split('\n'):
                        if 'LISTENING' in line:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                subprocess.run(f'taskkill /F /T /PID {pid}', shell=True, capture_output=True)
                except:
                    pass
                    
                print("✅ Node.js server stopped")
            except:
                pass
        
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
