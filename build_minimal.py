import subprocess
import sys
import os
import shutil

def create_folder_executable():
    """Create folder-based Windows executable (smaller, faster)"""
    
    print("🔨 Building ALT File Editor for Windows...")
    print("📦 This may take 5-10 minutes...")
    
    # Clean previous builds
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("🧹 Cleaned previous build")
    
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    cmd = [
        "pyinstaller",
        "--onedir",                     # Creates folder instead of single file
        "--name=LocZ",
        "--console",                    # Keep console for status messages
        
        # Include necessary files
        "--add-data=templates;templates",  # Windows uses semicolon
        
        # DON'T exclude PIL - sentence_transformers needs it!
        # Only exclude truly unnecessary modules
        "--exclude-module=matplotlib",
        "--exclude-module=cv2",
        "--exclude-module=tkinter",
        "--exclude-module=jupyter",
        "--exclude-module=IPython",
        "--exclude-module=pytest",
        "--exclude-module=sphinx",
        
        # Include all sentence-transformers dependencies
        "--collect-all=sentence_transformers",
        "--collect-all=transformers",
        "--collect-all=torch",
        "--collect-all=PIL",
        "--collect-all=Pillow",
        
        # Hidden imports (comprehensive list)
        "--hidden-import=sklearn.utils._cython_blas",
        "--hidden-import=sklearn.neighbors.typedefs",
        "--hidden-import=sklearn.tree._utils",
        "--hidden-import=sentence_transformers",
        "--hidden-import=transformers",
        "--hidden-import=torch",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=Pillow",
        "--hidden-import=requests",
        "--hidden-import=tqdm",
        "--hidden-import=numpy",
        "--hidden-import=huggingface_hub",
        
        "run_app.py"
    ]
    
    try:
        # Add icon if it exists
        if os.path.exists('app_icon.ico'):
            cmd.insert(-1, "--icon=app_icon.ico")
            print("🎨 Using custom icon")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build successful!")
        print("📁 Output folder: dist\\LocZ\\")
        print("🚀 Executable: dist\\LocZ\\LocZ.exe")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed!")
        print(f"Error: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("❌ PyInstaller not found!")
        print("Install it with: pip install pyinstaller")
        return False

if __name__ == "__main__":
    success = create_folder_executable()
    if success:
        print("\n🎉 Build successful! Now run create_launcher.py")
    else:
        print("\n❌ Build failed. Check errors above.")
    input("Press Enter to continue...")
