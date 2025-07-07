import tkinter as tk
import requests
import json
import customtkinter as ctk
import math
from datetime import datetime
import os


# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class UpdateVisualizer(ctk.CTkCanvas):
    def __init__(self, master, size=30, **kwargs):
        self.size = size

        # Risolvi il colore di sfondo in modo robusto
        mode = ctk.get_appearance_mode().lower()
        bg_color = "#333333" if mode == "dark" else "#DDDDDD"

        super().__init__(master, width=size, height=size,
                         bg=bg_color, highlightthickness=0, **kwargs)

        self.arc_id = None
        self.text_id = None
        self.last_update_time = datetime.now()
        self.update_interval = 5  # seconds

        self.create_oval(2, 2, size-2, size-2, outline="#333333", width=2)
        self.update_visualization(0)

    def update_visualization(self, elapsed):
        # Calculate progress (0-1)
        progress = elapsed / self.update_interval
        angle = 360 * progress

        # Delete previous arc if exists
        if self.arc_id:
            self.delete(self.arc_id)
        if self.text_id:
            self.delete(self.text_id)

        # Draw progress arc
        if progress < 1:
            self.arc_id = self.create_arc(
                2, 2, self.size-2, self.size-2,
                start=90, extent=-angle,
                outline="#BB86FC", width=2,
                style=tk.ARC
            )

        # Draw remaining time text
        remaining = max(0, self.update_interval - elapsed)
        self.text_id = self.create_text(
            self.size/2, self.size/2,
            text=f"{int(remaining)}",
            fill="#BB86FC",
            font=("Arial", 10)
        )

