"""
Launcher script to run both the FulfillTwin AI backend API and Streamlit frontend concurrently.
"""
import os
import sys
import subprocess
import atexit
import time
import webbrowser
import threading

def open_browser(port):
    # Wait a few seconds for Streamlit to fully initialize
    time.sleep(3)
    url = f"http://localhost:{port}"
    print(f"Opening browser at {url}...")
    webbrowser.open(url)

def main():
    # Set default environment variables
    api_port = os.environ.get("API_PORT", "5000")
    os.environ["FULFILLTWIN_API_URL"] = os.environ.get("FULFILLTWIN_API_URL", f"http://127.0.0.1:{api_port}")
    
    print(f"Starting FulfillTwin AI backend API on port {api_port}...")
    
    # Start the backend API process
    api_process = subprocess.Popen([sys.executable, "run_api.py"])
    
    # Ensure the API process is terminated when this script exits
    def cleanup():
        print("Shutting down backend API...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
    
    atexit.register(cleanup)
    
    # Give the API a moment to initialize
    time.sleep(2)
    
    print("Starting Streamlit frontend...")
    port = os.environ.get("PORT", "8502")
    
    # Automatically open the browser in a background thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    try:
        # Start the Streamlit app
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.address", "0.0.0.0",
            "--server.port", port
        ])
    except KeyboardInterrupt:
        print("Received exit signal, shutting down...")

if __name__ == "__main__":
    main()
