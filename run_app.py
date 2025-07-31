import threading
import time
import webbrowser
from app import app

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')
    print("\n🌐 LocZ - ALT File Editor is now running!")
    print("📍 URL: http://localhost:5000")
    print("❌ To stop the application, close this window")

def main():
    print("🚀 Starting LocZ - ALT File Editor...")
    print("📦 Setting up the application...")
    
    # Start browser opening in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n👋 ALT File Editor stopped.")
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
