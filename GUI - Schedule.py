import tkinter as tk
from tkinter import filedialog, messagebox
import schedule
import time
import threading
import subprocess
import sqlite3
import os
from datetime import datetime
from tkinter import ttk
from datetime import datetime

# Database setup
DB_FILE = "tasks.db"
LOG_FOLDER = "logs"

# Ensure log folder exists
os.makedirs(LOG_FOLDER, exist_ok=True)

def init_db():
    """Initialize the SQLite database and create the table if not exists."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        time TEXT,
                        script TEXT)''')
    conn.commit()
    conn.close()

def load_tasks():
    """Load scheduled tasks from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT time, script FROM tasks")
    rows = cursor.fetchall()
    conn.close()

    for time_, script in rows:
        job = schedule.every().day.at(time_).do(run_script, script)
        scheduled_tasks.append((time_, script, job))
        task_list.insert(tk.END, f"{time_} - {script}")

def save_task_to_db(time_, script):
    """Save a task to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (time, script) VALUES (?, ?)", (time_, script))
    conn.commit()
    conn.close()

def remove_task_from_db(time_, script):
    """Remove a task from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE time = ? AND script = ?", (time_, script))
    conn.commit()
    conn.close()

def select_script():
    """Open file dialog to select a Python script."""
    script_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
    if script_path:
        script_entry.delete(0, tk.END)
        script_entry.insert(0, script_path)

def add_task():
    """Add a new scheduled task."""
    script_path = script_entry.get()
    scheduled_time = time_entry.get()

    if not script_path or not scheduled_time:
        messagebox.showwarning("Warning", "Please select a script and enter a time!")
        return

    # Add to schedule
    job = schedule.every().day.at(scheduled_time).do(run_script, script_path)
    
    # Store the task
    scheduled_tasks.append((scheduled_time, script_path, job))
    
    # Save task in database
    save_task_to_db(scheduled_time, script_path)
    
    # Update UI list
    task_list.insert(tk.END, f"{scheduled_time} - {script_path}")
    
    messagebox.showinfo("Success", f"Scheduled {script_path} at {scheduled_time}!")

def run_script(script_path):
    """Run the selected script in the background and log output with timestamps."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_FOLDER, f"log_{timestamp}.txt")

    with open(log_file, "w") as log:
        log.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting script: {script_path}\n")
        
        process = subprocess.Popen(
            ["python", script_path], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True
        )

        # Read and log output in real-time
        for line in iter(process.stdout.readline, ''):
            timestamped_line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}"
            log.write(timestamped_line)
            log.flush()  # Ensures immediate writing to file
        
        for line in iter(process.stderr.readline, ''):
            timestamped_line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {line}"
            log.write(timestamped_line)
            log.flush()

    messagebox.showinfo("Success", f"Executed {script_path} in background!\nLog: {log_file}")


def run_selected_task():
    """Execute the selected task immediately in the background."""
    try:
        selected_index = task_list.curselection()[0]
        _, script_path, _ = scheduled_tasks[selected_index]
        run_script(script_path)
    except IndexError:
        messagebox.showwarning("Warning", "Please select a task to run now!")

def start_scheduler():
    """Start the scheduler in a separate thread."""
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)

    threading.Thread(target=run_schedule, daemon=True).start()
    messagebox.showinfo("Scheduler Started", "Scheduler is now running in the background!")

def remove_task():
    """Remove a selected task from the list, scheduler, and database."""
    try:
        selected_index = task_list.curselection()[0]
        time_, script_path, job = scheduled_tasks[selected_index]
        
        # Cancel scheduled job
        schedule.cancel_job(job)

        # Remove from database
        remove_task_from_db(time_, script_path)

        # Remove from list and UI
        scheduled_tasks.pop(selected_index)
        task_list.delete(selected_index)

        messagebox.showinfo("Success", "Task removed successfully!")
    except IndexError:
        messagebox.showwarning("Warning", "Please select a task to remove!")

def edit_task():
    """Edit a selected task's time or script path."""
    try:
        selected_index = task_list.curselection()[0]
        old_time, old_script, job = scheduled_tasks[selected_index]

        # Cancel old job
        schedule.cancel_job(job)

        # Remove old task from database
        remove_task_from_db(old_time, old_script)

        # Get new values
        new_script = script_entry.get() or old_script
        new_time = time_entry.get() or old_time

        # Add new scheduled job
        new_job = schedule.every().day.at(new_time).do(run_script, new_script)

        # Update database
        save_task_to_db(new_time, new_script)

        # Update list
        scheduled_tasks[selected_index] = (new_time, new_script, new_job)
        task_list.delete(selected_index)
        task_list.insert(selected_index, f"{new_time} - {new_script}")

        messagebox.showinfo("Success", "Task updated successfully!")
    except IndexError:
        messagebox.showwarning("Warning", "Please select a task to edit!")

# GUI Setup
root = tk.Tk()
root.title("Python Script Scheduler")
root.geometry("500x500")

# Initialize database
init_db()

# Script Selection
tk.Label(root, text="Select Script:").pack(pady=5)
script_entry = tk.Entry(root, width=50)
script_entry.pack()
tk.Button(root, text="Browse", command=select_script).pack()

# Time Selection
tk.Label(root, text="Enter Time (HH:MM, 24-hour format):").pack(pady=5)
time_entry = tk.Entry(root, width=20)
time_entry.pack()

# Buttons
tk.Button(root, text="Add Task", command=add_task).pack(pady=5)
tk.Button(root, text="Edit Task", command=edit_task).pack(pady=5)
tk.Button(root, text="Remove Task", command=remove_task).pack(pady=5)
tk.Button(root, text="Run Now", command=run_selected_task, bg="blue", fg="white").pack(pady=5)

# Task List
tk.Label(root, text="Scheduled Tasks:").pack()
task_list = tk.Listbox(root, width=70, height=10)
task_list.pack()

# Start Scheduler Button
tk.Button(root, text="Start Scheduler", command=start_scheduler, bg="green", fg="white").pack(pady=10)

# Load tasks from database
scheduled_tasks = []
load_tasks()

# Run GUI
root.mainloop()
