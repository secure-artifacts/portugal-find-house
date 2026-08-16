#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
葡萄牙房源采集脚本

功能：
- 根据地区、房间数、面积等条件生成葡萄牙房产网站搜索页。
- 从搜索页发现房源链接，进入房源页提取名称、信息、联系方式、网址、照片。
- 可下载照片到本地，也可上传到 Google Drive，并把云端文件夹地址写入 CSV 表格。
- 支持真实 Chrome / 登录会话，绕开普通脚本请求被 403/验证码拦截的问题。
- 支持 Google 地图 / Google 搜索房地产结果。

注意：
- 很多网站会隐藏电话或要求登录/点击后才显示，脚本只能抓取页面 HTML 中公开可见的信息。
- 房产网站结构经常变化；如果自动搜索不理想，请把搜索结果页或房源页用 --seed-url 传入。
- 反爬处理应使用浏览器登录，不要用普通 HTTP 硬刷。Idealista 等站点几乎必须先登录。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import mimetypes
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

import requests


class BrowserRequiredError(RuntimeError):
    pass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_SITES = [
    "idealista",
    "imovirtual",
    "supercasa",
    "kyero",
    "remax",
    "predimed",
    "portadafrente",
    "google_maps",
]

KYERO_LOCATION_IDS = {
    "coimbra": ("coimbra-district", "57113"),
    "lisboa": ("lisbon-region", "55529"),
    "lisbon": ("lisbon-region", "55529"),
    "porto": ("porto-district", "57304"),
    "faro": ("algarve", "55539"),
    "algarve": ("algarve", "55539"),
    "setubal": ("setubal-district", "57421"),
    "setúbal": ("setubal-district", "57421"),
    "madeira": ("madeira", "55736"),
    "azores": ("azores", "55535"),
}

RENT_SUPPORTED_SITES = {
    "idealista",
    "imovirtual",
    "supercasa",
    "kyero",
    "google_maps",
    "remax",
    "predimed",
    "portadafrente",
}

AREA_ALIASES = {
    "coimbra": [
        "coimbra",
        "santo antónio dos olivais",
        "santo antonio dos olivais",
        "celas",
        "sé nova",
        "se nova",
        "almedina",
        "santa clara",
        "eiras",
        "são martinho do bispo",
        "sao martinho do bispo",
        "ribeira de frades",
        "ceira",
        "torres do mondego",
        "assafarge",
        "antuzede",
        "traz-de-vilela",
        "norton de matos",
        "solum",
    ],
    "mafra": ["mafra", "ericeira", "malveira", "venda do pinheiro", "igreja nova", "cheleiros", "milharado"],
    "lisboa": [
        "lisboa",
        "lisbon",
        "ajuda",
        "alcantara",
        "alcântara",
        "alvalade",
        "areeiro",
        "arroios",
        "avenidas novas",
        "beato",
        "belem",
        "belém",
        "benfica",
        "campo de ourique",
        "campolide",
        "carnide",
        "estrela",
        "lumiar",
        "marvila",
        "misericordia",
        "misericórdia",
        "olivais",
        "parque das nacoes",
        "parque das nações",
        "penha de franca",
        "penha de frança",
        "santa clara",
        "santa maria maior",
        "santo antonio",
        "santo antónio",
        "sao domingos de benfica",
        "são domingos de benfica",
        "sao vicente",
        "são vicente",
        "telheiras",
        "alfama",
        "chiado",
        "bairro alto",
        "baixa",
        "graca",
        "graça",
        "anjos",
        "intendente",
        "saldanha",
        "campo grande",
        "entrecampos",
        "restelo",
    ],
    "porto": ["porto"],
}
AREA_ALIASES["lisbon"] = AREA_ALIASES["lisboa"]

IMOVIRTUAL_LOCATIONS = {
    "lisboa": "lisboa/lisboa",
    "lisbon": "lisboa/lisboa",
    "porto": "porto/porto",
    "coimbra": "coimbra/coimbra",
    "mafra": "lisboa/mafra",
    "loures": "lisboa/loures",
    "sintra": "lisboa/sintra",
    "cascais": "lisboa/cascais",
    "oeiras": "lisboa/oeiras",
    "amadora": "lisboa/amadora",
    "odivelas": "lisboa/odivelas",
    "setubal": "setubal/setubal",
    "setúbal": "setubal/setubal",
    "faro": "faro/faro",
}

OTHER_AREA_HINTS = [
    "porto",
    "viseu",
    "faro",
    "coimbra",
    "braga",
    "aveiro",
    "madeira",
    "portimao",
    "portimão",
    "gondomar",
    "trofa",
    "ermesinde",
    "esmoriz",
    "cantanhede",
    "serta",
    "sertã",
    "leiria",
    "evora",
    "évora",
    "vila-do-conde",
    "rio-tinto",
    "aguas-santas",
    "quarteira",
    "vilamoura",
    "algarve",
    "matosinhos",
    "gaia",
    "maia",
    "valongo",
    "paranhos",
    "ramalde",
    "bonfim",
    "guimaraes",
    "guimarães",
]

DEFAULT_DRIVE_PARENT_FOLDER_ID = "1cAud70i5ttESqM79m9JdiT9nNPyT82g0"
DEFAULT_SHEET_ID = "1o1aJOU63NTO582H0xkK1JRnVyBi1pE7GwpqPvXq5-dM"
DEFAULT_SHEET_NAME = "找房子"
DEFAULT_MAPS_SHEET_NAME = "工作表1"
DEFAULT_PLACES_API_KEY = ""
PLACE_HEADERS = [
    "商家名称",
    "地址",
    "Google地图链接",
    "电话",
    "网站",
    "评分",
    "评价数量",
    "营业状态",
    "营业时间",
    "纬度",
    "经度",
    "Place ID",
    "商家类型",
    "照片文件夹",
    "照片链接",
    "搜索关键词",
    "搜索地区",
    "导出时间",
]
WEEKDAY_ZH = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
}
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SITE_DOMAINS = {
    "idealista": "idealista.pt",
    "imovirtual": "imovirtual.com",
    "supercasa": "supercasa.pt",
    "kyero": "kyero.com",
    "remax": "remax.pt",
    "predimed": "predimed.pt",
    "portadafrente": "portadafrente.com",
    "google_maps": "google.com",
}

LISTING_HINTS = {
    "idealista.pt": ["/imovel/"],
    "imovirtual.com": ["/anuncio/"],
    "supercasa.pt": ["/venda-", "/arrendamento-", "/i"],
    "kyero.com": ["/property/", "/en/property/"],
    "remax.pt": ["/imoveis/"],
    "predimed.pt": ["/Imovel/", "/imovel/"],
    "portadafrente.com": ["/imoveis/"],
    "google.com": ["/maps/place/", "/maps/search/"],
    "google.pt": ["/maps/place/", "/maps/search/"],
}

SITE_LOGIN_URLS = {
    "idealista": "https://www.idealista.pt/login",
    "imovirtual": "https://www.imovirtual.com/pt/konto/login",
    "supercasa": "https://supercasa.pt/login",
    "kyero": "https://www.kyero.com/en/users/sign_in",
    "remax": "https://www.remax.pt/pt/login",
    "predimed": "https://predimed.pt/Login",
    "portadafrente": "https://www.portadafrente.com/login",
    "google_maps": "https://accounts.google.com/ServiceLogin?hl=pt-PT",
}

SITE_ACCOUNT_URLS = {
    "idealista": "https://www.idealista.pt/user",
    "imovirtual": "https://www.imovirtual.com/pt/konto",
    "supercasa": "https://supercasa.pt/",
    "kyero": "https://www.kyero.com/en/users/edit",
    "remax": "https://www.remax.pt/pt/",
    "predimed": "https://predimed.pt/",
    "portadafrente": "https://www.portadafrente.com/",
    "google_maps": "https://myaccount.google.com/",
}

SITE_COOKIE_DOMAINS = {
    "idealista": ["idealista.pt"],
    "imovirtual": ["imovirtual.com"],
    "supercasa": ["supercasa.pt"],
    "kyero": ["kyero.com"],
    "remax": ["remax.pt"],
    "predimed": ["predimed.pt"],
    "portadafrente": ["portadafrente.com"],
    "google_maps": ["google.com", "google.pt"],
}

EMAIL_SKIP = (
    "example.com",
    "sentry.io",
    "wixpress.com",
    "schema.org",
    "idealista.pt",
    "imovirtual.com",
    "supercasa.pt",
    "kyero.com",
    "remax.pt",
    "predimed.pt",
    "portadafrente.com",
    "google.com",
    "gstatic.com",
    "w3.org",
)


def find_browser_path() -> str | None:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        str(Path.home() / "AppData/Local/Microsoft/Edge/Application/msedge.exe"),
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def pick_free_port(start: int = 9222, limit: int = 20) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("找不到可用的浏览器调试端口")


def login_urls_for(sites: list[str]) -> list[str]:
    urls: list[str] = []
    for site in sites:
        url = SITE_LOGIN_URLS.get(site)
        if url and url not in urls:
            urls.append(url)
    return urls


