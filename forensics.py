import os
import json
import pytsk3
import ctypes  #It provides C compatible data types, and allows calling functions in DLLs or shared libraries.
import winreg   #Allows access to the Windows registry
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import time 

# Function to combine split image files
def combine_split_images(image_dir, output_file):
    try:
        files = os.listdir(image_dir)
        split_files = [file for file in files if file.endswith(".001")]
        split_files.sort()

        with open(output_file, 'wb') as output:
            for split_file in split_files:
                with open(os.path.join(image_dir, split_file), 'rb') as input:
                    output.write(input.read())

        return os.path.getsize(output_file), None
    except Exception as e:
        return None, f"An error occurred while combining split image files: {e}"

# Function to analyze the combined image file
def analyze_image(image_path):
    try:
        file_name = os.path.basename(image_path)
        file_size = os.path.getsize(image_path)
        
        access_time = time.ctime(os.path.getatime(image_path))
        modified_time = time.ctime(os.path.getmtime(image_path))

        with open(image_path, 'rb') as f:
            image_content = f.read(100).hex()
        
        return {
            "file_name": file_name,
            "file_size": file_size,
            "access_time": access_time,
            "modified_time": modified_time,
            "image_content": image_content
        }, None
    except Exception as e:
        return None, f"An error occurred while analyzing the image: {e}"

# Function to save information to a JSON file
def save_to_json(data, output_path):
    try:
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=4)
        return None
    except Exception as e:
        return f"An error occurred while saving to JSON: {e}"

# Function to handle FTK Image Analysis
def handle_ftk_image_analysis(text_widget):
    image_dir = filedialog.askdirectory(title="Select Directory Containing Split Image Files")
    if not image_dir:
        return

    output_file = filedialog.asksaveasfilename(defaultextension=".img", title="Save Combined Image As")
    if not output_file:
        return

    combined_size, error = combine_split_images(image_dir, output_file)
    if error:
        messagebox.showerror("Error", error)
        return

    if combined_size is not None:
        image_info, error = analyze_image(output_file)
        if error:
            messagebox.showerror("Error", error)
            return

        json_output_path = filedialog.asksaveasfilename(defaultextension=".json", title="Save Image Info As JSON")
        if json_output_path:
            error = save_to_json(image_info, json_output_path)
            if error:
                messagebox.showerror("Error", error)
                return
            messagebox.showinfo("Success", f"Image combined and analyzed. Info saved to {json_output_path}")

        # Display the information on the GUI
        text_widget.insert(tk.END, f"Information for combined image:\n")
        text_widget.insert(tk.END, json.dumps(image_info, indent=4) + "\n\n")

        # Display the contents of the JSON file on the GUI
        with open(json_output_path, 'r') as f:
            json_content = json.load(f)
            text_widget.insert(tk.END, "Contents of image_info.json:\n")
            text_widget.insert(tk.END, json.dumps(json_content, indent=4) + "\n\n")

# Function to count items in a directory
def count_items(path):
    directories = 0
    files = 0
    folders = 0
    file_types = {}

    try:
        for root, _, files_list in os.walk(path):
            folders += 1
            for file in files_list:
                files += 1
                file_ext = os.path.splitext(file)[1].lower()
                file_types[file_ext] = file_types.get(file_ext, 0) + 1
    except Exception as e:
        print(f"An error occurred while processing the path {path}: {e}")

    directories = folders - 1  # Subtract 1 for the root folder itself
    return directories, files, folders, file_types

# Function to get the file system of a drive
def get_drive_file_system(drive_path):
    try:
        fs_info = ctypes.create_unicode_buffer(255)
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive_path),
            fs_info,
            len(fs_info)
        )
        return fs_info.value.strip()
    except Exception as e:
        print(f"An error occurred while getting file system information for {drive_path}: {e}")
        return "Unknown"

# Function to get disk space information
def get_disk_space_info(drive_path):
    free_bytes = ctypes.c_ulonglong(0)
    total_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(drive_path),
        None,
        ctypes.pointer(total_bytes),
        ctypes.pointer(free_bytes)
    )
    total_gb = total_bytes.value / (1024**3)
    free_gb = free_bytes.value / (1024**3)
    return total_gb, free_gb

# Function to list logical drives
def list_logical_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in range(26):
        if bitmask & (1 << letter):
            drives.append(chr(65 + letter) + ':\\')
    return drives

# Function to analyze a drive
def analyze_drive(drive_path, text_widget):
    if os.path.exists(drive_path):
        file_system = get_drive_file_system(drive_path)
        info = count_items(drive_path)
        total_gb, free_gb = get_disk_space_info(drive_path)
        drive_info = {
            "file_system": file_system,
            "total_space_gb": round(total_gb, 2),
            "free_space_gb": round(free_gb, 2),
            "directories": info[0],
            "files": info[1],
            "folders": info[2],
            "file_types": info[3]
        }

        text_widget.insert(tk.END, f"Information for {drive_path}:\n")
        text_widget.insert(tk.END, json.dumps(drive_info, indent=4) + "\n\n")
    else:
        text_widget.insert(tk.END, f"Drive path does not exist: {drive_path}\n")

# Function to check and analyze a drive
def check_and_analyze_drive(drive_path, text_widget):
    logical_drives = list_logical_drives()
    if drive_path in logical_drives:
        text_widget.insert(tk.END, f"{drive_path} is a logical drive.\n")
    else:
        text_widget.insert(tk.END, f"{drive_path} is a physical drive.\n")
    analyze_drive(drive_path, text_widget)