class HueController:

    def __init__(self, root):
        self.root = root
        self.root.title("Philips Hue Controller")
        self.root.geometry("450x380")

        # Color configuration
        self.ACTIVE_COLOR = "#BB86FC"  # Normal purple
        self.INACTIVE_COLOR = "#8762b5"  # Darker purple
        self.DISABLED_COLOR = "#b2abba"  # Background color

        # Bridge configuration
        self.BRIDGE_IP = self.discover_bridge_ip()
        self.USERNAME = self.load_username()
        self.LIGHTS = self.discover_lights()

        # Track slider changes
        self.slider_changes_enabled = False
        self.initial_brightness = {lid: 50 for lid in self.LIGHTS}

        if not self.USERNAME:
            self.show_connect_button()
        else:
            self.create_widgets()
            self.update_all_lights()
            self.slider_changes_enabled = True
            self.last_update_time = datetime.now()
            self.update_visualizer()

    def load_username(self):
        if os.path.exists("hue_user.json"):
            with open("hue_user.json", "r") as f:
                data = json.load(f)
                return data.get("username")
        return None

    def save_username(self, username):
        with open("hue_user.json", "w") as f:
            json.dump({"username": username}, f)

    def show_connect_button(self):
        self.connect_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.connect_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        label = ctk.CTkLabel(
            self.connect_frame,
            text="Press the button on your Hue Bridge,\nthen click Connect.",
            font=("Arial", 14),
            text_color=self.ACTIVE_COLOR
        )
        label.pack(pady=20)
        btn = ctk.CTkButton(
            self.connect_frame,
            text="Connect to Bridge",
            command=self.register_username
        )
        btn.pack(pady=10)
        self.connect_status = ctk.CTkLabel(self.connect_frame, text="", text_color="red")
        self.connect_status.pack(pady=5)

    def register_username(self):
        url = f"http://{self.BRIDGE_IP}/api"
        payload = {"devicetype": "huecontroller#desktop"}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            data = resp.json()
            if isinstance(data, list) and "success" in data[0]:
                username = data[0]["success"]["username"]
                self.save_username(username)
                self.USERNAME = username
                self.connect_status.configure(text="Success! Restarting...", text_color="green")
                self.connect_frame.after(1500, self.restart_app)
            else:
                self.connect_status.configure(text="Press the bridge button and try again.", text_color="red")
        except Exception as e:
            self.connect_status.configure(text=f"Error: {e}", text_color="red")

    def restart_app(self):
        self.connect_frame.destroy()
        self.create_widgets()
        self.update_all_lights()
        self.slider_changes_enabled = True
        self.last_update_time = datetime.now()
        self.update_visualizer()

    def create_widgets(self):
        # Main container
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header with title and visualizer
        header_frame = ctk.CTkFrame(self.main_frame, fg_color=self.main_frame._fg_color)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        # Title
        self.title = ctk.CTkLabel(
            header_frame,
            text="Hue Light Controller",
            font=("Arial", 20, "bold"),
            text_color=self.ACTIVE_COLOR
        )
        self.title.pack(side=tk.LEFT)

        # Update visualizer
        self.visualizer = UpdateVisualizer(header_frame, size=30)
        self.visualizer.pack(side=tk.RIGHT, padx=10)

        # Last updated label
        self.last_updated_label = ctk.CTkLabel(
            header_frame,
            text="",
            text_color="#888888",
            font=("Arial", 10)
        )
        self.last_updated_label.pack(side=tk.RIGHT)

        # Light controls container
        self.light_vars = {}
        self.light_sliders = {}
        self.light_labels = {}
        self.status_labels = {}

        for light_id, name in sorted(self.LIGHTS.items(), key=lambda x: x[0], reverse=True):
            # Light frame
            frame = ctk.CTkFrame(self.main_frame, corner_radius=8)
            frame.pack(fill=tk.X, padx=10, pady=8)

            # Light name and toggle
            top_frame = ctk.CTkFrame(frame, fg_color="transparent")
            top_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

            ctk.CTkLabel(
                top_frame,
                text=name,
                font=("Arial", 14),
                text_color=self.ACTIVE_COLOR,
                anchor="w"
            ).pack(side=tk.LEFT, padx=5)

            # Toggle switch
            self.light_vars[light_id] = ctk.BooleanVar()
            switch = ctk.CTkSwitch(
                top_frame,
                text="",
                variable=self.light_vars[light_id],
                command=lambda id=light_id: self.toggle_light(id),
                switch_width=40,
                switch_height=20,
                button_color="#FFFFFF",
                button_hover_color="#EEEEEE",
                fg_color=self.DISABLED_COLOR,
                progress_color=self.ACTIVE_COLOR
            )
            switch.pack(side=tk.RIGHT, padx=5)

            # Status label
            self.status_labels[light_id] = ctk.CTkLabel(
                top_frame,
                text="Off",
                text_color="#888888",
                font=("Arial", 12)
            )
            self.status_labels[light_id].pack(side=tk.RIGHT, padx=5)

            # Brightness slider
            self.light_sliders[light_id] = ctk.CTkSlider(
                frame,
                from_=0,
                to=100,
                number_of_steps=100,
                command=lambda val, id=light_id: self.update_brightness(id, val),
                button_color=self.ACTIVE_COLOR,
                button_hover_color="#9A67EA",
                progress_color=self.ACTIVE_COLOR,
                fg_color=self.DISABLED_COLOR
            )
            self.light_sliders[light_id].set(50)
            self.light_sliders[light_id].pack(fill=tk.X, padx=10, pady=(5, 10))

            # Brightness percentage label
            self.light_labels[light_id] = ctk.CTkLabel(
                frame,
                text="50%",
                text_color="white",
                font=("Arial", 12)
            )
            self.light_labels[light_id].pack(pady=(0, 10))

    def update_visualizer(self):
        now = datetime.now()
        elapsed = (now - self.last_update_time).total_seconds()

        # Update the visualizer
        self.visualizer.update_visualization(elapsed % 5)

        # Update last updated text
        if elapsed >= 5:
            self.last_update_time = now
            self.update_all_lights()
            self.last_updated_label.configure(
                text=now.strftime("Last: %H:%M:%S")
            )

        # Schedule next update
        self.root.after(200, self.update_visualizer)

    def update_slider_color(self, light_id, is_on):
        """Update slider colors based on light state"""
        slider = self.light_sliders[light_id]
        if is_on:
            slider.configure(button_color=self.ACTIVE_COLOR,
                           progress_color=self.ACTIVE_COLOR)
        else:
            slider.configure(button_color=self.INACTIVE_COLOR,
                           progress_color=self.INACTIVE_COLOR)

    def toggle_light(self, light_id):
        try:
            new_state = self.light_vars[light_id].get()
            url = f"http://{self.BRIDGE_IP}/api/{self.USERNAME}/lights/{light_id}/state"
            payload = {"on": new_state}
            requests.put(url, json=payload, timeout=3)

            # Update UI
            status = "On" if new_state else "Off"
            color = self.ACTIVE_COLOR if new_state else "#888888"
            self.status_labels[light_id].configure(text=status, text_color=color)
            self.update_slider_color(light_id, new_state)

            # If turning on, restore brightness
            if new_state:
                self.update_brightness(light_id, self.light_sliders[light_id].get())
        except Exception as e:
            print(f"Error toggling light {light_id}: {e}")
            self.light_vars[light_id].set(not self.light_vars[light_id].get())

    def update_brightness(self, light_id, value):
        if not self.slider_changes_enabled:
            return

        try:
            brightness = int(float(value))
            url = f"http://{self.BRIDGE_IP}/api/{self.USERNAME}/lights/{light_id}/state"
            payload = {
                "on": True,
                "bri": int(brightness * 254 / 100)
            }
            requests.put(url, json=payload, timeout=3)
            self.light_labels[light_id].configure(text=f"{brightness}%")

            # Update toggle if light was off
            if not self.light_vars[light_id].get():
                self.light_vars[light_id].set(True)
                self.status_labels[light_id].configure(text="On", text_color=self.ACTIVE_COLOR)
                self.update_slider_color(light_id, True)
        except Exception as e:
            print(f"Error updating brightness for light {light_id}: {e}")

    def update_light_status(self, light_id):
        try:
            url = f"http://{self.BRIDGE_IP}/api/{self.USERNAME}/lights/{light_id}"
            response = requests.get(url, timeout=3)
            data = response.json()

            is_on = data['state']['on']
            self.light_vars[light_id].set(is_on)

            status = "On" if is_on else "Off"
            color = self.ACTIVE_COLOR if is_on else "#888888"
            self.status_labels[light_id].configure(text=status, text_color=color)
            self.update_slider_color(light_id, is_on)

            if 'bri' in data['state']:
                brightness = round(data['state']['bri'] / 254 * 100)
                self.light_sliders[light_id].set(brightness)
                self.light_labels[light_id].configure(text=f"{brightness}%")
                self.initial_brightness[light_id] = brightness
        except Exception as e:
            print(f"Error updating status for light {light_id}: {e}")
            self.status_labels[light_id].configure(text="Error", text_color="red")

    def update_all_lights(self):
        for light_id in self.LIGHTS.keys():
            self.update_light_status(light_id)

    def discover_bridge_ip(self):
        # Try official discovery first
        try:
            response = requests.get("https://discovery.meethue.com/", timeout=3)
            bridges = response.json()
            if bridges and 'internalipaddress' in bridges[0]:
                print("Bridge ip found (official):", bridges[0]['internalipaddress'])
                return bridges[0]['internalipaddress']
        except Exception as e:
            print(f"Official discovery error: {e}")
        # Fallback: scan local network for /description.xml
        print("Trying local network scan for Hue bridge...")
        import socket
        base_ip = "192.168.1."
        for i in range(2, 255):
            ip = f"{base_ip}{i}"
            try:
                url = f"http://{ip}/description.xml"
                resp = requests.get(url, timeout=0.5)
                if resp.status_code == 200 and "Philips hue bridge" in resp.text:
                    print(f"Bridge ip found (scan): {ip}")
                    return ip
            except Exception:
                continue
        print("No Hue bridge found on the network.")
        return None

    def discover_lights(self):
        """Discover available lights from the bridge and return a dict {id: name} for reachable lights only."""
        lights = {}
        if not self.BRIDGE_IP or not self.USERNAME:
            return lights
        try:
            url = f"http://{self.BRIDGE_IP}/api/{self.USERNAME}/lights"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            for lid, info in data.items():
                # Only add lights that are reachable
                if info.get("state", {}).get("reachable", True):
                    lights[int(lid)] = info.get("name", f"Light {lid}")
        except Exception as e:
            print(f"Error discovering lights: {e}")
        return lights

if __name__ == "__main__":
    root = ctk.CTk()
    app = HueController(root)
    root.mainloop()