def open_login_browser(sites: list[str], profile_dir: str | Path, port: int | None = None) -> dict:
    browser_path = find_browser_path()
    if not browser_path:
        raise RuntimeError(
            "找不到 Chrome 或 Edge。请先安装 Google Chrome，"
            "或在设置里填写已打开的 Chrome CDP 地址。"
        )
    profile = Path(profile_dir).expanduser().resolve()
    profile.mkdir(parents=True, exist_ok=True)
    urls = login_urls_for(sites) or ["https://www.idealista.pt/login"]
    if port is None:
        port = pick_free_port()
    cmd = [
        browser_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--new-window",
        urls[0],
    ]
    for extra in urls[1:]:
        cmd.append(extra)
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    print(f"[登录] 正在打开浏览器：{browser_path}", flush=True)
    print(f"[登录] 资料目录：{profile}", flush=True)
    print(f"[登录] 登录页：{' | '.join(urls)}", flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    if not wait_for_port("127.0.0.1", port, timeout=20):
        # Chrome sometimes attaches slowly; the window may still be visible.
        print("[登录] 调试端口还没就绪，但浏览器窗口应该已经打开。请看任务栏。", flush=True)
    return {
        "pid": proc.pid,
        "port": port,
        "cdp_url": f"http://127.0.0.1:{port}",
        "profile": str(profile),
        "urls": urls,
        "browser": browser_path,
    }


def extract_account_emails(text: str) -> list[str]:
    found = re.findall(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", text or "", flags=re.I)
    emails: list[str] = []
    for raw in found:
        email = raw.strip(".,;:()<>\"' ").lower()
        if any(skip in email for skip in EMAIL_SKIP):
            continue
        if email not in emails:
            emails.append(email)
    return emails


def detect_login_state(sites: list[str], cdp_url: str = "") -> dict[str, dict]:
    """Read current Chrome session and return {site: {logged_in, email}}."""
    result = {site: {"logged_in": False, "email": ""} for site in sites}
    target = (cdp_url or "").strip()
    if target:
        parsed = urlparse(target)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9222
        if not wait_for_port(host, port, timeout=0.4):
            target = ""
    if not target:
        return result
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return result
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.connect_over_cdp(target)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        cookies = []
        try:
            cookies = context.cookies()
        except Exception:
            cookies = []
        page = context.pages[0] if context.pages else context.new_page()
        for site in sites:
            domains = SITE_COOKIE_DOMAINS.get(site, [])
            site_cookies = [
                cookie
                for cookie in cookies
                if any(domain in str(cookie.get("domain") or "") for domain in domains)
            ]
            email = ""
            for cookie in site_cookies:
                emails = extract_account_emails(str(cookie.get("value") or ""))
                if emails:
                    email = emails[0]
                    break
            logged_in = False
            account_url = SITE_ACCOUNT_URLS.get(site)
            if account_url:
                try:
                    page.goto(account_url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(1200)
                    html = page.content()
                    title = (page.title() or "").lower()
                    current = (page.url or "").lower()
                    emails = extract_account_emails(html)
                    if emails:
                        email = emails[0]
                    still_login = any(
                        token in current
                        for token in ("/login", "signin", "sign-in", "sign_in", "accounts.google.com/servicelogin")
                    )
                    logged_in = bool(email) or (not still_login and len(site_cookies) >= 2)
                    if "login" in title and not email:
                        logged_in = False
                except Exception:
                    logged_in = bool(email) or len(site_cookies) >= 4
            else:
                logged_in = bool(email) or len(site_cookies) >= 4
            result[site] = {"logged_in": logged_in, "email": email}
        return result
    except Exception as exc:
        print(f"[登录] 检测登录状态失败：{exc}", flush=True)
        return result
    finally:
        try:
            playwright.stop()
        except Exception:
            pass

BROWSER_REQUIRED_HOSTS = (
    "idealista.pt",
    "kyero.com",
    "supercasa.pt",
    "google.com",
    "google.pt",
)

CHALLENGE_TITLES = [
    "just a moment",
    "attention required",
    "access denied",
    "pardon our interruption",
    "unusual traffic",
    "checking your browser",
]

CHALLENGE_BODY = [
    "cf_chl",
    "cf-challenge",
    "cf-browser-verification",
    "captcha-delivery",
    "px-captcha",
    "please verify you are a human",
    "enable javascript and cookies",
    "checking your browser before accessing",
    "verifica que no eres un robot",
    "não sou um robot",
    "confirme que é humano",
]

LISTING_READY_HINTS = [
    "/imovel/",
    "/anuncio/",
    "/en/property/",
    "og:title",
    "application/ld+json",
    "quartos",
    "tipologia",
    "m²",
    "m2",
]

COOKIE_BUTTON_SELECTORS = [
    "#didomi-notice-agree-button",
    "#onetrust-accept-btn-handler",
    "button#onetrust-accept-btn-handler",
    "[data-testid='uc-accept-all-button']",
    "button[aria-label*='Aceitar']",
    "button[aria-label*='Accept']",
    "button:has-text('Aceitar todos')",
    "button:has-text('Aceitar cookies')",
    "button:has-text('Aceitar')",
    "button:has-text('Accept all')",
    "button:has-text('Accept')",
    "button:has-text('Concordo')",
    "button:has-text('I agree')",
    "button:has-text('Got it')",
    "button:has-text('Concordar')",
]


@dataclass
class Listing:
    source: str
    name: str
    info: str
    contact: str
    url: str
    photo_cloud_folder: str
    photo_local_folder: str
    price: str
    rooms: str
    area: str
    location: str
    image_count: int


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.in_title = False
        self.meta: dict[str, str] = {}
        self.links: list[tuple[str, str]] = []
        self.images: list[str] = []
        self.srcsets: list[str] = []
        self.json_ld: list[str] = []
        self._in_json_ld = False
        self._json_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): v or "" for k, v in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content")
            if key and content:
                self.meta[key.lower()] = html.unescape(content).strip()
        elif tag == "a":
            href = attrs_dict.get("href")
            text = attrs_dict.get("title") or attrs_dict.get("aria-label") or ""
            if href:
                self.links.append((href, html.unescape(text).strip()))
        elif tag == "img":
            src = attrs_dict.get("src") or attrs_dict.get("data-src") or attrs_dict.get("data-original")
            if src:
                self.images.append(src)
            srcset = attrs_dict.get("srcset") or attrs_dict.get("data-srcset")
            if srcset:
                self.srcsets.append(srcset)
        elif tag == "script":
            script_type = attrs_dict.get("type", "").lower()
            if "ld+json" in script_type:
                self._in_json_ld = True
                self._json_buf = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            text = "".join(self._json_buf).strip()
            if text:
                self.json_ld.append(text)

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._in_json_ld:
            self._json_buf.append(data)


def slugify(value: str, fallback: str = "item") -> str:
    value = re.sub(r"[^\w\-\.]+", "-", value.strip(), flags=re.UNICODE).strip("-")
    return value[:80] or fallback


def clean_text(value: str, limit: int = 500) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def fetch(session: requests.Session, url: str, pause: float) -> str:
    time.sleep(pause)
    response = session.get(url, timeout=30)
    if response.status_code == 403 and ("Just a moment" in response.text or "cf_chl" in response.text or "Cloudflare" in response.text):
        raise BrowserRequiredError("网站需要浏览器验证/Cloudflare")
    if response.status_code == 403:
        raise BrowserRequiredError("网站拒绝普通脚本访问，尝试使用浏览器自动化")
    response.raise_for_status()
    return response.text


def is_google_host(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return "google." in host or host.endswith("goo.gl")


def is_google_maps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return ("google." in host and "/maps" in path) or host.endswith("goo.gl")


def is_google_search_url(url: str) -> bool:
    parsed = urlparse(url)
    return "google." in parsed.netloc.lower() and parsed.path.startswith("/search")


def needs_browser(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(item in host for item in BROWSER_REQUIRED_HOSTS) or is_google_host(url)


def page_has_listing_content(content: str) -> bool:
    text = content or ""
    if any(hint in text.lower() for hint in LISTING_READY_HINTS):
        return True
    if "€" in text and ("T1" in text or "T2" in text or "T3" in text or "T4" in text):
        return True
    return False


def page_looks_blocked(title: str, content: str) -> bool:
    title_l = (title or "").lower()
    if any(marker in title_l for marker in CHALLENGE_TITLES):
        return not page_has_listing_content(content)
    head = (content or "")[:12000].lower()
    if any(marker in head for marker in CHALLENGE_BODY):
        return not page_has_listing_content(content)
    return False


def unwrap_google_url(url: str) -> str:
    parsed = urlparse(url)
    if "google." not in parsed.netloc.lower():
        return url
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in ("q", "url", "u"):
        value = params.get(key, "")
        if value.startswith("http://") or value.startswith("https://"):
            return value
    if parsed.path.startswith("/url") or parsed.path.startswith("/imgres"):
        for key in ("q", "url", "imgurl"):
            value = params.get(key, "")
            if value.startswith("http://") or value.startswith("https://"):
                return value
    return url


def wait_for_port(host: str, port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


class BrowserFetcher:
    def __init__(
        self,
        visible: bool,
        profile_dir: Path,
        wait_seconds: int,
        backend: str = "cdp",
        cdp_url: str | None = None,
    ) -> None:
        self.visible = visible
        self.profile_dir = Path(profile_dir).expanduser().resolve()
        self.wait_seconds = wait_seconds
        self.backend = backend
        self.cdp_url = (cdp_url or "").strip() or None
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._chrome_proc: subprocess.Popen[str] | None = None
        self._attached = bool(self.cdp_url)
        self._keep_open = False

    def _browser_path(self) -> str | None:
        return find_browser_path()

    def _start_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("未安装 Playwright，请运行：python -m pip install playwright") from exc
        if not self._playwright:
            self._playwright = sync_playwright().start()
        return self._playwright

    def _connect_cdp(self, cdp_url: str) -> None:
        playwright = self._start_playwright()
        self._browser = playwright.chromium.connect_over_cdp(cdp_url)
        if self._browser.contexts:
            self._context = self._browser.contexts[0]
        else:
            self._context = self._browser.new_context(locale="pt-PT", viewport={"width": 1365, "height": 900})
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        print(f"[浏览器] 已连接到真实 Chrome：{cdp_url}", flush=True)

    def _launch_real_chrome(self) -> None:
        browser_path = self._browser_path()
        if not browser_path:
            raise RuntimeError("找不到 Chrome/Edge，无法使用真实浏览器模式")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        if self.cdp_url and "://" in self.cdp_url:
            parsed = urlparse(self.cdp_url)
            port = parsed.port or 9222
            existing = f"http://127.0.0.1:{port}"
            if wait_for_port("127.0.0.1", port, timeout=0.4):
                print(f"[浏览器] 连接到已打开的 Chrome：{existing}", flush=True)
                self._attached = True
                self._connect_cdp(existing)
                return
        port = pick_free_port()
        launch_cmd = [
            browser_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--lang=pt-PT",
            "--new-window",
            "about:blank",
        ]
        if not self.visible:
            launch_cmd.append("--headless=new")
        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        print(f"[浏览器] 启动真实 Chrome，资料目录：{self.profile_dir}", flush=True)
        self._chrome_proc = subprocess.Popen(
            launch_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        if not wait_for_port("127.0.0.1", port, timeout=25):
            raise RuntimeError(
                f"Chrome 没有成功打开调试端口。请先关掉所有占用资料目录的 Chrome 窗口，再试一次。"
            )
        self._connect_cdp(f"http://127.0.0.1:{port}")

    def _launch_playwright_persistent(self) -> None:
        playwright = self._start_playwright()
        launch_args = {
            "headless": not self.visible,
            "viewport": {"width": 1365, "height": 900},
            "locale": "pt-PT",
        }
        browser_path = self._browser_path()
        if browser_path:
            launch_args["executable_path"] = browser_path
        profile_candidates = [self.profile_dir]
        runtime_profile = self.profile_dir.parent / f"{self.profile_dir.name}_runtime_{os.getpid()}_{int(time.time())}"
        profile_candidates.append(runtime_profile)
        last_error: Exception | None = None
        for profile_dir in profile_candidates:
            try:
                profile_dir.mkdir(parents=True, exist_ok=True)
                self._context = playwright.chromium.launch_persistent_context(
                    str(profile_dir),
                    **launch_args,
                )
                if profile_dir != self.profile_dir:
                    print(f"[浏览器] 默认资料目录被占用，已改用临时目录：{profile_dir}", flush=True)
                break
            except Exception as exc:
                last_error = exc
                print(f"[浏览器] 启动失败，资料目录可能被占用：{profile_dir}", flush=True)
        if not self._context:
            raise RuntimeError(f"浏览器启动失败：{last_error}")
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

    def start(self) -> None:
        if self._page:
            return
        if self.cdp_url:
            parsed = urlparse(self.cdp_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 9222
            if wait_for_port(host, port, timeout=0.6):
                try:
                    self._attached = True
                    self._connect_cdp(self.cdp_url)
                    return
                except Exception as exc:
                    print(f"[浏览器] 连接已有 Chrome 失败：{exc}，改为重新启动", flush=True)
                    self._attached = False
            else:
                print(f"[浏览器] {self.cdp_url} 没有在运行，改为启动新的 Chrome", flush=True)
            self.cdp_url = None
        if self.backend == "cdp":
            try:
                self._launch_real_chrome()
                return
            except Exception as exc:
                print(f"[浏览器] 真实 Chrome 启动失败，回退 Playwright：{exc}", flush=True)
        self._launch_playwright_persistent()

    def close(self) -> None:
        if self._keep_open:
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
            self._playwright = None
            self._browser = None
            self._context = None
            self._page = None
            print("[浏览器] 登录窗口保持打开，不会自动关闭。", flush=True)
            return
        if self._attached:
            if self._playwright:
                self._playwright.stop()
            self._playwright = None
            self._browser = None
            self._context = None
            self._page = None
            return
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._chrome_proc and self._chrome_proc.poll() is None:
            self._chrome_proc.terminate()
            try:
                self._chrome_proc.wait(timeout=8)
            except Exception:
                self._chrome_proc.kill()
        self._chrome_proc = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None

    def dismiss_overlays(self) -> None:
        assert self._page is not None
        for selector in COOKIE_BUTTON_SELECTORS:
            try:
                button = self._page.locator(selector).first
                if button.count() and button.is_visible(timeout=400):
                    button.click(timeout=1500)
                    self._page.wait_for_timeout(400)
                    print(f"[浏览器] 已点击 Cookie/同意按钮：{selector}", flush=True)
                    return
            except Exception:
                continue

    def current_html(self) -> str:
        assert self._page is not None
        return self._page.content()

    def current_url(self) -> str:
        assert self._page is not None
        return self._page.url

    def fetch(self, url: str) -> str:
        self.start()
        assert self._page is not None
        print(f"[浏览器] 打开页面：{url}", flush=True)
        self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self._page.wait_for_timeout(1500)
        self.dismiss_overlays()
        challenge_wait = min(35, max(8, self.wait_seconds if page_looks_blocked(self._page.title(), "") else 12))
        deadline = time.time() + challenge_wait
        warned = False
        while True:
            title = self._page.title() or ""
            content = self._page.content()
            blocked = page_looks_blocked(title, content)
            if not blocked:
                try:
                    self._page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                self.dismiss_overlays()
                if is_google_maps_url(self._page.url) or is_google_search_url(self._page.url):
                    self.scroll_results(rounds=8)
                else:
                    self.scroll_results(rounds=2)
                    self._wait_for_listing_links()
                print("[浏览器] 页面已读取", flush=True)
                return self._page.content()
            if time.time() >= deadline:
                break
            if not warned:
                print("[浏览器] 这是人机验证页，不是账号没登录。请在弹出的 Chrome 里点一下验证，通过后脚本会继续。", flush=True)
                warned = True
            self._page.wait_for_timeout(3000)
        print("[浏览器] 验证页仍在，先按当前页面继续采集", flush=True)
        self.scroll_results(rounds=2)
        return self._page.content()

    def _wait_for_listing_links(self) -> None:
        assert self._page is not None
        try:
            self._page.wait_for_selector(
                "a[href*='imovel'], a[href*='anuncio'], a[href*='property'], a[href*='/maps/place/']",
                timeout=8000,
            )
        except Exception:
            pass

    def scroll_results(self, rounds: int = 5) -> None:
        assert self._page is not None
        for _ in range(max(1, rounds)):
            try:
                scrolled = self._page.evaluate(
                    """
                    () => {
                      const feed = document.querySelector('div[role="feed"]');
                      if (feed) {
                        feed.scrollTop = feed.scrollHeight;
                        return 'feed';
                      }
                      window.scrollBy(0, Math.max(700, window.innerHeight));
                      return 'window';
                    }
                    """
                )
                if scrolled:
                    self._page.wait_for_timeout(700)
            except Exception:
                try:
                    self._page.mouse.wheel(0, 1600)
                    self._page.wait_for_timeout(700)
                except Exception:
                    break

    def collect_hrefs(self) -> list[str]:
        self.start()
        assert self._page is not None
        try:
            hrefs = self._page.eval_on_selector_all("a[href]", "els => els.map(a => a.href)")
        except Exception:
            hrefs = []
        cleaned: list[str] = []
        seen: set[str] = set()
        for href in hrefs:
            url = unwrap_google_url(str(href or "")).split("#")[0]
            if url.startswith(("http://", "https://")) and url not in seen:
                seen.add(url)
                cleaned.append(url)
        return cleaned

    def extract_google_cards(self) -> list[dict[str, str]]:
        self.start()
        assert self._page is not None
        self.scroll_results(rounds=10)
        try:
            cards = self._page.evaluate(
                """
                () => {
                  const items = [];
                  const seen = new Set();
                  const add = (url, name, info) => {
                    if (!url || seen.has(url)) return;
                    seen.add(url);
                    items.push({
                      url,
                      name: (name || '').trim(),
                      info: (info || '').replace(/\\s+/g, ' ').trim().slice(0, 500),
                    });
                  };
                  const propertyRe = /idealista\\.pt|imovirtual\\.com|supercasa\\.pt|kyero\\.com|remax\\.pt|predimed\\.pt|portadafrente\\.com/i;
                  const listingRe = /imovel|anuncio|property|imoveis|venda|arrendar|arrendamento/i;
                  for (const a of document.querySelectorAll('a[href]')) {
                    const href = a.href || '';
                    const card = a.closest('[role="article"]') || a.closest('div[jscontroller]') || a;
                    const text = (card && card.innerText) ? card.innerText : (a.innerText || '');
                    const name = (text.split('\\n').map(s => s.trim()).filter(Boolean)[0] || a.getAttribute('aria-label') || '');
                    if (/\\/maps\\/place\\//.test(href) || /maps\\.app\\.goo\\.gl/.test(href)) {
                      add(href, name, text);
                    } else if (propertyRe.test(href) && listingRe.test(href)) {
                      add(href, name, text);
                    }
                  }
                  return items;
                }
                """
            )
        except Exception as exc:
            print(f"[谷歌地图] 提取卡片失败：{exc}", flush=True)
            cards = []
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in cards or []:
            url = unwrap_google_url(str(item.get("url") or "")).split("#")[0]
            if not url or url in seen:
                continue
            seen.add(url)
            results.append(
                {
                    "url": url,
                    "name": clean_text(str(item.get("name") or ""), 180),
                    "info": clean_text(str(item.get("info") or ""), 500),
                }
            )
        print(f"[谷歌地图] 本页提取到 {len(results)} 个结果", flush=True)
        return results

    def login_sites(self, sites: list[str]) -> None:
        self.visible = True
        self._keep_open = True
        urls = login_urls_for(sites)
        try:
            self.start()
            if self._page is not None and urls:
                print(f"[登录] 打开登录页：{urls[0]}", flush=True)
                self._page.goto(urls[0], wait_until="domcontentloaded", timeout=60000)
                self.dismiss_overlays()
                for extra in urls[1:]:
                    try:
                        page = self._context.new_page() if self._context else self._page
                        page.goto(extra, wait_until="domcontentloaded", timeout=60000)
                    except Exception as exc:
                        print(f"[登录] 额外标签打开失败：{exc}", flush=True)
        except Exception as exc:
            print(f"[登录] 自动化打开失败，改用系统 Chrome：{exc}", flush=True)
            opened = open_login_browser(sites, self.profile_dir)
            print(f"[登录] 已打开浏览器，CDP：{opened['cdp_url']}", flush=True)
            self._keep_open = True
            return
        print("[登录] 浏览器会保持打开。请在窗口里完成登录，然后回到软件点「标记已登录」。", flush=True)
        print(f"[登录] Cookie 保存在：{self.profile_dir}", flush=True)


def fetch_page(session: requests.Session, url: str, args: argparse.Namespace, browser: BrowserFetcher | None) -> str:
    force_browser = args.browser_mode == "always" or needs_browser(url)
    if force_browser:
        if not browser:
            raise RuntimeError("该网站需要浏览器访问，但浏览器模式未初始化")
        return browser.fetch(url)
    try:
        return fetch(session, url, args.pause)
    except BrowserRequiredError as exc:
        if args.browser_mode == "off":
            raise RuntimeError(f"{exc}；当前未启用浏览器自动化") from exc
        if not browser:
            raise
        print(f"[浏览器] 普通请求失败：{exc}，切换到浏览器自动化", flush=True)
        return browser.fetch(url)


def absolute_url(base: str, value: str) -> str:
    if not value:
        return ""
    return urljoin(base, html.unescape(value))


def source_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if "google." in host and ("/maps" in path or path.startswith("/search")):
        return "google_maps"
    for source, domain in SITE_DOMAINS.items():
        if source == "google_maps":
            continue
        if domain in host:
            return source
    return host.replace("www.", "")


def looks_like_listing(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path
    if "google." in host and "/maps/place/" in path:
        return True
    if host.endswith("goo.gl") and "maps" in path:
        return True
    for domain, hints in LISTING_HINTS.items():
        if domain in host and any(hint in path for hint in hints):
            if domain.startswith("google.") and "/maps/search/" in path:
                return False
            return True
    return False


def discover_listing_urls(page_url: str, page_html: str, max_links: int) -> list[str]:
    parser = HeadParser()
    parser.feed(page_html)
    found: list[str] = []
    seen: set[str] = set()

    def add_candidate(raw: str) -> bool:
        url = unwrap_google_url(absolute_url(page_url, html.unescape(raw))).split("#")[0]
        url = url.rstrip("\\")
        if not url.startswith(("http://", "https://")):
            return False
        if looks_like_listing(url) and url not in seen:
            seen.add(url)
            found.append(url)
            return True
        return False

    for href, _ in parser.links:
        add_candidate(href)
        if len(found) >= max_links:
            return found
    raw_patterns = [
        r"https?://[^\"'\s<>]+/(?:zh/)?imovel/\d+/?",
        r"/(?:zh/)?imovel/\d+/?",
        r"https?://[^\"'\s<>]+/pt/anuncio/[^\"'\s<>]+",
        r"/pt/anuncio/[^\"'\s<>]+",
        r"https?://[^\"'\s<>]+/en/property/[^\"'\s<>]+",
        r"/en/property/[^\"'\s<>]+",
        r"https?://www\.google\.[^\"'\s<>]+/maps/place/[^\"'\s<>]+",
        r"https?://maps\.app\.goo\.gl/[^\"'\s<>]+",
    ]
    for pattern in raw_patterns:
        for match in re.findall(pattern, page_html, flags=re.I):
            add_candidate(match)
            if len(found) >= max_links:
                return found
    return found


def read_json_ld(parser: HeadParser) -> dict:
    merged: dict = {}
    for blob in parser.json_ld:
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                merged.update({k: v for k, v in item.items() if v})
    return merged


def extract_contact(text: str, parser: HeadParser) -> str:
    contacts: set[str] = set()
    for href, _ in parser.links:
        if href.startswith("mailto:"):
            contacts.add(href.replace("mailto:", "").split("?")[0])
        if href.startswith("tel:"):
            contacts.add(href.replace("tel:", ""))

    phone_patterns = [
        r"(?:\+351\s*)?(?:9[1236]\d|2\d{2})[\s.\-]?\d{3}[\s.\-]?\d{3}",
        r"\b\d{3}[\s.\-]?\d{3}[\s.\-]?\d{3}\b",
    ]
    for pattern in phone_patterns:
        for match in re.findall(pattern, text):
            contacts.add(re.sub(r"\s+", " ", match).strip())
    for email in re.findall(r"[\w.\-+]+@[\w.\-]+\.\w+", text):
        contacts.add(email)
    return "; ".join(sorted(contacts))


def extract_price(text: str) -> str:
    patterns = [
        r"(?<![\d.,])\d{1,3}(?:[.\s]\d{3})+(?:[,.]\d{2})?\s*€",
        r"€\s*\d{1,3}(?:[.\s]\d{3})+(?:[,.]\d{2})?",
        r"(?<![\d])\d{4,7}\s*€",
        r"€\s*\d{4,7}",
        r"\d{4,7}(?:[.\s]\d{3})?\s*EUR",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return clean_text(match.group(0), 60)
    return ""


def extract_rooms(text: str) -> str:
    match = re.search(r"\bT\s?(\d{1,2})\b", text, flags=re.I)
    if match:
        return f"T{match.group(1)}"
    match = re.search(r"(\d{1,2})\s*(?:quartos|bedrooms|rooms)", text, flags=re.I)
    return match.group(0) if match else ""


def extract_area(text: str) -> str:
    match = re.search(r"\d{2,5}(?:[,.]\d+)?\s*m[²2]", text, flags=re.I)
    return clean_text(match.group(0), 40) if match else ""


def extract_location(text: str) -> str:
    hints = ["Lisboa", "Porto", "Mafra", "Loures", "Sintra", "Cascais", "Oeiras", "Almada", "Setúbal", "Faro"]
    for hint in hints:
        if re.search(rf"\b{re.escape(hint)}\b", text, flags=re.I):
            return hint
    return ""


def extract_images(page_url: str, parser: HeadParser, page_html: str = "") -> list[str]:
    candidates: list[str] = []
    for key in ["og:image", "twitter:image", "image"]:
        if parser.meta.get(key):
            candidates.append(parser.meta[key])
    candidates.extend(parser.images)
    for srcset in parser.srcsets:
        for part in srcset.split(","):
            candidates.append(part.strip().split(" ")[0])
    candidates.extend(
        match.replace("\\/", "/")
        for match in re.findall(r"https?:\\?/\\?/[^\"'\s<>]+?\.(?:jpg|jpeg|png|webp)", page_html, flags=re.I)
    )

    seen: set[str] = set()
    images: list[str] = []
    for image in candidates:
        url = absolute_url(page_url, image).split("?")[0]
        lower = url.lower()
        if not lower.startswith(("http://", "https://")):
            continue
        if not any(ext in lower for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            continue
        if url not in seen:
            seen.add(url)
            images.append(url)
    return images[:20]


def parse_listing(page_url: str, page_html: str) -> tuple[Listing, list[str]]:
    parser = HeadParser()
    parser.feed(page_html)
    json_ld = read_json_ld(parser)
    plain = re.sub(r"<[^>]+>", " ", page_html)
    plain = clean_text(plain, 5000)

    title = (
        clean_text(str(json_ld.get("name", "")), 180)
        or clean_text(parser.meta.get("og:title", ""), 180)
        or clean_text(" ".join(parser.title_parts), 180)
    )
    description = (
        clean_text(str(json_ld.get("description", "")), 700)
        or clean_text(parser.meta.get("og:description", ""), 700)
        or clean_text(plain, 700)
    )
    contact = extract_contact(plain, parser)
    listing = Listing(
        source=source_from_url(page_url),
        name=title,
        info=description,
        contact=contact,
        url=page_url,
        photo_cloud_folder="",
        photo_local_folder="",
        price=extract_price(plain),
        rooms=extract_rooms(plain),
        area=extract_area(plain),
        location=extract_location(plain),
        image_count=0,
    )
    return listing, extract_images(page_url, parser, page_html)


def build_search_urls(args: argparse.Namespace) -> list[str]:
    area = slugify(args.area.lower())
    quoted = quote(args.area)
    urls: list[str] = []

    for site in args.sites:
        if args.deal == "rent" and site not in RENT_SUPPORTED_SITES:
            print(f"[跳过网站] {site} 暂未配置可靠租房搜索，避免混入买房结果", flush=True)
            continue
        if site == "idealista":
            deal = "arrendar" if args.deal == "rent" else "comprar"
            rooms_path = f"com-t{args.min_rooms}/" if args.min_rooms else ""
            urls.append(f"https://www.idealista.pt/{deal}-casas/{area}/{rooms_path}")
        elif site == "imovirtual":
            deal = "arrendar" if args.deal == "rent" else "comprar"
            location = IMOVIRTUAL_LOCATIONS.get(args.area.strip().lower(), quoted.lower())
            extra = ""
            if args.min_rooms:
                extra = "?" + urlencode({f"search[filter_enum_rooms_num][0]": str(args.min_rooms)})
            if args.min_area:
                extra += ("&" if extra else "?") + urlencode({"search[filter_float_m:from]": str(args.min_area)})
            for kind in ("apartamento", "moradia"):
                urls.append(f"https://www.imovirtual.com/pt/resultados/{deal}/{kind}/{location}{extra}")
        elif site == "supercasa":
            deal = "arrendar" if args.deal == "rent" else "comprar"
            urls.append(f"https://supercasa.pt/{deal}-casas/{area}")
        elif site == "kyero":
            kyero_area = KYERO_LOCATION_IDS.get(args.area.strip().lower())
            if kyero_area:
                slug, location_id = kyero_area
                if args.deal == "rent":
                    urls.append(f"https://www.kyero.com/en/{slug}-property-long-let-1l{location_id}")
                else:
                    urls.append(f"https://www.kyero.com/en/{slug}-property-for-sale-0l{location_id}")
            else:
                suffix = "property-long-let" if args.deal == "rent" else "property-for-sale"
                urls.append(f"https://www.kyero.com/en/portugal-{suffix}?search={quoted}")
        elif site == "remax":
            if args.deal == "rent":
                urls.append(
                    "https://www.remax.pt/pt/arrendar?searchQueryState="
                    f"{{%22regionName%22:%22{quoted}%22,%22businessType%22:2}}"
                )
            else:
                urls.append(
                    "https://www.remax.pt/pt/pesquisa/imoveis/venda?searchQueryState="
                    f"{{%22regionName%22:%22{quoted}%22}}"
                )
        elif site == "predimed":
            if args.deal == "rent":
                urls.append(f"https://predimed.pt/Imoveis?search={quoted}&negocio=arrendamento")
            else:
                urls.append(f"https://predimed.pt/Imoveis?search={quoted}&negocio=venda")
        elif site == "portadafrente":
            if args.deal == "rent":
                urls.append(f"https://www.portadafrente.com/imoveis?search={quoted}&finalidade=arrendamento")
            else:
                urls.append(f"https://www.portadafrente.com/imoveis?search={quoted}&finalidade=venda")
        elif site == "google_maps":
            query = build_maps_query(args)
            print(f"[谷歌地图] 关键词搜索：{query}", flush=True)
            urls.append(f"https://www.google.com/maps/search/{quote(query)}")
            urls.append(f"https://www.google.com/search?q={quote(query)}&hl=pt-PT&gl=pt")

    return urls


def build_maps_query(args: argparse.Namespace) -> str:
    parts: list[str] = []
    keyword = str(getattr(args, "keyword", "") or "").strip()
    area = str(args.area or "").strip()
    if keyword:
        parts.append(keyword)
        if area and area.lower() not in keyword.lower():
            parts.append(area)
    else:
        parts.append("casas para arrendar" if args.deal == "rent" else "casas à venda")
        if area:
            parts.append(area)
    hay = " ".join(parts).lower()
    if "portugal" not in hay:
        parts.append("Portugal")
    if args.min_rooms and f"t{args.min_rooms}" not in hay and f"{args.min_rooms} quarto" not in hay:
        parts.append(f"T{args.min_rooms}")
    if args.min_area and f"{args.min_area}" not in hay:
        parts.append(f"{args.min_area}m2")
    if args.max_area and "até" not in hay:
        parts.append(f"até {args.max_area}m2")
    if args.deal == "rent" and not any(word in hay for word in ("arrendar", "arrendamento", "alugar", "rent")):
        parts.append("arrendar")
    if args.deal == "sale" and not any(word in hay for word in ("venda", "comprar", "sale")):
        parts.append("venda")
    return " ".join(part for part in parts if part)


def add_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params[key] = value
    return urlunparse(parsed._replace(query=urlencode(params)))


def paged_search_url(url: str, page: int) -> str:
    if page <= 1:
        return url
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if "google." in host and ("/maps" in path or path.startswith("/search")):
        return url
    if "idealista.pt" in host:
        base = url.rstrip("/")
        if base.endswith(".htm"):
            return add_query_param(url, "pagina", str(page))
        return f"{base}/pagina-{page}.htm"
    return add_query_param(url, "page", str(page))


def iter_search_urls(args: argparse.Namespace) -> Iterable[str]:
    base_urls = args.seed_url if args.no_auto_search else args.seed_url + build_search_urls(args)
    if args.seed_url and args.no_auto_search:
        for url in base_urls:
            yield url
        return

    max_pages = max(1, args.max_search_pages)
    for base_url in base_urls:
        if looks_like_listing(base_url):
            yield base_url
            continue
        for page in range(1, max_pages + 1):
            yield paged_search_url(base_url, page)


def get_base_search_urls(args: argparse.Namespace) -> list[str]:
    return args.seed_url if args.no_auto_search else args.seed_url + build_search_urls(args)


def iter_one_site_urls(base_url: str, args: argparse.Namespace) -> Iterable[str]:
    if looks_like_listing(base_url) or is_google_maps_url(base_url) or is_google_search_url(base_url):
        yield base_url
        return
    for page in range(1, max(1, args.max_search_pages) + 1):
        yield paged_search_url(base_url, page)


def listing_from_card(item: dict[str, str], fallback_location: str = "") -> Listing:
    text = " ".join([item.get("name", ""), item.get("info", "")])
    url = item.get("url", "")
    return Listing(
        source=source_from_url(url) if url else "google_maps",
        name=clean_text(item.get("name") or "Google 地图房源", 180),
        info=clean_text(item.get("info") or "", 700),
        contact=extract_contact(text, HeadParser()),
        url=url,
        photo_cloud_folder="",
        photo_local_folder="",
        price=extract_price(text),
        rooms=extract_rooms(text),
        area=extract_area(text),
        location=extract_location(text) or fallback_location,
        image_count=0,
    )


def _fold(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("ú", "u")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ç", "c")
    )


def area_aliases(area: str) -> list[str]:
    wanted = (area or "").strip().lower()
    return AREA_ALIASES.get(wanted, [wanted])


def candidate_should_skip(url: str, args: argparse.Namespace) -> str:
    hay = _fold(url)
    aliases = [_fold(item) for item in area_aliases(args.area) if item]
    if args.min_rooms:
        room_match = re.search(r"(?:^|[^a-z0-9])t(\d{1,2})(?:[^a-z0-9]|$)", hay)
        if room_match and int(room_match.group(1)) < args.min_rooms:
            return f"链接里是 T{room_match.group(1)}，少于 {args.min_rooms}"
    if args.strict_area:
        if aliases and any(item in hay for item in aliases):
            return ""
        if any(hint in hay for hint in OTHER_AREA_HINTS) and not any(item in hay for item in aliases):
            return f"链接地区不像 {args.area}"
    return ""


def passes_filters(listing: Listing, args: argparse.Namespace) -> bool:
    text = " ".join([listing.name, listing.info, listing.rooms, listing.area]).lower()
    if args.strict_area:
        wanted = args.area.strip().lower()
        aliases = area_aliases(args.area)
        text_ascii = _fold(text)
        url_ascii = _fold(listing.url)
        alias_ascii = [_fold(item) for item in aliases if item]
        if alias_ascii and not any(item in text_ascii or item in url_ascii for item in alias_ascii):
            if listing.source == "google_maps":
                print("[筛选] 谷歌地图结果未直接写出地区名，但搜索本身已按地区查询，予以保留", flush=True)
            else:
                print(f"[筛选跳过] 地区不匹配：需要 {args.area}", flush=True)
                return False
    if args.deal == "rent":
        rent_terms = ["arrendamento", "arrendar", "alugar", "renda", "rental", "rent", "long-let", "long let", "/arrendar/"]
        sale_terms = ["venda", "comprar", "sale", "for-sale", "for sale", "/comprar/"]
        haystack = f"{text} {listing.url.lower()}"
        if any(term in haystack for term in sale_terms) and not any(term in haystack for term in rent_terms):
            print("[筛选跳过] 租房模式下疑似买房链接", flush=True)
            return False
    if args.min_rooms is not None:
        room_match = re.search(r"\bT\s?(\d{1,2})\b", text, flags=re.I)
        if room_match and int(room_match.group(1)) < args.min_rooms:
            print(f"[筛选跳过] 房间数 {room_match.group(1)} 小于 {args.min_rooms}", flush=True)
            return False
    if args.max_rooms is not None:
        room_match = re.search(r"\bT\s?(\d{1,2})\b", text, flags=re.I)
        if room_match and int(room_match.group(1)) > args.max_rooms:
            print(f"[筛选跳过] 房间数 {room_match.group(1)} 大于 {args.max_rooms}", flush=True)
            return False
    if args.min_area is not None:
        area_match = re.search(r"(\d{2,5})(?:[,.]\d+)?\s*m", text, flags=re.I)
        if area_match and int(area_match.group(1)) < args.min_area:
            print(f"[筛选跳过] 面积 {area_match.group(1)} 小于 {args.min_area}", flush=True)
            return False
    if args.max_area is not None:
        area_match = re.search(r"(\d{2,5})(?:[,.]\d+)?\s*m", text, flags=re.I)
        if area_match and int(area_match.group(1)) > args.max_area:
            print(f"[筛选跳过] 面积 {area_match.group(1)} 大于 {args.max_area}", flush=True)
            return False
    return True


def download_images(session: requests.Session, images: list[str], folder: Path, pause: float) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    print(f"[照片] 发现 {len(images)} 个候选图片，开始下载", flush=True)
    for idx, image_url in enumerate(images, start=1):
        try:
            time.sleep(pause)
            response = session.get(image_url, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            print(f"[照片跳过] {image_url}: {exc}")
            continue

        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        ext = mimetypes.guess_extension(content_type) or Path(urlparse(image_url).path).suffix or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"
        digest = hashlib.sha1(image_url.encode("utf-8")).hexdigest()[:10]
        path = folder / f"{idx:02d}-{digest}{ext}"
        path.write_bytes(response.content)
        saved.append(path)
        print(f"[照片] 下载成功 {len(saved)}/{len(images)}：{path.name}", flush=True)
    print(f"[照片] 下载完成：成功 {len(saved)} 张", flush=True)
    return saved


def _read_json_dict(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def classify_google_json(path: Path) -> str:
    if not path.exists():
        return "missing"
    data = _read_json_dict(path)
    if data.get("type") == "service_account" and data.get("client_email"):
        return "service-account"
    if "installed" in data or "web" in data:
        return "oauth-client"
    if data.get("refresh_token") and data.get("client_id"):
        return "user-token"
    return "unknown"


def resolve_google_paths(credentials_path: Path, token_path: Path, service_account_path: Path) -> tuple[Path, Path, Path]:
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)
    service_account_path = Path(service_account_path)
    token_kind = classify_google_json(token_path)
    cred_kind = classify_google_json(credentials_path)
    service_kind = classify_google_json(service_account_path)

    if cred_kind != "oauth-client":
        if token_kind == "oauth-client":
            credentials_path = token_path
            cred_kind = "oauth-client"
        elif service_kind == "oauth-client":
            credentials_path = service_account_path
            cred_kind = "oauth-client"

    if token_kind != "user-token":
        fallback_token = Path(__file__).resolve().parent / "drive_token.json"
        if token_path.resolve() == credentials_path.resolve() or token_kind in {"oauth-client", "service-account", "unknown"}:
            print(f"[授权] Token 文件不是已登录凭证，改用：{fallback_token}", flush=True)
            token_path = fallback_token

    if service_kind != "service-account":
        fallback_sa = Path(__file__).resolve().parent / "service_account.json"
        if service_account_path.resolve() == credentials_path.resolve() or service_kind in {"oauth-client", "user-token", "unknown"}:
            if fallback_sa.exists():
                print(f"[授权] 服务账号文件不对，改用：{fallback_sa}", flush=True)
                service_account_path = fallback_sa
    return credentials_path, token_path, service_account_path


def load_google_credentials(
    credentials_path: Path,
    token_path: Path,
    auth_mode: str,
    service_account_path: Path,
    scopes: list[str],
):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials_path, token_path, service_account_path = resolve_google_paths(
        credentials_path, token_path, service_account_path
    )

    if auth_mode == "service-account":
        if classify_google_json(service_account_path) != "service-account":
            print("[授权] 没有可用的服务账号 JSON，改用 OAuth 登录。", flush=True)
        else:
            return service_account.Credentials.from_service_account_file(
                str(service_account_path),
                scopes=scopes,
            )

    creds = None
    if classify_google_json(token_path) == "user-token":
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
        granted_scopes = set(creds.scopes or [])
        if not set(scopes).issubset(granted_scopes):
            creds = None
        client_info = _read_json_dict(credentials_path).get("installed") or _read_json_dict(credentials_path).get("web") or {}
        if creds and client_info.get("client_id") and creds.client_id != client_info.get("client_id"):
            print("[授权] Token 和 OAuth 客户端不是同一套，需要重新登录。", flush=True)
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                print(f"[授权] Google token 已失效，需要重新登录：{exc}", flush=True)
                creds = None
        if not creds or not creds.valid:
            if classify_google_json(credentials_path) != "oauth-client":
                raise FileNotFoundError(
                    "找不到 OAuth 客户端 JSON。请在设置里把「OAuth 客户端」指到 Desktop 凭证文件，"
                    "「Token」单独指到 drive_token.json，不要三个框填同一个文件。"
                )
            print("[授权] 正在打开浏览器，请用你的 Google 账号重新授权 Drive/表格。", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        print(f"[授权] 新的授权已保存：{token_path}", flush=True)
    return creds


class GoogleExporter:
    def __init__(
        self,
        credentials_path: Path,
        token_path: Path,
        parent_folder_id: str | None,
        drive_auth_mode: str,
        sheet_auth_mode: str,
        service_account_path: Path,
    ):
        from googleapiclient.discovery import build

        drive_creds = load_google_credentials(
            credentials_path,
            token_path,
            drive_auth_mode,
            service_account_path,
            DRIVE_SCOPES,
        )
        sheet_creds = load_google_credentials(
            credentials_path,
            token_path,
            sheet_auth_mode,
            service_account_path,
            SHEETS_SCOPES,
        )
        try:
            import httplib2
            from google_auth_httplib2 import AuthorizedHttp

            self.drive = build("drive", "v3", http=AuthorizedHttp(drive_creds, http=httplib2.Http(timeout=90)))
            self.sheets = build("sheets", "v4", http=AuthorizedHttp(sheet_creds, http=httplib2.Http(timeout=90)))
        except Exception:
            self.drive = build("drive", "v3", credentials=drive_creds)
            self.sheets = build("sheets", "v4", credentials=sheet_creds)
        self.parent_folder_id = parent_folder_id
        self._ready_sheets: set[tuple[str, str]] = set()

    def _execute(self, request, what: str, attempts: int = 4):
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return request.execute()
            except Exception as exc:
                last_error = exc
                wait = min(20, 2 * attempt)
                print(f"[表格] {what} 第 {attempt} 次失败：{exc}，{wait} 秒后重试", flush=True)
                time.sleep(wait)
        raise last_error or RuntimeError(f"{what} 失败")

    def create_folder(self, name: str) -> tuple[str, str]:
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if self.parent_folder_id:
            metadata["parents"] = [self.parent_folder_id]
        folder = self.drive.files().create(body=metadata, fields="id, webViewLink").execute()
        folder_id = folder["id"]
        permission = {"type": "anyone", "role": "reader"}
        self.drive.permissions().create(fileId=folder_id, body=permission).execute()
        return folder_id, folder.get("webViewLink", f"https://drive.google.com/drive/folders/{folder_id}")

    def upload_files(self, folder_id: str, files: Iterable[Path]) -> None:
        from googleapiclient.http import MediaFileUpload

        files = list(files)
        print(f"[云端] 开始上传 {len(files)} 张照片", flush=True)
        for idx, file_path in enumerate(files, start=1):
            media = MediaFileUpload(str(file_path), resumable=True)
            metadata = {"name": file_path.name, "parents": [folder_id]}
            uploaded = self.drive.files().create(body=metadata, media_body=media, fields="id").execute()
            self.drive.permissions().create(
                fileId=uploaded["id"],
                body={"type": "anyone", "role": "reader"},
            ).execute()
            print(f"[云端] 上传成功 {idx}/{len(files)}：{file_path.name}", flush=True)
        print(f"[云端] 照片上传完成：{len(files)} 张", flush=True)

    def ensure_sheet(self, spreadsheet_id: str, sheet_name: str) -> None:
        spreadsheet = self.sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get("sheets", [])
        if any(s.get("properties", {}).get("title") == sheet_name for s in sheets):
            return
        body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        self.sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    def append_listings(self, spreadsheet_id: str, sheet_name: str, rows: list[Listing]) -> None:
        if not rows:
            return
        print(f"[表格] 准备写入 {len(rows)} 条到 {sheet_name}", flush=True)
        key = (spreadsheet_id, sheet_name)
        fieldnames = list(Listing.__dataclass_fields__.keys())
        if key not in self._ready_sheets:
            self.ensure_sheet(spreadsheet_id, sheet_name)
            header_range = f"'{sheet_name}'!A1:{chr(ord('A') + len(fieldnames) - 1)}1"
            header = self._execute(
                self.sheets.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=header_range,
                ),
                "读取表头",
            ).get("values", [])
            if not header:
                self._execute(
                    self.sheets.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"'{sheet_name}'!A1",
                        valueInputOption="RAW",
                        body={"values": [fieldnames]},
                    ),
                    "写入表头",
                )
            self._ready_sheets.add(key)
        values = [[asdict(row).get(field, "") for field in fieldnames] for row in rows]
        self._execute(
            self.sheets.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": values},
            ),
            "追加房源",
        )
        print(f"[表格] 写入完成：{len(rows)} 条", flush=True)

    def existing_urls(self, spreadsheet_id: str, sheet_name: str) -> set[str]:
        self.ensure_sheet(spreadsheet_id, sheet_name)
        fieldnames = list(Listing.__dataclass_fields__.keys())
        url_index = fieldnames.index("url")
        values = self.sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A:Z",
        ).execute().get("values", [])
        urls: set[str] = set()
        for row in values[1:]:
            if len(row) > url_index and row[url_index]:
                urls.add(row[url_index].strip())
        print(f"[排重] 表格里已有 {len(urls)} 个房源 URL", flush=True)
        return urls

    def existing_place_ids(self, spreadsheet_id: str, sheet_name: str) -> set[str]:
        self.ensure_sheet(spreadsheet_id, sheet_name)
        values = self._execute(
            self.sheets.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A:R",
            ),
            "读取已有地点",
        ).get("values", [])
        ids: set[str] = set()
        for row in values[1:]:
            if len(row) > 11 and row[11].strip():
                ids.add(row[11].strip())
        print(f"[排重] {sheet_name} 里已有 {len(ids)} 个 Place ID", flush=True)
        return ids

    def append_place_rows(self, spreadsheet_id: str, sheet_name: str, rows: list[list[str]]) -> None:
        if not rows:
            return
        print(f"[表格] 准备写入 {len(rows)} 条到 {sheet_name}", flush=True)
        key = (spreadsheet_id, sheet_name)
        if key not in self._ready_sheets:
            self.ensure_sheet(spreadsheet_id, sheet_name)
            header = self._execute(
                self.sheets.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_name}'!A1:R1",
                ),
                "读取工作表1表头",
            ).get("values", [])
            if not header:
                self._execute(
                    self.sheets.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"'{sheet_name}'!A1",
                        valueInputOption="RAW",
                        body={"values": [PLACE_HEADERS]},
                    ),
                    "写入工作表1表头",
                )
            self._ready_sheets.add(key)
        self._execute(
            self.sheets.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": rows},
            ),
            "追加地点",
        )
        print(f"[表格] {sheet_name} 写入完成：{len(rows)} 条", flush=True)


def write_csv(rows: list[Listing], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(Listing.__dataclass_fields__.keys())
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="葡萄牙房地产网站房源采集并导出 CSV")
    parser.add_argument("--area", default=None, help="地区，例如 Mafra、Loures、Lisboa、Porto。登录模式可不填")
    parser.add_argument("--keyword", default="", help="谷歌地图/搜索关键词，例如 T4 apartamento Alcântara")
    parser.add_argument("--deal", choices=["sale", "rent"], default="sale", help="sale=买房，rent=租房")
    parser.add_argument("--sites", nargs="+", default=DEFAULT_SITES, choices=DEFAULT_SITES, help="要采集的网站")
    parser.add_argument("--min-rooms", type=int, default=None, help="最少房间数，例如 3")
    parser.add_argument("--max-rooms", type=int, default=None, help="最多房间数")
    parser.add_argument("--min-area", type=int, default=None, help="最小面积，单位 m2")
    parser.add_argument("--max-area", type=int, default=None, help="最大面积，单位 m2")
    parser.add_argument("--max-search-pages", type=int, default=50, help="每个网站最多读取多少个搜索页")
    parser.add_argument("--max-listings", type=int, default=0, help="最多采集多少个房源，0 表示不限制")
    parser.add_argument("--stop-empty-pages", type=int, default=3, help="连续多少个搜索页没有新房源后停止")
    parser.add_argument("--strict-area", action=argparse.BooleanOptionalAction, default=True, help="严格过滤地区")
    parser.add_argument("--seed-url", action="append", default=[], help="额外输入搜索页或房源页，可重复使用")
    parser.add_argument("--no-auto-search", action="store_true", help="只使用 --seed-url，不自动生成网站搜索页")
    parser.add_argument("--output", default="outputs/portugal_properties.csv", help="CSV 输出路径")
    parser.add_argument("--photo-dir", default="outputs/property_photos", help="照片本地保存目录")
    parser.add_argument("--no-photos", action="store_true", help="不下载照片")
    parser.add_argument("--upload-drive", action="store_true", help="上传照片到 Google Drive")
    parser.add_argument("--auth-mode", choices=["oauth", "service-account"], default=None, help="Use one auth mode for both Drive and Sheets")
    parser.add_argument("--drive-auth-mode", choices=["oauth", "service-account"], default="oauth", help="Auth mode for Google Drive uploads")
    parser.add_argument("--sheet-auth-mode", choices=["oauth", "service-account"], default="service-account", help="Auth mode for Google Sheets writes")
    parser.add_argument("--google-credentials", default="oauth_client.json", help="Google OAuth 客户端 JSON 路径")
    parser.add_argument("--google-token", default="drive_token.json", help="Google OAuth token 保存路径")
    parser.add_argument("--service-account", default="service_account.json", help="Google 服务账号 JSON 路径")
    parser.add_argument("--drive-parent-folder-id", default=DEFAULT_DRIVE_PARENT_FOLDER_ID, help="Google Drive parent folder ID")
    parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID, help="Google Sheets spreadsheet ID")
    parser.add_argument("--sheet-name", default=DEFAULT_SHEET_NAME, help="Google Sheets worksheet name")
    parser.add_argument("--maps-sheet-name", default=DEFAULT_MAPS_SHEET_NAME, help="谷歌关键词搜索写入的工作表，默认 工作表1")
    parser.add_argument("--google-places-key", default=DEFAULT_PLACES_API_KEY, help="Google Places API Key，用于关键词搜地图并登记工作表1")
    parser.add_argument("--no-write-sheet", action="store_true", help="Do not append rows to Google Sheets")
    parser.add_argument("--pause", type=float, default=1.5, help="每次请求之间暂停秒数，建议不要太小")
    parser.add_argument("--browser-mode", choices=["fallback", "always", "off"], default="fallback", help="浏览器自动化模式")
    parser.add_argument("--browser-visible", action=argparse.BooleanOptionalAction, default=True, help="显示自动化浏览器窗口")
    parser.add_argument("--browser-profile", default="browser_profile", help="浏览器 Cookie/登录状态保存目录")
    parser.add_argument("--browser-wait-seconds", type=int, default=180, help="遇到验证时最多等待多少秒")
    parser.add_argument("--browser-backend", choices=["cdp", "playwright"], default="cdp", help="cdp=真实 Chrome（推荐），playwright=内置自动化浏览器")
    parser.add_argument("--cdp-url", default="", help="连接到已打开的 Chrome，例如 http://127.0.0.1:9222")
    parser.add_argument("--login", action="store_true", help="只打开选中网站的登录页，让你手动登录并保存 Cookie")
    args = parser.parse_args()
    if not args.login and not args.area and not args.seed_url:
        parser.error("请提供 --area，或使用 --login 先登录，或用 --seed-url 提供链接")
    if not args.area:
        args.area = "Mafra"
    if args.login or "google_maps" in args.sites:
        if args.browser_mode == "off":
            args.browser_mode = "always"
    return args


def format_opening_hours(weekday_text: list[str]) -> str:
    parts: list[str] = []
    for line in weekday_text:
        text = line
        for en, zh in WEEKDAY_ZH.items():
            text = text.replace(en, zh)
        text = text.replace("Open 24 hours", "24小时营业").replace("Closed", "休息")
        parts.append(text)
    return " | ".join(parts)


def places_query(args: argparse.Namespace) -> str:
    keyword = str(getattr(args, "keyword", "") or "").strip()
    area = str(args.area or "").strip()
    if keyword and area and area.lower() not in keyword.lower():
        return f"{keyword} {area}"
    if keyword:
        return keyword
    if args.deal == "rent":
        return f"casas para arrendar {area} Portugal"
    return f"casas à venda {area} Portugal"


def fetch_place_details(api_key: str, place_id: str) -> dict:
    response = requests.get(
        "https://maps.googleapis.com/maps/api/place/details/json",
        params={
            "place_id": place_id,
            "language": "zh-CN",
            "fields": "name,formatted_address,formatted_phone_number,international_phone_number,website,rating,user_ratings_total,business_status,opening_hours,geometry,types,photos,url",
            "key": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("result") or {}


def search_google_places(args: argparse.Namespace) -> list[list[str]]:
    api_key = str(getattr(args, "google_places_key", "") or DEFAULT_PLACES_API_KEY).strip()
    if not api_key:
        raise RuntimeError("缺少 Google Places API Key")
    query = places_query(args)
    print(f"[谷歌搜索] 关键词：{query}", flush=True)
    rows: list[list[str]] = []
    page_token = ""
    exported = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    limit = args.max_listings if args.max_listings and args.max_listings > 0 else 60
    while len(rows) < limit:
        params = {"query": query, "language": "zh-CN", "key": api_key}
        if page_token:
            time.sleep(2)
            params["pagetoken"] = page_token
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status not in {"OK", "ZERO_RESULTS"}:
            raise RuntimeError(f"Google Places 返回 {status}: {payload.get('error_message') or ''}".strip())
        results = payload.get("results") or []
        if not results:
            break
        for item in results:
            if len(rows) >= limit:
                break
            place_id = item.get("place_id") or ""
            details: dict = {}
            try:
                details = fetch_place_details(api_key, place_id) if place_id else {}
            except Exception as exc:
                print(f"[谷歌搜索] 详情失败 {place_id}: {exc}", flush=True)
            name = details.get("name") or item.get("name") or ""
            address = details.get("formatted_address") or item.get("formatted_address") or ""
            maps_url = (
                "https://www.google.com/maps/search/?api=1&"
                + urlencode({"query": f"{name} {address}".strip(), "query_place_id": place_id})
            )
            phone = details.get("international_phone_number") or details.get("formatted_phone_number") or "N/A"
            website = details.get("website") or "N/A"
            rating = details.get("rating") if details.get("rating") is not None else item.get("rating", "")
            reviews = details.get("user_ratings_total")
            if reviews is None:
                reviews = item.get("user_ratings_total", "")
            status_text = details.get("business_status") or item.get("business_status") or ""
            hours = format_opening_hours((details.get("opening_hours") or {}).get("weekday_text") or []) or "N/A"
            loc = (details.get("geometry") or item.get("geometry") or {}).get("location") or {}
            types = ", ".join(details.get("types") or item.get("types") or [])
            photos = details.get("photos") or item.get("photos") or []
            photo_links = []
            for photo in photos[:5]:
                ref = photo.get("photo_reference")
                if ref:
                    photo_links.append(
                        "https://maps.googleapis.com/maps/api/place/photo?"
                        + urlencode({"maxwidth": 1200, "photoreference": ref, "key": api_key})
                    )
            rows.append(
                [
                    name,
                    address,
                    maps_url,
                    phone,
                    website,
                    rating,
                    reviews,
                    status_text,
                    hours,
                    loc.get("lat", ""),
                    loc.get("lng", ""),
                    place_id,
                    types,
                    "",
                    " | ".join(photo_links),
                    str(getattr(args, "keyword", "") or query),
                    args.area,
                    exported,
                ]
            )
            print(f"[谷歌搜索] 已取 {len(rows)}：{name}", flush=True)
        page_token = payload.get("next_page_token") or ""
        if not page_token:
            break
    print(f"[谷歌搜索] 共取得 {len(rows)} 条", flush=True)
    return rows


def run_google_places_to_sheet(args: argparse.Namespace, exporter: GoogleExporter | None) -> int:
    try:
        places = search_google_places(args)
    except Exception as exc:
        print(f"[谷歌搜索] 失败：{exc}", flush=True)
        return 0
    if not exporter or args.no_write_sheet:
        print("[谷歌搜索] 未写入表格（未启用写表）", flush=True)
        return len(places)
    sheet_name = getattr(args, "maps_sheet_name", None) or DEFAULT_MAPS_SHEET_NAME
    existing: set[str] = set()
    try:
        existing = exporter.existing_place_ids(args.sheet_id, sheet_name)
    except Exception as exc:
        print(f"[排重警告] 读取 {sheet_name} 失败：{exc}", flush=True)
    fresh = [row for row in places if not row[11] or row[11] not in existing]
    skipped = len(places) - len(fresh)
    if skipped:
        print(f"[排重] 跳过 {sheet_name} 已有 {skipped} 条", flush=True)
    if not fresh:
        print(f"[谷歌搜索] 没有新地点需要写入 {sheet_name}", flush=True)
        return 0
    exporter.append_place_rows(args.sheet_id, sheet_name, fresh)
    return len(fresh)


def make_exporter(args: argparse.Namespace) -> GoogleExporter:
    credentials_path = Path(args.google_credentials)
    token_path = Path(args.google_token)
    service_account_path = Path(args.service_account)
    drive_auth_mode = args.auth_mode or args.drive_auth_mode
    sheet_auth_mode = args.auth_mode or args.sheet_auth_mode
    credentials_path, token_path, service_account_path = resolve_google_paths(
        credentials_path, token_path, service_account_path
    )
    if (drive_auth_mode == "oauth" or sheet_auth_mode == "oauth") and classify_google_json(credentials_path) != "oauth-client":
        raise FileNotFoundError(f"找不到 Google OAuth 客户端文件：{credentials_path}")
    if drive_auth_mode == "service-account" and classify_google_json(service_account_path) != "service-account":
        print("[授权] 服务账号不可用，Drive 改用 OAuth", flush=True)
        drive_auth_mode = "oauth"
    if sheet_auth_mode == "service-account" and classify_google_json(service_account_path) != "service-account":
        print("[授权] 服务账号不可用，表格改用 OAuth", flush=True)
        sheet_auth_mode = "oauth"
    return GoogleExporter(
        credentials_path,
        token_path,
        args.drive_parent_folder_id,
        drive_auth_mode,
        sheet_auth_mode,
        service_account_path,
    )


def make_browser(args: argparse.Namespace) -> BrowserFetcher | None:
    if args.browser_mode == "off" and not args.login:
        return None
    return BrowserFetcher(
        visible=args.browser_visible,
        profile_dir=Path(args.browser_profile),
        wait_seconds=args.browser_wait_seconds,
        backend=args.browser_backend,
        cdp_url=args.cdp_url or None,
    )


def run_login(args: argparse.Namespace) -> int:
    profile = Path(args.browser_profile).expanduser()
    if not profile.is_absolute():
        profile = Path.cwd() / profile
    try:
        opened = open_login_browser(list(args.sites), profile)
        print(f"[登录] 浏览器已打开，请在窗口里登录。完成后回到软件点「标记已登录」。", flush=True)
        print(f"[登录] CDP：{opened['cdp_url']}", flush=True)
        return 0
    except Exception as exc:
        print(f"[登录] 直接打开浏览器失败：{exc}", flush=True)
        browser = make_browser(args)
        if not browser:
            raise RuntimeError("登录模式必须启用浏览器") from exc
        try:
            browser.login_sites(list(args.sites))
            return 0
        finally:
            browser.close()


def main() -> int:
    args = parse_args()
    if args.login:
        return run_login(args)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8,zh;q=0.7",
        }
    )
    browser = make_browser(args)

    listing_urls: list[str] = []
    seen_urls: set[str] = set()
    for base_url in get_base_search_urls(args):
        empty_pages = 0
        site_added = 0
        print(f"[开始网站] {source_from_url(base_url)} {base_url}", flush=True)
        for url in iter_one_site_urls(base_url, args):
            print(f"[搜索页] {url}", flush=True)
            if looks_like_listing(url) and not is_google_maps_url(url) and not is_google_search_url(url):
                candidates = [url]
            else:
                try:
                    page_html = fetch_page(session, url, args, browser)
                    link_limit = args.max_listings if args.max_listings and args.max_listings > 0 else 200
                    candidates = discover_listing_urls(url, page_html, link_limit)
                    if browser and (is_google_maps_url(url) or is_google_search_url(url)):
                        for card in browser.extract_google_cards():
                            card_url = card.get("url") or ""
                            if card_url and card_url not in candidates:
                                candidates.append(card_url)
                except Exception as exc:
                    print(f"[搜索失败] {url}: {exc}", flush=True)
                    empty_pages += 1
                    if empty_pages >= args.stop_empty_pages:
                        print(f"[跳过网站] 连续 {empty_pages} 个搜索页没有可用结果，继续下一个网站", flush=True)
                        break
                    continue
            new_count = 0
            for candidate in candidates:
                if candidate not in seen_urls:
                    seen_urls.add(candidate)
                    listing_urls.append(candidate)
                    new_count += 1
                    site_added += 1
                if args.max_listings and args.max_listings > 0 and len(listing_urls) >= args.max_listings:
                    break
            print(f"[搜索页完成] 新增 {new_count} 个房源，累计 {len(listing_urls)} 个", flush=True)
            empty_pages = 0 if new_count else empty_pages + 1
            if empty_pages >= args.stop_empty_pages:
                print(f"[结束网站] 连续 {empty_pages} 个搜索页没有新房源，继续下一个网站", flush=True)
                break
            if args.max_listings and args.max_listings > 0 and len(listing_urls) >= args.max_listings:
                break
        print(f"[网站完成] {source_from_url(base_url)} 新增 {site_added} 个房源", flush=True)
        if args.max_listings and args.max_listings > 0 and len(listing_urls) >= args.max_listings:
            break

    print(f"[发现房源] {len(listing_urls)} 个", flush=True)
    exporter = None
    if args.upload_drive or not args.no_write_sheet:
        exporter = make_exporter(args)

    rows: list[Listing] = []
    for idx, listing_url in enumerate(listing_urls, start=1):
        print(f"[房源 {idx}/{len(listing_urls)}] {listing_url}")
        try:
            page_html = fetch_page(session, listing_url, args, browser)
            listing, images = parse_listing(listing_url, page_html)
            print(f"[解析] 标题：{listing.name}", flush=True)
            print(f"[解析] 候选图片：{len(images)} 张", flush=True)
        except Exception as exc:
            print(f"[房源失败] {listing_url}: {exc}")
            continue

        if not passes_filters(listing, args):
            print("[筛选跳过] 不符合房间数/面积条件")
            continue

        local_files: list[Path] = []
        folder_id = ""
        folder_link = ""
        if exporter and args.upload_drive:
            folder_name = f"{idx:03d}-{listing.source}-{slugify(listing.name, 'listing')}"
            folder_id, folder_link = exporter.create_folder(folder_name)
            listing.photo_cloud_folder = folder_link
            print(f"[云端] 已创建房源文件夹：{folder_link}", flush=True)

        if not args.no_photos and images:
            folder_name = f"{idx:03d}-{listing.source}-{slugify(listing.name, 'listing')}"
            local_folder = Path(args.photo_dir) / folder_name
            local_files = download_images(session, images, local_folder, args.pause)
            listing.photo_local_folder = str(local_folder.resolve())
            listing.image_count = len(local_files)
            if exporter and args.upload_drive and folder_id and local_files:
                try:
                    exporter.upload_files(folder_id, local_files)
                except Exception as exc:
                    print(f"[云端失败] 照片上传失败：{exc}", flush=True)
        elif args.no_photos:
            print("[照片] 已选择不下载照片", flush=True)
        else:
            print("[照片] 页面里没有解析到可下载图片，所以云端文件夹可能为空", flush=True)

        rows.append(listing)
        print(f"[记录] 已加入待写入表格：{listing.name}", flush=True)

    output_path = Path(args.output)
    write_csv(rows, output_path)
    if exporter and not args.no_write_sheet:
        exporter.append_listings(args.sheet_id, args.sheet_name, rows)
    print(f"[完成] 已写入 {output_path.resolve()}，共 {len(rows)} 条")
    if browser:
        browser.close()
    return 0


def main_sequential() -> int:
    args = parse_args()
    if args.login:
        return run_login(args)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8,zh;q=0.7",
        }
    )

    only_maps = args.sites == ["google_maps"] and not args.seed_url
    browser = None if only_maps else make_browser(args)

    exporter = None
    if args.upload_drive or not args.no_write_sheet:
        exporter = make_exporter(args)

    output_path = Path(args.output)
    rows: list[Listing] = []
    seen_urls: set[str] = set()
    existing_sheet_urls: set[str] = set()
    if exporter and not args.no_write_sheet:
        try:
            existing_sheet_urls = exporter.existing_urls(args.sheet_id, args.sheet_name)
            seen_urls.update(existing_sheet_urls)
        except Exception as exc:
            print(f"[排重警告] 读取表格已有 URL 失败：{exc}", flush=True)
    write_csv(rows, output_path)

    maps_saved = 0
    if "google_maps" in args.sites:
        maps_saved = run_google_places_to_sheet(args, exporter)
        print(f"[谷歌搜索] 已按工作表1格式登记 {maps_saved} 条", flush=True)
        args.sites = [site for site in args.sites if site != "google_maps"]
        if not args.sites and not args.seed_url:
            print(f"[完成] 谷歌关键词已写入工作表1，共 {maps_saved} 条新纪录", flush=True)
            if browser:
                browser.close()
            return 0

    def reached_limit() -> bool:
        return bool(args.max_listings and args.max_listings > 0 and len(rows) >= args.max_listings)

    def handle_listing(listing_url: str, site_label: str) -> None:
        if listing_url in existing_sheet_urls:
            print(f"[排重跳过] 表格已存在：{listing_url}", flush=True)
            return
        if listing_url in seen_urls:
            print(f"[排重跳过] 本次已处理：{listing_url}", flush=True)
            return
        if reached_limit():
            return
        seen_urls.add(listing_url)
        saved_no = len(rows) + 1
        checked_no = len(seen_urls)
        skip_reason = candidate_should_skip(listing_url, args)
        if skip_reason:
            print(f"[{site_label}] 预筛跳过：{skip_reason} | {listing_url}", flush=True)
            return
        print(f"[{site_label}] 检查候选 {checked_no}，如果符合将保存为第 {saved_no} 条：{listing_url}", flush=True)
        try:
            page_html = fetch_page(session, listing_url, args, browser)
            listing, images = parse_listing(listing_url, page_html)
            print(f"[解析] 标题：{listing.name}", flush=True)
            print(f"[解析] 候选图片：{len(images)} 张", flush=True)
        except Exception as exc:
            print(f"[房源失败] {listing_url}: {exc}", flush=True)
            return

        if not passes_filters(listing, args):
            print("[筛选跳过] 不符合条件，不写入表格", flush=True)
            return

        folder_id = ""
        if exporter and args.upload_drive:
            folder_name = f"{saved_no:03d}-{listing.source}-{slugify(listing.name, 'listing')}"
            try:
                folder_id, folder_link = exporter.create_folder(folder_name)
                listing.photo_cloud_folder = folder_link
                print(f"[云端] 已创建房源文件夹：{folder_link}", flush=True)
            except Exception as exc:
                print(f"[云端失败] 创建房源文件夹失败：{exc}", flush=True)

        if args.no_photos:
            print("[照片] 已选择不下载照片", flush=True)
        elif images:
            folder_name = f"{saved_no:03d}-{listing.source}-{slugify(listing.name, 'listing')}"
            local_folder = Path(args.photo_dir) / folder_name
            local_files = download_images(session, images, local_folder, args.pause)
            listing.photo_local_folder = str(local_folder.resolve())
            listing.image_count = len(local_files)
            if exporter and args.upload_drive and folder_id and local_files:
                try:
                    exporter.upload_files(folder_id, local_files)
                except Exception as exc:
                    print(f"[云端失败] 照片上传失败：{exc}", flush=True)
            elif exporter and args.upload_drive and not local_files:
                print("[照片] 候选图片下载失败，云端文件夹可能为空", flush=True)
        else:
            print("[照片] 页面里没有解析到可下载图片，云端文件夹可能为空", flush=True)

        rows.append(listing)
        write_csv(rows, output_path)
        print(f"[CSV] 已更新本地文件：{output_path.resolve()}，当前 {len(rows)} 条", flush=True)
        if exporter and not args.no_write_sheet:
            try:
                exporter.append_listings(args.sheet_id, args.sheet_name, [listing])
            except Exception as exc:
                print(f"[表格失败] 写入 Google 表格超时或失败，房源已保存在本地 CSV：{exc}", flush=True)
        print(f"[记录] 已完成并写入：{listing.name}", flush=True)

    def persist_listing(listing: Listing, images: list[str] | None = None) -> None:
        if reached_limit():
            return
        images = images or []
        if not passes_filters(listing, args):
            print("[筛选跳过] 不符合条件，不写入表格", flush=True)
            return
        saved_no = len(rows) + 1
        folder_id = ""
        if exporter and args.upload_drive:
            folder_name = f"{saved_no:03d}-{listing.source}-{slugify(listing.name, 'listing')}"
            try:
                folder_id, folder_link = exporter.create_folder(folder_name)
                listing.photo_cloud_folder = folder_link
                print(f"[云端] 已创建房源文件夹：{folder_link}", flush=True)
            except Exception as exc:
                print(f"[云端失败] 创建房源文件夹失败：{exc}", flush=True)
        if args.no_photos:
            print("[照片] 已选择不下载照片", flush=True)
        elif images:
            folder_name = f"{saved_no:03d}-{listing.source}-{slugify(listing.name, 'listing')}"
            local_folder = Path(args.photo_dir) / folder_name
            local_files = download_images(session, images, local_folder, args.pause)
            listing.photo_local_folder = str(local_folder.resolve())
            listing.image_count = len(local_files)
            if exporter and args.upload_drive and folder_id and local_files:
                try:
                    exporter.upload_files(folder_id, local_files)
                except Exception as exc:
                    print(f"[云端失败] 照片上传失败：{exc}", flush=True)
        rows.append(listing)
        write_csv(rows, output_path)
        print(f"[CSV] 已更新本地文件：{output_path.resolve()}，当前 {len(rows)} 条", flush=True)
        if exporter and not args.no_write_sheet:
            try:
                exporter.append_listings(args.sheet_id, args.sheet_name, [listing])
            except Exception as exc:
                print(f"[表格失败] 写入 Google 表格超时或失败，房源已保存在本地 CSV：{exc}", flush=True)
        print(f"[记录] 已完成并写入：{listing.name}", flush=True)

    def handle_maps_card(card: dict[str, str], site_label: str) -> None:
        listing_url = (card.get("url") or "").strip()
        if not listing_url:
            return
        if listing_url in existing_sheet_urls:
            print(f"[排重跳过] 表格已存在：{listing_url}", flush=True)
            return
        if listing_url in seen_urls:
            print(f"[排重跳过] 本次已处理：{listing_url}", flush=True)
            return
        if reached_limit():
            return
        seen_urls.add(listing_url)
        listing = listing_from_card(card, fallback_location=args.area)
        print(f"[{site_label}] 保存谷歌地图结果：{listing.name} | {listing_url}", flush=True)
        persist_listing(listing)

    try:
        for base_url in get_base_search_urls(args):
            if reached_limit():
                break
            site_label = source_from_url(base_url)
            empty_pages = 0
            site_saved_before = len(rows)
            print(f"[开始网站] {site_label} {base_url}", flush=True)
            for url in iter_one_site_urls(base_url, args):
                if reached_limit():
                    break
                print(f"[{site_label}] 搜索页：{url}", flush=True)
                maps_cards: list[dict[str, str]] = []
                if looks_like_listing(url) and not is_google_maps_url(url) and not is_google_search_url(url):
                    candidates = [url]
                else:
                    try:
                        page_html = fetch_page(session, url, args, browser)
                        candidates = discover_listing_urls(url, page_html, 200)
                        if browser and (is_google_maps_url(url) or is_google_search_url(url)):
                            maps_cards = browser.extract_google_cards()
                            for card in maps_cards:
                                card_url = card.get("url") or ""
                                if card_url and card_url not in candidates:
                                    candidates.append(card_url)
                    except Exception as exc:
                        print(f"[{site_label}] 搜索失败：{exc}", flush=True)
                        empty_pages += 1
                        if empty_pages >= args.stop_empty_pages:
                            print(f"[{site_label}] 连续 {empty_pages} 页失败/无结果，进入下一个网站", flush=True)
                            break
                        continue

                new_candidates = [candidate for candidate in candidates if candidate not in seen_urls]
                print(f"[{site_label}] 本页发现 {len(candidates)} 个链接，其中新链接 {len(new_candidates)} 个", flush=True)
                if not new_candidates:
                    empty_pages += 1
                    if empty_pages >= args.stop_empty_pages:
                        print(f"[{site_label}] 连续 {empty_pages} 页没有新房源，进入下一个网站", flush=True)
                        break
                    continue
                empty_pages = 0
                card_by_url = {item.get("url", ""): item for item in maps_cards if item.get("url")}
                for candidate in new_candidates:
                    card = card_by_url.get(candidate)
                    if card and source_from_url(candidate) == "google_maps":
                        handle_maps_card(card, site_label)
                    else:
                        handle_listing(candidate, site_label)
                    if reached_limit():
                        break
            print(f"[网站完成] {site_label} 保存 {len(rows) - site_saved_before} 条，累计 {len(rows)} 条", flush=True)

        print(f"[完成] 已写入 {output_path.resolve()}，共 {len(rows)} 条", flush=True)
        return 0
    finally:
        if browser:
            browser.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main_sequential())
    except KeyboardInterrupt:
        print("\n已取消")
        raise SystemExit(130)
