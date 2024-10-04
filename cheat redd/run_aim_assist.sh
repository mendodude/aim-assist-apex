#!/bin/bash

# Change to the directory containing the script
cd "$(dirname "$0")"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if required Python packages are installed
required_packages=("opencv-python" "numpy" "pynput" "pyautogui")
for package in "${required_packages[@]}"
do
    if ! python3 -c "import $package" &> /dev/null
    then
        echo "Installing required package: $package"
        pip3 install $package
    fi
done

# Check if screen recording permission is granted
if ! osascript -e 'tell application "System Events" to get processes whose name contains "Terminal"' &> /dev/null; then
    echo "Screen recording permission is required to run this script."
    echo "Please grant screen recording permission to Terminal in System Preferences > Security & Privacy > Privacy > Screen Recording"
    echo "After granting permission, please restart the Terminal and run this script again."
    exit 1
fi

# Run the Python script
python3 aim_assist.py

# If the script exits, wait for user input before closing the terminal
read -p "Press Enter to exit..."