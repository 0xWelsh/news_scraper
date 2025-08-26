import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, Menu
import threading
import webbrowser
import sqlite3
import hashlib
import math
import os
import random
import re
import textwrap
import time
import subprocess
import base64
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin
import shutil

import feedparser
import frontmatter
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from markdownify import markdownify as md
from readability import Document

class ProfessionalContentAggregator:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Content Pro - Professional Content Aggregator")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        
        self.setup_styles()
        self.setup_menu()
        self.setup_gui()
        self.load_config()
        self.stop_event = threading.Event()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure('TNotebook', background='#f0f0f0')
        self.style.configure('TNotebook.Tab', padding=[20, 5], font=('Helvetica', 10, 'bold'))
        
    def setup_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Configuration", command=self.new_config)
        file_menu.add_command(label="Load Configuration", command=self.load_config_dialog)
        file_menu.add_command(label="Save Configuration", command=self.save_config_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(header_frame, text="AI Content Pro", font=('Helvetica', 14, 'bold')).pack(side=tk.LEFT)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.setup_config_tab()
        self.setup_control_tab()
        self.setup_results_tab()
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Professional Content Aggregator v2.0")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def setup_config_tab(self):
        config_frame = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(config_frame, text="Configuration")
        
        ttk.Label(config_frame, text="Content Niche:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.niche_var = tk.StringVar(value="AI + Cybersecurity news for beginners")
        ttk.Entry(config_frame, textvariable=self.niche_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(config_frame, text="Output Directory:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.out_dir_var = tk.StringVar(value="drafts")
        dir_frame = ttk.Frame(config_frame)
        dir_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Entry(dir_frame, textvariable=self.out_dir_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory, width=10).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Label(config_frame, text="Images Directory:", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.images_dir_var = tk.StringVar(value="images")
        images_dir_frame = ttk.Frame(config_frame)
        images_dir_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Entry(images_dir_frame, textvariable=self.images_dir_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(images_dir_frame, text="Browse", command=self.browse_images_directory, width=10).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Label(config_frame, text="RSS Sources:", font=('Helvetica', 10, 'bold')).grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.sources_text = scrolledtext.ScrolledText(config_frame, width=60, height=6, font=('Courier', 9))
        self.sources_text.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.sources_text.insert("1.0", "https://feeds.arstechnica.com/arstechnica/technology-lab\nhttps://www.wired.com/feed/category/security/latest/rss")
        
        ttk.Label(config_frame, text="Keywords Configuration:", font=('Helvetica', 10, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=(20, 5))
        
        ttk.Label(config_frame, text="Must-Have:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.must_have_var = tk.StringVar(value="AI,security,malware,ransomware")
        ttk.Entry(config_frame, textvariable=self.must_have_var, width=40).grid(row=5, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        ttk.Label(config_frame, text="Nice-to-Have:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.nice_have_var = tk.StringVar(value="beginner,how to,guide,tools")
        ttk.Entry(config_frame, textvariable=self.nice_have_var, width=40).grid(row=6, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        ttk.Label(config_frame, text="Avoid:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.avoid_var = tk.StringVar(value="giveaway,hiring,meme")
        ttk.Entry(config_frame, textvariable=self.avoid_var, width=40).grid(row=7, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        ttk.Label(config_frame, text="Max Articles:").grid(row=8, column=0, sticky=tk.W, pady=10)
        self.top_k_var = tk.StringVar(value="5")
        ttk.Spinbox(config_frame, from_=1, to=20, textvariable=self.top_k_var, width=10).grid(row=8, column=1, sticky=tk.W, padx=5, pady=10)
        
        ttk.Label(config_frame, text="Max Images per Article:").grid(row=9, column=0, sticky=tk.W, pady=10)
        self.max_images_var = tk.StringVar(value="3")
        ttk.Spinbox(config_frame, from_=0, to=10, textvariable=self.max_images_var, width=10).grid(row=9, column=1, sticky=tk.W, padx=5, pady=10)
        
        btn_frame = ttk.Frame(config_frame)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="Save Configuration", command=self.save_config_dialog, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Load Configuration", command=self.load_config_dialog, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset to Defaults", command=self.reset_config, width=15).pack(side=tk.LEFT, padx=5)
        
        config_frame.columnconfigure(1, weight=1)
        
    def setup_control_tab(self):
        control_frame = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(control_frame, text="Control")
        
        control_btn_frame = ttk.Frame(control_frame)
        control_btn_frame.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        self.start_btn = ttk.Button(control_btn_frame, text="▶ Start Aggregation", command=self.start_aggregation, width=20)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_btn_frame, text="⏹ Stop", command=self.stop_aggregation, state=tk.DISABLED, width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Progress:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.progress = ttk.Progressbar(control_frame, orient=tk.HORIZONTAL, length=500, mode='determinate')
        self.progress.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(control_frame, text="Activity Log:", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(20, 5))
        self.log_text = scrolledtext.ScrolledText(control_frame, width=80, height=15, font=('Courier', 9))
        self.log_text.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        control_frame.columnconfigure(1, weight=1)
        control_frame.rowconfigure(3, weight=1)
        
    def setup_results_tab(self):
        results_frame = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(results_frame, text="Results")
        
        ttk.Label(results_frame, text="Generated Drafts:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        list_frame = ttk.Frame(results_frame)
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.drafts_listbox = tk.Listbox(list_frame, width=80, height=15, font=('Helvetica', 10))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.drafts_listbox.yview)
        self.drafts_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.drafts_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = ttk.Frame(results_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=15)
        
        ttk.Button(btn_frame, text="Open Draft", command=self.open_draft, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Open Folder", command=self.open_folder, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Open With", command=self.open_with_menu, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.update_drafts_list, width=15).pack(side=tk.LEFT, padx=5)
        
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.out_dir_var.set(directory)
            
    def browse_images_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.images_dir_var.set(directory)
            
    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("1.0", f"[{timestamp}] {message}\n")
        self.log_text.config(state=tk.DISABLED)
        self.status_var.set(message)
        self.root.update_idletasks()
        
    def update_progress(self, value):
        self.progress['value'] = value
        self.root.update_idletasks()
        
    def update_drafts_list(self):
        drafts_dir = Path(self.out_dir_var.get())
        if drafts_dir.exists():
            draft_files = []
            for f in drafts_dir.glob('*.md'):
                draft_files.append((f.stat().st_mtime, f.name))
        
        
        draft_files.sort(reverse=True, key=lambda x: x[0])
        
        self.drafts_listbox.delete(0, tk.END)
        for mtime, filename in draft_files:
            self.drafts_listbox.insert(tk.END, filename)
                
    def get_config_from_gui(self):
        return {
            "NICHE": self.niche_var.get(),
            "SOURCES": [s.strip() for s in self.sources_text.get("1.0", tk.END).split('\n') if s.strip()],
            "KEYWORDS": {
                "must_have": [k.strip() for k in self.must_have_var.get().split(',') if k.strip()],
                "nice_to_have": [k.strip() for k in self.nice_have_var.get().split(',') if k.strip()],
                "avoid": [k.strip() for k in self.avoid_var.get().split(',') if k.strip()]
            },
            "REQUEST_SETTINGS": {
                "MAX_CONTENT_LENGTH": 200000,
                "MIN_CONTENT_LENGTH": 300,
                "TIMEOUT": 30,
                "THROTTLE_DELAY": 3.0,
                "RETRY_ATTEMPTS": 3,
            },
            "OUTPUT": {
                "TOP_K": int(self.top_k_var.get()),
                "OUT_DIR": self.out_dir_var.get(),
                "IMAGES_DIR": self.images_dir_var.get(),
                "MAX_IMAGES": int(self.max_images_var.get()),
                "DB_PATH": "state.db",
            },
        }
        
    def save_config_dialog(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            title="Save Configuration"
        )
        if filename:
            config = self.get_config_from_gui()
            with open(filename, 'w') as f:
                yaml.dump(config, f)
            self.log_message(f"Configuration saved to {filename}")
            
    def load_config_dialog(self):
        filename = filedialog.askopenfilename(
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            title="Load Configuration"
        )
        if filename:
            self.load_config(filename)
            
    def load_config(self, filename=None):
        if filename and os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    config = yaml.safe_load(f)
                
                self.niche_var.set(config.get('NICHE', ''))
                self.sources_text.delete("1.0", tk.END)
                self.sources_text.insert("1.0", '\n'.join(config.get('SOURCES', [])))
                self.must_have_var.set(','.join(config.get('KEYWORDS', {}).get('must_have', [])))
                self.nice_have_var.set(','.join(config.get('KEYWORDS', {}).get('nice_to_have', [])))
                self.avoid_var.set(','.join(config.get('KEYWORDS', {}).get('avoid', [])))
                self.out_dir_var.set(config.get('OUTPUT', {}).get('OUT_DIR', 'drafts'))
                self.images_dir_var.set(config.get('OUTPUT', {}).get('IMAGES_DIR', 'images'))
                self.top_k_var.set(str(config.get('OUTPUT', {}).get('TOP_K', 5)))
                self.max_images_var.set(str(config.get('OUTPUT', {}).get('MAX_IMAGES', 3)))
                
                self.log_message(f"Configuration loaded from {filename}")
            except Exception as e:
                self.log_message(f"Error loading config: {e}")
                
    def new_config(self):
        if messagebox.askyesno("New Configuration", "Create new configuration? Current settings will be lost."):
            self.reset_config()
            
    def reset_config(self):
        self.niche_var.set("AI + Cybersecurity news for beginners")
        self.out_dir_var.set("drafts")
        self.images_dir_var.set("images")
        self.sources_text.delete("1.0", tk.END)
        self.sources_text.insert("1.0", "https://feeds.arstechnica.com/arstechnica/technology-lab\nhttps://www.wired.com/feed/category/security/latest/rss")
        self.must_have_var.set("AI,security,malware,ransomware")
        self.nice_have_var.set("beginner,how to,guide,tools")
        self.avoid_var.set("giveaway,hiring,meme")
        self.top_k_var.set("5")
        self.max_images_var.set("3")
        self.log_message("Configuration reset to defaults")
        
    def show_about(self):
        about_text = """AI Content Pro - Professional Content Aggregator
Version 2.0

A powerful tool for aggregating and summarizing content
from multiple RSS feeds into publish-ready drafts.

© 2024 Your Company Name"""
        messagebox.showinfo("About AI Content Pro", about_text)
        
    def open_draft(self):
        selection = self.drafts_listbox.curselection()
        if selection:
            draft_name = self.drafts_listbox.get(selection[0])
            draft_path = Path(self.out_dir_var.get()) / draft_name
            try:
                os.system(f"xdg-open '{draft_path}'")
            except:
                try:
                    os.system(f"open '{draft_path}'")
                except:
                    os.startfile(str(draft_path))
                    
    def open_folder(self):
        drafts_dir = Path(self.out_dir_var.get())
        try:
            os.system(f"xdg-open '{drafts_dir}'")
        except:
            try:
                os.system(f"open '{drafts_dir}'")
            except:
                os.startfile(str(drafts_dir))

    def open_with_menu(self):
        selection = self.drafts_listbox.curselection()
        if not selection:
            return
            
        draft_name = self.drafts_listbox.get(selection[0])
        draft_path = Path(self.out_dir_var.get()) / draft_name
        
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="VS Code", command=lambda: self.open_with_app(draft_path, "code"))
        menu.add_command(label="Sublime Text", command=lambda: self.open_with_app(draft_path, "subl"))
        menu.add_command(label="Atom", command=lambda: self.open_with_app(draft_path, "atom"))
        menu.add_command(label="Vim", command=lambda: self.open_with_app(draft_path, "vim"))
        menu.add_command(label="Nano", command=lambda: self.open_with_app(draft_path, "nano"))
        menu.add_command(label="Custom Editor...", command=lambda: self.open_with_custom(draft_path))
        
        menu.post(self.root.winfo_pointerx(), self.root.winfo_pointery())
        
    def open_with_app(self, file_path, app_name):
        try:
            subprocess.Popen([app_name, str(file_path)])
            self.log_message(f"Opening with {app_name}")
        except FileNotFoundError:
            self.log_message(f"Error: {app_name} not found. Please install it or use a different editor.")
        except Exception as e:
            self.log_message(f"Error opening with {app_name}: {e}")
            
    def open_with_custom(self, file_path):
        app_name = filedialog.askopenfilename(
            title="Select Application to Open With",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if app_name:
            try:
                subprocess.Popen([app_name, str(file_path)])
                self.log_message(f"Opening with custom application: {app_name}")
            except Exception as e:
                self.log_message(f"Error opening with custom application: {e}")

    def start_aggregation(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.stop_event.clear()
        threading.Thread(target=self.run_aggregation, daemon=True).start()
        
    def stop_aggregation(self):
        self.stop_event.set()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log_message("Aggregation stopped by user")
        
    def run_aggregation(self):
        try:
            config = self.get_config_from_gui()
            aggregator = ContentAggregator(config)
            
            self.log_message(f"Starting aggregation for: {config['NICHE']}")
            
            candidates = aggregator.fetch_candidates()
            self.log_message(f"Found {len(candidates)} candidates")
            
            scored = []
            for candidate in candidates:
                if self.stop_event.is_set():
                    return
                    
                if aggregator.is_seen(candidate["link"]):
                    continue
                    
                try:
                    candidate["score"] = aggregator.rank_item(candidate["entry"])
                    if candidate["score"] > 0.5:
                        scored.append(candidate)
                except Exception:
                    continue
                    
            scored.sort(key=lambda x: x["score"], reverse=True)
            top_k = min(config["OUTPUT"]["TOP_K"], len(scored))
            
            for i, candidate in enumerate(scored[:top_k]):
                if self.stop_event.is_set():
                    return
                    
                self.log_message(f"Processing {i+1}/{top_k}: {candidate['title'][:50]}...")
                self.update_progress((i / top_k) * 100)
                
                try:
                    time.sleep(random.uniform(1.0, config["REQUEST_SETTINGS"]["THROTTLE_DELAY"]))
                    extracted = aggregator.extract_readable(candidate["link"])
                    
                    if not extracted["ok"]:
                        self.log_message(f"  ✗ {extracted['error']}")
                        continue
                        
                    draft = aggregator.make_draft(candidate, extracted)
                    draft_path = aggregator.save_draft(draft, candidate["title"])
                    
                    aggregator.mark_seen(candidate["link"], processed=True)
                    self.log_message(f"  ✓ Draft saved: {draft_path}")
                    
                except Exception as e:
                    self.log_message(f"  ! Error: {str(e)}")
                    continue
                    
            self.log_message("Processing completed successfully")
            self.update_progress(100)
            self.update_drafts_list()
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
        except Exception as e:
            self.log_message(f"Fatal error: {str(e)}")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

class ContentAggregator:
    def __init__(self, config):
        self.config = config
        self.db_conn = self.connect_db()
        self.ensure_dirs()
        self.session = requests.Session()
        self.user_agents = self.load_user_agents()
        self.cookies = {}

    def load_user_agents(self):
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
        ]

    def connect_db(self):
        db_path = self.config["OUTPUT"]["DB_PATH"]
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE,
                added_at TEXT,
                processed BOOLEAN DEFAULT 0
            )
        """)
        return conn

    def ensure_dirs(self):
        out_dir = self.config["OUTPUT"]["OUT_DIR"]
        images_dir = self.config["OUTPUT"]["IMAGES_DIR"]
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        Path(images_dir).mkdir(parents=True, exist_ok=True)

    def is_seen(self, url):
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        cur = self.db_conn.execute("SELECT 1 FROM seen WHERE id=?", (url_hash,))
        return cur.fetchone() is not None

    def mark_seen(self, url, processed=False):
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        self.db_conn.execute(
            "INSERT OR IGNORE INTO seen(id, url, added_at, processed) VALUES(?, ?, ?, ?)",
            (url_hash, url, datetime.now(timezone.utc).isoformat(), processed)
        )
        self.db_conn.commit()

    @staticmethod
    def domain_of(url):
        try:
            return urlparse(url).netloc.replace("www.", "")
        except ValueError:
            return ""

    def safe_get(self, url):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "User-Agent": random.choice(self.user_agents),
        }

        for attempt in range(self.config["REQUEST_SETTINGS"]["RETRY_ATTEMPTS"]):
            try:
                time.sleep(random.uniform(1.0, self.config["REQUEST_SETTINGS"]["THROTTLE_DELAY"]))
                resp = self.session.get(url, headers=headers, timeout=self.config["REQUEST_SETTINGS"]["TIMEOUT"])
                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                if attempt == self.config["REQUEST_SETTINGS"]["RETRY_ATTEMPTS"] - 1:
                    raise
                time.sleep(2 ** attempt)

    def extract_images(self, soup, base_url):
        images = []
        max_images = self.config["OUTPUT"]["MAX_IMAGES"]
        
        for img in soup.find_all('img'):
            if len(images) >= max_images:
                break
                
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
                
            alt = img.get('alt', '').strip()
            if not alt or len(alt) < 5:
                continue
                
            try:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(base_url, src)
                elif not src.startswith(('http://', 'https://')):
                    src = urljoin(base_url, src)
                    
                images.append({'url': src, 'alt': alt})
            except:
                continue
                
        return images

    def download_image(self, image_url, image_name):
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://www.google.com/"
            }
            
            response = self.session.get(image_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            images_dir = Path(self.config["OUTPUT"]["IMAGES_DIR"])
            image_path = images_dir / image_name
            
            with open(image_path, 'wb') as f:
                f.write(response.content)
                
            return image_path
        except Exception as e:
            return None

    def parse_date(self, entry):
        date_fields = ["published", "updated", "created", "pubDate"]
        for field in date_fields:
            if hasattr(entry, field):
                try:
                    return dateparser.parse(getattr(entry, field))
                except (ValueError, AttributeError):
                    continue
        return datetime.now(timezone.utc)

    def freshness_score(self, dt):
        if not dt:
            return 0.4
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return math.exp(-age_hours * math.log(2) / 168)

    def keyword_score(self, text):
        text_lower = text.lower()
        kw = self.config["KEYWORDS"]
        
        if not any(k.lower() in text_lower for k in kw["must_have"]):
            return 0.0
            
        score = 1.0
        score += 0.2 * sum(1 for k in kw["nice_to_have"] if k.lower() in text_lower)
        score -= 0.5 * sum(1 for k in kw["avoid"] if k.lower() in text_lower)
        return max(0.0, min(2.0, score))

    def rank_item(self, entry):
        title = entry.get("title", "")
        summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ")
        url = entry.get("link", "")
        host = self.domain_of(url)
        dt = self.parse_date(entry)

        text = f"{title}\n\n{summary}"
        ks = self.keyword_score(text)
        fs = self.freshness_score(dt)
        sw = self.config.get("SOURCE_WEIGHTS", {}).get(host, 1.0)

        return (0.6 * ks) + (0.3 * fs) + (0.1 * sw)

    def extract_readable(self, url):
        try:
            resp = self.safe_get(url)
            doc = Document(resp.text)
            title = doc.title() or ""
            soup = BeautifulSoup(doc.summary(), "html.parser")
            
            for tag in ["script", "style", "nav", "footer", "form", "iframe", "aside"]:
                for element in soup.find_all(tag):
                    element.decompose()
                    
            text = soup.get_text("\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            
            if len(text) < self.config["REQUEST_SETTINGS"]["MIN_CONTENT_LENGTH"]:
                return {"ok": False, "error": "Content too short", "text": text, "title": title}
                
            images = self.extract_images(soup, url)
                
            return {
                "ok": True,
                "title": title,
                "text": text,
                "markdown": md(str(soup)),
                "url": url,
                "images": images
            }
            
        except Exception as e:
            return {"ok": False, "error": str(e), "text": "", "title": ""}

    def simple_summarize(self, text):
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) < 3:
            return text[:500], text
            
        scored = []
        for i, s in enumerate(sentences):
            score = 1.0 + self.keyword_score(s) - (i / 100)
            scored.append((score, s))
            
        scored.sort(reverse=True, key=lambda x: x[0])
        summary = " ".join([s for _, s in scored[:5]])
        bullets = "\n".join(f"- {s}" for s in [s for _, s in scored[:3]])
        
        return summary, bullets

    def make_draft(self, entry, extracted):
        title = entry.get("title") or extracted.get("title") or "Untitled"
        link = entry.get("link", "")
        domain = self.domain_of(link)
        
        summary, bullets = self.simple_summarize(extracted.get("text", ""))
        
        image_markdown = ""
        if extracted.get("images"):
            image_markdown = "\n\n## Images\n\n"
            for i, img in enumerate(extracted["images"][:self.config["OUTPUT"]["MAX_IMAGES"]]):
                image_name = f"{hashlib.md5(img['url'].encode()).hexdigest()[:10]}.jpg"
                downloaded_path = self.download_image(img['url'], image_name)
                if downloaded_path:
                    image_markdown += f"![{img['alt']}](./{self.config['OUTPUT']['IMAGES_DIR']}/{image_name})\n\n"
        
        body = f"""# {title}

**TL;DR**: {summary}

## Key Takeaways
{bullets}
{image_markdown}
## Full Story
{extracted.get('markdown', extracted.get('text', ''))}

---
*Source: [{domain}]({link}). Automatically summarized for educational purposes.*
"""
        post = frontmatter.Post(body)
        post.metadata.update({
            "title": title,
            "date": datetime.now(timezone.utc).isoformat(),
            "tags": ["AI", "Security", "Tech"],
            "source": domain,
            "status": "draft"
        })
        
        return frontmatter.dumps(post)

    def save_draft(self, content, title):
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]
        filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title}.md"
        filepath = Path(self.config["OUTPUT"]["OUT_DIR"]) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return str(filepath)

    def fetch_candidates(self):
        candidates = []
        
        for source in self.config["SOURCES"]:
            try:
                feed = feedparser.parse(source)
                if feed.bozo and feed.bozo_exception:
                    continue
                    
                for entry in feed.entries:
                    if not entry.get("link"):
                        continue
                        
                    candidates.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", ""),
                        "entry": entry,
                    })
                    
            except Exception:
                continue
                
        return candidates

def main():
    root = tk.Tk()
    app = ProfessionalContentAggregator(root)
    root.mainloop()

if __name__ == "__main__":
    main()