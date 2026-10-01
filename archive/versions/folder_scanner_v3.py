import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Column index constants
COL_SUBFOLDER   = 0
COL_POSTER      = 1
COL_POSTER_SIZE = 2
COL_FANART      = 3
COL_FANART_SIZE = 4


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 ** 2):.2f} MB"


def open_file(path):
    """Open a file with the default Windows application."""
    try:
        os.startfile(path)
    except AttributeError:
        # Fallback for non-Windows (macOS / Linux)
        try:
            subprocess.Popen(["xdg-open", path])
        except FileNotFoundError:
            subprocess.Popen(["open", path])
    except Exception as e:
        messagebox.showerror("Cannot open file", str(e))


def scan_folder(root_path):
    results = []
    try:
        entries = os.scandir(root_path)
    except PermissionError:
        messagebox.showerror("Permission Error", f"Cannot access: {root_path}")
        return results

    for entry in entries:
        if entry.is_dir():
            subfolder_path = entry.path
            poster_path    = os.path.join(subfolder_path, "poster.jpg")
            fanart_path    = os.path.join(subfolder_path, "fanart.jpg")

            poster_exists  = os.path.isfile(poster_path)
            fanart_exists  = os.path.isfile(fanart_path)
            poster_bytes   = os.path.getsize(poster_path) if poster_exists else 0
            fanart_bytes   = os.path.getsize(fanart_path) if fanart_exists else 0

            results.append({
                "subfolder":     entry.name,
                "subfolder_path": subfolder_path,
                "poster_exists": poster_exists,
                "poster_path":   poster_path,
                "poster_bytes":  poster_bytes,
                "poster_size":   format_size(poster_bytes) if poster_exists else "—",
                "fanart_exists": fanart_exists,
                "fanart_path":   fanart_path,
                "fanart_bytes":  fanart_bytes,
                "fanart_size":   format_size(fanart_bytes) if fanart_exists else "—",
            })

    return results


