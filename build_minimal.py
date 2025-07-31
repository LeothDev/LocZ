import subprocess
def create_folder_executable():
    """Create folder-based Windows executable (smaller, faster)"""
    
    cmd = [
        "pyinstaller",
        "--onedir",                     # Creates folder instead of single file
        "--name=ALT_File_Editor",
        "--icon=app_icon.ico",
        
        # Include necessary files
        "--add-data=templates:templates",
        
        # Exclude unnecessary modules for smaller size
        "--exclude-module=matplotlib",
        "--exclude-module=PIL", 
        "--exclude-module=cv2",
        "--exclude-module=tkinter",
        "--exclude-module=jupyter",
        "--exclude-module=IPython",
        
        # Hidden imports
        "--hidden-import=sklearn.utils._cython_blas",
        "--hidden-import=sklearn.neighbors.typedefs",
        "--hidden-import=sklearn.tree._utils",
        "--hidden-import=sentence_transformers",
        
        # Console window (so Teresa can see status messages)
        "--console",
        
        "run_app.py"
    ]
    
    print("🔨 Building folder-based Windows executable...")
    try:
        subprocess.run(cmd, check=True)
        print("✅ Build complete!")
        print("📁 Output folder: dist/ALT_File_Editor/")
        print("🚀 Executable: dist/ALT_File_Editor/ALT_File_Editor.exe")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")

if __name__ == "__main__":
    create_folder_executable()
