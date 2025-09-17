import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
from PIL import Image, ImageTk, ImageEnhance
from perlin_noise import PerlinNoise
import cv2  # Dependency for high-quality denoising
import threading
import logging
import os
import platform

# --- Setup professional logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Compatibility for Pillow resampling ---
try:
    resampling = Image.Resampling
except AttributeError:
    class _Res:
        NEAREST = Image.NEAREST
        BILINEAR = Image.BILINEAR
        LANCZOS = Image.LANCZOS
    resampling = _Res()

class OrganicGrainGeneratorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Organic Grain Generator")
        self.master.geometry("1400x800")

        # --- Core Properties ---
        self.initializing = True
        self.width = 1920
        self.height = 1080
        self.background_pil_image = None
        self._cached_fixed_maps = {}
        self.pil_image = None
        self.processed_pil_image = None

        # --- Zoom Properties ---
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_photo_image = None
        self.ZOOM_FACTOR = 5.0
        self.ZOOM_VIEW_SIZE = 256
        self.zoom_levels = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0, 16.0, 32.0]
        self.current_zoom_index = 3

        # --- GUI Layout & Styling ---
        self.setup_dark_theme()
        
        top_frame = ttk.Frame(self.master, style="Dark.TFrame")
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        status_bar_frame = ttk.Frame(self.master, style="Dark.TFrame")
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
        status_bar_frame.columnconfigure(0, weight=1)
        self.credits_label = ttk.Label(status_bar_frame, text="Organic Grain Generator | Written by Nathaniel Westveer", style="TLabel", anchor=tk.E)
        self.credits_label.grid(row=0, column=1, sticky='e')

        master_control_frame = ttk.Frame(top_frame, width=350, style="Dark.TFrame")
        master_control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)
        master_control_frame.pack_propagate(False)

        self.preview_progress_bar = ttk.Progressbar(master_control_frame, orient="horizontal", mode="indeterminate")
        
        self.control_canvas = tk.Canvas(master_control_frame, highlightthickness=0, background="#252525")
        control_scrollbar = ttk.Scrollbar(master_control_frame, orient="vertical", command=self.control_canvas.yview)
        self.control_canvas.configure(yscrollcommand=control_scrollbar.set)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        control_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.control_frame = ttk.Frame(self.control_canvas, padding="10", style="Dark.TFrame")
        self.control_frame_id = self.control_canvas.create_window((0, 0), window=self.control_frame, anchor="nw")

        self.image_frame = ttk.Frame(top_frame, padding="10", style="Dark.TFrame")
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.image_frame, background='#282828', highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self.image_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.image_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.v_scroll.grid(row=0, column=1, sticky='ns')
        self.h_scroll.grid(row=1, column=0, sticky='ew')
        self.image_frame.grid_rowconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(0, weight=1)
        
        self.photo_image = None
        self.canvas_image_id = None
        self.create_widgets()
        self.initializing = False
        self.master.after(100, self.update_noise)
        self._bind_events()

    def setup_dark_theme(self):
        style = ttk.Style(self.master)
        style.theme_use('clam')
        BG_COLOR, FG_COLOR, SELECT_BG, ACTIVE_BG, BUTTON_COLOR, TROUGH_COLOR, HANDLE_COLOR = "#252525", "#EAEAEA", "#3E3E3E", "#505050", "#4A4A4A", "#333333", "#CDCDCD"
        style.configure(".", background=BG_COLOR, foreground=FG_COLOR, fieldbackground=SELECT_BG, borderwidth=0, lightcolor=BG_COLOR, darkcolor=BG_COLOR)
        style.configure("Dark.TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR)
        style.configure("TLabelframe", background=BG_COLOR, bordercolor=SELECT_BG)
        style.configure("TLabelframe.Label", background=BG_COLOR, foreground=FG_COLOR)
        style.configure("TButton", background=BUTTON_COLOR, foreground=FG_COLOR, font=('Helvetica', 10), borderwidth=1, relief="raised")
        style.map("TButton", background=[('active', ACTIVE_BG), ('pressed', SELECT_BG)], relief=[('pressed', 'sunken')])
        style.layout('TEntry', [('Entry.field', {'sticky': 'nswe', 'children': [('Entry.padding', {'sticky': 'nswe', 'children': [('Entry.textarea', {'sticky': 'nswe'})]})]})])
        style.configure("TEntry", foreground=FG_COLOR, fieldbackground=SELECT_BG, insertcolor=FG_COLOR)
        style.map("TCombobox", fieldbackground=[('readonly', SELECT_BG)], selectbackground=[('readonly', BG_COLOR)])
        style.configure("TCheckbutton", background=BG_COLOR, foreground=FG_COLOR)
        style.map("TCheckbutton", indicatorcolor=[('pressed', BG_COLOR), ('selected', HANDLE_COLOR)], background=[('active', BG_COLOR)])
        style.configure("TScrollbar", troughcolor=TROUGH_COLOR, background=BUTTON_COLOR, gripcount=0)
        style.map("TScrollbar", background=[('active', ACTIVE_BG)])
        style.configure("Horizontal.TProgressbar", troughcolor=TROUGH_COLOR, background=HANDLE_COLOR)
        style.configure("Horizontal.TScale", troughcolor=TROUGH_COLOR, background=HANDLE_COLOR, gripcount=0)
        style.map("Horizontal.TScale", background=[('active', 'white'), ('pressed', 'white')])
        self.master.config(background=BG_COLOR)

    def _bind_events(self):
        self.image_frame.bind("<Configure>", self.on_frame_resize)
        self.control_frame.bind("<Configure>", self._on_control_frame_configure)
        self.control_canvas.bind("<Configure>", self._on_control_canvas_configure)
        self._bind_to_mouse_wheel(self.control_canvas)
        self._bind_children_to_mouse_wheel(self.control_frame)
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.control_canvas.bind("<ButtonPress-2>", self._control_pan_start)
        self.control_canvas.bind("<B2-Motion>", self._control_pan_move)
        self._bind_children_to_pan(self.control_frame)
        self._bind_to_mouse_wheel(self.canvas, self._on_canvas_scroll_zoom)

    def _on_control_frame_configure(self, event): self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))
    def _on_control_canvas_configure(self, event): self.control_canvas.itemconfig(self.control_frame_id, width=event.width)
    def _on_mouse_wheel(self, event):
        delta = event.delta / 120 if platform.system() != "Linux" else -1 if event.num == 5 else 1
        self.control_canvas.yview_scroll(int(-1 * delta), "units")
    def _bind_to_mouse_wheel(self, widget, command=None):
        command = command or self._on_mouse_wheel
        widget.bind("<MouseWheel>", command); widget.bind("<Button-4>", command); widget.bind("<Button-5>", command)
    def _bind_children_to_mouse_wheel(self, parent):
        for child in parent.winfo_children():
            self._bind_to_mouse_wheel(child)
            if child.winfo_children(): self._bind_children_to_mouse_wheel(child)
    def _control_pan_start(self, event): self.control_canvas.scan_mark(event.x, event.y)
    def _control_pan_move(self, event): self.control_canvas.scan_dragto(event.x, event.y, gain=1)
    def _bind_children_to_pan(self, parent):
        for child in parent.winfo_children():
            child.bind("<ButtonPress-2>", self._control_pan_start); child.bind("<B2-Motion>", self._control_pan_move)
            if child.winfo_children(): self._bind_children_to_pan(child)
    def _pan_start(self, event): self.canvas.scan_mark(event.x, event.y)
    def _pan_move(self, event): self.canvas.scan_dragto(event.x, event.y, gain=1)
    def _on_canvas_scroll_zoom(self, event):
        if self.pil_image is None or self.zoom_var.get() == "Fit to Window": return
        zoom_in = (event.num == 4) if platform.system() == "Linux" else (event.delta > 0)
        self.current_zoom_index = min(len(self.zoom_levels) - 1, self.current_zoom_index + 1) if zoom_in else max(0, self.current_zoom_index - 1)
        current_scale = float(self.zoom_var.get().replace('%', '')) / 100.0
        canvas_x, canvas_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        image_x, image_y = canvas_x / current_scale, canvas_y / current_scale
        new_scale = self.zoom_levels[self.current_zoom_index]
        self.zoom_var.set(f"{new_scale * 100:.0f}%"); self.zoom_combo.set(f"{new_scale * 100:.0f}%")
        self._update_display_image()
        new_canvas_x, new_canvas_y = image_x * new_scale, image_y * new_scale
        scroll_x, scroll_y = new_canvas_x - event.x, new_canvas_y - event.y
        if self.width * new_scale > 0: self.canvas.xview_moveto(scroll_x / (self.width * new_scale))
        if self.height * new_scale > 0: self.canvas.yview_moveto(scroll_y / (self.height * new_scale))

    def create_widgets(self):
        self.slider_defaults = {"Grain Size": 1, "PRNU (Gain FPN)": 0, "DSNU (Offset FPN)": 0, "Shot Noise (Poisson)": 0, "Read Noise (Gaussian)": 0, "Color Noise": 0, "Shadow Noise Bias": 0, "Banding": 0, "Bit Depth": 8, "Firefly Density (%)": 0, "Firefly Intensity": 0, "Firefly Coloration": 0, "Bloom / Crush": 0, "Bloom / Crush Strength": 100, "Denoise Param 1": 0, "Denoise Param 2": 10, "Mix": 100, "Micro-contrast": 0, "Texture Variation": 0, "Saturation": 0, "Filmic Saturation": 0, "Lift": 0, "Roll-off": 0, "Contrast": 0}
        
        dim_frame = ttk.LabelFrame(self.control_frame, text="Dimensions"); dim_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dim_frame, text="Width:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.width_var = tk.StringVar(value=str(self.width)); self.width_entry = ttk.Entry(dim_frame, textvariable=self.width_var, width=8); self.width_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(dim_frame, text="Height:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.height_var = tk.StringVar(value=str(self.height)); self.height_entry = ttk.Entry(dim_frame, textvariable=self.height_var, width=8); self.height_entry.grid(row=1, column=1, padx=5, pady=2)
        self.update_dim_button = ttk.Button(dim_frame, text="Update Dimensions", command=self.update_dimensions); self.update_dim_button.grid(row=2, column=0, columnspan=2, pady=5)
        
        bg_frame = ttk.LabelFrame(self.control_frame, text="Background Image"); bg_frame.pack(fill=tk.X, pady=5)
        self.bg_status_label = ttk.Label(bg_frame, text="Status: No Image Loaded"); self.bg_status_label.pack(pady=(2, 4))
        ttk.Button(bg_frame, text="Load Background Image...", command=self.load_background_image).pack(fill=tk.X, padx=5)
        ttk.Button(bg_frame, text="Clear Background", command=self.clear_background_image).pack(fill=tk.X, padx=5, pady=(2, 5))

        perf_frame = ttk.LabelFrame(self.control_frame, text="Controls"); perf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(perf_frame, text="Noise Seed:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.seed_var = tk.StringVar(value=str(np.random.randint(0, 10000))); ttk.Entry(perf_frame, textvariable=self.seed_var, width=8).grid(row=0, column=1, padx=5, pady=3)
        self.realtime_preview_var = tk.BooleanVar(value=True); ttk.Checkbutton(perf_frame, text="Real-time Preview", variable=self.realtime_preview_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(perf_frame, text="Supersampling:").grid(row=2, column=0, padx=5, pady=3, sticky="w")
        self.supersample_var = tk.StringVar(); self.supersample_combo = ttk.Combobox(perf_frame, textvariable=self.supersample_var, state="readonly", width=10, values=("1x (Off)", "2x", "3x", "4x")); self.supersample_combo.set("1x (Off)"); self.supersample_combo.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        self.update_preview_button = ttk.Button(perf_frame, text="Update Full Preview", command=self.update_noise); self.update_preview_button.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        sliders_frame = ttk.LabelFrame(self.control_frame, text="Noise Parameters"); sliders_frame.pack(fill=tk.X, pady=5)
        self.sliders = {}
        slider_params = {"Grain Size": (1, 8), "PRNU (Gain FPN)": (0, 5.0), "DSNU (Offset FPN)": (0, 10.0), "Shot Noise (Poisson)": (0, 5.0), "Read Noise (Gaussian)": (0, 15.0), "Color Noise": (0, 20.0), "Shadow Noise Bias": (0, 5.0), "Banding": (0, 0.1), "Bit Depth": (4, 8), "Firefly Density (%)": (0, 1.0), "Firefly Intensity": (0, 500.0), "Firefly Coloration": (0, 2.0)}
        for i, (name, params) in enumerate(slider_params.items()):
            ttk.Label(sliders_frame, text=name).grid(row=i, column=0, sticky="w", padx=5)
            slider = ttk.Scale(sliders_frame, from_=params[0], to=params[1], orient=tk.HORIZONTAL, command=self.on_slider_drag); slider.set(self.slider_defaults[name]); slider.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders[name] = slider
        sliders_frame.columnconfigure(1, weight=1); self.sliders["Shadow Noise Bias"].config(state="disabled")

        post_process_frame = ttk.LabelFrame(self.control_frame, text="Post-Processing"); post_process_frame.pack(fill=tk.X, pady=5)
        ttk.Label(post_process_frame, text="Bloom / Crush").grid(row=0, column=0, sticky="w", padx=5)
        bloom_crush_slider = ttk.Scale(post_process_frame, from_=-10, to=10, orient=tk.HORIZONTAL, command=self.on_slider_drag); bloom_crush_slider.set(self.slider_defaults["Bloom / Crush"]); bloom_crush_slider.grid(row=0, column=1, sticky="ew", padx=5, pady=2); bloom_crush_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Bloom / Crush"] = bloom_crush_slider
        ttk.Label(post_process_frame, text="Strength (%)").grid(row=1, column=0, sticky="w", padx=5)
        bc_strength_slider = ttk.Scale(post_process_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); bc_strength_slider.set(self.slider_defaults["Bloom / Crush Strength"]); bc_strength_slider.grid(row=1, column=1, sticky="ew", padx=5, pady=2); bc_strength_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Bloom / Crush Strength"] = bc_strength_slider
        ttk.Label(post_process_frame, text="Denoise Mode:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.denoise_mode_var = tk.StringVar(); self.denoise_mode_combo = ttk.Combobox(post_process_frame, textvariable=self.denoise_mode_var, state="readonly", values=["Photographic (NL-Means)", "Edge-Aware Smooth"]); self.denoise_mode_combo.set("Photographic (NL-Means)"); self.denoise_mode_combo.grid(row=2, column=1, sticky="ew", padx=5, pady=2); self.denoise_mode_combo.bind("<<ComboboxSelected>>", self.on_denoise_mode_change)
        self.denoise_label_1 = ttk.Label(post_process_frame, text="Denoise Strength"); self.denoise_label_1.grid(row=3, column=0, sticky="w", padx=5)
        denoise_slider_1 = ttk.Scale(post_process_frame, from_=0, to=30, orient=tk.HORIZONTAL, command=self.on_slider_drag); denoise_slider_1.set(self.slider_defaults["Denoise Param 1"]); denoise_slider_1.grid(row=3, column=1, sticky="ew", padx=5, pady=2); denoise_slider_1.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Denoise Param 1"] = denoise_slider_1
        self.denoise_label_2 = ttk.Label(post_process_frame, text="Detail Preservation"); self.denoise_label_2.grid(row=4, column=0, sticky="w", padx=5)
        denoise_slider_2 = ttk.Scale(post_process_frame, from_=0, to=30, orient=tk.HORIZONTAL, command=self.on_slider_drag); denoise_slider_2.set(self.slider_defaults["Denoise Param 2"]); denoise_slider_2.grid(row=4, column=1, sticky="ew", padx=5, pady=2); denoise_slider_2.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Denoise Param 2"] = denoise_slider_2
        ttk.Label(post_process_frame, text="Mix (%)").grid(row=5, column=0, sticky="w", padx=5)
        mix_slider = ttk.Scale(post_process_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); mix_slider.set(self.slider_defaults["Mix"]); mix_slider.grid(row=5, column=1, sticky="ew", padx=5, pady=2); mix_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Mix"] = mix_slider
        post_process_frame.columnconfigure(1, weight=1)
        
        texture_frame = ttk.LabelFrame(self.control_frame, text="Texture & Clarity"); texture_frame.pack(fill=tk.X, pady=5)
        ttk.Label(texture_frame, text="Micro-contrast").grid(row=0, column=0, sticky="w", padx=5)
        micro_contrast_slider = ttk.Scale(texture_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); micro_contrast_slider.set(self.slider_defaults["Micro-contrast"]); micro_contrast_slider.grid(row=0, column=1, sticky="ew", padx=5, pady=2); micro_contrast_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Micro-contrast"] = micro_contrast_slider
        ttk.Label(texture_frame, text="Texture Variation").grid(row=1, column=0, sticky="w", padx=5)
        texture_var_slider = ttk.Scale(texture_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); texture_var_slider.set(self.slider_defaults["Texture Variation"]); texture_var_slider.grid(row=1, column=1, sticky="ew", padx=5, pady=2); texture_var_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Texture Variation"] = texture_var_slider
        texture_frame.columnconfigure(1, weight=1)
        
        tone_frame = ttk.LabelFrame(self.control_frame, text="Tone, Contrast & Color"); tone_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tone_frame, text="Saturation").grid(row=0, column=0, sticky="w", padx=5)
        saturation_slider = ttk.Scale(tone_frame, from_=-100, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); saturation_slider.set(self.slider_defaults["Saturation"]); saturation_slider.grid(row=0, column=1, sticky="ew", padx=5, pady=2); saturation_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Saturation"] = saturation_slider
        ttk.Label(tone_frame, text="Filmic Saturation").grid(row=1, column=0, sticky="w", padx=5)
        filmic_sat_slider = ttk.Scale(tone_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); filmic_sat_slider.set(self.slider_defaults["Filmic Saturation"]); filmic_sat_slider.grid(row=1, column=1, sticky="ew", padx=5, pady=2); filmic_sat_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Filmic Saturation"] = filmic_sat_slider
        ttk.Label(tone_frame, text="Lift (Shadows)").grid(row=2, column=0, sticky="w", padx=5)
        lift_slider = ttk.Scale(tone_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); lift_slider.set(self.slider_defaults["Lift"]); lift_slider.grid(row=2, column=1, sticky="ew", padx=5, pady=2); lift_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Lift"] = lift_slider
        ttk.Label(tone_frame, text="Roll-off (Highlights)").grid(row=3, column=0, sticky="w", padx=5)
        rolloff_slider = ttk.Scale(tone_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); rolloff_slider.set(self.slider_defaults["Roll-off"]); rolloff_slider.grid(row=3, column=1, sticky="ew", padx=5, pady=2); rolloff_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Roll-off"] = rolloff_slider
        ttk.Label(tone_frame, text="Contrast").grid(row=4, column=0, sticky="w", padx=5)
        contrast_slider = ttk.Scale(tone_frame, from_=-100, to=100, orient=tk.HORIZONTAL, command=self.on_slider_drag); contrast_slider.set(self.slider_defaults["Contrast"]); contrast_slider.grid(row=4, column=1, sticky="ew", padx=5, pady=2); contrast_slider.bind("<ButtonRelease-1>", self.on_slider_release); self.sliders["Contrast"] = contrast_slider
        tone_frame.columnconfigure(1, weight=1)

        ttk.Button(self.control_frame, text="Reset All Settings", command=self.reset_all_sliders).pack(fill=tk.X, pady=(10,5))

        view_save_frame = ttk.LabelFrame(self.control_frame, text="View & Save"); view_save_frame.pack(fill=tk.X, pady=10)
        zoom_frame = ttk.Frame(view_save_frame, style="Dark.TFrame"); zoom_frame.pack(fill=tk.X, padx=5, pady=(2,4))
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        self.zoom_var = tk.StringVar(); self.zoom_combo = ttk.Combobox(zoom_frame, textvariable=self.zoom_var, state="readonly", width=12, values=["Fit to Window"] + [f"{z*100:.0f}%" for z in self.zoom_levels]); self.zoom_var.set("100%"); self.zoom_combo.set("100%"); self.zoom_combo.pack(side=tk.LEFT, padx=5); self.zoom_combo.bind("<<ComboboxSelected>>", self.on_zoom_change)
        
        self.show_original_var = tk.BooleanVar(value=False)
        self.show_original_check = ttk.Checkbutton(view_save_frame, text="Show Original", variable=self.show_original_var, command=self.on_toggle_original, state="disabled")
        self.show_original_check.pack(pady=4)

        self.zoom_button = ttk.Button(view_save_frame, text="Show Detail View", command=self.toggle_zoom_window); self.zoom_button.pack(fill=tk.X, padx=5, pady=(0,5))
        ttk.Button(view_save_frame, text="Save Single Image", command=self.save_image).pack(fill=tk.X, padx=5)

        export_frame = ttk.LabelFrame(self.control_frame, text="Sequence Export"); export_frame.pack(fill=tk.X, pady=5)
        ttk.Label(export_frame, text="Export Mode:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.export_mode_var = tk.StringVar(); self.export_mode_combo = ttk.Combobox(export_frame, textvariable=self.export_mode_var, state="readonly", width=15, values=("Grain Plate Only", "Composited Image")); self.export_mode_combo.set("Grain Plate Only"); self.export_mode_combo.grid(row=0, column=1, columnspan=3, padx=5, pady=3, sticky="w")
        ttk.Label(export_frame, text="Prefix:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.prefix_var = tk.StringVar(value="noise_plate"); ttk.Entry(export_frame, textvariable=self.prefix_var).grid(row=1, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
        ttk.Label(export_frame, text="Start:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.start_frame_var = tk.StringVar(value="1001"); ttk.Entry(export_frame, textvariable=self.start_frame_var, width=8).grid(row=2, column=1, padx=5, pady=2)
        ttk.Label(export_frame, text="End:").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.end_frame_var = tk.StringVar(value="1010"); ttk.Entry(export_frame, textvariable=self.end_frame_var, width=8).grid(row=2, column=3, padx=5, pady=2)
        self.export_button = ttk.Button(export_frame, text="Export Sequence", command=self.export_sequence); self.export_button.grid(row=3, column=0, columnspan=4, pady=5, sticky="ew")
        self.progress_bar = ttk.Progressbar(export_frame, orient="horizontal", mode="determinate"); self.progress_bar.grid(row=4, column=0, columnspan=4, pady=(5,0), sticky="ew")

    def get_rng_for_frame(self, seed_offset=0): return np.random.default_rng(self.get_master_seed() + seed_offset)
    def get_supersample_factor(self):
        try: return max(1, int((self.supersample_var.get() or "").split('x')[0].strip()))
        except: return 1
    def _overlay_blend(self, background, grain_plate):
        low_mask = background <= 0.5
        result = np.zeros_like(background, dtype=np.float32)
        result[low_mask] = 2 * background[low_mask] * grain_plate[low_mask]
        result[~low_mask] = 1 - 2 * (1 - background[~low_mask]) * (1 - grain_plate[~low_mask])
        return result

    def _generate_base_image(self, seed_offset=0, composite=True):
        luma_mask = None
        shadow_bias_strength = self.sliders["Shadow Noise Bias"].get() if self.background_pil_image else 0.0
        
        if self.background_pil_image and shadow_bias_strength > 0:
            luma_arr_float = np.array(self.background_pil_image.convert('L'), dtype=np.float32) / 255.0
            luma_mask = 1.0 + ((1.0 - luma_arr_float) * float(shadow_bias_strength))
        
        factor = self.get_supersample_factor()
        render_width, render_height = self.width * factor, self.height * factor

        if luma_mask is not None and factor > 1:
            lm_img = Image.fromarray(luma_mask.astype(np.float32)).resize((render_width, render_height), resample=resampling.BILINEAR)
            luma_mask = np.array(lm_img)

        grain_plate_arr = self._generate_grain_plate(render_width, render_height, seed_offset, luma_mask)
        if factor > 1:
            grain_plate_arr = np.array(Image.fromarray(grain_plate_arr).resize((self.width, self.height), resample=resampling.LANCZOS))

        if composite and self.background_pil_image:
            bg_arr_float = np.array(self.background_pil_image.convert('RGB'), dtype=np.float32) / 255.0
            grain_arr_float = np.array(Image.fromarray(grain_plate_arr).convert('RGB'), dtype=np.float32) / 255.0
            return np.clip(self._overlay_blend(bg_arr_float, grain_arr_float) * 255.0, 0, 255).astype(np.uint8)
        return grain_plate_arr

    def _resize_noise_array(self, noise_array, target_w, target_h):
        min_val, max_val = noise_array.min(), noise_array.max()
        if max_val == min_val: return np.full((target_h, target_w), min_val, dtype=np.float32)
        
        offset_noise = noise_array - min_val
        scaled_noise = (offset_noise / (max_val - min_val) * 255.0).astype(np.uint8)
        
        img = Image.fromarray(scaled_noise).resize((target_w, target_h), resample=resampling.NEAREST)
        
        original_range = max_val - min_val
        resized_float = (np.array(img).astype(np.float32) / 255.0) * original_range + min_val
        return resized_float

    def _generate_grain_plate(self, width, height, seed_offset, luma_mask=None):
        rng = self.get_rng_for_frame(seed_offset)
        prnu_map, dsnu_map, banding_map, _ = self._get_fixed_maps_for_resolution(width, height)
        luma_image = np.full((height, width), 128.0, dtype=np.float32)
        luma_image *= (1.0 + (prnu_map - 1.0) * self.sliders["PRNU (Gain FPN)"].get())
        luma_image += dsnu_map * self.sliders["DSNU (Offset FPN)"].get()
        
        grain_size = int(round(self.sliders["Grain Size"].get()))
        scaled_w, scaled_h = max(1, width // grain_size), max(1, height // grain_size)

        if (strength := self.sliders["Shot Noise (Poisson)"].get()) > 0:
            small_noise = ((rng.poisson(25.0, (scaled_h, scaled_w)).astype(np.float32) / 50.0) * 255.0 - 128.0) * (strength / 5.0)
            shot_noise = self._resize_noise_array(small_noise, width, height)
            if luma_mask is not None: shot_noise *= luma_mask
            luma_image += shot_noise

        if (strength := self.sliders["Read Noise (Gaussian)"].get()) > 0:
            small_noise = rng.normal(0, 1, (scaled_h, scaled_w)).astype(np.float32) * strength
            read_noise = self._resize_noise_array(small_noise, width, height)
            if luma_mask is not None: read_noise *= luma_mask
            luma_image += read_noise

        luma_image += banding_map * 255 * self.sliders["Banding"].get()
        final_image = np.stack([luma_image] * 3, axis=-1)

        if (strength := self.sliders["Color Noise"].get()) > 0:
            small_noise = rng.normal(0.0, 1.0, (scaled_h, scaled_w, 3)).astype(np.float32) * strength
            color_noise_map = np.stack([
                self._resize_noise_array(small_noise[:,:,0], width, height),
                self._resize_noise_array(small_noise[:,:,1], width, height),
                self._resize_noise_array(small_noise[:,:,2], width, height)
            ], axis=-1)
            if luma_mask is not None: color_noise_map *= np.expand_dims(luma_mask, axis=-1)
            final_image += color_noise_map

        if (density := self.sliders["Firefly Density (%)"].get() / 100.0) > 0 and (num := int(width*height*density)) > 0:
            y, x = rng.integers(0, height, num), rng.integers(0, width, num)
            base = rng.random((num, 3)); gray = (base @ [0.299, 0.587, 0.114])[:, None]
            colors = gray + (base - gray) * self.sliders["Firefly Coloration"].get()
            final_image[y, x, :] = np.clip(colors * self.sliders["Firefly Intensity"].get(), 0, 255)

        if (bit_depth := int(self.sliders["Bit Depth"].get())) < 8:
            levels = 2**bit_depth; final_image = np.round(final_image / 255 * (levels-1)) * (255 / (levels-1))
        return np.clip(final_image, 0, 255).astype(np.uint8)

    def _get_fixed_maps_for_resolution(self, width, height):
        res_key = f"{width}x{height}"
        if res_key in self._cached_fixed_maps: return self._cached_fixed_maps[res_key]
        
        rng = self.get_rng_for_frame(0)
        prnu = 1.0 + (rng.standard_normal((height, width), np.float32) * 0.005)
        dsnu = rng.standard_normal((height, width), np.float32)
        
        perlin_legacy = PerlinNoise(octaves=6, seed=self.get_master_seed())
        banding = np.tile(np.array([perlin_legacy(y) for y in np.linspace(0, 5, height)], np.float32)[:, None], (1, width))

        rng_texture = np.random.default_rng(self.get_master_seed() + 1)
        small_w, small_h = max(1, width // 64), max(1, height // 64)
        random_map = rng_texture.random((small_h, small_w)).astype(np.float32)
        
        blurred_map = cv2.GaussianBlur(random_map, (0,0), sigmaX=16, sigmaY=16, borderType=cv2.BORDER_REFLECT)
        
        texture_map_pil = Image.fromarray(blurred_map).resize((width, height), resample=resampling.BILINEAR)
        texture_map = np.array(texture_map_pil)
        texture_map = (texture_map - texture_map.min()) / (texture_map.max() - texture_map.min())
        
        self._cached_fixed_maps[res_key] = (prnu, dsnu, banding, texture_map)
        return self._cached_fixed_maps[res_key]
    
    def _update_noise_worker(self):
        processed_image = self._get_processed_image()
        self.master.after(0, self._update_noise_complete, processed_image)

    def _update_noise_complete(self, processed_image):
        self.processed_pil_image = processed_image
        self.on_toggle_original()

        self.preview_progress_bar.stop()
        self.preview_progress_bar.pack_forget()
        self.update_preview_button.config(state="normal")

    def update_noise(self, event=None):
        if self.initializing: return
        is_realtime = self.realtime_preview_var.get() or self.zoom_window
        
        if is_realtime:
            self.processed_pil_image = self._get_processed_image()
            self.on_toggle_original()
        else: 
            self.update_preview_button.config(state="disabled")
            self.preview_progress_bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 5))
            self.preview_progress_bar.start()
            threading.Thread(target=self._update_noise_worker, daemon=True).start()

    def _get_processed_image(self, seed_offset=0, composite=True):
        image_to_process = Image.fromarray(self._generate_base_image(seed_offset, composite))
        
        bloom_crush_val = self.sliders["Bloom / Crush"].get()
        strength_percent = self.sliders["Bloom / Crush Strength"].get()
        if bloom_crush_val != 0 and strength_percent > 0:
            processed_bc = self._apply_bloom_crush(image_to_process, bloom_crush_val)
            mix_alpha = strength_percent / 100.0
            if mix_alpha < 1.0: image_to_process = Image.blend(image_to_process, processed_bc, alpha=mix_alpha)
            else: image_to_process = processed_bc
        
        denoise_strength = self.sliders["Denoise Param 1"].get()
        if denoise_strength > 0:
            mode = self.denoise_mode_var.get()
            denoised_image = None
            if mode == "Photographic (NL-Means)": denoised_image = self._apply_photographic_denoise(image_to_process)
            elif mode == "Edge-Aware Smooth": denoised_image = self._apply_edge_aware_denoise(image_to_process)
            
            if denoised_image:
                mix_alpha = self.sliders["Mix"].get() / 100.0
                if mix_alpha < 1.0: image_to_process = Image.blend(image_to_process, denoised_image, alpha=mix_alpha)
                else: image_to_process = denoised_image
        
        image_to_process = self._apply_micro_contrast(image_to_process)
        image_to_process = self._apply_saturation(image_to_process)
        s_curve_lut = self._generate_s_curve_lut()
        if s_curve_lut is not None:
            image_to_process = self._apply_lut(image_to_process, s_curve_lut)
        return image_to_process
    
    def _apply_bloom_crush(self, image_to_process, value):
        bgr_array = cv2.cvtColor(np.array(image_to_process), cv2.COLOR_RGB2BGR)
        kernel_size = abs(int(value)) * 2 + 1
        if kernel_size <= 1: return image_to_process
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        if value > 0: processed_bgr = cv2.dilate(bgr_array, kernel, iterations=1)
        else: processed_bgr = cv2.erode(bgr_array, kernel, iterations=1)
        return Image.fromarray(cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB))

    def _apply_photographic_denoise(self, image_to_process):
        strength = self.sliders["Denoise Param 1"].get()
        detail = self.sliders["Denoise Param 2"].get()
        bgr_array = cv2.cvtColor(np.array(image_to_process), cv2.COLOR_RGB2BGR)
        denoised_bgr = cv2.fastNlMeansDenoisingColored(bgr_array, None, h=strength, hColor=detail, templateWindowSize=7, searchWindowSize=21)
        return Image.fromarray(cv2.cvtColor(denoised_bgr, cv2.COLOR_BGR2RGB))
    
    def _apply_edge_aware_denoise(self, image_to_process):
        smoothing = int(self.sliders["Denoise Param 1"].get())
        sharpening = self.sliders["Denoise Param 2"].get() / 20.0
        image_arr = cv2.cvtColor(np.array(image_to_process), cv2.COLOR_RGB2BGR)
        smoothed = cv2.bilateralFilter(image_arr, d=-1, sigmaColor=smoothing, sigmaSpace=15)
        if sharpening > 0:
            gaussian = cv2.GaussianBlur(smoothed, (0, 0), 3)
            sharpened = cv2.addWeighted(smoothed, 1.0 + sharpening, gaussian, -sharpening, 0)
            return Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB))
        return Image.fromarray(cv2.cvtColor(smoothed, cv2.COLOR_BGR2RGB))
    
    def _apply_micro_contrast(self, image_to_process):
        strength = self.sliders["Micro-contrast"].get() / 100.0
        variation = self.sliders["Texture Variation"].get() / 100.0
        if strength == 0: return image_to_process

        bgr_array = cv2.cvtColor(np.array(image_to_process), cv2.COLOR_RGB2BGR)
        blurred = cv2.GaussianBlur(bgr_array, (0,0), 3)
        detail_layer = bgr_array.astype(np.float32) - blurred.astype(np.float32)
        _, _, _, texture_map = self._get_fixed_maps_for_resolution(image_to_process.width, image_to_process.height)
        
        flat_mask = np.ones_like(texture_map, dtype=np.float32)
        blended_mask = cv2.addWeighted(flat_mask, 1.0 - variation, texture_map, variation, 0)
        
        modulated_detail = detail_layer * np.expand_dims(blended_mask, axis=-1) * strength * 2.0
        final_bgr = np.clip(bgr_array.astype(np.float32) + modulated_detail, 0, 255).astype(np.uint8)
        return Image.fromarray(cv2.cvtColor(final_bgr, cv2.COLOR_BGR2RGB))

    def _apply_saturation(self, image_to_process):
        sat_value = self.sliders["Saturation"].get() / 100.0 + 1.0
        if sat_value != 1.0:
            enhancer = ImageEnhance.Color(image_to_process)
            image_to_process = enhancer.enhance(sat_value)

        filmic_sat_val = self.sliders["Filmic Saturation"].get() / 100.0
        if filmic_sat_val > 0:
            hsv = image_to_process.convert("HSV")
            h, s, v = hsv.split()
            s_np = np.array(s).astype(np.float32)
            v_np = np.array(v) / 255.0

            highlight_rolloff = 1.0 - (1.0 / (1.0 + np.exp(-(v_np - 0.8) * 15.0)))
            shadow_rolloff = 1.0 / (1.0 + np.exp((v_np - 0.2) * 15.0))
            
            mask = highlight_rolloff * shadow_rolloff
            filmic_mask = 1.0 - ((1.0 - mask) * filmic_sat_val)
            s_np *= filmic_mask
            s_new = Image.fromarray(np.clip(s_np, 0, 255).astype(np.uint8))
            image_to_process = Image.merge("HSV", (h, s_new, v)).convert("RGB")
        return image_to_process

    def _generate_s_curve_lut(self):
        lift = self.sliders["Lift"].get() / 100.0
        rolloff = self.sliders["Roll-off"].get() / 100.0
        contrast = self.sliders["Contrast"].get() / 100.0

        if lift == 0 and rolloff == 0 and contrast == 0: return None

        x = np.linspace(0, 1, 256, dtype=np.float32)
        alpha = 1.0 + contrast if contrast >= 0 else 1.0 / (1.0 - contrast)
        s_curve = x**alpha / (x**alpha + (1-x)**alpha)
        output_min = lift / 2.0
        output_max = 1.0 - (rolloff / 2.0)
        final_curve = s_curve * (output_max - output_min) + output_min
        return np.clip(final_curve * 255, 0, 255).astype(np.uint8)

    def _apply_lut(self, image, lut):
        if lut is None or len(lut) != 256: return image
        bgr_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        toned_bgr = cv2.LUT(bgr_array, lut)
        return Image.fromarray(cv2.cvtColor(toned_bgr, cv2.COLOR_BGR2RGB))

    def _update_display_image(self):
        if not self.pil_image: return
        zoom_str = self.zoom_var.get(); w, h = self.pil_image.size
        if zoom_str == "Fit to Window":
            fw, fh = self.canvas.winfo_width() - 4, self.canvas.winfo_height() - 4
            if fw <= 1 or fh <= 1: return
            scale = min(fw / w, fh / h)
            nw, nh = int(w * scale), int(h * scale)
        else:
            scale = float(zoom_str.replace('%','')) / 100.0
            nw, nh = int(w * scale), int(h * scale)
        if nw > 0 and nh > 0:
            resample = resampling.BILINEAR if scale < 1 else resampling.NEAREST
            display_img = self.pil_image.resize((nw, nh), resample=resample)
            self.photo_image = ImageTk.PhotoImage(display_img)
            if self.canvas_image_id: self.canvas.itemconfig(self.canvas_image_id, image=self.photo_image)
            else: self.canvas_image_id = self.canvas.create_image(0, 0, anchor='nw', image=self.photo_image)
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def on_denoise_mode_change(self, event=None):
        mode = self.denoise_mode_var.get()
        if mode == "Photographic (NL-Means)":
            self.denoise_label_1.config(text="Denoise Strength")
            self.denoise_label_2.config(text="Detail Preservation")
            self.sliders["Denoise Param 1"].config(to=30)
            self.sliders["Denoise Param 2"].config(to=30)
        elif mode == "Edge-Aware Smooth":
            self.denoise_label_1.config(text="Smoothing")
            self.denoise_label_2.config(text="Sharpening")
            self.sliders["Denoise Param 1"].config(to=100) 
            self.sliders["Denoise Param 2"].config(to=30)
        self.update_noise()

    def on_slider_drag(self, event=None):
        if not self.initializing and (self.realtime_preview_var.get() or self.zoom_window): self.update_noise()
    def on_slider_release(self, event=None):
        if not self.initializing and not self.realtime_preview_var.get(): self.update_noise()
    
    def on_toggle_original(self):
        if self.show_original_var.get() and self.background_pil_image:
            self.pil_image = self.background_pil_image
        else:
            self.pil_image = self.processed_pil_image
        self._update_display_image()
        if self.zoom_window: self.update_zoom_view()

    def on_zoom_change(self, event=None):
        if (zoom_str := self.zoom_var.get()) != "Fit to Window":
            target_zoom = float(zoom_str.replace('%','')) / 100.0
            self.current_zoom_index = min(range(len(self.zoom_levels)), key=lambda i: abs(self.zoom_levels[i]-target_zoom))
        self._update_display_image()
    def on_frame_resize(self, event=None):
        if self.zoom_var.get() == "Fit to Window": self.master.after(50, self._update_display_image)
    def update_dimensions(self):
        try:
            w, h = int(self.width_var.get()), int(self.height_var.get())
            if w <= 0 or h <= 0: raise ValueError
            self.master.config(cursor="watch"); self.update_dim_button.config(state="disabled"); self.master.update_idletasks()
            self.width, self.height = w, h
            self._cached_fixed_maps.clear(); self.update_noise()
        except ValueError: logging.error("Invalid dimensions.")
        finally: self.master.config(cursor=""); self.update_dim_button.config(state="normal")
    def load_background_image(self):
        if not (fp := filedialog.askopenfilename(filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All", "*.*")])): return
        try:
            img = Image.open(fp).convert('RGB')
            self.background_pil_image = img; self.width, self.height = img.size
            self.width_var.set(str(self.width)); self.height_var.set(str(self.height))
            self.width_entry.config(state="disabled"); self.height_entry.config(state="disabled"); self.update_dim_button.config(state="disabled")
            self.bg_status_label.config(text=f"Loaded: {os.path.basename(fp)}")
            self.sliders["Shadow Noise Bias"].config(state="normal")
            self.show_original_check.config(state="normal")
            self.update_noise()
        except Exception as e: logging.error(f"Failed to load image: {e}"); self.clear_background_image()
    def clear_background_image(self):
        self.background_pil_image = None
        self.width_entry.config(state="normal"); self.height_entry.config(state="normal"); self.update_dim_button.config(state="normal")
        self.bg_status_label.config(text="Status: No Image Loaded")
        self.sliders["Shadow Noise Bias"].set(0); self.sliders["Shadow Noise Bias"].config(state="disabled")
        self.show_original_var.set(False); self.show_original_check.config(state="disabled")
        self.update_noise()
    def reset_all_sliders(self):
        for name, slider in self.sliders.items():
            if name in self.slider_defaults:
                slider.set(self.slider_defaults[name])
        
        if self.background_pil_image:
            default_image = self.background_pil_image
        else:
            default_image = Image.new('RGB', (self.width, self.height), (128, 128, 128))
        
        self.processed_pil_image = default_image
        self.on_toggle_original()

    def export_sequence(self):
        try:
            prefix, start, end = self.prefix_var.get(), int(self.start_frame_var.get()), int(self.end_frame_var.get())
            if start > end or not prefix: raise ValueError
        except ValueError: logging.error("Invalid sequence."); return
        if not (fp := filedialog.askdirectory()): return
        self.export_button.config(state="disabled"); self.master.config(cursor="watch")
        self.progress_bar["maximum"] = end - start + 1; self.progress_bar["value"] = 0
        threading.Thread(target=self._export_worker, args=(fp, start, end, prefix), daemon=True).start()
    def _export_worker(self, fp, start, end, prefix):
        composite = self.export_mode_var.get() == "Composited Image" and self.background_pil_image
        os.makedirs(fp, exist_ok=True)
        
        for i, frame in enumerate(range(start, end + 1)):
            final_image = self._get_processed_image(seed_offset=frame, composite=composite)
            final_image.save(os.path.join(fp, f"{prefix}.{frame:04d}.png"))
            self.master.after(0, self.progress_bar.config, {'value': i + 1})
        self.master.after(0, self._export_done_ui_cleanup)
    def _export_done_ui_cleanup(self):
        self.export_button.config(state="normal"); self.master.config(cursor="")
        self.progress_bar["value"] = 0
    def save_image(self):
        if not self.pil_image: return
        if not (fp := filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])): return
        self.pil_image.save(fp); logging.info(f"Saved image to {fp}")
    def get_master_seed(self):
        try: return int(self.seed_var.get())
        except: return 0
    def update_zoom_view(self):
        if not self.zoom_window or not self.pil_image: return
        cs = int(self.ZOOM_VIEW_SIZE / self.ZOOM_FACTOR)
        w, h = self.pil_image.size; cx, cy = w // 2, h // 2
        box = (max(0, cx-cs//2), max(0, cy-cs//2), min(w, cx+cs//2), min(h, cy+cs//2))
        zoomed = self.pil_image.crop(box).resize((self.ZOOM_VIEW_SIZE, self.ZOOM_VIEW_SIZE), resample=resampling.NEAREST)
        self.zoom_photo_image = ImageTk.PhotoImage(zoomed); self.zoom_label.config(image=self.zoom_photo_image)
    def toggle_zoom_window(self):
        if self.zoom_window: self.on_zoom_window_close()
        else:
            self.zoom_window = tk.Toplevel(self.master)
            self.zoom_window.title(f"Detail View ({self.ZOOM_FACTOR * 100:.0f}%)"); self.zoom_window.geometry(f"{self.ZOOM_VIEW_SIZE}x{self.ZOOM_VIEW_SIZE}"); self.zoom_window.resizable(False, False)
            self.zoom_label = ttk.Label(self.zoom_window); self.zoom_label.pack(fill=tk.BOTH, expand=True)
            self.zoom_window.protocol("WM_DELETE_WINDOW", self.on_zoom_window_close); self.zoom_button.config(text="Hide Detail View")
            self.update_noise()
    def on_zoom_window_close(self):
        if self.zoom_window: self.zoom_window.destroy()
        self.zoom_window = None; self.zoom_label = None; self.zoom_button.config(text="Show Detail View")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrganicGrainGeneratorApp(root)
    root.mainloop()
