import argparse
import subprocess
import sys
import os
import time
import shutil

def run_command(command, cwd=None, shell=True):
    print(f"Running: {command}")
    subprocess.run(command, cwd=cwd, shell=shell, check=True)

def start():
    print("Starting services...")
    run_command("docker compose up -d --build")
    print("\nServices started!")
    print("Frontend: http://localhost:5173")
    print("Backend:  http://localhost:8000")

def stop():
    print("Stopping services...")
    run_command("docker compose down")
    print("Services stopped.")

def load_data():
    print("Loading data...")
    try:
        # Check if services are running
        subprocess.run("docker compose ps", shell=True, check=True, stdout=subprocess.DEVNULL)
        
        # Run data loader inside the api container
        # -T disables pseudo-tty allocation
        run_command("docker compose exec -T api python -c \"from app.data_loader import load_data; print(load_data('/app/data/data.xlsx'))\"")
        print("\nData loading complete!")
    except subprocess.CalledProcessError:
        print("\n[ERROR] Could not load data.")
        print("Make sure the services are running first. Run: python manage.py start")

def share():
    print("Sharing application via ngrok...")
    
    # Check if ngrok is installed
    if not shutil.which("ngrok"):
        print("[ERROR] ngrok not found in PATH.")
        print("Please install ngrok or add it to your PATH.")
        # Try to find ngrok in current directory or parent directories as fallback?
        # For now, just fail.
        return

    print("Starting ngrok tunnel to port 5173 (Frontend)...")
    print("The frontend is configured to proxy /api requests to the backend, so only one tunnel is needed.")
    
    try:
        # Start ngrok
        # We use 'start' to open a new window for ngrok if on Windows, 
        # but we want to capture the URL. 
        # Actually, let's just run it and let the user see the output.
        if sys.platform == "win32":
            subprocess.run("start cmd /k ngrok http 5173", shell=True)
            print("\nNgrok started in a new window.")
            print("Copy the forwarding URL (https://....ngrok-free.app) and open it in your browser.")
        else:
            print("Run 'ngrok http 5173' in a separate terminal.")
            
    except Exception as e:
        print(f"Error starting ngrok: {e}")

def main():
    parser = argparse.ArgumentParser(description="EMI Project Management Script")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("start", help="Start the application (Docker)")
    subparsers.add_parser("stop", help="Stop the application")
    subparsers.add_parser("load-data", help="Load data from Excel into Database")
    subparsers.add_parser("share", help="Share the application via ngrok")

    args = parser.parse_args()

    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "load-data":
        load_data()
    elif args.command == "share":
        share()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
