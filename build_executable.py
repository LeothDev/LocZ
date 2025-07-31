import subprocess
import sys
import os

def install_requirements():
    """Install PyInstaller and requirements"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def create_executable():
    """Create Windows executable"""
    
    # PyInstaller command for Windows executable
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single executable file
        "--windowed",                   # No console window (optional)
        "--name=LocZ",       # Executable name
        "--icon=icon.ico",              # Add icon if you have one (optional)
        "--add-data=templates:templates", # Include templates folder
        "--hidden-import=sklearn.utils._cython_blas",
        "--hidden-import=sklearn.neighbors.typedefs", 
        "--hidden-import=sklearn.neighbors.quad_tree",
        "--hidden-import=sklearn.tree._utils",
        "--collect-all=sentence_transformers",
        "--collect-all=transformers",
        "--collect-all=torch",
        "run_app.py"
    ]
    
    print("🔨 Building Windows executable...")
    subprocess.run(cmd)
    print("✅ Build complete! Check the 'dist' folder.")

if __name__ == "__main__":
    install_requirements()
    create_executable()
