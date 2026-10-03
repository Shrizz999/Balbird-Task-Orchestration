"""
Extension Requests view for the manager dashboard.

Shows all pending deadline extension requests submitted by employees,
and lets the manager approve / reject each one, optionally overriding
the deadline with a custom date.
"""

import sys
import os
import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry

# Ensure the project root is importable (so `services.*` resolves)
if getattr(sys, 'frozen', False):
    _project_root = os.path.dirname(sys.executable)
else:
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from services.extension_store import (
    get_all_pending_requests,
    get_all_requests,
    decide_request,
)
from .components import (
    BG_COLOR, CARD_BG, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED,
    ACCENT_COLOR, FONT_H1, FONT_BOLD, FONT_MAIN, FONT_SMALL, CHART_COLORS,
)
from data.repository import DataRepository

# Extra colours
SUCCESS_COLOR = "#10b981"
WARNING_COLOR = "#f59e0b"
ERROR_COLOR = "#ef4444"

REFRESH_INTERVAL_MS = 30_000  # Auto-poll for new requests every 30 s


class ExtensionRequestsView(ctk.CTkFrame):
    """Manager-facing view that lists and lets the manager decide on
    deadline extension requests submitted by employees."""

    def __init__(self, master, repository: DataRepository, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self.repository = repository

        # --- Header ---
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(20, 5))

        ctk.CTkLabel(hdr, text="Deadline Extension Requests", font=FONT_H1,
                     text_color=TEXT_COLOR).pack(side="left")

        self.btn_refresh = ctk.CTkButton(
            hdr, text="↻ Refresh", width=90, font=FONT_BOLD,
            fg_color=ACCENT_COLOR, hover_color="#0284c7",
            command=self.refresh_data)
        self.btn_refresh.pack(side="right")

        # --- Filter toggle ---
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(5, 10))

        self.show_all_var = ctk.BooleanVar(value=False)
        self.chk_show_all = ctk.CTkCheckBox(
            filter_frame, text="Show decided requests too",
            variable=self.show_all_var, font=FONT_MAIN,
            text_color=TEXT_MUTED, command=self._render_cards)
        self.chk_show_all.pack(side="left")

        self.lbl_count = ctk.CTkLabel(filter_frame, text="", font=FONT_SMALL,
                                       text_color=TEXT_MUTED)
        self.lbl_count.pack(side="right")

        # --- Scrollable cards ---
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.scroll.grid_columnconfigure(0, weight=1)

        self._all_requests = []
        self._render_cards()

        # Auto-refresh
        self._schedule_auto_poll()

    # ── Data ─────────────────────────────────────────────────────────

    def refresh_data(self):
        """Re-read the extension store and redraw."""
        self._all_requests = get_all_requests()
        self._render_cards()

    def _schedule_auto_poll(self):
        def _tick():
            self._all_requests = get_all_requests()
            self._render_cards()
            self.after(REFRESH_INTERVAL_MS, _tick)
        self.after(REFRESH_INTERVAL_MS, _tick)

    # ── UI ───────────────────────────────────────────────────────────

    def _render_cards(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        self._all_requests = get_all_requests()

        if self.show_all_var.get():
            display = self._all_requests
        else:
            display = [r for r in self._all_requests if r["status"] == "Pending"]

        pending_count = sum(1 for r in self._all_requests if r["status"] == "Pending")
        self.lbl_count.configure(text=f"{pending_count} pending request(s)")

        if not display:
            ctk.CTkLabel(self.scroll, text="No extension requests to show.",
                         font=FONT_MAIN, text_color=TEXT_MUTED).pack(pady=40)
            return

        for idx, req in enumerate(reversed(display)):
            self._build_request_card(idx, req)

    def _build_request_card(self, idx: int, req: dict):
        is_pending = req["status"] == "Pending"

        card = ctk.CTkFrame(self.scroll, fg_color=CARD_BG, border_width=1,
                            border_color=BORDER_COLOR, corner_radius=8)
        card.grid(row=idx, column=0, sticky="ew", pady=6, padx=4)
        card.grid_columnconfigure(1, weight=1)

        # ── Left: status badge ──
        if req["status"] == "Pending":
            badge_color, badge_text = WARNING_COLOR, "⏳ PENDING"
        elif req["status"] == "Approved":
            badge_color, badge_text = SUCCESS_COLOR, "✓ APPROVED"
        else:
            badge_color, badge_text = ERROR_COLOR, "✗ REJECTED"

        badge = ctk.CTkLabel(card, text=badge_text, font=("Inter", 11, "bold"),
                             text_color="white", fg_color=badge_color,
                             corner_radius=4, width=100, height=26)
        badge.grid(row=0, column=0, padx=(12, 8), pady=(12, 4), sticky="nw")

        # ── Right: details ──
        details = ctk.CTkFrame(card, fg_color="transparent")
        details.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(10, 4))
        details.grid_columnconfigure(0, weight=1)

        # Employee + task ID
        ctk.CTkLabel(details,
                     text=f"{req['employee']}  —  Task [{req['task_id']}]",
                     font=FONT_BOLD, text_color=TEXT_COLOR).grid(
                         row=0, column=0, sticky="w")

        # Task description
        desc = req.get("task_description", "")
        if len(desc) > 100:
            desc = desc[:100] + "…"
        ctk.CTkLabel(details, text=desc, font=FONT_MAIN,
                     text_color=TEXT_MUTED, wraplength=500, justify="left").grid(
                         row=1, column=0, sticky="w", pady=(2, 4))

        # Deadline info row
        dl_frame = ctk.CTkFrame(details, fg_color="transparent")
        dl_frame.grid(row=2, column=0, sticky="w", pady=(0, 2))

        ctk.CTkLabel(dl_frame, text=f"Current: {req['current_deadline'] or '—'}",
                     font=FONT_SMALL, text_color=TEXT_MUTED).pack(side="left", padx=(0, 15))
        ctk.CTkLabel(dl_frame, text=f"Requested: {req['requested_deadline']}",
                     font=("Inter", 10, "bold"), text_color=ACCENT_COLOR).pack(side="left", padx=(0, 15))
        ctk.CTkLabel(dl_frame, text=f"Submitted: {req['submitted_at']}",
                     font=FONT_SMALL, text_color=TEXT_MUTED).pack(side="left")

        # Reason
        ctk.CTkLabel(details, text=f"Reason: {req['reason']}",
                     font=FONT_SMALL, text_color=TEXT_COLOR,
                     wraplength=500, justify="left").grid(
                         row=3, column=0, sticky="w", pady=(2, 6))

        if is_pending:
            self._build_action_row(card, req, row=1)
        else:
            # Show decision info
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))

            final_dl = req.get("manager_deadline") or req["requested_deadline"]
            decided_at = req.get("decided_at", "")
            note = req.get("manager_note", "")
            info_parts = [f"Final deadline: {final_dl}", f"Decided: {decided_at}"]
            if note:
                info_parts.append(f"Note: {note}")
            ctk.CTkLabel(info_frame, text="  |  ".join(info_parts),
                         font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")

    def _build_action_row(self, card, req, row):
        """Build the approve/reject controls for a pending request."""
        action = ctk.CTkFrame(card, fg_color="transparent")
        action.grid(row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 12))

        # Custom deadline override (optional)
        ctk.CTkLabel(action, text="Override deadline:", font=FONT_SMALL,
                     text_color=TEXT_MUTED).pack(side="left", padx=(0, 5))

        deadline_entry = DateEntry(action, width=14, date_pattern='dd/mm/yyyy',
                                   background="#1e293b", foreground="white",
                                   borderwidth=2, font=FONT_SMALL)
        
        # Default to the requested deadline
        if req.get("requested_deadline"):
            try:
                from datetime import datetime
                dt = datetime.strptime(req["requested_deadline"], "%d/%m/%Y")
                deadline_entry.set_date(dt)
            except ValueError:
                pass
                
        deadline_entry.pack(side="left", padx=(0, 10))

        # Manager note
        ctk.CTkLabel(action, text="Note:", font=FONT_SMALL,
                     text_color=TEXT_MUTED).pack(side="left", padx=(0, 5))
        note_entry = ctk.CTkEntry(action, width=160, font=FONT_SMALL,
                                  placeholder_text="optional note…",
                                  fg_color=BG_COLOR, border_width=1,
                                  border_color=BORDER_COLOR, text_color=TEXT_COLOR)
        note_entry.pack(side="left", padx=(0, 15))

        # Buttons
        def _approve():
            custom_dl = deadline_entry.get().strip()
            note = note_entry.get().strip()
            decide_request(req["id"], "Approved",
                           manager_deadline=custom_dl, manager_note=note)
                           
            task_obj = next((t for t in self.repository.get_tasks() if t.id == req["task_id"]), None)
            if task_obj:
                try:
                    from services.n8n_client import N8nClient
                    from datetime import datetime
                    n8n = N8nClient()
                    orig_reason = req.get("reason", "")
                    manager_msg = f"Approved: {note}" if note else "Extension Approved"
                    
                    update_payload = {
                        "Task ID": task_obj.id,
                        "Date": task_obj.date,
                        "Task Description": task_obj.task,
                        "Assigned To": task_obj.person,
                        "Assigned By": "Manager",
                        "Deadline": custom_dl,
                        "Priority": task_obj.priority,
                        "Status": "Pending",
                        "Reason": f"{orig_reason} | Manager: {manager_msg}",
                        "Source": task_obj.source,
                        "Updated By": "Manager UI",
                        "Last Updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                    n8n.submit_live_updates([update_payload])
                except Exception as e:
                    print(f"Failed to update Google Sheet via n8n: {e}")
                    
            self.refresh_data()

        def _reject():
            note = note_entry.get().strip()
            decide_request(req["id"], "Rejected",
                           manager_deadline="", manager_note=note)
                           
            task_obj = next((t for t in self.repository.get_tasks() if t.id == req["task_id"]), None)
            if task_obj:
                try:
                    from services.n8n_client import N8nClient
                    from datetime import datetime
                    n8n = N8nClient()
                    orig_reason = req.get("reason", "")
                    manager_msg = f"Rejected: {note}" if note else "Extension Rejected"
                    
                    update_payload = {
                        "Task ID": task_obj.id,
                        "Date": task_obj.date,
                        "Task Description": task_obj.task,
                        "Assigned To": task_obj.person,
                        "Assigned By": "Manager",
                        "Deadline": req["current_deadline"],
                        "Priority": task_obj.priority,
                        "Status": "Pending",
                        "Reason": f"{orig_reason} | Manager: {manager_msg}",
                        "Source": task_obj.source,
                        "Updated By": "Manager UI",
                        "Last Updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                    n8n.submit_live_updates([update_payload])
                except Exception as e:
                    print(f"Failed to update Google Sheet via n8n: {e}")
                    
            self.refresh_data()

        ctk.CTkButton(action, text="✓ Approve", width=90, height=30,
                      font=("Inter", 12, "bold"),
                      fg_color=SUCCESS_COLOR, hover_color="#059669",
                      command=_approve).pack(side="right", padx=(5, 0))

        ctk.CTkButton(action, text="✗ Reject", width=90, height=30,
                      font=("Inter", 12, "bold"),
                      fg_color=ERROR_COLOR, hover_color="#dc2626",
                      command=_reject).pack(side="right")
