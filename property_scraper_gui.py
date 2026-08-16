#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GUI launcher for portugal_property_scraper.py."""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


APP_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = APP_DIR / "portugal_property_scraper.py"
SETTINGS_PATH = APP_DIR / "app_settings.json"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
LOGO_PNG = APP_DIR / "assets" / "logo.png"
LOGO_SMALL = APP_DIR / "assets" / "logo_header.png"
LOGO_ICO = APP_DIR / "assets" / "logo.ico"

SITES = ["imovirtual", "idealista", "supercasa", "kyero", "remax", "predimed", "portadafrente", "google_maps"]
LOGIN_NEEDED_SITES = {"idealista", "imovirtual", "google_maps"}
SITE_META = {
    "imovirtual": ("Imovirtual", ""),
    "idealista": ("Idealista", "登录"),
    "supercasa": ("Supercasa", ""),
    "kyero": ("Kyero", ""),
    "remax": ("RE/MAX", ""),
    "predimed": ("Predimed", ""),
    "portadafrente": ("Porta da Frente", ""),
    "google_maps": ("Google 地图", ""),
}

DEFAULT_SETTINGS = {
    "accounts": {site: {"logged_in": False, "last_login": "", "email": ""} for site in SITES},
    "last_email": "",
    "keyword": "",
    "sheet_id": "1o1aJOU63NTO582H0xkK1JRnVyBi1pE7GwpqPvXq5-dM",
    "sheet_name": "找房子",
    "maps_sheet_name": "工作表1",
    "google_places_key": "",
    "drive_folder_id": "1cAud70i5ttESqM79m9JdiT9nNPyT82g0",
    "upload_drive": True,
    "write_sheet": True,
    "google_credentials": "oauth_client.json",
    "google_token": "drive_token.json",
    "service_account": "service_account.json",
    "cdp_url": "",
    "real_chrome": True,
    "browser_visible": True,
    "browser_auto": True,
    "browser_profile": "browser_profile",
}

TXT = {
    "title": "葡萄牙找房",
    "subtitle": "找房采集",
    "nav_home": "采集",
    "nav_settings": "设置",
    "conditions": "找房条件",
    "area": "地区",
    "keyword": "关键词",
    "keyword_hint": "勾选 Google 地图后按这个搜，结果写入工作表1",
    "maps_sheet": "谷歌搜索写入工作表",
    "places_key": "Google Places API Key",
    "type": "类型",
    "buy": "买房",
    "rent": "租房",
    "max_items": "最多房源，0=不限",
    "min_rooms": "最少房间",
    "max_rooms": "最多房间",
    "min_area": "最小面积 m²",
    "max_area": "最大面积 m²",
    "max_pages": "最多搜索页",
    "csv": "CSV 文件",
    "sites": "网站",
    "sites_hint": "Idealista 建议先在设置里登录。",
    "select_all": "全选",
    "select_none": "清空",
    "collect_options": "采集选项",
    "auto_all": "自动一直找完",
    "manual_only": "只用手动链接",
    "strict_area": "严格地区过滤",
    "manual_links": "手动链接，每行一个",
    "seed_placeholder": "在这里粘贴搜索页或房源链接，每行一个",
    "start": "开始采集",
    "stop": "停止",
    "clear": "清空日志",
    "browse": "浏览",
    "open_dir": "打开目录",
    "log": "运行日志",
    "idle": "待命",
    "logging_in": "登录中",
    "running_status": "采集中",
    "done_status": "已完成",
    "stopped_status": "已停止",
    "error_status": "出错",
    "no_script": "找不到采集脚本：",
    "need_site": "至少选择一个网站",
    "cannot_start": "无法启动",
    "running": "开始运行：",
    "login_running": "开始登录：",
    "done": "采集结束，退出码",
    "gui_error": "界面错误",
    "stop_requested": "已请求停止",
    "settings_accounts": "账号管理",
    "settings_sheet": "登记表格",
    "settings_browser": "浏览器",
    "logged_in": "已登录",
    "logged_out": "未登录",
    "login_one": "登录",
    "mark_in": "标记已登录",
    "clear_one": "清除状态",
    "login_needed": "登录未登录的网站",
    "detect_login": "检测登录状态",
    "ask_email": "登录邮箱",
    "save_settings": "保存设置",
    "saved": "设置已保存，下次打开会自动读取。",
    "account_hint": "登录一次后，Cookie 会留在本地浏览器资料里。下次找房不用再登，除非网站掉线或你点了清除。",
    "sheet_hint": "找房结果写入这里的 Google 表格，照片上传到指定云端文件夹。",
    "upload": "上传照片到云端",
    "sheet": "写入表格",
    "sheet_id": "表格 ID",
    "sheet_name": "工作表名",
    "drive_folder": "Drive 文件夹 ID",
    "oauth": "OAuth 客户端 JSON（Desktop 凭证）",
    "token": "登录后的 Token（不要和服务端凭证填同一个文件）",
    "service": "服务账号 JSON（写表格用，可留默认）",
    "real_chrome": "使用真实 Chrome",
    "browser_visible": "显示浏览器窗口",
    "browser_auto": "启用浏览器自动化",
    "cdp_url": "已打开的 Chrome CDP，可留空",
    "welcome": (
        "欢迎使用葡萄牙找房。\n"
        "  1. 第一次请先打开右上角「设置」，登录 Idealista / Google 等账号\n"
        "  2. 登记表格和云端文件夹也在设置里，保存后下次自动带上\n"
        "  3. 回到采集页，选网站，点「开始采集」\n"
        "  4. 勾选 Google 地图并填写关键词，会按工作表1的格式自动登记\n"
    ),
}
DEAL_LABELS = {TXT["buy"]: "sale", TXT["rent"]: "rent"}


class C:
    bg = "#F4F5F7"
    header = "#FFFFFF"
    surface = "#FFFFFF"
    surface2 = "#F3F4F6"
    surface3 = "#E5E7EB"
    line = "#E5E7EB"
    text = "#111827"
    muted = "#6B7280"
    faint = "#9CA3AF"
    accent = "#E11D48"
    accent_h = "#F43F5E"
    accent_d = "#BE123C"
    accent_soft = "#FFF1F2"
    cream = "#FFFFFF"
    danger = "#E11D48"
    danger_h = "#F43F5E"
    ok = "#059669"
    warn = "#D97706"
    info = "#2563EB"
    maps = "#0F766E"
    chip_on = "#FFF1F2"
    chip_off = "#FFFFFF"
    input_bg = "#F9FAFB"
    log_bg = "#111827"
    log_fg = "#E5E7EB"
    nav_on = "#111827"
    nav_off = "#6B7280"


def load_settings() -> dict:
    data = json.loads(json.dumps(DEFAULT_SETTINGS))
    if SETTINGS_PATH.exists():
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        for key, value in raw.items():
            if key == "accounts" and isinstance(value, dict):
                for site in SITES:
                    saved = value.get(site) or {}
                    data["accounts"][site] = {
                        "logged_in": bool(saved.get("logged_in")),
                        "last_login": str(saved.get("last_login") or ""),
                        "email": str(saved.get("email") or ""),
                    }
            else:
                data[key] = value
    return data


