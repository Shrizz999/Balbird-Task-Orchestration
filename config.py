import os
import sys
from pathlib import Path

# ==============================================================================
# CONFIGURATION
# ==============================================================================
SUPABASE_URL = "https://bzvyqzivhnlqdzjkujyi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ6dnlxeml2aG5scWR6amt1anlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg5Njg1OTksImV4cCI6MjEwNDU0NDU5OX0.Z-C3il7l2Oa6aD-axbnD2wDIwGLMJKhcmwcopU5ZK6Q"

N8N_WEBHOOK_URL = "https://n8n.srv1463077.hstgr.cloud/form/bbdf4375-d5e3-47b0-aef9-90a2e2050f22"
N8N_MONTHLY_UPDATES_WEBHOOK_URL = "https://n8n.srv1463077.hstgr.cloud/webhook/monthly-goals-update"
N8N_EXTENSION_WEBHOOK_URL = "https://n8n.srv1463077.hstgr.cloud/webhook/extension-requests"

# Workspace root directory — works both in dev and in frozen PyInstaller exe
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# For local development/testing without live Google Sheets API, we load local CSVs.
USE_LOCAL_CSV = False
LOCAL_CSV_DIR = BASE_DIR

SHEET_BASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTHrHDX22vdQV7YQKrDOenwKBBenyG98ERPGBysBRRW-iKEuKBAryRb6hOQ_-zNuG2hq0Vd-KlBVN2o/pub?output=csv&gid="

SHEET_GIDS = {
    "Boss": "0",
    "Tasks": "1931533029",
    "Goals": "1837353468",
    "Extensions": "1895469142"
}

CSV_FILES = {
    "Goals": BASE_DIR / "Copy of BalPigeon - Goals.csv",
    "Boss": BASE_DIR / "Copy of BalPigeon - Boss.csv",
    "Tasks": BASE_DIR / "Copy of BalPigeon - Tasks.csv"
}

# ── Business Logic ──
DEPARTMENTS = {
    "SO department": ["Swapnali", "Ganesh"],
    "PO department": [],
    "Sales Department": [],
    "Logistics Department": []
}
ALL_EMPLOYEES = [emp for emps in DEPARTMENTS.values() for emp in emps]
ALL_DEPARTMENTS = list(DEPARTMENTS.keys())

# ── Color Palette ──
# Clean enterprise light mode theme
COLORS = {
    "bg": "#f4f6f9",
    "card_bg": "#ffffff",
    "sidebar_bg": "#1e293b",
    "sidebar_hover": "#334155",
    "sidebar_text": "#f8fafc",
    "sidebar_text_active": "#38bdf8",
    "input_bg": "#ffffff",
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "highlight": "#ef4444",
    "highlight_hover": "#dc2626",
    "text_main": "#1f2937",
    "text_dim": "#6b7280",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "border": "#e5e7eb"
}

FONTS = {
    "header": ("Segoe UI", 24, "bold"),
    "subheader": ("Segoe UI", 16, "bold"),
    "body": ("Segoe UI", 12),
    "body_bold": ("Segoe UI", 12, "bold"),
    "small": ("Segoe UI", 10),
    "console": ("Cascadia Code", 10)
}
