import sys
import os
import webbrowser
import threading
import time
from app_lightweight import app

def open_browser():
    time.sleep(2)  # Wait for Flask to start
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("=" * 50)
    print("    ALT File Editor - Starting...")
    print("=" * 50)
    print("The webpage will open automatically.")
    print("To stop: Close this window or press Ctrl+C")
    print("=" * 50)
    
    # Start browser in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nApplication stopped.")
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to close...")