# ── Sort options ──────────────────────────────────────────────────────────────
SORT_OPTIONS = {
    "Subfolder name (A → Z)":          (lambda r: r["subfolder"].lower(), False),
    "Subfolder name (Z → A)":          (lambda r: r["subfolder"].lower(), True),
    "poster.jpg size (large → small)": (lambda r: r["poster_bytes"],      True),
    "poster.jpg size (small → large)": (lambda r: r["poster_bytes"],      False),
    "fanart.jpg size (large → small)": (lambda r: r["fanart_bytes"],      True),
    "fanart.jpg size (small → large)": (lambda r: r["fanart_bytes"],      False),
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Subfolder Image Scanner")
        self.geometry("980x620")
        self.minsize(720, 420)
        self.configure(bg="#1e1e2e")
        # Maps treeview item id → result dict (keeps full paths after sort)
        self._item_map: dict[str, dict] = {}
        self._results: list[dict] = []
        self._build_ui()

    # ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#1e1e2e")
        header.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(
            header, text="🎬  Subfolder Image Scanner",
            font=("Helvetica", 17, "bold"),
            bg="#1e1e2e", fg="#cdd6f4"
        ).pack(side="left")

        # Folder picker
        picker = tk.Frame(self, bg="#1e1e2e")
        picker.pack(fill="x", padx=20, pady=(0, 8))

        self.folder_var = tk.StringVar(value="No folder selected")
        tk.Label(
            picker, textvariable=self.folder_var,
            font=("Helvetica", 10), bg="#313244", fg="#a6adc8",
            anchor="w", padx=10, pady=6, relief="flat"
        ).pack(side="left", fill="x", expand=True, ipady=2)

        tk.Button(
            picker, text="  Browse…  ",
            font=("Helvetica", 10, "bold"),
            bg="#89b4fa", fg="#1e1e2e", relief="flat",
            activebackground="#74c7ec", cursor="hand2",
            command=self._browse
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            picker, text="  Scan  ",
            font=("Helvetica", 10, "bold"),
            bg="#a6e3a1", fg="#1e1e2e", relief="flat",
            activebackground="#94e2d5", cursor="hand2",
            command=self._scan
        ).pack(side="left", padx=(6, 0))

        # Sort row
        sort_row = tk.Frame(self, bg="#1e1e2e")
        sort_row.pack(fill="x", padx=20, pady=(0, 4))

        tk.Label(
            sort_row, text="Sort by:",
            font=("Helvetica", 10), bg="#1e1e2e", fg="#a6adc8"
        ).pack(side="left")

        self.sort_var = tk.StringVar(value="Subfolder name (A → Z)")
        sort_menu = ttk.Combobox(
            sort_row, textvariable=self.sort_var,
            values=list(SORT_OPTIONS.keys()),
            state="readonly", width=36,
            font=("Helvetica", 10)
        )
        sort_menu.pack(side="left", padx=(8, 0))
        sort_menu.bind("<<ComboboxSelected>>", lambda _: self._refresh_table())

        # Hint label
        tk.Label(
            sort_row,
            text="  ·  Double-click ✅ to open image",
            font=("Helvetica", 9, "italic"),
            bg="#1e1e2e", fg="#585b70"
        ).pack(side="left", padx=(16, 0))

        # Stats bar
        self.stats_var = tk.StringVar(value="")
        tk.Label(
            self, textvariable=self.stats_var,
            font=("Helvetica", 9), bg="#1e1e2e", fg="#6c7086"
        ).pack(anchor="w", padx=22)

        # Table
        table_frame = tk.Frame(self, bg="#1e1e2e")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
            background="#313244", foreground="#cdd6f4",
            fieldbackground="#313244", rowheight=26,
            font=("Helvetica", 10))
        style.configure("Treeview.Heading",
            background="#45475a", foreground="#89b4fa",
            font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview",
            background=[("selected", "#585b70")],
            foreground=[("selected", "#cdd6f4")])

        columns = ("subfolder", "poster", "poster_size", "fanart", "fanart_size")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            selectmode="browse", style="Treeview"
        )

        self.tree.heading("subfolder",   text="Subfolder")
        self.tree.heading("poster",      text="poster.jpg")
        self.tree.heading("poster_size", text="Size")
        self.tree.heading("fanart",      text="fanart.jpg")
        self.tree.heading("fanart_size", text="Size")

        self.tree.column("subfolder",   width=320, anchor="w",      stretch=True)
        self.tree.column("poster",      width=90,  anchor="center", stretch=False)
        self.tree.column("poster_size", width=105, anchor="center", stretch=False)
        self.tree.column("fanart",      width=90,  anchor="center", stretch=False)
        self.tree.column("fanart_size", width=105, anchor="center", stretch=False)

        self.tree.tag_configure("odd", background="#2a2a3d")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Double-click binding
        self.tree.bind("<Double-1>", self._on_double_click)

        self._folder = None

    # ── Double-click handler ─────────────────────────────────────
    def _on_double_click(self, event):
        """Identify which column was clicked and open the image if it exists."""
        item_id = self.tree.identify_row(event.y)
        col_id  = self.tree.identify_column(event.x)   # returns "#1", "#2", etc.
        if not item_id or not col_id:
            return

        col_index = int(col_id.lstrip("#")) - 1        # convert to 0-based int
        data = self._item_map.get(item_id)
        if data is None:
            return

        if col_index in (COL_POSTER, COL_POSTER_SIZE):
            if data["poster_exists"]:
                open_file(data["poster_path"])
            else:
                messagebox.showinfo("Not found", "poster.jpg does not exist in this folder.")

        elif col_index in (COL_FANART, COL_FANART_SIZE):
            if data["fanart_exists"]:
                open_file(data["fanart_path"])
            else:
                messagebox.showinfo("Not found", "fanart.jpg does not exist in this folder.")

    # ── Browse / Scan / Refresh ──────────────────────────────────
    def _browse(self):
        path = filedialog.askdirectory(title="Select root folder")
        if path:
            self._folder = path
            self.folder_var.set(path)
            self.stats_var.set("")
            self._results = []
            self._item_map.clear()
            for row in self.tree.get_children():
                self.tree.delete(row)

    def _scan(self):
        if not self._folder:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return

        self._results = scan_folder(self._folder)

        if not self._results:
            messagebox.showinfo("Empty", "No subfolders found in the selected folder.")
            self.stats_var.set("")
            return

        total        = len(self._results)
        poster_count = sum(1 for r in self._results if r["poster_exists"])
        fanart_count = sum(1 for r in self._results if r["fanart_exists"])
        self.stats_var.set(
            f"{total} subfolder(s) scanned  •  "
            f"poster.jpg: {poster_count}/{total}  •  "
            f"fanart.jpg: {fanart_count}/{total}"
        )
        self._refresh_table()

    def _refresh_table(self):
        """Re-render the table with the current sort order."""
        if not self._results:
            return

        for row in self.tree.get_children():
            self.tree.delete(row)
        self._item_map.clear()

        key_fn, reverse = SORT_OPTIONS[self.sort_var.get()]
        sorted_results  = sorted(self._results, key=key_fn, reverse=reverse)

        for i, r in enumerate(sorted_results):
            iid = self.tree.insert("", "end", values=(
                r["subfolder"],
                "✅" if r["poster_exists"] else "❌",
                r["poster_size"],
                "✅" if r["fanart_exists"] else "❌",
                r["fanart_size"],
            ), tags=("odd",) if i % 2 else ())
            # Store full data so double-click can find the file path
            self._item_map[iid] = r


if __name__ == "__main__":
    app = App()
    app.mainloop()