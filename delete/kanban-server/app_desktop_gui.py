# app_desktop_gui.py
"""
A graphical user interface for monitoring a Flask-based server and displaying its API documentation.

This module provides:
- Real-time log viewer (from app.log)
- Interactive API reference (from routes.yaml)
- Periodic server health check (every 60 seconds)
- Example display on endpoint selection
"""

import tkinter as tk
from tkinter import ttk, Text, Scrollbar
import yaml
import os
import time
import threading
import requests
from threading import Thread

# Global configuration
LOG_FILE = "app.log"
CONFIG_FILE = "routes.yaml"
SERVER_URL = "http://localhost:5000/api/tasks"  # Health check endpoint
CHECK_INTERVAL = 60  # seconds


class ServerMonitorGUI:
    """
    Main GUI class for server monitoring and API documentation.
    """

    def __init__(self, root):
        """
        Initialize the GUI.

        :param root: Root Tk window.
        :type root: tkinter.Tk
        """
        self.root = root
        self.root.title("Server Monitor & API Documentation — Checking server status...")
        self.root.geometry("1000x750")

        # Server status tracking
        self.server_online = False
        self.status_label = None

        # Create main layout
        main_frame = ttk.PanedWindow(root, orient=tk.VERTICAL)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # === Status Bar ===
        status_frame = ttk.Frame(main_frame)
        self.status_label = ttk.Label(status_frame, text="Server status: Unknown", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT)
        main_frame.add(status_frame, weight=0)

        # === Endpoints Frame ===
        endpoints_frame = ttk.LabelFrame(main_frame, text="API Endpoints")
        main_frame.add(endpoints_frame, weight=1)

        columns = ("method", "path", "action", "description")
        self.tree = ttk.Treeview(endpoints_frame, columns=columns, show="headings", height=8)
        self.tree.heading("method", text="Method")
        self.tree.heading("path", text="Path")
        self.tree.heading("action", text="Action")
        self.tree.heading("description", text="Description")
        self.tree.column("method", width=80)
        self.tree.column("path", width=250)
        self.tree.column("action", width=100)
        self.tree.column("description", width=400)

        vsb = Scrollbar(endpoints_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        endpoints_frame.grid_rowconfigure(0, weight=1)
        endpoints_frame.grid_columnconfigure(0, weight=1)

        # === Example Frame ===
        example_frame = ttk.LabelFrame(main_frame, text="Example Usage (click an endpoint)")
        main_frame.add(example_frame, weight=0)

        self.example_text = Text(example_frame, height=4, wrap=tk.WORD, font=("Courier", 10))
        self.example_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.example_text.config(state=tk.DISABLED)

        # Bind selection (only on user click)
        self.tree.bind("<<TreeviewSelect>>", self.on_endpoint_select)

        # === Logs Frame ===
        logs_frame = ttk.LabelFrame(main_frame, text="Server Logs (Live)")
        main_frame.add(logs_frame, weight=2)

        self.log_text = Text(logs_frame, wrap=tk.NONE, font=("Courier", 9))
        log_vsb = Scrollbar(logs_frame, orient="vertical", command=self.log_text.yview)
        log_hsb = Scrollbar(logs_frame, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=log_vsb.set, xscrollcommand=log_hsb.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_vsb.grid(row=0, column=1, sticky="ns")
        log_hsb.grid(row=1, column=0, sticky="ew")
        logs_frame.grid_rowconfigure(0, weight=1)
        logs_frame.grid_columnconfigure(0, weight=1)

        # Load data
        self.load_endpoints()

        # Start background tasks
        self.start_log_monitoring()
        self.start_server_status_checker()

    def load_endpoints(self):
        """Load API routes from YAML into the tree."""
        if not os.path.exists(CONFIG_FILE):
            self.log_error(f"Config file not found: {CONFIG_FILE}")
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.log_error(f"Failed to parse {CONFIG_FILE}: {e}")
            return

        # Clear any existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        for route in config.get('routes', []):
            self.tree.insert(
                "",
                "end",
                values=(
                    route['method'],
                    route['path'],
                    route['action'],
                    route.get('description', '')
                ),
                tags=(route.get('example', ''),)
            )

    def on_endpoint_select(self, event):
        """
        Show example only when user explicitly selects a row.
        Avoids auto-trigger on load.
        """
        selection = self.tree.selection()
        if not selection:
            return

        # Get the example from tags
        item_id = selection[0]
        tags = self.tree.item(item_id, "tags")
        example = tags[0] if tags else ""

        # Update example text box
        self.example_text.config(state=tk.NORMAL)
        self.example_text.delete(1.0, tk.END)
        if example:
            self.example_text.insert(tk.END, example)
        else:
            self.example_text.insert(tk.END, "[No example available]")
        self.example_text.config(state=tk.DISABLED)

    def log_error(self, message):
        """Log error to GUI log area."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[GUI ERROR] {message}\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def read_log_file(self):
        """Read current log file content."""
        if not os.path.exists(LOG_FILE):
            return "[Log file not created yet]"
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"[Failed to read log: {e}]"

    def update_logs(self):
        """Refresh log display."""
        content = self.read_log_file()
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, content)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def start_log_monitoring(self):
        """Monitor log file for changes in background."""
        def monitor():
            last_size = 0
            while True:
                try:
                    if os.path.exists(LOG_FILE):
                        curr_size = os.path.getsize(LOG_FILE)
                        if curr_size != last_size:
                            self.root.after(0, self.update_logs)
                            last_size = curr_size
                    time.sleep(2)
                except Exception:
                    break
        Thread(target=monitor, daemon=True).start()

    def check_server_status(self):
        """
        Perform a lightweight health check by requesting /api/tasks.
        Runs in background thread.
        """
        try:
            # Timeout after 3 seconds
            response = requests.get(SERVER_URL, timeout=3)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def update_server_status_ui(self, is_online):
        """
        Update UI to reflect server status.

        :param is_online: Whether server is reachable.
        :type is_online: bool
        """
        status_text = "Server: Online" if is_online else "Server: Offline"
        color = "green" if is_online else "red"
        self.status_label.config(text=status_text, foreground=color)
        self.root.title(f"Server Monitor & API Documentation — {status_text}")

    def start_server_status_checker(self):
        """
        Start periodic server health check (every CHECK_INTERVAL seconds).
        """
        def checker():
            while True:
                is_online = self.check_server_status()
                # Schedule UI update on main thread
                self.root.after(0, self.update_server_status_ui, is_online)
                time.sleep(CHECK_INTERVAL)
        Thread(target=checker, daemon=True).start()


if __name__ == "__main__":
    # Ensure requests is available
    try:
        import requests
    except ImportError:
        print("Error: 'requests' package is required for server health checks.")
        print("Run: pip install requests")
        exit(1)

    root = tk.Tk()
    app = ServerMonitorGUI(root)
    root.mainloop()