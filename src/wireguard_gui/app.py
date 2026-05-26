import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import os
import threading

from .wg_manager import list_profiles, get_status, toggle_connection, import_profile, save_config

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AddProfileModal(ctk.CTkToplevel):
    def __init__(self, master, refresh_callback):
        super().__init__(master)
        self.refresh_callback = refresh_callback
        self.title("Add Profile")
        self.geometry("500x550")
        self.minsize(400, 400)
        self.wait_visibility()  # Wait for window to be viewable before grabbing
        self.grab_set()  # Make modal

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        self.header = ctk.CTkLabel(self, text="Add New Configuration", font=ctk.CTkFont(size=20, weight="bold"))
        self.header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")

        # Name input
        self.name_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.name_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.name_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.name_frame, text="Profile Name:").grid(row=0, column=0, padx=(0,10))
        self.name_entry = ctk.CTkEntry(self.name_frame, placeholder_text="e.g. wg0")
        self.name_entry.grid(row=0, column=1, sticky="ew")

        # Text area
        self.textbox = ctk.CTkTextbox(self, width=400, height=300)
        self.textbox.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.textbox.insert("0.0", "put your WireGuard config here...")
        self.textbox.configure(text_color="gray")

        def clear_placeholder(event):
            if self.textbox.get("0.0", "end-1c") == "put your WireGuard config here...":
                self.textbox.delete("0.0", "end")
                self.textbox.configure(text_color=["gray10", "gray90"])

        def add_placeholder(event):
            if not self.textbox.get("0.0", "end-1c").strip():
                self.textbox.insert("0.0", "put your WireGuard config here...")
                self.textbox.configure(text_color="gray")

        self.textbox.bind("<FocusIn>", clear_placeholder)
        self.textbox.bind("<FocusOut>", add_placeholder)

        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        self.btn_frame.grid_columnconfigure(1, weight=1)

        self.import_btn = ctk.CTkButton(self.btn_frame, text="Import the File Instead", command=self.import_file, fg_color="transparent", border_width=1)
        self.import_btn.grid(row=0, column=0, sticky="w")

        self.save_btn = ctk.CTkButton(self.btn_frame, text="Save & Add", command=self.save_text, fg_color="#2FA572", hover_color="#238258")
        self.save_btn.grid(row=0, column=2, sticky="e")

    def save_text(self):
        name = self.name_entry.get().strip()
        content = self.textbox.get("0.0", "end").strip()
        if not name:
            messagebox.showerror("Error", "Please add a profile name.", parent=self)
            return
        if not content or content.startswith("put your"):
            messagebox.showerror("Error", "Please put the configuration content.", parent=self)
            return
            
        success, msg = save_config(name, content)
        if success:
            self.refresh_callback()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)

    def import_file(self):
        file_path = filedialog.askopenfilename(
            title="Select WireGuard Config",
            filetypes=(("WireGuard Configs", "*.conf"), ("All Files", "*.*")),
            parent=self
        )
        if file_path:
            success, msg = import_profile(file_path)
            if success:
                self.refresh_callback()
                self.destroy()
            else:
                messagebox.showerror("Import Error", msg, parent=self)

class WireGuardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WireGuard Manager")
        self.geometry("800x550")
        self.minsize(700, 500)

        self.profiles = []
        self.selected_profile = None
        self.is_connected = False
        
        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar setup
        self.setup_sidebar()

        # Main frame setup
        self.setup_main_frame()

        # Load initial profiles
        self.refresh_profiles()
        
        # Start update loop
        self.update_status_loop()

    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1E1E1E")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(1, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="WireGuard", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 15))

        self.profile_listbox = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="Your Profiles", label_font=ctk.CTkFont(size=14, weight="bold"), fg_color="transparent")
        self.profile_listbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.add_button = ctk.CTkButton(self.sidebar_frame, text="+ Add Profile", command=self.open_add_modal, height=40, font=ctk.CTkFont(weight="bold"))
        self.add_button.grid(row=2, column=0, padx=20, pady=25)

    def setup_main_frame(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#121212")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Header Area
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="ew")
        
        self.profile_title = ctk.CTkLabel(self.header_frame, text="Select a Profile", font=ctk.CTkFont(size=36, weight="bold"))
        self.profile_title.pack(side="left")

        # Connection Card
        self.status_card = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#242424")
        self.status_card.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        self.status_card.grid_columnconfigure(1, weight=1)

        self.status_indicator = ctk.CTkFrame(self.status_card, width=15, height=15, corner_radius=10, fg_color="gray")
        self.status_indicator.grid(row=0, column=0, padx=(25, 10), pady=30)
        
        self.status_label = ctk.CTkLabel(self.status_card, text="Disconnected", font=ctk.CTkFont(size=20, weight="bold"))
        self.status_label.grid(row=0, column=1, sticky="w", pady=30)

        self.toggle_button = ctk.CTkButton(self.status_card, text="Connect", font=ctk.CTkFont(size=16, weight="bold"), 
                                           height=45, width=150, command=self.toggle_action, state="disabled")
        self.toggle_button.grid(row=0, column=2, padx=25, pady=30)
        
        # Loading Bar (hidden by default)
        self.progress_bar = ctk.CTkProgressBar(self.status_card, mode="indeterminate", height=4)
        self.progress_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=25, pady=(0, 15))
        self.progress_bar.grid_remove() # Hide initially

        # Stats Card
        self.stats_card = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#242424")
        self.stats_card.grid(row=2, column=0, padx=40, pady=20, sticky="nsew")
        
        self.stats_title = ctk.CTkLabel(self.stats_card, text="Connection Statistics", font=ctk.CTkFont(size=18, weight="bold"))
        self.stats_title.pack(anchor="w", padx=25, pady=(20, 10))

        self.stats_label = ctk.CTkLabel(self.stats_card, text="No active connection data.", font=ctk.CTkFont(size=14), justify="left", text_color="#A0A0A0")
        self.stats_label.pack(anchor="w", padx=25, pady=10)

    def open_add_modal(self):
        AddProfileModal(self, self.refresh_profiles)

    def refresh_profiles(self):
        # Clear existing buttons
        for widget in self.profile_listbox.winfo_children():
            widget.destroy()

        self.profiles = list_profiles()
        
        for profile in self.profiles:
            btn = ctk.CTkButton(self.profile_listbox, text=profile, 
                                command=lambda p=profile: self.select_profile(p),
                                fg_color="transparent", text_color="gray90", 
                                hover_color="#333333", anchor="w", font=ctk.CTkFont(size=14))
            btn.pack(fill="x", pady=4, padx=5)
            
        if self.profiles and not self.selected_profile:
            self.select_profile(self.profiles[0])

    def select_profile(self, profile):
        self.selected_profile = profile
        self.profile_title.configure(text=profile)
        self.toggle_button.configure(state="normal")
        self.update_status_view()

    def update_status_loop(self):
        """Periodically update the connection status and stats."""
        # Only poll if we aren't currently loading
        if not self.progress_bar.winfo_ismapped():
            self.update_status_view()
        self.after(3000, self.update_status_loop)

    def update_status_view(self):
        if not self.selected_profile:
            return

        status_data = get_status(self.selected_profile)
        status = status_data.get("status", "unknown")
        
        if status == "connected":
            self.is_connected = True
            self.status_label.configure(text="Connected", text_color="#2FA572")
            self.status_indicator.configure(fg_color="#2FA572")
            self.toggle_button.configure(text="Disconnect", fg_color="#C93B3B", hover_color="#A12F2F")
            
            # Format stats
            peers = status_data.get("peers", [])
            if peers:
                peer = peers[0]
                stats_text = (f"• Endpoint IP:      {peer.get('endpoint', 'N/A')}\n\n"
                              f"• Last Handshake:   {peer.get('latest_handshake', 'N/A')}\n\n"
                              f"• Data Transfer:    {peer.get('transfer', 'N/A')}")
                self.stats_label.configure(text=stats_text, text_color="white")
            else:
                self.stats_label.configure(text="No peer data available.", text_color="#A0A0A0")
                
        elif status == "disconnected":
            self.is_connected = False
            self.status_label.configure(text="Disconnected", text_color="gray")
            self.status_indicator.configure(fg_color="gray")
            self.toggle_button.configure(text="Connect", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"])
            self.stats_label.configure(text="No active connection data.", text_color="#A0A0A0")
        else:
            self.status_label.configure(text="Error", text_color="#C93B3B")
            self.status_indicator.configure(fg_color="#C93B3B")
            self.stats_label.configure(text=f"Error: {status_data.get('message', '')}", text_color="#C93B3B")

    def toggle_action(self):
        if not self.selected_profile:
            return
            
        # UI Loading State
        is_connecting = not self.is_connected
        self.toggle_button.configure(state="disabled", text="Connecting..." if is_connecting else "Disconnecting...")
        self.progress_bar.grid() # Show loader
        self.progress_bar.start()
        
        # Run toggle in a thread so UI doesn't freeze
        threading.Thread(target=self._perform_toggle, args=(is_connecting,), daemon=True).start()

    def _perform_toggle(self, is_connecting):
        success, msg = toggle_connection(self.selected_profile, is_connecting)
        
        # Schedule UI updates back on the main thread
        self.after(0, lambda: self._toggle_finished(success, msg))

    def _toggle_finished(self, success, msg):
        self.progress_bar.stop()
        self.progress_bar.grid_remove() # Hide loader
        self.toggle_button.configure(state="normal")
        
        if not success:
            messagebox.showerror("Connection Error", msg)
            
        self.update_status_view()

def main():
    app = WireGuardApp()
    app.mainloop()

if __name__ == "__main__":
    main()
