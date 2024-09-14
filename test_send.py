import os
import ctypes
import subprocess
import sys

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def share_folder_on_windows(folder_path, share_name):
    # Ensure the folder exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # Command to share the folder with full access for everyone
    share_command = f'net share {share_name}="{folder_path}" /grant:everyone,full'
    
    try:
        # Execute the command to share the folder
        subprocess.run(share_command, shell=True, check=True)
        print(f"Folder '{folder_path}' shared as '{share_name}' successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to share the folder: {e}")

if __name__ == "__main__":
    folder_to_share = "C:\datasets"
    share_name = "datasets"
    
    if is_admin():
        share_folder_on_windows(folder_to_share, share_name)
    else:
        print("Script is not running with administrative privileges. Attempting to elevate...")
        # Re-run the script with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
