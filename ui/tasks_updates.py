import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from config import COLORS, FONTS
from services.n8n_client import N8nClient

class TasksUpdatesFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.n8n_client = N8nClient()
        
        self.pack(fill="both", expand=True, padx=20, pady=20)
        self.setup_ui()

    def setup_ui(self):
        lbl_header = ctk.CTkLabel(self, text="Meeting Transcript", font=FONTS["header"], text_color=COLORS["text_main"])
        lbl_header.pack(anchor="w", pady=(0, 20))

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)

        # ── Left: Transcript ──
        card_transcript = ctk.CTkFrame(container, fg_color=COLORS["card_bg"], corner_radius=8)
        card_transcript.grid(row=0, column=0, sticky="nsew")

        lbl_transcript = ctk.CTkLabel(card_transcript, text="Meeting Transcript", font=FONTS["subheader"], text_color=COLORS["text_main"])
        lbl_transcript.pack(anchor="w", padx=20, pady=(20, 10))

        self.text_transcript = ctk.CTkTextbox(card_transcript, height=300)
        self.text_transcript.pack(fill="both", expand=True, padx=20, pady=10)

        btn_row = ctk.CTkFrame(card_transcript, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        
        self.btn_browse = ctk.CTkButton(btn_row, text="Browse .txt", width=120, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self.browse_file)
        self.btn_browse.pack(side="left")

        self.btn_clear = ctk.CTkButton(btn_row, text="Clear", width=100, fg_color="transparent", text_color=COLORS["text_main"], border_width=1, command=lambda: self.text_transcript.delete("1.0", "end"))
        self.btn_clear.pack(side="right")

        self.btn_submit_transcript = ctk.CTkButton(card_transcript, text="Send Transcript to n8n", font=FONTS["body_bold"], fg_color=COLORS["highlight"], hover_color=COLORS["highlight_hover"], height=40, command=self.submit_transcript_only)
        self.btn_submit_transcript.pack(fill="x", padx=20, pady=(0, 20))

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select Transcript", filetypes=[("Text files", "*.txt")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.text_transcript.delete("1.0", "end")
                    self.text_transcript.insert("1.0", f.read())
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read file:\n{e}")

    def submit_transcript_only(self):
        transcript = self.text_transcript.get("1.0", "end").strip()
        if not transcript:
            messagebox.showwarning("Missing Info", "No transcript provided.")
            return

        self.btn_submit_transcript.configure(state="disabled")
        try:
            success = self.n8n_client.submit_transcript(transcript)
            if success:
                messagebox.showinfo("Success", "Transcript successfully sent to n8n.")
                self.text_transcript.delete("1.0", "end")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit transcript:\n{e}")
        finally:
            self.btn_submit_transcript.configure(state="normal")
