def create_launcher_batch():
    """Create a simple .bat file for easy launching"""
    
    bat_content = '''@echo off
title LocZ - ALT File Editor - Italian Localization Tool
echo.
echo ===============================================
echo    LocZ - ALT File Editor - Starting...
echo ===============================================
echo.
echo 🚀 Loading application...
echo 📂 Keep this window open while working
echo 🌐 Browser will open automatically
echo.
LocZ.exe
echo.
echo 👋 LocZ - ALT File Editor has stopped.
pause
'''
    
    with open('dist/LocZ/Start_LocZ.bat', 'w') as f:
        f.write(bat_content)
    
    print("✅ Created Start_LocZ.bat launcher")

if __name__ == "__main__":
    create_launcher_batch()
