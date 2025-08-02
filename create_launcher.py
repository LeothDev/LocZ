import os
import shutil

def create_launcher_files():
    """Create launcher files for easy use"""
    
    dist_folder = "dist\\LocZ"
    
    if not os.path.exists(dist_folder):
        print("Build folder not found! Run build_minimal.py first.")
        return False
    
    # 1. Create user-friendly batch launcher
    bat_content = '''@echo off
title LocZ - ALT File Editor - Italian Localization Tool
color 0A
echo.
echo ===============================================
echo    LocZ - ALT File Editor - Italian Localization
echo ===============================================
echo.
echo Starting application...
echo Keep this window open while working
echo Browser will open automatically in a few seconds
echo.
echo  IMPORTANT: Do NOT close this window!
echo    Closing this window will stop the application.
echo.
echo ===============================================
echo.

LocZ.exe

echo.
echo ===============================================
echo LocZ - ALT File Editor has stopped.
echo    You can now safely close this window.
echo ===============================================
pause
'''
    
    # 2. Create README for Teresa
    readme_content = '''# LocZ - Quick Start Guide

## How to Use:
1. Double-click "Start_LocZ.bat"
2. Wait for browser to open (may take 10-20 seconds)
3. Upload your Excel ALT file
4. Start editing Italian translations
5. Use "Export Modified" to download your changes

## Important Notes:
- Keep the black console window open while working
- Your work is automatically saved as you type
- The similarity search becomes available after processing
- Dark mode button is in the top-right corner

## Troubleshooting:
- If browser doesn't open: Go to http://localhost:5000
- If app won't start: Check if port 5000 is free
- For any issues: Check the console window for error messages

## Files in this folder:
- Start_LocZ.bat  ← CLICK THIS TO START
- LocZ.exe      ← Main application
- _internal/               ← Application files (don't touch)
- translations.db          ← Your work database (created automatically)

Built for Teresa - Italian Localization Specialist
'''
    
    # Write files
    try:
        # Batch launcher
        with open(os.path.join(dist_folder, "Start_LocZ.bat"), 'w', encoding='utf-8') as f:
            f.write(bat_content)
        print("Created launcher: Start_LocZ.bat")
        
        # README
        with open(os.path.join(dist_folder, "README.txt"), 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("Created README.txt")
        
        # Create desktop shortcut batch
        shortcut_content = f'''@echo off
cd /d "{os.path.abspath(dist_folder)}"
start "LocZ - ALT File Editor" "Start ALT Editor.bat"
'''
        
        with open("LocZ_Shortcut.bat", 'w') as f:
            f.write(shortcut_content)
        print("Created desktop shortcut:LocZ_Shortcut.bat")
        
        print(f"\nPackage ready in: {dist_folder}")
        print("\nTo distribute:")
        print(f"   1. Zip the entire '{dist_folder}' folder")
        print("   2. Send to Teresa")
        print("   3. She extracts and double-clicks 'Start_LocZ.bat'")
        
        return True
        
    except Exception as e:
        print(f"Error creating launcher files: {e}")
        return False

if __name__ == "__main__":
    success = create_launcher_files()
    if not success:
        print("Failed to create launcher files")
    input("Press Enter to exit...")
