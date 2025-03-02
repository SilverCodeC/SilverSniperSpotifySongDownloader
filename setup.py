import os
import sys
import subprocess

# Define the target folder for local installations
LIBS_DIR = os.path.join(os.getcwd(), "libs")
if not os.path.exists(LIBS_DIR):
    os.makedirs(LIBS_DIR)

# List of required packages
required_packages = [
    "spotipy",
    "yt-dlp",
    "youtube-search-python",
    "mutagen",
    "flask",
    "requests"
]

def install_packages(packages):
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"{pkg} is already installed.")
        except ImportError:
            print(f"Installing {pkg} into {LIBS_DIR} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--target=" + LIBS_DIR, pkg])

install_packages(required_packages)
print("All dependencies installed/updated in the 'libs' folder.")
print("Launching main application...")
subprocess.check_call([sys.executable, "main.py"])