def save_settings(data: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _try_dpi() -> None:
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            from ctypes import windll

            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _font(size: int = 10, bold: bool = False, family: str | None = None) -> tuple:
    name = family or "Microsoft YaHei UI"
    return (name, size, "bold") if bold else (name, size)


def load_photo(path: Path, size: int) -> tk.PhotoImage | None:
    if not path.exists():
        return None
    try:
        from PIL import Image, ImageTk

        image = Image.open(path).convert("RGBA")
        image = image.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception:
        try:
            photo = tk.PhotoImage(file=str(path))
            if photo.width() > size:
                photo = photo.subsample(max(1, photo.width() // size), max(1, photo.height() // size))
            return photo
        except Exception:
            return None


class HoverButton(tk.Label):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command,
        *,
        kind: str = "primary",
        width: int = 10,
        **kwargs,
    ) -> None:
        self.command = command
        self.kind = kind
        self._enabled = True
        palette = {
            "primary": (C.accent, C.accent_h, C.cream, "#F3C5CE"),
            "secondary": (C.surface2, C.accent_soft, C.text, C.surface3),
            "ghost": (C.surface, C.surface2, C.text, C.surface2),
            "danger": (C.surface, C.accent_soft, C.accent, C.surface2),
        }
        self.bg, self.hover, self.fg, self.disabled_bg = palette[kind]
        border = C.accent if kind == "danger" else (C.line if kind in {"ghost", "secondary"} else self.bg)
        super().__init__(
            master,
            text=text,
            bg=self.bg,
            fg=self.fg,
            font=_font(9, bold=True),
            padx=14,
            pady=6,
            cursor="hand2",
            width=width,
            highlightthickness=1,
            highlightbackground=border,
            **kwargs,
        )
        self.bind("<Enter>", lambda _e: self._paint(self.hover if self._enabled else self.disabled_bg))
        self.bind("<Leave>", lambda _e: self._paint(self.bg if self._enabled else self.disabled_bg))
        self.bind("<Button-1>", self._click)

    def _paint(self, color: str) -> None:
        self.configure(bg=color)

    def _click(self, _event=None) -> None:
        if self._enabled and self.command:
            self.command()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(
            bg=self.bg if enabled else self.disabled_bg,
            fg=self.fg if enabled else C.faint,
            cursor="hand2" if enabled else "arrow",
        )


class Chip(tk.Frame):
    def __init__(self, master: tk.Misc, title: str, badge: str, variable: tk.BooleanVar) -> None:
        super().__init__(master, bg=C.chip_off, highlightthickness=1, highlightbackground=C.line)
        self.variable = variable
        self.name = tk.Label(self, text=title, font=_font(9), bg=C.chip_off, fg=C.text)
        self.name.pack(side="left", padx=(10, 2 if badge else 10), pady=5)
        self.tag = None
        if badge:
            self.tag = tk.Label(self, text=badge, font=_font(8), bg=C.chip_off, fg=C.accent)
            self.tag.pack(side="left", padx=(0, 10), pady=5)
        for widget in (self, self.name, self.tag):
            if widget is None:
                continue
            widget.bind("<Button-1>", self._toggle)
            widget.configure(cursor="hand2")
        variable.trace_add("write", lambda *_: self.refresh())
        self.refresh()

    def _toggle(self, _event=None) -> None:
        self.variable.set(not self.variable.get())

    def refresh(self) -> None:
        on = self.variable.get()
        bg = C.chip_on if on else C.chip_off
        fg = C.accent if on else C.text
        border = C.accent if on else C.line
        self.configure(bg=bg, highlightbackground=border)
        self.name.configure(bg=bg, fg=fg, font=_font(9, bold=on))
        if self.tag:
            self.tag.configure(bg=bg, fg=C.accent)


class Switch(tk.Frame):
    def __init__(self, master: tk.Misc, text: str, variable: tk.BooleanVar) -> None:
        super().__init__(master, bg=C.surface)
        self.variable = variable
        self.track = tk.Canvas(self, width=34, height=18, bg=C.surface, highlightthickness=0, cursor="hand2")
        self.track.pack(side="left")
        self.label = tk.Label(self, text=text, bg=C.surface, fg=C.text, font=_font(9), cursor="hand2")
        self.label.pack(side="left", padx=(8, 0))
        for widget in (self, self.track, self.label):
            widget.bind("<Button-1>", self._toggle)
        variable.trace_add("write", lambda *_: self.draw())
        self.draw()

    def _toggle(self, _event=None) -> None:
        self.variable.set(not self.variable.get())

    def draw(self) -> None:
        self.track.delete("all")
        on = self.variable.get()
        fill = C.accent if on else C.surface3
        self.track.create_oval(1, 1, 17, 17, fill=fill, outline=fill)
        self.track.create_oval(17, 1, 33, 17, fill=fill, outline=fill)
        self.track.create_rectangle(9, 1, 25, 17, fill=fill, outline=fill)
        knob_x = 18 if on else 2
        self.track.create_oval(knob_x, 2, knob_x + 14, 16, fill=C.cream, outline=C.cream)


class PlaceholderText(tk.Text):
    def __init__(self, master: tk.Misc, placeholder: str, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self._showing = False
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self.show_placeholder()

    def show_placeholder(self) -> None:
        self.delete("1.0", "end")
        self.insert("1.0", self.placeholder)
        self.configure(fg=C.faint)
        self._showing = True

    def _focus_in(self, _event=None) -> None:
        if self._showing:
            self.delete("1.0", "end")
            self.configure(fg=C.text)
            self._showing = False

    def _focus_out(self, _event=None) -> None:
        if not self.get("1.0", "end").strip():
            self.show_placeholder()

    def real_lines(self) -> list[str]:
        if self._showing:
            return []
        return [line.strip() for line in self.get("1.0", "end").splitlines() if line.strip()]


class Segmented(tk.Frame):
    def __init__(self, master: tk.Misc, options: list[str], variable: tk.StringVar) -> None:
        super().__init__(master, bg=C.surface2, highlightthickness=1, highlightbackground=C.line)
        self.variable = variable
        self.buttons: dict[str, tk.Label] = {}
        for option in options:
            label = tk.Label(self, text=option, font=_font(9), padx=12, pady=4, cursor="hand2")
            label.pack(side="left")
            label.bind("<Button-1>", lambda _e, value=option: variable.set(value))
            self.buttons[option] = label
        variable.trace_add("write", lambda *_: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        current = self.variable.get()
        for option, label in self.buttons.items():
            on = option == current
            label.configure(
                bg=C.surface if on else C.surface2,
                fg=C.accent if on else C.muted,
                font=_font(9, bold=on),
            )


class Card(tk.Frame):
    def __init__(self, master: tk.Misc, title: str, hint: str = "") -> None:
        super().__init__(master, bg=C.surface, highlightthickness=1, highlightbackground=C.line)
        head = tk.Frame(self, bg=C.surface)
        head.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(head, text=title, bg=C.surface, fg=C.text, font=_font(10, bold=True)).pack(side="left")
        if hint:
            tk.Label(head, text=hint, bg=C.surface, fg=C.faint, font=_font(8)).pack(side="right")
        self.body = tk.Frame(self, bg=C.surface)
        self.body.pack(fill="both", expand=True, padx=12, pady=(0, 10))


class TextTab(tk.Frame):
    def __init__(self, master: tk.Misc, text: str, command) -> None:
        super().__init__(master, bg=C.header)
        self.active = False
        self.label = tk.Label(self, text=text, bg=C.header, fg=C.nav_off, font=_font(11), cursor="hand2", padx=4)
        self.label.pack()
        self.bar = tk.Frame(self, bg=C.header, height=2)
        self.bar.pack(fill="x", pady=(6, 0))
        for widget in (self, self.label):
            widget.bind("<Button-1>", lambda _e: command())

    def set_active(self, active: bool) -> None:
        self.active = active
        self.label.configure(fg=C.nav_on if active else C.nav_off, font=_font(11, bold=active))
        self.bar.configure(bg=C.accent if active else C.header)


class ScraperGui(tk.Tk):
    def __init__(self) -> None:
        _try_dpi()
        super().__init__()
        self.title(TXT["title"])
        self.geometry("1220x780")
        self.minsize(1080, 700)
        self.configure(bg=C.bg)
        self.settings = load_settings()
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.site_vars: dict[str, tk.BooleanVar] = {}
        self.account_labels: dict[str, tk.Label] = {}
        self._follow_log = True
        self._saved_count = 0
        self._pending_login_sites: list[str] = []
        self._page = "home"
        self._logo_image = None

        self._init_vars()
        self._set_icon()
        self._build_ui()
        self._write_welcome()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._drain_output)

    def _init_vars(self) -> None:
        self.area_var = tk.StringVar(value="Mafra")
        self.keyword_var = tk.StringVar(value=str(self.settings.get("keyword") or ""))
        self.deal_label_var = tk.StringVar(value=TXT["buy"])
        self.min_rooms_var = tk.StringVar(value="")
        self.max_rooms_var = tk.StringVar(value="")
        self.min_area_var = tk.StringVar(value="")
        self.max_area_var = tk.StringVar(value="")
        self.max_listings_var = tk.StringVar(value="0")
        self.max_pages_var = tk.StringVar(value="50")
        self.output_var = tk.StringVar(value="properties_gui.csv")
        self.auto_all_var = tk.BooleanVar(value=True)
        self.no_auto_var = tk.BooleanVar(value=False)
        self.strict_area_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value=TXT["idle"])
        self.stats_var = tk.StringVar(value="尚未开始")
        self.account_summary_var = tk.StringVar(value="")
        self.upload_drive_var = tk.BooleanVar(value=bool(self.settings.get("upload_drive", True)))
        self.write_sheet_var = tk.BooleanVar(value=bool(self.settings.get("write_sheet", True)))
        self.real_chrome_var = tk.BooleanVar(value=bool(self.settings.get("real_chrome", True)))
        self.browser_visible_var = tk.BooleanVar(value=bool(self.settings.get("browser_visible", True)))
        self.browser_auto_var = tk.BooleanVar(value=bool(self.settings.get("browser_auto", True)))
        self.sheet_id_var = tk.StringVar(value=str(self.settings.get("sheet_id") or DEFAULT_SETTINGS["sheet_id"]))
        self.sheet_name_var = tk.StringVar(value=str(self.settings.get("sheet_name") or DEFAULT_SETTINGS["sheet_name"]))
        self.maps_sheet_var = tk.StringVar(value=str(self.settings.get("maps_sheet_name") or DEFAULT_SETTINGS["maps_sheet_name"]))
        self.places_key_var = tk.StringVar(value=str(self.settings.get("google_places_key") or DEFAULT_SETTINGS["google_places_key"]))
        self.drive_folder_var = tk.StringVar(value=str(self.settings.get("drive_folder_id") or DEFAULT_SETTINGS["drive_folder_id"]))
        oauth = str(self.settings.get("google_credentials") or (APP_DIR / "oauth_client.json"))
        token = str(self.settings.get("google_token") or (APP_DIR / "drive_token.json"))
        service = str(self.settings.get("service_account") or (APP_DIR / "service_account.json"))
        if Path(token).name == Path(oauth).name and Path(token).resolve() == Path(oauth).resolve():
            token = str(APP_DIR / "drive_token.json")
        if Path(service).resolve() == Path(oauth).resolve():
            service = str(APP_DIR / "service_account.json")
        self.oauth_var = tk.StringVar(value=oauth)
        self.token_var = tk.StringVar(value=token)
        self.service_var = tk.StringVar(value=service)
        self.cdp_url_var = tk.StringVar(value=str(self.settings.get("cdp_url") or ""))
        self._refresh_account_summary()

    def _set_icon(self) -> None:
        if LOGO_ICO.exists():
            try:
                self.iconbitmap(str(LOGO_ICO))
            except Exception:
                pass
        self._logo_image = load_photo(LOGO_PNG, 32)
        if self._logo_image:
            try:
                self.iconphoto(True, self._logo_image)
            except Exception:
                pass

    def _build_ui(self) -> None:
        self._build_header()
        self.pages = tk.Frame(self, bg=C.bg)
        self.pages.pack(fill="both", expand=True)
        self.home_page = tk.Frame(self.pages, bg=C.bg)
        self.settings_page = tk.Frame(self.pages, bg=C.bg)
        self.home_page.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.settings_page.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._build_home()
        self._build_settings()
        self._build_footer()
        self._bind_shortcuts()
        self._show_page("home")
        self.auto_all_var.trace_add("write", lambda *_: self._sync_auto_all())
        self._sync_auto_all()

    def _build_header(self) -> None:
        bar = tk.Frame(self, bg=C.header, highlightthickness=1, highlightbackground=C.line)
        bar.pack(fill="x")
        header = tk.Frame(bar, bg=C.header)
        header.pack(fill="x", padx=16, pady=8)

        brand = tk.Frame(header, bg=C.header)
        brand.pack(side="left")
        self._header_logo = load_photo(LOGO_SMALL if LOGO_SMALL.exists() else LOGO_PNG, 28)
        if self._header_logo:
            tk.Label(brand, image=self._header_logo, bg=C.header).pack(side="left", padx=(0, 8))
        tk.Label(brand, text=TXT["title"], bg=C.header, fg=C.text, font=_font(13, bold=True)).pack(side="left")

        nav = tk.Frame(header, bg=C.header)
        nav.pack(side="left", padx=28)
        self.nav_home = TextTab(nav, TXT["nav_home"], lambda: self._show_page("home"))
        self.nav_home.pack(side="left", padx=(0, 18))
        self.nav_settings = TextTab(nav, TXT["nav_settings"], lambda: self._show_page("settings"))
        self.nav_settings.pack(side="left")

        right = tk.Frame(header, bg=C.header)
        right.pack(side="right")
        account = tk.Label(
            right,
            textvariable=self.account_summary_var,
            bg=C.header,
            fg=C.muted,
            font=_font(9),
            cursor="hand2",
        )
        account.pack(side="left", padx=(0, 16))
        account.bind("<Button-1>", lambda _e: self._show_page("settings"))
        self.status_dot = tk.Label(right, text="●", bg=C.header, fg=C.warn, font=_font(8))
        self.status_dot.pack(side="left")
        tk.Label(right, textvariable=self.status_var, bg=C.header, fg=C.text, font=_font(9)).pack(side="left", padx=(4, 0))

    def _show_page(self, name: str) -> None:
        if self._page == "settings" and name != "settings":
            self._collect_settings_from_form()
            save_settings(self.settings)
        self._page = name
        if name == "settings":
            self.settings_page.lift()
            self._refresh_account_rows()
        else:
            self.home_page.lift()
        self.nav_home.set_active(name == "home")
        self.nav_settings.set_active(name == "settings")

    def _field(self, parent: tk.Misc, label: str, variable: tk.StringVar, width: int = 16) -> tk.Entry:
        box = tk.Frame(parent, bg=C.surface)
        box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(box, text=label, bg=C.surface, fg=C.muted, font=_font(8)).pack(anchor="w")
        entry = tk.Entry(
            box,
            textvariable=variable,
            bg=C.input_bg,
            fg=C.text,
            insertbackground=C.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=C.line,
            highlightcolor=C.accent,
            font=_font(10),
            width=width,
        )
        entry.pack(fill="x", ipady=3, pady=(2, 0))
        return entry

    def _labeled_entry(self, parent: tk.Misc, label: str, variable: tk.StringVar, browse: bool = False) -> None:
        tk.Label(parent, text=label, bg=C.surface, fg=C.muted, font=_font(8)).pack(anchor="w", pady=(8, 0))
        row = tk.Frame(parent, bg=C.surface)
        row.pack(fill="x", pady=(4, 0))
        tk.Entry(
            row,
            textvariable=variable,
            bg=C.input_bg,
            fg=C.text,
            insertbackground=C.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=C.line,
            highlightcolor=C.accent,
            font=_font(10),
        ).pack(side="left", fill="x", expand=True, ipady=5)
        if browse:
            HoverButton(row, TXT["browse"], lambda: self._browse_into(variable), kind="ghost", width=6).pack(
                side="left", padx=(8, 0)
            )

    def _build_home(self) -> None:
        body = tk.Frame(self.home_page, bg=C.bg)
        body.pack(fill="both", expand=True, padx=14, pady=10)
        pane = tk.PanedWindow(body, orient="horizontal", bg=C.bg, sashwidth=6, sashrelief="flat", bd=0)
        pane.pack(fill="both", expand=True)
        left_wrap = tk.Frame(pane, bg=C.bg)
        right_wrap = tk.Frame(pane, bg=C.bg)
        pane.add(left_wrap, minsize=520, stretch="always")
        pane.add(right_wrap, minsize=420, stretch="always")
        self._build_left(left_wrap)
        self._build_log(right_wrap)

    def _build_left(self, parent: tk.Misc) -> None:
        canvas = tk.Canvas(parent, bg=C.bg, highlightthickness=0)
        scroll = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=C.bg)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _sync(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window, width=canvas.winfo_width())

        inner.bind("<Configure>", _sync)
        canvas.bind("<Configure>", _sync)

        def _wheel(event: tk.Event) -> str | None:
            widget = event.widget
            if isinstance(widget, tk.Misc) and str(widget).startswith(str(canvas)):
                canvas.yview_scroll(int(-event.delta / 120), "units")
                return "break"
            return None

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        self.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"), add="+")

        cond = Card(inner, TXT["conditions"], "谷歌地图按关键词搜")
        cond.pack(fill="x", pady=(0, 8))
        row1 = tk.Frame(cond.body, bg=C.surface)
        row1.pack(fill="x")
        self._field(row1, TXT["area"], self.area_var, 14)
        self._field(row1, TXT["keyword"], self.keyword_var, 18)
        type_box = tk.Frame(row1, bg=C.surface)
        type_box.pack(side="left", padx=(0, 10))
        tk.Label(type_box, text=TXT["type"], bg=C.surface, fg=C.muted, font=_font(8)).pack(anchor="w")
        Segmented(type_box, [TXT["buy"], TXT["rent"]], self.deal_label_var).pack(anchor="w", pady=(4, 0))
        self._field(row1, TXT["max_items"], self.max_listings_var, 10)

        row2 = tk.Frame(cond.body, bg=C.surface)
        row2.pack(fill="x", pady=(8, 0))
        self._field(row2, TXT["min_rooms"], self.min_rooms_var, 10)
        self._field(row2, TXT["max_rooms"], self.max_rooms_var, 10)
        self._field(row2, TXT["min_area"], self.min_area_var, 10)
        self._field(row2, TXT["max_area"], self.max_area_var, 10)

        row3 = tk.Frame(cond.body, bg=C.surface)
        row3.pack(fill="x", pady=(8, 0))
        self._field(row3, TXT["max_pages"], self.max_pages_var, 10)
        csv_box = tk.Frame(row3, bg=C.surface)
        csv_box.pack(side="left", fill="x", expand=True)
        tk.Label(csv_box, text=TXT["csv"], bg=C.surface, fg=C.muted, font=_font(8)).pack(anchor="w")
        csv_row = tk.Frame(csv_box, bg=C.surface)
        csv_row.pack(fill="x", pady=(4, 0))
        tk.Entry(
            csv_row,
            textvariable=self.output_var,
            bg=C.input_bg,
            fg=C.text,
            insertbackground=C.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=C.line,
            highlightcolor=C.accent,
            font=_font(10),
        ).pack(side="left", fill="x", expand=True, ipady=3)
        HoverButton(csv_row, TXT["browse"], self._browse_csv, kind="ghost", width=6).pack(side="left", padx=(8, 0))

        sites = Card(inner, TXT["sites"], TXT["sites_hint"])
        sites.pack(fill="x", pady=(0, 8))
        actions = tk.Frame(sites.body, bg=C.surface)
        actions.pack(fill="x", pady=(0, 8))
        tk.Label(actions, text="点击选择，可多选", bg=C.surface, fg=C.faint, font=_font(8)).pack(side="left")
        link = tk.Label(actions, text=TXT["select_all"], bg=C.surface, fg=C.accent, font=_font(8, bold=True), cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda _e: self._set_all_sites(True))
        tk.Label(actions, text=" · ", bg=C.surface, fg=C.faint, font=_font(8)).pack(side="right")
        link2 = tk.Label(actions, text=TXT["select_none"], bg=C.surface, fg=C.accent, font=_font(8, bold=True), cursor="hand2")
        link2.pack(side="right")
        link2.bind("<Button-1>", lambda _e: self._set_all_sites(False))

        chip_wrap = tk.Frame(sites.body, bg=C.surface)
        chip_wrap.pack(fill="x")
        for idx, site in enumerate(SITES):
            var = tk.BooleanVar(value=(site in {"imovirtual", "google_maps"}))
            self.site_vars[site] = var
            title, badge = SITE_META[site]
            Chip(chip_wrap, title, badge, var).grid(row=idx // 4, column=idx % 4, sticky="we", padx=(0, 6), pady=(0, 6))
        for col in range(4):
            chip_wrap.columnconfigure(col, weight=1)

        options = Card(inner, TXT["collect_options"], "账号和表格在设置里")
        options.pack(fill="x", pady=(0, 8))
        grid = tk.Frame(options.body, bg=C.surface)
        grid.pack(fill="x")
        for idx, (var, text) in enumerate(
            [
                (self.auto_all_var, TXT["auto_all"]),
                (self.no_auto_var, TXT["manual_only"]),
                (self.strict_area_var, TXT["strict_area"]),
            ]
        ):
            cell = tk.Frame(grid, bg=C.input_bg, highlightthickness=1, highlightbackground=C.line)
            cell.grid(row=0, column=idx, sticky="we", padx=(0, 8))
            Switch(cell, text, var).pack(anchor="w", padx=8, pady=6)
            grid.columnconfigure(idx, weight=1)
        tk.Label(options.body, text=TXT["manual_links"], bg=C.surface, fg=C.muted, font=_font(8)).pack(
            anchor="w", pady=(8, 3)
        )
        self.seed_text = PlaceholderText(
            options.body,
            TXT["seed_placeholder"],
            height=3,
            wrap="word",
            bg=C.input_bg,
            fg=C.faint,
            insertbackground=C.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=C.line,
            highlightcolor=C.accent,
            font=_font(9),
        )
        self.seed_text.pack(fill="x")

    def _build_settings(self) -> None:
        canvas = tk.Canvas(self.settings_page, bg=C.bg, highlightthickness=0)
        scroll = tk.Scrollbar(self.settings_page, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=14, pady=10)
        inner = tk.Frame(canvas, bg=C.bg)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _sync(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window, width=canvas.winfo_width())

        inner.bind("<Configure>", _sync)
        canvas.bind("<Configure>", _sync)

        accounts = Card(inner, TXT["settings_accounts"], TXT["account_hint"])
        accounts.pack(fill="x", pady=(0, 12))
        self.account_box = tk.Frame(accounts.body, bg=C.surface)
        self.account_box.pack(fill="x")
        actions = tk.Frame(accounts.body, bg=C.surface)
        actions.pack(fill="x", pady=(10, 0))
        HoverButton(actions, TXT["login_needed"], self._login_missing, kind="primary", width=16).pack(side="left")
        HoverButton(actions, TXT["detect_login"], self._detect_login_status, kind="ghost", width=12).pack(
            side="left", padx=(8, 0)
        )
        tk.Label(
            actions,
            text="这里的登录是网站账号。采集时若弹出验证码，在 Chrome 里点一下即可，和有没有填邮箱无关。",
            bg=C.surface,
            fg=C.faint,
            font=_font(8),
        ).pack(side="left", padx=12)

        sheet = Card(inner, TXT["settings_sheet"], TXT["sheet_hint"])
        sheet.pack(fill="x", pady=(0, 12))
        switches = tk.Frame(sheet.body, bg=C.surface)
        switches.pack(fill="x")
        left = tk.Frame(switches, bg=C.input_bg, highlightthickness=1, highlightbackground=C.line)
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        Switch(left, TXT["sheet"], self.write_sheet_var).pack(anchor="w", padx=10, pady=8)
        right = tk.Frame(switches, bg=C.input_bg, highlightthickness=1, highlightbackground=C.line)
        right.pack(side="left", fill="x", expand=True)
        Switch(right, TXT["upload"], self.upload_drive_var).pack(anchor="w", padx=10, pady=8)
        self._labeled_entry(sheet.body, TXT["sheet_id"], self.sheet_id_var)
        self._labeled_entry(sheet.body, TXT["sheet_name"], self.sheet_name_var)
        self._labeled_entry(sheet.body, TXT["maps_sheet"], self.maps_sheet_var)
        self._labeled_entry(sheet.body, TXT["places_key"], self.places_key_var)
        self._labeled_entry(sheet.body, TXT["drive_folder"], self.drive_folder_var)
        self._labeled_entry(sheet.body, TXT["oauth"], self.oauth_var, browse=True)
        self._labeled_entry(sheet.body, TXT["token"], self.token_var, browse=True)
        self._labeled_entry(sheet.body, TXT["service"], self.service_var, browse=True)

        browser = Card(inner, TXT["settings_browser"], "真实 Chrome 更不容易被拦")
        browser.pack(fill="x", pady=(0, 12))
        brow = tk.Frame(browser.body, bg=C.surface)
        brow.pack(fill="x")
        for idx, (var, text) in enumerate(
            [
                (self.real_chrome_var, TXT["real_chrome"]),
                (self.browser_visible_var, TXT["browser_visible"]),
                (self.browser_auto_var, TXT["browser_auto"]),
            ]
        ):
            cell = tk.Frame(brow, bg=C.input_bg, highlightthickness=1, highlightbackground=C.line)
            cell.grid(row=0, column=idx, sticky="we", padx=(0, 8))
            Switch(cell, text, var).pack(anchor="w", padx=10, pady=8)
            brow.columnconfigure(idx, weight=1)
        self._labeled_entry(browser.body, TXT["cdp_url"], self.cdp_url_var)

        HoverButton(inner, TXT["save_settings"], self._save_settings_clicked, kind="primary", width=12).pack(
            anchor="w", pady=(0, 20)
        )
        self._refresh_account_rows()

    def _refresh_account_rows(self) -> None:
        for child in self.account_box.winfo_children():
            child.destroy()
        self.account_labels.clear()
        for site in SITES:
            info = self.settings["accounts"].get(site, {"logged_in": False, "last_login": "", "email": ""})
            row = tk.Frame(self.account_box, bg=C.input_bg, highlightthickness=1, highlightbackground=C.line)
            row.pack(fill="x", pady=(0, 6))
            title, badge = SITE_META[site]
            left = tk.Frame(row, bg=C.input_bg)
            left.pack(side="left", fill="x", expand=True, padx=10, pady=7)
            name = title if not badge else f"{title}  ·  {badge}"
            tk.Label(left, text=name, bg=C.input_bg, fg=C.text, font=_font(9, bold=True)).pack(anchor="w")
            email = (info.get("email") or "").strip()
            if info.get("logged_in"):
                status = f"已登录  {email}" if email else "已登录（账号已进，邮箱可点「标记已登录」补上）"
                extra = f"    {info.get('last_login')}" if info.get("last_login") else ""
                color = C.ok
            else:
                status = TXT["logged_out"]
                extra = ""
                color = C.faint
            label = tk.Label(left, text=status + extra, bg=C.input_bg, fg=color, font=_font(8))
            label.pack(anchor="w")
            self.account_labels[site] = label
            btns = tk.Frame(row, bg=C.input_bg)
            btns.pack(side="right", padx=10)
            HoverButton(btns, TXT["login_one"], lambda s=site: self.start_login([s]), kind="primary", width=8).pack(
                side="left", padx=4
            )
            HoverButton(btns, TXT["mark_in"], lambda s=site: self._mark_login(s, True), kind="ghost", width=10).pack(
                side="left", padx=4
            )
            HoverButton(btns, TXT["clear_one"], lambda s=site: self._mark_login(s, False), kind="ghost", width=8).pack(
                side="left", padx=4
            )
        self._refresh_account_summary()

    def _build_log(self, parent: tk.Misc) -> None:
        card = tk.Frame(parent, bg=C.surface, highlightthickness=1, highlightbackground=C.line)
        card.pack(fill="both", expand=True, padx=(8, 0))
        head = tk.Frame(card, bg=C.surface)
        head.pack(fill="x", padx=12, pady=(8, 6))
        tk.Label(head, text=TXT["log"], bg=C.surface, fg=C.text, font=_font(10, bold=True)).pack(side="left")
        tk.Label(head, textvariable=self.stats_var, bg=C.surface, fg=C.muted, font=_font(8)).pack(side="right")
        wrap = tk.Frame(card, bg=C.log_bg)
        wrap.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.log = tk.Text(
            wrap,
            wrap="word",
            bg=C.log_bg,
            fg=C.log_fg,
            insertbackground=C.log_fg,
            relief="flat",
            highlightthickness=0,
            font=("Consolas", 9),
            padx=10,
            pady=10,
        )
        scroll = tk.Scrollbar(wrap, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.log.bind("<MouseWheel>", self._on_log_scroll)
        self._init_log_tags()

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=C.header, highlightthickness=1, highlightbackground=C.line)
        footer.pack(fill="x", side="bottom")
        inner = tk.Frame(footer, bg=C.header)
        inner.pack(fill="x", padx=16, pady=8)
        self.start_button = HoverButton(inner, TXT["start"], self.start_scrape, kind="primary", width=12)
        self.start_button.pack(side="left")
        self.stop_button = HoverButton(inner, TXT["stop"], self.stop_scrape, kind="danger", width=8)
        self.stop_button.pack(side="left", padx=(10, 0))
        self.stop_button.set_enabled(False)
        HoverButton(inner, TXT["open_dir"], self._open_output_dir, kind="ghost", width=8).pack(side="right")
        HoverButton(inner, TXT["clear"], self._clear_log, kind="ghost", width=8).pack(side="right", padx=(0, 8))
        tk.Label(inner, text="Ctrl+Enter 采集 · Esc 停止", bg=C.header, fg=C.faint, font=_font(8)).pack(
            side="right", padx=16
        )

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-Return>", lambda _e: self.start_scrape())
        self.bind("<Escape>", lambda _e: self.stop_scrape())

    def _init_log_tags(self) -> None:
        self.log.tag_configure("muted", foreground="#8AA4BE")
        self.log.tag_configure("ok", foreground="#5DCA97")
        self.log.tag_configure("err", foreground="#FF8A80")
        self.log.tag_configure("warn", foreground="#F0C14A")
        self.log.tag_configure("info", foreground="#7EC2FF")
        self.log.tag_configure("maps", foreground="#63D2B2")
        self.log.tag_configure("accent", foreground="#8DC4FF")
        self.log.tag_configure("plain", foreground=C.log_fg)

    def _write_welcome(self) -> None:
        self.log.insert("end", TXT["welcome"], "muted")

    def _log_tag(self, line: str) -> str:
        text = line.lower()
        if any(key in text for key in ["失败", "错误", "error", "traceback", "无法"]):
            return "err"
        if any(key in text for key in ["完成", "成功", "已写入", "已记录", "[记录]"]):
            return "ok"
        if any(key in text for key in ["登录", "验证", "等待"]):
            return "warn"
        if "谷歌地图" in text or "google" in text:
            return "maps"
        if any(key in text for key in ["浏览器", "chrome", "搜索页"]):
            return "info"
        if text.startswith("开始"):
            return "accent"
        return "plain"

    def _set_status(self, text: str, color: str) -> None:
        self.status_var.set(text)
        self.status_dot.configure(fg=color)

    def _set_all_sites(self, value: bool) -> None:
        for var in self.site_vars.values():
            var.set(value)

    def _sync_auto_all(self) -> None:
        if self.auto_all_var.get():
            self.max_listings_var.set("0")

    def _refresh_account_summary(self) -> None:
        accounts = self.settings.get("accounts", {})
        logged = sum(1 for site in SITES if accounts.get(site, {}).get("logged_in"))
        emails = [str(accounts.get(site, {}).get("email") or "") for site in SITES if accounts.get(site, {}).get("email")]
        unique = []
        for email in emails:
            if email not in unique:
                unique.append(email)
        suffix = f"  ·  {unique[0]}" if unique else ""
        if len(unique) > 1:
            suffix += f" 等{len(unique)}个邮箱"
        self.account_summary_var.set(f"已登录 {logged}/{len(SITES)}{suffix}")

    def _ask_email(self, site: str, current: str = "") -> str:
        title = SITE_META.get(site, (site, ""))[0]
        initial = current or str(self.settings.get("last_email") or "")
        email = simpledialog.askstring(
            TXT["ask_email"],
            f"请输入 {title} 登录用的邮箱：\n这样下次能看出当前登的是哪个账号。",
            initialvalue=initial,
            parent=self,
        )
        return (email or "").strip()

    def _write_account(self, site: str, logged_in: bool, email: str = "") -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M") if logged_in else ""
        old = self.settings.get("accounts", {}).get(site, {})
        keep_email = email or (old.get("email") if logged_in else "")
        self.settings.setdefault("accounts", {})
        self.settings["accounts"][site] = {
            "logged_in": logged_in,
            "last_login": now if logged_in else "",
            "email": keep_email if logged_in else "",
        }
        if keep_email:
            self.settings["last_email"] = keep_email
        save_settings(self.settings)

    def _mark_login(self, site: str, logged_in: bool) -> None:
        email = ""
        if logged_in:
            current = str(self.settings.get("accounts", {}).get(site, {}).get("email") or "")
            email = self._ask_email(site, current)
        self._write_account(site, logged_in, email)
        self._refresh_account_rows()

    def _detect_login_status(self) -> None:
        self._append_log("\n正在检测各网站登录状态和邮箱…\n", "info")
        self.update_idletasks()

        def work() -> None:
            try:
                from portugal_property_scraper import detect_login_state

                profile = (APP_DIR / str(self.settings.get("browser_profile") or "browser_profile")).resolve()
                detected = detect_login_state(SITES, self.cdp_url_var.get().strip() or str(self.settings.get("cdp_url") or ""))
                self.output_queue.put(("__LOGIN_DETECT__", detected, str(profile)))
            except Exception as exc:
                self.output_queue.put(f"\n检测登录失败：{exc}\n")

        threading.Thread(target=work, daemon=True).start()

    def _apply_detected_login(self, detected: dict) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        found = 0
        for site, info in detected.items():
            current = self.settings.setdefault("accounts", {}).setdefault(
                site, {"logged_in": False, "last_login": "", "email": ""}
            )
            email = str(info.get("email") or current.get("email") or "")
            if info.get("logged_in"):
                current["logged_in"] = True
                current["last_login"] = current.get("last_login") or now
                if email:
                    current["email"] = email
                    self.settings["last_email"] = email
                found += 1
            elif email:
                current["email"] = email
        save_settings(self.settings)
        self._refresh_account_rows()
        self._append_log(f"检测完成：确认已登录 {found} 个网站。\n", "ok")
        emails = [info.get("email") for info in detected.values() if info.get("email")]
        if emails:
            self._append_log("邮箱：" + "、".join(dict.fromkeys(emails)) + "\n", "ok")
        else:
            self._append_log("没有从页面读到邮箱。可点「标记已登录」手动填写。\n", "warn")

    def _login_missing(self) -> None:
        missing = [site for site in SITES if not self.settings["accounts"].get(site, {}).get("logged_in")]
        if not missing:
            messagebox.showinfo(TXT["settings_accounts"], "选中的网站都已经标记为已登录。")
            return
        self.start_login(missing)

    def _collect_settings_from_form(self) -> None:
        self.settings["upload_drive"] = self.upload_drive_var.get()
        self.settings["write_sheet"] = self.write_sheet_var.get()
        self.settings["real_chrome"] = self.real_chrome_var.get()
        self.settings["browser_visible"] = self.browser_visible_var.get()
        self.settings["browser_auto"] = self.browser_auto_var.get()
        self.settings["sheet_id"] = self.sheet_id_var.get().strip()
        self.settings["sheet_name"] = self.sheet_name_var.get().strip() or "找房子"
        self.settings["maps_sheet_name"] = self.maps_sheet_var.get().strip() or "工作表1"
        self.settings["google_places_key"] = self.places_key_var.get().strip()
        self.settings["drive_folder_id"] = self.drive_folder_var.get().strip()
        self.settings["keyword"] = self.keyword_var.get().strip()
        oauth = self.oauth_var.get().strip() or str(APP_DIR / "oauth_client.json")
        token = self.token_var.get().strip() or str(APP_DIR / "drive_token.json")
        service = self.service_var.get().strip() or str(APP_DIR / "service_account.json")
        if Path(token).resolve() == Path(oauth).resolve():
            token = str(APP_DIR / "drive_token.json")
            self.token_var.set(token)
        if Path(service).resolve() == Path(oauth).resolve():
            service = str(APP_DIR / "service_account.json")
            self.service_var.set(service)
        self.settings["google_credentials"] = oauth
        self.settings["google_token"] = token
        self.settings["service_account"] = service
        self.settings["cdp_url"] = self.cdp_url_var.get().strip()

    def _save_settings_clicked(self) -> None:
        self._collect_settings_from_form()
        save_settings(self.settings)
        self._refresh_account_summary()
        messagebox.showinfo(TXT["nav_settings"], TXT["saved"])

    def _browse_into(self, variable: tk.StringVar) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if path:
            variable.set(path)

    def _browse_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title=TXT["csv"],
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All files", "*.*")],
            initialfile=Path(self.output_var.get() or "properties_gui.csv").name,
        )
        if path:
            self.output_var.set(path)

    def _open_output_dir(self) -> None:
        raw = self.output_var.get().strip() or "outputs"
        path = Path(raw)
        folder = path.parent if path.suffix else path
        if not folder.is_absolute():
            folder = APP_DIR / folder
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os_start = getattr(__import__("os"), "startfile", None)
            if os_start:
                os_start(folder)
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            messagebox.showerror(TXT["cannot_start"], str(exc))

    def _clear_log(self) -> None:
        self.log.delete("1.0", "end")
        self._saved_count = 0
        self.stats_var.set("日志已清空")
        self._write_welcome()

    def _on_log_scroll(self, event) -> None:
        self._follow_log = event.delta < 0
        self.log.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _on_close(self) -> None:
        self._collect_settings_from_form()
        save_settings(self.settings)
        self.destroy()

    def build_command(self, sites: list[str] | None = None) -> list[str]:
        if not SCRIPT_PATH.exists():
            raise FileNotFoundError(TXT["no_script"] + str(SCRIPT_PATH))
        self._collect_settings_from_form()
        sites = sites if sites is not None else [site for site, var in self.site_vars.items() if var.get()]
        if not sites:
            raise ValueError(TXT["need_site"])

        max_listings = self.max_listings_var.get().strip() or "0"
        max_pages = self.max_pages_var.get().strip() or "50"
        if self.auto_all_var.get():
            max_listings = "0"

        cmd = [
            sys.executable,
            str(SCRIPT_PATH),
            "--area",
            self.area_var.get().strip() or "Mafra",
            "--deal",
            DEAL_LABELS[self.deal_label_var.get()],
            "--sites",
            *sites,
            "--max-listings",
            max_listings,
            "--max-search-pages",
            max_pages,
            "--output",
            self.output_var.get().strip() or "properties_gui.csv",
            "--sheet-id",
            self.sheet_id_var.get().strip() or DEFAULT_SETTINGS["sheet_id"],
            "--sheet-name",
            self.sheet_name_var.get().strip() or DEFAULT_SETTINGS["sheet_name"],
            "--maps-sheet-name",
            self.maps_sheet_var.get().strip() or DEFAULT_SETTINGS["maps_sheet_name"],
            "--google-places-key",
            self.places_key_var.get().strip() or DEFAULT_SETTINGS["google_places_key"],
            "--drive-parent-folder-id",
            self.drive_folder_var.get().strip() or DEFAULT_SETTINGS["drive_folder_id"],
            "--google-credentials",
            self.oauth_var.get().strip() or "oauth_client.json",
            "--google-token",
            self.token_var.get().strip() or "drive_token.json",
            "--service-account",
            self.service_var.get().strip() or "service_account.json",
            "--browser-profile",
            str((APP_DIR / str(self.settings.get("browser_profile") or "browser_profile")).resolve()),
        ]
        keyword = self.keyword_var.get().strip()
        if keyword:
            cmd.extend(["--keyword", keyword])

        optional_pairs = [
            ("--min-rooms", self.min_rooms_var.get()),
            ("--max-rooms", self.max_rooms_var.get()),
            ("--min-area", self.min_area_var.get()),
            ("--max-area", self.max_area_var.get()),
        ]
        for flag, value in optional_pairs:
            value = value.strip()
            if value:
                cmd.extend([flag, value])
        if self.upload_drive_var.get():
            cmd.append("--upload-drive")
        if not self.write_sheet_var.get():
            cmd.append("--no-write-sheet")
        if self.no_auto_var.get():
            cmd.append("--no-auto-search")
        if not self.strict_area_var.get():
            cmd.append("--no-strict-area")
        if not self.browser_auto_var.get():
            cmd.extend(["--browser-mode", "off"])
        if not self.browser_visible_var.get():
            cmd.append("--no-browser-visible")
        cmd.extend(["--browser-backend", "cdp" if self.real_chrome_var.get() else "playwright"])
        cdp_url = self.cdp_url_var.get().strip()
        if cdp_url:
            parsed_host, parsed_port = "127.0.0.1", 9222
            try:
                from urllib.parse import urlparse

                parsed = urlparse(cdp_url)
                parsed_host = parsed.hostname or "127.0.0.1"
                parsed_port = parsed.port or 9222
            except Exception:
                pass
            import socket as _socket

            alive = False
            try:
                with _socket.create_connection((parsed_host, parsed_port), timeout=0.4):
                    alive = True
            except OSError:
                alive = False
            if alive:
                cmd.extend(["--cdp-url", cdp_url])
            else:
                print("CDP 未在运行，采集时会自动新开 Chrome")
        for url in self.seed_text.real_lines():
            cmd.extend(["--seed-url", url])
        return cmd

    def _set_running(self, running: bool, mode: str = "scrape") -> None:
        self.start_button.set_enabled(not running)
        self.stop_button.set_enabled(running)
        if running:
            if mode == "login":
                self._set_status(TXT["logging_in"], C.warn)
                self.stats_var.set("请在 Chrome 里完成登录")
            else:
                self._set_status(TXT["running_status"], C.accent)
                self.stats_var.set("正在采集…")
        elif self.status_var.get() not in {TXT["done_status"], TXT["stopped_status"], TXT["error_status"]}:
            self._set_status(TXT["idle"], C.warn)

    def _append_log(self, text: str, tag: str | None = None) -> None:
        self.log.insert("end", text, tag or self._log_tag(text))
        if self._follow_log:
            self.log.see("end")
        if "[记录]" in text or "已完成并写入" in text:
            self._saved_count += 1
            self.stats_var.set(f"已保存 {self._saved_count} 条")
        if "共 " in text and "条" in text:
            self.stats_var.set(text.strip().strip("[]"))

    def start_scrape(self) -> None:
        if self.process and self.process.poll() is None:
            return
        selected = [site for site, var in self.site_vars.items() if var.get()]
        missing = [
            SITE_META[site][0]
            for site in selected
            if site in LOGIN_NEEDED_SITES and not self.settings["accounts"].get(site, {}).get("logged_in")
        ]
        if missing:
            go = messagebox.askyesnocancel(
                TXT["settings_accounts"],
                "这些网站还没确认登录（搜房更容易被拦）：\n"
                + "、".join(missing)
                + "\n\n选「是」去设置里登录，选「否」仍然开始采集。",
            )
            if go is None:
                return
            if go:
                self._show_page("settings")
                return
        try:
            cmd = self.build_command()
        except Exception as exc:
            messagebox.showerror(TXT["cannot_start"], str(exc))
            return
        self._show_page("home")
        self._follow_log = True
        self._saved_count = 0
        self._pending_login_sites = []
        self._append_log("\n" + TXT["running"] + "\n", "accent")
        self._append_log(" ".join(cmd) + "\n\n", "muted")
        self._set_running(True, "scrape")
        threading.Thread(target=self._run_process, args=(cmd,), daemon=True).start()

    def start_login(self, sites: list[str]) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showinfo(TXT["settings_accounts"], "当前还有任务在跑，请先停止再登录。")
            return
        profile = (APP_DIR / str(self.settings.get("browser_profile") or "browser_profile")).resolve()
        names = "、".join(SITE_META.get(site, (site, ""))[0] for site in sites)
        try:
            from portugal_property_scraper import open_login_browser

            opened = open_login_browser(sites, profile)
        except Exception as exc:
            self._append_log(f"\n无法打开浏览器登录：{exc}\n", "err")
            messagebox.showerror(
                "无法打开浏览器登录",
                "没能打开 Chrome / Edge。\n\n"
                "请检查：\n"
                "1. 已安装 Google Chrome 或 Microsoft Edge\n"
                "2. 先关掉占用同一资料目录的旧 Chrome 窗口\n"
                "3. 也可以双击 start_chrome_for_login.bat 手动打开\n\n"
                f"详细错误：{exc}",
            )
            return
        self.settings["cdp_url"] = opened["cdp_url"]
        self.cdp_url_var.set(opened["cdp_url"])
        save_settings(self.settings)
        self._show_page("home")
        self._follow_log = True
        self._append_log("\n已打开登录浏览器\n", "ok")
        self._append_log(f"网站：{names}\n", "warn")
        self._append_log(f"地址：{' | '.join(opened['urls'])}\n", "muted")
        self._append_log("请在弹出的 Chrome 里完成登录，然后回设置页点「标记已登录」。\n", "warn")
        self._append_log("如果没看到窗口，请看任务栏有没有闪动的 Chrome / Edge。\n", "muted")
        messagebox.showinfo(
            "请在浏览器里登录",
            f"已打开 {names} 的登录页。\n\n"
            "1. 在弹出的 Chrome 里完成登录和验证码\n"
            "2. 回到软件设置页，点「检测登录状态」读出邮箱\n"
            "   或点「标记已登录」手动填写邮箱\n"
            "3. 然后再开始采集\n\n"
            "窗口如果被挡住，请看任务栏。",
        )
        shared = self._ask_email(sites[0], str(self.settings.get("last_email") or ""))
        if shared:
            for site in sites:
                self._write_account(site, True, shared)
            self._refresh_account_rows()
            self._append_log(f"已记录登录邮箱：{shared}\n", "ok")

    def _run_process(self, cmd: list[str]) -> None:
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.output_queue.put(line)
            code = self.process.wait()
            self.output_queue.put(f"\n[{TXT['title']}] {TXT['done']} {code}\n")
            self.output_queue.put("__GUI_CODE__" + str(code))
        except Exception as exc:
            self.output_queue.put(f"\n[{TXT['gui_error']}] {exc}\n")
            self.output_queue.put("__GUI_CODE__1")
        finally:
            self.output_queue.put("__GUI_DONE__")

    def stop_scrape(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.output_queue.put("\n[" + TXT["title"] + "] " + TXT["stop_requested"] + "\n")
            self._set_status(TXT["stopped_status"], C.danger)
            self._pending_login_sites = []

    def _finish_login_if_needed(self, code: str) -> None:
        if code == "0" and self._pending_login_sites:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            for site in self._pending_login_sites:
                self.settings.setdefault("accounts", {})
                self.settings["accounts"][site] = {"logged_in": True, "last_login": now}
            save_settings(self.settings)
            self._append_log(f"\n已保存登录状态：{', '.join(self._pending_login_sites)}\n下次采集会直接使用本地浏览器资料，不用重新登录。\n", "ok")
            self._refresh_account_summary()
        self._pending_login_sites = []

    def _drain_output(self) -> None:
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, tuple) and item and item[0] == "__LOGIN_DETECT__":
                self._apply_detected_login(item[1])
                continue
            if item == "__GUI_DONE__":
                self._set_running(False)
                continue
            if item.startswith("__GUI_CODE__"):
                code = item.replace("__GUI_CODE__", "")
                self._finish_login_if_needed(code)
                if code == "0":
                    self._set_status(TXT["done_status"], C.ok)
                elif self.status_var.get() != TXT["stopped_status"]:
                    self._set_status(TXT["error_status"], C.danger)
                continue
            self._append_log(item)
        self.after(120, self._drain_output)


if __name__ == "__main__":
    app = ScraperGui()
    app.mainloop()