# Function to analyze all drives
def analyze_all_drives(text_widget):
    drives = list_logical_drives()
    for drive in drives:
        check_and_analyze_drive(drive, text_widget)

def read_registry_value(key, subkey, value_name):
    try:
        registry_key = winreg.OpenKey(key, subkey)
        value, _ = winreg.QueryValueEx(registry_key, value_name)
        winreg.CloseKey(registry_key)
        return value
    except FileNotFoundError:
        return None

def get_system_information():
    system_information = {}

    # Read operating system version
    system_information["OSVersion"] = read_registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        "ProductName"
    )

    # Read computer name
    system_information["ComputerName"] = read_registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName",
        "ComputerName"
    )

    # Read hardware information
    system_information["Processor"] = read_registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        "ProcessorNameString"
    )
    system_information["Memory"] = read_registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"HARDWARE\RESOURCEMAP\System Resources\Physical Memory",
        "MemoryReserved"
    )
    system_information["GraphicsCard"] = read_registry_value(
        winreg.HKEY_LOCAL_MACHINE,
        r"HARDWARE\DEVICEMAP\VIDEO",
        "\\Device\\Video0"
    )

    return system_information

def read_registry_subkey(key, subkey):
    try:
        registry_key = winreg.OpenKey(key, subkey)
        subkey_info = {}
        index = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(registry_key, index)
                subkey_info[subkey_name] = read_registry_subkey_values(registry_key, subkey_name)
                index += 1
            except OSError:
                break
        winreg.CloseKey(registry_key)
        return subkey_info
    except FileNotFoundError:
        return None

def read_registry_subkey_values(key, subkey):
    subkey_values = {}
    try:
        registry_key = winreg.OpenKey(key, subkey)
        index = 0
        while True:
            try:
                value_name, value_data, value_type = winreg.EnumValue(registry_key, index)
                subkey_values[value_name] = value_data
                index += 1
            except OSError:
                break
        winreg.CloseKey(registry_key)
    except FileNotFoundError:
        pass
    return subkey_values

def get_installed_software():
    installed_software = {}

    # Read installed software information from HKEY_LOCAL_MACHINE
    lm_subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    installed_software["LocalMachine"] = read_registry_subkey(winreg.HKEY_LOCAL_MACHINE, lm_subkey)

    # Read installed software information from HKEY_CURRENT_USER
    cu_subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    installed_software["CurrentUser"] = read_registry_subkey(winreg.HKEY_CURRENT_USER, cu_subkey)

    return installed_software

def retrieve_registry_info():
    result = []

    # Retrieve user interface settings
    key = winreg.HKEY_CURRENT_USER
    subkey = r"Control Panel\Desktop"
    wallpaper = read_registry_value(key, subkey, "Wallpaper")
    screensaver = read_registry_value(key, subkey, "SCRNSAVE.EXE")
    screensaver_timeout = read_registry_value(key, subkey, "ScreenSaveTimeOut")

    result.append("User Interface Settings:")
    result.append(f"Wallpaper: {wallpaper}")
    result.append(f"Screen Saver: {screensaver}")
    result.append(f"Screen Saver Timeout (seconds): {screensaver_timeout}\n")

    # Retrieve system information
    system_info = get_system_information()
    if system_info:
        result.append("System Information:")
        for key, value in system_info.items():
            result.append(f"{key}: {value}")
    else:
        result.append("Failed to retrieve system information.")

    # Retrieve installed software information
    software_info = get_installed_software()
    if software_info:
        result.append("\nInstalled Software Information:")
        for location, software_list in software_info.items():
            result.append(f"\nLocation: {location}")
            for software_name, software_details in software_list.items():
                result.append(f"\nSoftware Name: {software_name}")
                for key, value in software_details.items():
                    result.append(f"{key}: {value}")
    else:
        result.append("Failed to retrieve installed software information.")

    return "\n".join(result)

def create_gui():
    def show_drive_buttons():
        analyze_c_button.pack(pady=5)
        analyze_d_button.pack(pady=5)
        analyze_all_button.pack_forget()

    def display_registry_info():
        info = retrieve_registry_info()
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, info)

    window = tk.Tk()
    window.title("Analysis Tool")
    window.configure(bg="black")

    analyze_all_button = tk.Button(window, text="Hard Disk Analysis", command=show_drive_buttons, bg="black", fg="white")
    analyze_all_button.pack(pady=5)

    analyze_c_button = tk.Button(window, text="Analyze C Drive", command=lambda: check_and_analyze_drive("C:\\", result_text), bg="black", fg="white")
    analyze_c_button.pack_forget()

    analyze_d_button = tk.Button(window, text="Analyze D Drive", command=lambda: check_and_analyze_drive("D:\\", result_text), bg="black", fg="white")
    analyze_d_button.pack_forget()

    ftk_image_analysis_button = tk.Button(window, text="FTK Image Analysis", command=lambda: handle_ftk_image_analysis(result_text), bg="black", fg="white")
    ftk_image_analysis_button.pack(pady=5)

    registry_info_button = tk.Button(window, text="Registry Info", command=display_registry_info, bg="black", fg="white")
    registry_info_button.pack(pady=5)

    result_text = scrolledtext.ScrolledText(window, width=80, height=20, bg="black", fg="white")
    result_text.pack(pady=10)

    window.mainloop()
if __name__ == "__main__":
    create_gui()