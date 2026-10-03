import customtkinter as ctk
from config import COLORS, FONTS

def create_card(parent, title: str, value: str, icon: str = "") -> ctk.CTkFrame:
    card = ctk.CTkFrame(parent, fg_color=COLORS["card_bg"], corner_radius=8)
    
    title_lbl = ctk.CTkLabel(card, text=title, font=FONTS["small"], text_color=COLORS["text_dim"])
    title_lbl.pack(anchor="w", padx=15, pady=(15, 0))
    
    val_text = f"{icon} {value}" if icon else value
    val_lbl = ctk.CTkLabel(card, text=val_text, font=FONTS["subheader"], text_color=COLORS["text_main"])
    val_lbl.pack(anchor="w", padx=15, pady=(5, 15))
    
    return card

class StatusBadge(ctk.CTkFrame):
    def __init__(self, parent, status: str, **kwargs):
        super().__init__(parent, corner_radius=12, **kwargs)
        
        status = status.title()
        if status in ["Completed", "Done"]:
            color = COLORS["success"]
        elif status in ["Pending", "Upcoming"]:
            color = COLORS["accent"]
        elif status in ["Overdue", "Delayed", "Failed"]:
            color = COLORS["error"]
        else:
            color = COLORS["text_dim"]
            
        self.configure(fg_color=color)
        
        lbl = ctk.CTkLabel(self, text=status, font=FONTS["small"], text_color="#ffffff")
        lbl.pack(padx=10, pady=2)
