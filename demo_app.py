#!/usr/bin/env python3
"""
Pulse — Project Management App
Realistic dummy app for testing Quest AI testing framework.

Run:   python demo_app.py
Login: demo@pulse.app / demo123
"""

import tkinter as tk
from tkinter import ttk, messagebox

# ─── Palette ────────────────────────────────────────────────────────────────
BG      = "#F0F2F5"
SIDEBAR = "#16213E"
SB_HOVER= "#1E2D52"
SB_ACT  = "#4361EE"
ACCENT  = "#4361EE"
WHITE   = "#FFFFFF"
TEXT    = "#1A1A2E"
TEXT2   = "#6B7280"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER  = "#EF4444"
BORDER  = "#E5E7EB"

PRIORITY_COLORS = {
    "Critical": ("#FCA5A5", "#7F1D1D"),
    "High":     ("#FED7AA", "#92400E"),
    "Medium":   ("#FDE68A", "#78350F"),
    "Low":      ("#BBF7D0", "#065F46"),
}

# ─── Sample Data ─────────────────────────────────────────────────────────────
TASKS_DATA = [
    {"id": 1,  "title": "Design new landing page",       "priority": "High",     "status": "In Progress", "due": "Mar 18", "assignee": "AL"},
    {"id": 2,  "title": "Fix login bug on mobile",       "priority": "Critical", "status": "Todo",        "due": "Mar 15", "assignee": "BK"},
    {"id": 3,  "title": "Update API documentation",      "priority": "Medium",   "status": "Todo",        "due": "Mar 22", "assignee": "CJ"},
    {"id": 4,  "title": "Set up CI/CD pipeline",         "priority": "High",     "status": "In Progress", "due": "Mar 20", "assignee": "AL"},
    {"id": 5,  "title": "User research interviews",      "priority": "Low",      "status": "Todo",        "due": "Mar 25", "assignee": "DM"},
    {"id": 6,  "title": "Performance optimization",      "priority": "Medium",   "status": "Done",        "due": "Mar 14", "assignee": "BK"},
    {"id": 7,  "title": "Write unit tests for auth",     "priority": "High",     "status": "In Progress", "due": "Mar 17", "assignee": "CJ"},
    {"id": 8,  "title": "Localization (French/German)",  "priority": "Low",      "status": "Todo",        "due": "Apr 1",  "assignee": "DM"},
    {"id": 9,  "title": "Database schema migration",     "priority": "Critical", "status": "Done",        "due": "Mar 14", "assignee": "AL"},
    {"id": 10, "title": "Accessibility audit",           "priority": "Medium",   "status": "Todo",        "due": "Mar 28", "assignee": "BK"},
    {"id": 11, "title": "Onboarding flow redesign",      "priority": "High",     "status": "Todo",        "due": "Apr 3",  "assignee": "ES"},
    {"id": 12, "title": "Analytics dashboard widgets",   "priority": "Medium",   "status": "In Progress", "due": "Mar 29", "assignee": "FW"},
]

PROJECTS_DATA = [
    {"name": "Website Redesign",        "desc": "Overhaul the marketing site with new brand identity",  "progress": 65, "tasks": 24, "team": 4, "color": "#4361EE"},
    {"name": "Mobile App v2.0",         "desc": "iOS and Android rebuild with React Native",            "progress": 32, "tasks": 41, "team": 6, "color": "#7209B7"},
    {"name": "Q2 Marketing Campaign",   "desc": "Launch campaign across 3 channels in 6 regions",      "progress": 88, "tasks": 15, "team": 3, "color": "#F72585"},
    {"name": "Data Analytics Platform", "desc": "Internal BI dashboard with real-time metrics",         "progress": 12, "tasks": 28, "team": 5, "color": "#06B6D4"},
]

TEAM_DATA = [
    {"name": "Alex Lim",    "initials": "AL", "role": "Lead Engineer",    "status": "online",  "color": "#4361EE"},
    {"name": "Blake Kim",   "initials": "BK", "role": "Product Designer", "status": "online",  "color": "#7209B7"},
    {"name": "Casey Jones", "initials": "CJ", "role": "Backend Engineer", "status": "away",    "color": "#F72585"},
    {"name": "Drew Morgan", "initials": "DM", "role": "QA Engineer",      "status": "offline", "color": "#10B981"},
    {"name": "Emery Silva", "initials": "ES", "role": "DevOps Engineer",  "status": "online",  "color": "#F59E0B"},
    {"name": "Fiona Walsh", "initials": "FW", "role": "Data Scientist",   "status": "away",    "color": "#06B6D4"},
]

ASSIGNEE_COLORS = {
    "AL": "#4361EE", "BK": "#7209B7", "CJ": "#F72585",
    "DM": "#10B981", "ES": "#F59E0B", "FW": "#06B6D4",
}

ACTIVITY = [
    ("BK", "#7209B7", "Blake created 'Fix login bug on mobile'",     "2m ago"),
    ("AL", "#4361EE", "Alex updated landing page design task",       "15m ago"),
    ("CJ", "#F72585", "Casey closed 3 failing test cases",           "1h ago"),
    ("DM", "#10B981", "Drew flagged a performance regression",       "2h ago"),
    ("AL", "#4361EE", "Alex merged PR #247 into main",               "3h ago"),
    ("ES", "#F59E0B", "Emery deployed CI/CD pipeline fix",           "4h ago"),
]


class PulseApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pulse")
        self.root.geometry("1200x750")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(900, 600)

        # Must init after Tk()
        self.tasks = []
        for t in TASKS_DATA:
            task = dict(t)
            task["done_var"] = tk.BooleanVar(value=(t["status"] == "Done"))
            self.tasks.append(task)

        self.projects = PROJECTS_DATA
        self.team = TEAM_DATA
        self.current_user = {"name": "Sam Taylor", "initials": "ST", "email": "demo@pulse.app"}
        self.current_view = None
        self.sidebar_buttons = {}

        self._setup_menu()
        self._show_login()
        self.root.mainloop()

    # ─── Menu ─────────────────────────────────────────────────────────────────
    def _setup_menu(self):
        mb = tk.Menu(self.root)

        file_m = tk.Menu(mb, tearoff=0)
        file_m.add_command(label="New Task",        accelerator="Command+N", command=self._add_task_dialog)
        file_m.add_command(label="New Project",     command=lambda: None)
        file_m.add_separator()
        file_m.add_command(label="Import Tasks…",   command=lambda: None)
        file_m.add_command(label="Export Report…",  command=lambda: None)
        file_m.add_separator()
        file_m.add_command(label="Quit Pulse",      accelerator="Command+Q", command=self.root.quit)
        mb.add_cascade(label="File", menu=file_m)

        edit_m = tk.Menu(mb, tearoff=0)
        edit_m.add_command(label="Undo",  accelerator="Command+Z",       command=lambda: None)
        edit_m.add_command(label="Redo",  accelerator="Command+Shift+Z", command=lambda: None)
        edit_m.add_separator()
        edit_m.add_command(label="Find…", accelerator="Command+F",       command=lambda: None)
        mb.add_cascade(label="Edit", menu=edit_m)

        view_m = tk.Menu(mb, tearoff=0)
        view_m.add_command(label="Dashboard", command=lambda: self._navigate("dashboard"))
        view_m.add_command(label="Tasks",     command=lambda: self._navigate("tasks"))
        view_m.add_command(label="Projects",  command=lambda: self._navigate("projects"))
        view_m.add_command(label="Team",      command=lambda: self._navigate("team"))
        view_m.add_separator()
        view_m.add_command(label="Settings",  command=lambda: self._navigate("settings"))
        mb.add_cascade(label="View", menu=view_m)

        help_m = tk.Menu(mb, tearoff=0)
        help_m.add_command(label="Pulse Help",          command=lambda: None)
        help_m.add_command(label="Keyboard Shortcuts",  command=self._show_shortcuts)
        help_m.add_separator()
        help_m.add_command(label="About Pulse",         command=self._show_about)
        mb.add_cascade(label="Help", menu=help_m)

        self.root.config(menu=mb)
        self.root.bind("<Command-n>", lambda e: self._add_task_dialog())
        self.root.bind("<Command-q>", lambda e: self.root.quit())

    # ─── Login ────────────────────────────────────────────────────────────────
    def _show_login(self):
        self.login_frame = tk.Frame(self.root, bg="#EEF0F8")
        self.login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        card = tk.Frame(self.login_frame, bg=WHITE)
        card.place(relx=0.5, rely=0.5, anchor="center", width=400, height=500)

        # Logo
        logo_wrap = tk.Frame(card, bg=WHITE)
        logo_wrap.pack(pady=(36, 8))
        logo_sq = tk.Frame(logo_wrap, bg=ACCENT, width=56, height=56)
        logo_sq.pack()
        logo_sq.pack_propagate(False)
        tk.Label(logo_sq, text="P", font=("Helvetica", 26, "bold"), bg=ACCENT, fg=WHITE).pack(expand=True)

        tk.Label(card, text="Pulse", font=("Helvetica", 24, "bold"), bg=WHITE, fg=TEXT).pack()
        tk.Label(card, text="Sign in to your workspace", font=("Helvetica", 13), bg=WHITE, fg=TEXT2).pack(pady=(4, 28))

        form = tk.Frame(card, bg=WHITE)
        form.pack(fill="x", padx=36)

        # Email
        tk.Label(form, text="Email address", font=("Helvetica", 12), bg=WHITE, fg=TEXT, anchor="w").pack(fill="x")
        self.email_var = tk.StringVar(value="demo@pulse.app")
        email_e = tk.Entry(form, textvariable=self.email_var, font=("Helvetica", 13),
                           bg="#F9FAFB", fg=TEXT, relief="solid", bd=1, insertbackground=ACCENT)
        email_e.pack(fill="x", ipady=9, pady=(4, 14))

        # Password
        tk.Label(form, text="Password", font=("Helvetica", 12), bg=WHITE, fg=TEXT, anchor="w").pack(fill="x")
        self.pass_var = tk.StringVar(value="demo123")
        pass_e = tk.Entry(form, textvariable=self.pass_var, show="●",
                          font=("Helvetica", 13), bg="#F9FAFB", fg=TEXT,
                          relief="solid", bd=1, insertbackground=ACCENT)
        pass_e.pack(fill="x", ipady=9, pady=(4, 4))

        tk.Label(form, text="Forgot password?", font=("Helvetica", 11),
                 bg=WHITE, fg=ACCENT, cursor="hand2", anchor="e").pack(fill="x")

        sign_in = tk.Button(form, text="Sign In", font=("Helvetica", 13, "bold"),
                            bg=ACCENT, fg=WHITE, relief="flat", bd=0,
                            activebackground="#3251DD", activeforeground=WHITE,
                            cursor="hand2", command=self._do_login)
        sign_in.pack(fill="x", ipady=11, pady=(16, 8))

        tk.Label(form, text="Demo: demo@pulse.app  /  demo123",
                 font=("Helvetica", 10), bg=WHITE, fg=TEXT2).pack()

        pass_e.bind("<Return>", lambda e: self._do_login())
        email_e.bind("<Return>", lambda e: pass_e.focus_set())

    def _do_login(self):
        if self.email_var.get().strip() == "demo@pulse.app" and self.pass_var.get().strip() == "demo123":
            self.login_frame.destroy()
            self._build_main()
        else:
            messagebox.showerror("Login Failed",
                                 "Invalid credentials.\n\nUse:\n  demo@pulse.app\n  demo123")

    # ─── Main Layout ─────────────────────────────────────────────────────────
    def _build_main(self):
        self.main_frame = tk.Frame(self.root, bg=BG)
        self.main_frame.pack(fill="both", expand=True)

        self._build_sidebar()

        right = tk.Frame(self.main_frame, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_header(right)
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x")

        self.content_area = tk.Frame(right, bg=BG)
        self.content_area.pack(fill="both", expand=True, padx=24, pady=20)

        self._navigate("dashboard")

    def _build_sidebar(self):
        sb = tk.Frame(self.main_frame, bg=SIDEBAR, width=210)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # Brand
        brand = tk.Frame(sb, bg=SIDEBAR)
        brand.pack(fill="x", padx=16, pady=20)
        logo = tk.Frame(brand, bg=ACCENT, width=34, height=34)
        logo.pack(side="left")
        logo.pack_propagate(False)
        tk.Label(logo, text="P", font=("Helvetica", 17, "bold"), bg=ACCENT, fg=WHITE).pack(expand=True)
        tk.Label(brand, text="Pulse", font=("Helvetica", 16, "bold"), bg=SIDEBAR, fg=WHITE).pack(side="left", padx=10)

        tk.Frame(sb, bg="#2A3A5C", height=1).pack(fill="x", padx=16, pady=(0, 8))

        nav_items = [
            ("dashboard", "⊞", "Dashboard"),
            ("tasks",     "✓", "Tasks"),
            ("projects",  "⬡", "Projects"),
            ("team",      "◎", "Team"),
        ]
        for view_id, icon, label in nav_items:
            self._nav_item(sb, view_id, icon, label)

        tk.Frame(sb, bg="#2A3A5C", height=1).pack(fill="x", padx=16, pady=8)
        self._nav_item(sb, "settings", "⚙", "Settings")

        # User block
        tk.Frame(sb, bg="#2A3A5C", height=1).pack(side="bottom", fill="x")
        bottom = tk.Frame(sb, bg="#0F1929")
        bottom.pack(side="bottom", fill="x")
        uf = tk.Frame(bottom, bg="#0F1929")
        uf.pack(fill="x", padx=16, pady=14)
        av = tk.Frame(uf, bg=ACCENT, width=32, height=32)
        av.pack(side="left")
        av.pack_propagate(False)
        tk.Label(av, text=self.current_user["initials"], font=("Helvetica", 11, "bold"),
                 bg=ACCENT, fg=WHITE).pack(expand=True)
        nf = tk.Frame(uf, bg="#0F1929")
        nf.pack(side="left", padx=8)
        tk.Label(nf, text=self.current_user["name"], font=("Helvetica", 11, "bold"),
                 bg="#0F1929", fg=WHITE).pack(anchor="w")
        tk.Label(nf, text="Admin", font=("Helvetica", 10),
                 bg="#0F1929", fg="#8B95A5").pack(anchor="w")

    def _nav_item(self, parent, view_id, icon, label):
        frame = tk.Frame(parent, bg=SIDEBAR, cursor="hand2")
        frame.pack(fill="x", padx=8, pady=2)
        icon_lbl = tk.Label(frame, text=icon, font=("Helvetica", 14),
                            bg=SIDEBAR, fg="#8B95A5", width=2)
        icon_lbl.pack(side="left", padx=(8, 0), pady=8)
        text_lbl = tk.Label(frame, text=label, font=("Helvetica", 12),
                            bg=SIDEBAR, fg="#B0BAC9", anchor="w")
        text_lbl.pack(side="left", padx=8, pady=8)

        self.sidebar_buttons[view_id] = (frame, icon_lbl, text_lbl)

        def click(e, v=view_id):
            self._navigate(v)
        def enter(e, f=frame, i=icon_lbl, t=text_lbl, v=view_id):
            if self.current_view != v:
                for w in (f, i, t): w.config(bg=SB_HOVER)
        def leave(e, f=frame, i=icon_lbl, t=text_lbl, v=view_id):
            if self.current_view != v:
                for w in (f, i, t): w.config(bg=SIDEBAR)

        for w in (frame, icon_lbl, text_lbl):
            w.bind("<Button-1>", click)
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=WHITE, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        self.header_title = tk.Label(hdr, text="Dashboard",
                                     font=("Helvetica", 18, "bold"), bg=WHITE, fg=TEXT)
        self.header_title.pack(side="left", padx=24)

        # Right controls
        right = tk.Frame(hdr, bg=WHITE)
        right.pack(side="right", padx=16)
        tk.Button(right, text="🔔", font=("Helvetica", 14), bg=WHITE, fg=TEXT2,
                  relief="flat", bd=0, cursor="hand2").pack(side="left", padx=8)
        av = tk.Frame(right, bg=ACCENT, width=34, height=34)
        av.pack(side="left")
        av.pack_propagate(False)
        tk.Label(av, text=self.current_user["initials"], font=("Helvetica", 12, "bold"),
                 bg=ACCENT, fg=WHITE).pack(expand=True)

        # Search
        sf = tk.Frame(hdr, bg="#F3F4F6", relief="flat")
        sf.pack(side="left", padx=16)
        tk.Label(sf, text="⌕", font=("Helvetica", 13), bg="#F3F4F6", fg=TEXT2).pack(side="left", padx=8, pady=6)
        self.search_entry = tk.Entry(sf, font=("Helvetica", 12), bg="#F3F4F6", fg=TEXT2,
                                     relief="flat", bd=0, insertbackground=ACCENT, width=22)
        self.search_entry.pack(side="left", padx=(0, 8), pady=6)
        self.search_entry.insert(0, "Search tasks…")
        self.search_entry.bind("<FocusIn>",  lambda e: self.search_entry.delete(0, "end")
                               if self.search_entry.get() == "Search tasks…" else None)
        self.search_entry.bind("<FocusOut>", lambda e: self.search_entry.insert(0, "Search tasks…")
                               if not self.search_entry.get() else None)

    # ─── Navigation ──────────────────────────────────────────────────────────
    def _navigate(self, view):
        for vid, (f, i, t) in self.sidebar_buttons.items():
            if vid == view:
                for w in (f, i, t): w.config(bg=SB_ACT)
                i.config(fg=WHITE)
                t.config(fg=WHITE)
            else:
                for w in (f, i, t): w.config(bg=SIDEBAR)
                i.config(fg="#8B95A5")
                t.config(fg="#B0BAC9")

        self.current_view = view
        titles = {"dashboard": "Dashboard", "tasks": "Tasks",
                  "projects": "Projects",  "team": "Team", "settings": "Settings"}
        if hasattr(self, "header_title"):
            self.header_title.config(text=titles.get(view, view.title()))

        for w in self.content_area.winfo_children():
            w.destroy()

        {"dashboard": self._view_dashboard,
         "tasks":     self._view_tasks,
         "projects":  self._view_projects,
         "team":      self._view_team,
         "settings":  self._view_settings}.get(view, lambda: None)()

    # ─── Dashboard View ───────────────────────────────────────────────────────
    def _view_dashboard(self):
        in_prog  = [t for t in self.tasks if t["status"] == "In Progress"]
        done     = [t for t in self.tasks if t["done_var"].get()]
        overdue  = [t for t in self.tasks if t["due"] in ("Mar 15",) and not t["done_var"].get()]

        stats = [
            ("Total Tasks",   str(len(self.tasks)),   ACCENT),
            ("In Progress",   str(len(in_prog)),      WARNING),
            ("Completed",     str(len(done)),          SUCCESS),
            ("Overdue",       str(max(len(overdue),2)), DANGER),
            ("Team Members",  str(len(self.team)),    "#7209B7"),
        ]

        stats_row = tk.Frame(self.content_area, bg=BG)
        stats_row.pack(fill="x", pady=(0, 16))
        for label, value, color in stats:
            card = tk.Frame(stats_row, bg=WHITE)
            card.pack(side="left", fill="both", expand=True, padx=(0, 12))
            tk.Frame(card, bg=color, height=4).pack(fill="x")
            tk.Label(card, text=value, font=("Helvetica", 28, "bold"), bg=WHITE, fg=TEXT).pack(pady=(14, 0))
            tk.Label(card, text=label, font=("Helvetica", 11), bg=WHITE, fg=TEXT2).pack(pady=(2, 14))

        cols = tk.Frame(self.content_area, bg=BG)
        cols.pack(fill="both", expand=True)

        # Recent tasks panel
        left = tk.Frame(cols, bg=WHITE)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        hdr_f = tk.Frame(left, bg=WHITE)
        hdr_f.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(hdr_f, text="Recent Tasks", font=("Helvetica", 14, "bold"), bg=WHITE, fg=TEXT).pack(side="left")
        tk.Button(hdr_f, text="+ New Task", font=("Helvetica", 11), bg=ACCENT, fg=WHITE,
                  relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                  command=self._add_task_dialog).pack(side="right")
        tk.Frame(left, bg=BORDER, height=1).pack(fill="x")

        for task in self.tasks[:7]:
            self._compact_task_row(left, task)

        # Activity feed
        right_panel = tk.Frame(cols, bg=WHITE, width=290)
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)
        tk.Label(right_panel, text="Activity", font=("Helvetica", 14, "bold"),
                 bg=WHITE, fg=TEXT).pack(anchor="w", padx=16, pady=16)
        tk.Frame(right_panel, bg=BORDER, height=1).pack(fill="x")
        for initials, color, text, ts in ACTIVITY:
            row = tk.Frame(right_panel, bg=WHITE)
            row.pack(fill="x", padx=16, pady=8)
            av = tk.Frame(row, bg=color, width=28, height=28)
            av.pack(side="left")
            av.pack_propagate(False)
            tk.Label(av, text=initials, font=("Helvetica", 9, "bold"), bg=color, fg=WHITE).pack(expand=True)
            info = tk.Frame(row, bg=WHITE)
            info.pack(side="left", padx=8, fill="x", expand=True)
            tk.Label(info, text=text, font=("Helvetica", 10), bg=WHITE, fg=TEXT,
                     anchor="w", wraplength=170, justify="left").pack(anchor="w")
            tk.Label(info, text=ts, font=("Helvetica", 9), bg=WHITE, fg=TEXT2).pack(anchor="w")

    def _compact_task_row(self, parent, task):
        row = tk.Frame(parent, bg=WHITE, cursor="hand2")
        row.pack(fill="x")
        tk.Frame(parent, bg="#F9FAFB", height=1).pack(fill="x")

        chk = tk.Checkbutton(row, variable=task["done_var"], bg=WHITE,
                             activebackground=WHITE, cursor="hand2",
                             command=lambda t=task: self._toggle_task(t))
        chk.pack(side="left", padx=(12, 4), pady=9)

        fg = TEXT2 if task["done_var"].get() else TEXT
        tk.Label(row, text=task["title"], font=("Helvetica", 12),
                 bg=WHITE, fg=fg, anchor="w").pack(side="left", fill="x", expand=True)

        pri = task["priority"]
        bg_c, fg_c = PRIORITY_COLORS.get(pri, ("#E5E7EB", TEXT2))
        tk.Label(row, text=pri, font=("Helvetica", 10), bg=bg_c, fg=fg_c,
                 padx=7, pady=2).pack(side="right", padx=4)
        tk.Label(row, text=task["due"], font=("Helvetica", 10), bg=WHITE, fg=TEXT2).pack(side="right", padx=4)

        av_c = ASSIGNEE_COLORS.get(task["assignee"], TEXT2)
        av = tk.Frame(row, bg=av_c, width=22, height=22)
        av.pack(side="right", padx=(4, 12))
        av.pack_propagate(False)
        tk.Label(av, text=task["assignee"], font=("Helvetica", 8, "bold"), bg=av_c, fg=WHITE).pack(expand=True)

        row.bind("<Enter>", lambda e, r=row: r.config(bg="#F8F9FA"))
        row.bind("<Leave>", lambda e, r=row: r.config(bg=WHITE))

    def _toggle_task(self, task):
        task["status"] = "Done" if task["done_var"].get() else "Todo"

    # ─── Tasks View ───────────────────────────────────────────────────────────
    def _view_tasks(self):
        toolbar = tk.Frame(self.content_area, bg=BG)
        toolbar.pack(fill="x", pady=(0, 14))

        tk.Button(toolbar, text="+ New Task", font=("Helvetica", 12), bg=ACCENT, fg=WHITE,
                  relief="flat", bd=0, padx=14, pady=7, cursor="hand2",
                  command=self._add_task_dialog).pack(side="left", padx=(0, 16))

        tk.Label(toolbar, text="Priority:", font=("Helvetica", 11), bg=BG, fg=TEXT2).pack(side="left")
        self.filter_priority = ttk.Combobox(toolbar,
                                             values=["All", "Critical", "High", "Medium", "Low"],
                                             state="readonly", width=10, font=("Helvetica", 11))
        self.filter_priority.set("All")
        self.filter_priority.pack(side="left", padx=(4, 16))
        self.filter_priority.bind("<<ComboboxSelected>>", lambda e: self._refresh_task_list())

        tk.Label(toolbar, text="Status:", font=("Helvetica", 11), bg=BG, fg=TEXT2).pack(side="left")
        self.filter_status = ttk.Combobox(toolbar,
                                           values=["All", "Todo", "In Progress", "Done"],
                                           state="readonly", width=12, font=("Helvetica", 11))
        self.filter_status.set("All")
        self.filter_status.pack(side="left", padx=4)
        self.filter_status.bind("<<ComboboxSelected>>", lambda e: self._refresh_task_list())

        list_frame = tk.Frame(self.content_area, bg=WHITE)
        list_frame.pack(fill="both", expand=True)

        # Table header
        hdr = tk.Frame(list_frame, bg="#F3F4F6")
        hdr.pack(fill="x")
        for col, flex, width in [("", False, 36), ("Task", True, 0), ("Priority", False, 90),
                                  ("Status", False, 100), ("Due", False, 80), ("Assignee", False, 70)]:
            tk.Label(hdr, text=col, font=("Helvetica", 11, "bold"), bg="#F3F4F6", fg=TEXT2,
                     anchor="w", width=width if width else 0).pack(
                side="left", padx=8 if col == "Task" else 4, pady=8,
                expand=col == "Task", fill="x" if col == "Task" else None)
        tk.Frame(list_frame, bg=BORDER, height=1).pack(fill="x")

        canvas = tk.Canvas(list_frame, bg=WHITE, highlightthickness=0)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.task_scroll_frame = tk.Frame(canvas, bg=WHITE)
        self.task_scroll_frame.bind("<Configure>",
                                    lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.task_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._refresh_task_list()

    def _refresh_task_list(self):
        for w in self.task_scroll_frame.winfo_children():
            w.destroy()

        pri_f = self.filter_priority.get() if hasattr(self, "filter_priority") else "All"
        sta_f = self.filter_status.get()   if hasattr(self, "filter_status")   else "All"

        for task in self.tasks:
            if pri_f != "All" and task["priority"] != pri_f:
                continue
            if sta_f != "All" and task["status"] != sta_f:
                continue
            self._full_task_row(self.task_scroll_frame, task)

    def _full_task_row(self, parent, task):
        row = tk.Frame(parent, bg=WHITE)
        row.pack(fill="x")
        tk.Frame(parent, bg="#F9FAFB", height=1).pack(fill="x")

        chk = tk.Checkbutton(row, variable=task["done_var"], bg=WHITE,
                             activebackground=WHITE, cursor="hand2",
                             command=lambda t=task: self._toggle_task(t))
        chk.pack(side="left", padx=8, pady=9)

        fg = TEXT2 if task["done_var"].get() else TEXT
        tk.Label(row, text=task["title"], font=("Helvetica", 12),
                 bg=WHITE, fg=fg, anchor="w").pack(side="left", fill="x", expand=True)

        status_c = {"Todo": ("#E5E7EB", TEXT2), "In Progress": ("#DBEAFE", "#1D4ED8"), "Done": ("#D1FAE5", "#065F46")}
        s_bg, s_fg = status_c.get(task["status"], ("#E5E7EB", TEXT2))
        tk.Label(row, text=task["status"], font=("Helvetica", 10),
                 bg=s_bg, fg=s_fg, padx=8, pady=2).pack(side="right", padx=12)
        tk.Label(row, text=task["due"], font=("Helvetica", 11),
                 bg=WHITE, fg=TEXT2).pack(side="right", padx=8)
        pri = task["priority"]
        bg_c, fg_c = PRIORITY_COLORS.get(pri, ("#E5E7EB", TEXT2))
        tk.Label(row, text=pri, font=("Helvetica", 10), bg=bg_c, fg=fg_c,
                 padx=7, pady=2).pack(side="right", padx=4)

        row.bind("<Enter>", lambda e, r=row: r.config(bg="#F8F9FA"))
        row.bind("<Leave>", lambda e, r=row: r.config(bg=WHITE))

    # ─── Projects View ────────────────────────────────────────────────────────
    def _view_projects(self):
        hdr = tk.Frame(self.content_area, bg=BG)
        hdr.pack(fill="x", pady=(0, 16))
        tk.Label(hdr, text="Active Projects", font=("Helvetica", 15, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="+ New Project", font=("Helvetica", 11), bg=ACCENT, fg=WHITE,
                  relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                  command=lambda: None).pack(side="right")

        grid = tk.Frame(self.content_area, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0, 1), weight=1)

        for i, proj in enumerate(self.projects):
            r, c = divmod(i, 2)
            card = tk.Frame(grid, bg=WHITE)
            card.grid(row=r, column=c, padx=(0, 12 if c == 0 else 0), pady=(0, 12), sticky="nsew")
            grid.rowconfigure(r, weight=1)

            tk.Frame(card, bg=proj["color"], height=5).pack(fill="x")
            body = tk.Frame(card, bg=WHITE)
            body.pack(fill="both", expand=True, padx=20, pady=16)

            tk.Label(body, text=proj["name"], font=("Helvetica", 14, "bold"), bg=WHITE, fg=TEXT).pack(anchor="w")
            tk.Label(body, text=proj["desc"], font=("Helvetica", 11), bg=WHITE, fg=TEXT2,
                     wraplength=260, justify="left").pack(anchor="w", pady=(4, 14))

            tk.Label(body, text=f"Progress   {proj['progress']}%",
                     font=("Helvetica", 11), bg=WHITE, fg=TEXT2).pack(anchor="w")
            bar_bg = tk.Frame(body, bg=BORDER, height=8)
            bar_bg.pack(fill="x", pady=(4, 14))
            bar_bg.update_idletasks()
            tk.Frame(bar_bg, bg=proj["color"], height=8).place(
                x=0, y=0, relheight=1, relwidth=proj["progress"] / 100)

            meta = tk.Frame(body, bg=WHITE)
            meta.pack(fill="x")
            tk.Label(meta, text=f"📋  {proj['tasks']} tasks",
                     font=("Helvetica", 11), bg=WHITE, fg=TEXT2).pack(side="left")
            tk.Label(meta, text=f"👤  {proj['team']} members",
                     font=("Helvetica", 11), bg=WHITE, fg=TEXT2).pack(side="left", padx=16)

            tk.Button(card, text="Open Project →", font=("Helvetica", 11),
                      bg=WHITE, fg=proj["color"], relief="flat", bd=0, cursor="hand2",
                      command=lambda n=proj["name"]: messagebox.showinfo("Project", f"Opening '{n}'…")
                      ).pack(anchor="e", padx=20, pady=12)

    # ─── Team View ────────────────────────────────────────────────────────────
    def _view_team(self):
        hdr = tk.Frame(self.content_area, bg=BG)
        hdr.pack(fill="x", pady=(0, 16))
        tk.Label(hdr, text="Team Members", font=("Helvetica", 15, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="Invite Member", font=("Helvetica", 11), bg=ACCENT, fg=WHITE,
                  relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                  command=lambda: messagebox.showinfo("Invite", "Invitation link copied to clipboard!")
                  ).pack(side="right")

        grid = tk.Frame(self.content_area, bg=BG)
        grid.pack(fill="both", expand=True)
        STATUS_C = {"online": SUCCESS, "away": WARNING, "offline": TEXT2}

        for i, m in enumerate(self.team):
            r, c = divmod(i, 3)
            card = tk.Frame(grid, bg=WHITE)
            card.grid(row=r, column=c, padx=(0, 12 if c < 2 else 0), pady=(0, 12), sticky="nsew")
            grid.columnconfigure(c, weight=1)

            body = tk.Frame(card, bg=WHITE)
            body.pack(fill="both", expand=True, padx=20, pady=20)

            av = tk.Frame(body, bg=m["color"], width=56, height=56)
            av.pack()
            av.pack_propagate(False)
            tk.Label(av, text=m["initials"], font=("Helvetica", 20, "bold"),
                     bg=m["color"], fg=WHITE).pack(expand=True)

            tk.Label(body, text=m["name"], font=("Helvetica", 13, "bold"), bg=WHITE, fg=TEXT).pack(pady=(10, 2))
            tk.Label(body, text=m["role"], font=("Helvetica", 11), bg=WHITE, fg=TEXT2).pack()

            srow = tk.Frame(body, bg=WHITE)
            srow.pack(pady=8)
            tk.Frame(srow, bg=STATUS_C[m["status"]], width=8, height=8).pack(side="left")
            tk.Label(srow, text=m["status"].capitalize(), font=("Helvetica", 10),
                     bg=WHITE, fg=STATUS_C[m["status"]]).pack(side="left", padx=4)

            tk.Button(body, text="Message", font=("Helvetica", 10), bg="#F3F4F6", fg=TEXT,
                      relief="flat", bd=0, padx=12, pady=4, cursor="hand2",
                      command=lambda n=m["name"]: messagebox.showinfo("Message",
                                                                       f"Opening chat with {n}…")
                      ).pack(pady=(4, 0))

    # ─── Settings View ────────────────────────────────────────────────────────
    def _view_settings(self):
        outer = tk.Frame(self.content_area, bg=WHITE)
        outer.pack(fill="both", expand=True)
        content = tk.Frame(outer, bg=WHITE)
        content.pack(fill="x", padx=36, pady=28, anchor="n")

        # Account section
        tk.Label(content, text="Account", font=("Helvetica", 14, "bold"), bg=WHITE, fg=TEXT).pack(anchor="w")
        tk.Frame(content, bg=BORDER, height=1).pack(fill="x", pady=12)

        av_row = tk.Frame(content, bg=WHITE)
        av_row.pack(fill="x", pady=(0, 16))
        av = tk.Frame(av_row, bg=ACCENT, width=56, height=56)
        av.pack(side="left")
        av.pack_propagate(False)
        tk.Label(av, text=self.current_user["initials"], font=("Helvetica", 18, "bold"),
                 bg=ACCENT, fg=WHITE).pack(expand=True)
        av_info = tk.Frame(av_row, bg=WHITE)
        av_info.pack(side="left", padx=16)
        tk.Label(av_info, text="Profile Photo", font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w")
        tk.Button(av_info, text="Change Photo", font=("Helvetica", 10), bg="#F3F4F6", fg=TEXT,
                  relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                  command=lambda: None).pack(anchor="w", pady=4)

        for label, default in [("Display Name", self.current_user["name"]),
                                ("Email Address", self.current_user["email"])]:
            tk.Label(content, text=label, font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w", pady=(12, 4))
            e = tk.Entry(content, font=("Helvetica", 12), bg="#F9FAFB", fg=TEXT,
                         relief="solid", bd=1, insertbackground=ACCENT)
            e.pack(fill="x", ipady=9)
            e.insert(0, default)

        # Preferences
        tk.Label(content, text="Preferences", font=("Helvetica", 14, "bold"),
                 bg=WHITE, fg=TEXT).pack(anchor="w", pady=(28, 0))
        tk.Frame(content, bg=BORDER, height=1).pack(fill="x", pady=12)

        self.notif_var = tk.BooleanVar(value=True)
        self.dark_var  = tk.BooleanVar(value=False)
        self.sound_var = tk.BooleanVar(value=True)
        for lbl, var in [("Email notifications", self.notif_var),
                          ("Dark mode (beta)", self.dark_var),
                          ("Sound effects", self.sound_var)]:
            r = tk.Frame(content, bg=WHITE)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=lbl, font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(side="left")
            tk.Checkbutton(r, variable=var, bg=WHITE, activebackground=WHITE, cursor="hand2").pack(side="right")

        tk.Label(content, text="Language", font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w", pady=(14, 4))
        lang = ttk.Combobox(content, values=["English", "Spanish", "French", "German", "Japanese"],
                            state="readonly", width=18, font=("Helvetica", 12))
        lang.set("English")
        lang.pack(anchor="w")

        tk.Button(content, text="Save Changes", font=("Helvetica", 12, "bold"),
                  bg=ACCENT, fg=WHITE, relief="flat", bd=0, padx=24, pady=10, cursor="hand2",
                  command=self._save_settings).pack(anchor="w", pady=(24, 0))

        # Danger zone
        tk.Label(content, text="Danger Zone", font=("Helvetica", 14, "bold"),
                 bg=WHITE, fg=DANGER).pack(anchor="w", pady=(28, 0))
        tk.Frame(content, bg="#FEE2E2", height=1).pack(fill="x", pady=12)
        tk.Button(content, text="Sign Out", font=("Helvetica", 12), bg="#FEF2F2", fg=DANGER,
                  relief="flat", bd=1, padx=16, pady=8, cursor="hand2",
                  command=self._sign_out).pack(anchor="w")

    def _save_settings(self):
        messagebox.showinfo("Saved", "Your settings have been saved successfully.")

    def _sign_out(self):
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            self.main_frame.destroy()
            self._show_login()

    # ─── New Task Dialog ──────────────────────────────────────────────────────
    def _add_task_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("New Task")
        dlg.geometry("480x540")
        dlg.configure(bg=WHITE)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="Create New Task", font=("Helvetica", 16, "bold"),
                 bg=WHITE, fg=TEXT).pack(pady=(24, 16), padx=24, anchor="w")
        tk.Frame(dlg, bg=BORDER, height=1).pack(fill="x")

        form = tk.Frame(dlg, bg=WHITE)
        form.pack(fill="both", expand=True, padx=24, pady=16)

        tk.Label(form, text="Title *", font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w")
        title_e = tk.Entry(form, font=("Helvetica", 12), bg="#F9FAFB", fg=TEXT,
                           relief="solid", bd=1, insertbackground=ACCENT)
        title_e.pack(fill="x", ipady=9, pady=(4, 14))
        title_e.focus_set()

        tk.Label(form, text="Description", font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w")
        desc_t = tk.Text(form, font=("Helvetica", 11), bg="#F9FAFB", fg=TEXT,
                         relief="solid", bd=1, height=4, insertbackground=ACCENT)
        desc_t.pack(fill="x", pady=(4, 14))

        two = tk.Frame(form, bg=WHITE)
        two.pack(fill="x", pady=(0, 14))
        lf = tk.Frame(two, bg=WHITE)
        lf.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(lf, text="Priority", font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w")
        pri_cb = ttk.Combobox(lf, values=["Low", "Medium", "High", "Critical"],
                              state="readonly", font=("Helvetica", 11))
        pri_cb.set("Medium")
        pri_cb.pack(fill="x", pady=4)

        rf = tk.Frame(two, bg=WHITE)
        rf.pack(side="right", fill="x", expand=True)
        tk.Label(rf, text="Assignee", font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w")
        asn_cb = ttk.Combobox(rf, values=[m["name"] for m in self.team],
                              state="readonly", font=("Helvetica", 11))
        asn_cb.set(self.team[0]["name"])
        asn_cb.pack(fill="x", pady=4)

        tk.Label(form, text="Due Date", font=("Helvetica", 12), bg=WHITE, fg=TEXT).pack(anchor="w")
        due_e = tk.Entry(form, font=("Helvetica", 12), bg="#F9FAFB", fg=TEXT,
                         relief="solid", bd=1, insertbackground=ACCENT)
        due_e.pack(fill="x", ipady=9, pady=(4, 0))
        due_e.insert(0, "Mar 30")

        btn_row = tk.Frame(dlg, bg=WHITE)
        btn_row.pack(fill="x", padx=24, pady=(8, 20))

        def create():
            title = title_e.get().strip()
            if not title:
                messagebox.showwarning("Required", "Task title is required.", parent=dlg)
                return
            task = {
                "id":       max(t["id"] for t in self.tasks) + 1,
                "title":    title,
                "priority": pri_cb.get(),
                "status":   "Todo",
                "due":      due_e.get() or "TBD",
                "assignee": asn_cb.get()[:2].upper() if asn_cb.get() else "??",
                "done_var": tk.BooleanVar(value=False),
            }
            self.tasks.insert(0, task)
            dlg.destroy()
            if self.current_view in ("tasks", "dashboard"):
                self._navigate(self.current_view)
            messagebox.showinfo("Created", f"Task '{title}' has been created.")

        tk.Button(btn_row, text="Cancel", font=("Helvetica", 12), bg="#F3F4F6", fg=TEXT,
                  relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
                  command=dlg.destroy).pack(side="left")
        tk.Button(btn_row, text="Create Task", font=("Helvetica", 12, "bold"),
                  bg=ACCENT, fg=WHITE, relief="flat", bd=0, padx=20, pady=8, cursor="hand2",
                  command=create).pack(side="right")

    # ─── Misc Dialogs ─────────────────────────────────────────────────────────
    def _show_shortcuts(self):
        messagebox.showinfo("Keyboard Shortcuts",
                            "Cmd+N    New Task\n"
                            "Cmd+F    Find\n"
                            "Cmd+Q    Quit\n"
                            "Cmd+Z    Undo\n"
                            "Cmd+Shift+Z   Redo")

    def _show_about(self):
        messagebox.showinfo("About Pulse",
                            "Pulse v2.4.1\n"
                            "Project Management for Modern Teams\n\n"
                            "© 2026 Pulse Software Inc.\n"
                            "All rights reserved.")


if __name__ == "__main__":
    PulseApp()
