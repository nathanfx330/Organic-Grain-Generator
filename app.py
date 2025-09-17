import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
from PIL import Image, ImageTk
from perlin_noise import PerlinNoise
import threading
import logging
import os
import platform

# --- Setup professional logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Compatibility for Pillow resampling (Image.Resampling fallback) ---
try:
    # Recommended for Pillow 10.0.0+
    resampling = Image.Resampling
except AttributeError:
    # Fallback for older Pillow versions
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

        # --- Zoom Properties ---
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_photo_image = None
        self.ZOOM_FACTOR = 5.0
        self.ZOOM_VIEW_SIZE = 256
        self.zoom_levels = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0, 16.0, 32.0]
        self.current_zoom_index = 3 # Start at 1.0 (100%)

        # --- GUI Layout & Styling ---
        self.setup_dark_theme()

        # --- Main Layout Frames (Top area for controls/canvas, Bottom for credits) ---
        top_frame = ttk.Frame(self.master, style="Dark.TFrame")
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        credits_frame = ttk.Frame(self.master, style="Dark.TFrame")
        credits_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

        # --- MASTER CONTROL FRAME (Packed into the left of top_frame) ---
        master_control_frame = ttk.Frame(top_frame, width=350, style="Dark.TFrame")
        master_control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)
        master_control_frame.pack_propagate(False)

        self.control_canvas = tk.Canvas(master_control_frame, highlightthickness=0, background="#252525")
        control_scrollbar = ttk.Scrollbar(master_control_frame, orient="vertical", command=self.control_canvas.yview)
        self.control_canvas.configure(yscrollcommand=control_scrollbar.set)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        control_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.control_frame = ttk.Frame(self.control_canvas, padding="10", style="Dark.TFrame")
        self.control_frame_id = self.control_canvas.create_window((0, 0), window=self.control_frame, anchor="nw")

        # --- Image Frame (Packed into the right of top_frame) ---
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
        
        # --- ADD CREDITS LABEL to the bottom frame ---
        credits_label = ttk.Label(
            credits_frame,
            text="Organic Grain Generator | Written by Nathaniel Westveer",
            style="TLabel",
            anchor=tk.E # Anchor text to the East (right)
        )
        credits_label.pack(fill=tk.X, padx=5, pady=2)

        self.photo_image = None
        self.canvas_image_id = None

        self.create_widgets()
        
        self.initializing = False
        self.master.after(100, self.update_noise)
        
        # --- Bindings ---
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

    def setup_dark_theme(self):
        """Configures a robust dark theme that preserves native widget styles."""
        BG_COLOR = "#252525"
        FG_COLOR = "#EAEAEA"
        SELECT_BG = "#3E3E3E"
        ACTIVE_BG = "#505050"
        BUTTON_COLOR = "#4A4A4A"
        TROUGH_COLOR = "#333333"
        HANDLE_COLOR = "#CDCDCD"
        
        style = ttk.Style(self.master)
        style.theme_use('clam')

        style.configure(".",
                        background=BG_COLOR,
                        foreground=FG_COLOR,
                        fieldbackground=SELECT_BG,
                        borderwidth=0,
                        lightcolor=BG_COLOR,
                        darkcolor=BG_COLOR)

        style.configure("Dark.TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR)
        style.configure("TLabelframe", background=BG_COLOR, bordercolor=SELECT_BG)
        style.configure("TLabelframe.Label", background=BG_COLOR, foreground=FG_COLOR)

        style.configure("TButton", background=BUTTON_COLOR, foreground=FG_COLOR, font=('Helvetica', 10), borderwidth=1, relief="raised")
        style.map("TButton",
                  background=[('active', ACTIVE_BG), ('pressed', SELECT_BG)],
                  relief=[('pressed', 'sunken')])

        style.layout('TEntry', [('Entry.field', {'sticky': 'nswe', 'children': [('Entry.padding', {'sticky': 'nswe', 'children': [('Entry.textarea', {'sticky': 'nswe'})]})]})])
        style.configure("TEntry", foreground=FG_COLOR, fieldbackground=SELECT_BG, insertcolor=FG_COLOR)
        style.map("TCombobox", fieldbackground=[('readonly', SELECT_BG)], selectbackground=[('readonly', BG_COLOR)])

        style.configure("TCheckbutton", background=BG_COLOR, foreground=FG_COLOR)
        style.map("TCheckbutton",
                  indicatorcolor=[('pressed', BG_COLOR), ('selected', HANDLE_COLOR)],
                  background=[('active', BG_COLOR)])

        style.configure("TScrollbar", troughcolor=TROUGH_COLOR, background=BUTTON_COLOR, gripcount=0)
        style.map("TScrollbar", background=[('active', ACTIVE_BG)])
        style.configure("Horizontal.TProgressbar", troughcolor=TROUGH_COLOR, background=HANDLE_COLOR)

        style.configure("Horizontal.TScale",
                        troughcolor=TROUGH_COLOR,
                        background=HANDLE_COLOR,
                        gripcount=0)
        style.map("Horizontal.TScale",
                  background=[('active', 'white'), ('pressed', 'white')])

        self.master.config(background=BG_COLOR)

    # --- Control Frame Scrolling Methods ---
    def _on_control_frame_configure(self, event):
        self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))

    def _on_control_canvas_configure(self, event):
        self.control_canvas.itemconfig(self.control_frame_id, width=event.width)

    def _on_mouse_wheel(self, event):
        if platform.system() == "Linux":
            if event.num == 5: self.control_canvas.yview_scroll(1, "units")
            elif event.num == 4: self.control_canvas.yview_scroll(-1, "units")
        else:
            self.control_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_to_mouse_wheel(self, widget, command=None):
        if command is None: command = self._on_mouse_wheel
        widget.bind("<MouseWheel>", command)
        widget.bind("<Button-4>", command)
        widget.bind("<Button-5>", command)
        
    def _bind_children_to_mouse_wheel(self, parent):
        for child in parent.winfo_children():
            self._bind_to_mouse_wheel(child)
            if child.winfo_children(): self._bind_children_to_mouse_wheel(child)

    def _control_pan_start(self, event): self.control_canvas.scan_mark(event.x, event.y)
    def _control_pan_move(self, event): self.control_canvas.scan_dragto(event.x, event.y, gain=1)
        
    def _bind_children_to_pan(self, parent):
        for child in parent.winfo_children():
            child.bind("<ButtonPress-2>", self._control_pan_start)
            child.bind("<B2-Motion>", self._control_pan_move)
            if child.winfo_children(): self._bind_children_to_pan(child)

    # --- Canvas Pan and Zoom Methods ---
    def _pan_start(self, event): self.canvas.scan_mark(event.x, event.y)
    def _pan_move(self, event): self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_canvas_scroll_zoom(self, event):
        if self.pil_image is None or self.zoom_var.get() == "Fit to Window": return

        zoom_in = False
        if platform.system() == "Linux":
            if event.num == 4: zoom_in = True
        elif event.delta > 0:
            zoom_in = True

        if zoom_in:
            self.current_zoom_index = min(len(self.zoom_levels) - 1, self.current_zoom_index + 1)
        else:
            self.current_zoom_index = max(0, self.current_zoom_index - 1)

        current_scale = float(self.zoom_var.get().replace('%', '')) / 100.0
        canvas_x = self.canvas.canvasx(event.x); canvas_y = self.canvas.canvasy(event.y)
        image_x = canvas_x / current_scale; image_y = canvas_y / current_scale

        new_scale = self.zoom_levels[self.current_zoom_index]
        self.zoom_var.set(f"{new_scale * 100:.0f}%"); self.zoom_combo.set(f"{new_scale * 100:.0f}%")
        self._update_display_image()

        new_canvas_x = image_x * new_scale; new_canvas_y = image_y * new_scale
        scroll_x = new_canvas_x - event.x; scroll_y = new_canvas_y - event.y
        if self.width * new_scale > 0: self.canvas.xview_moveto(scroll_x / (self.width * new_scale))
        if self.height * new_scale > 0: self.canvas.yview_moveto(scroll_y / (self.height * new_scale))
        
    def create_widgets(self):
        # --- Dimensions ---
        dim_frame = ttk.LabelFrame(self.control_frame, text="Dimensions")
        dim_frame.pack(fill=tk.X, pady=5)
        ttk.Label(dim_frame, text="Width:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.width_var = tk.StringVar(value=str(self.width))
        self.width_entry = ttk.Entry(dim_frame, textvariable=self.width_var, width=8)
        self.width_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(dim_frame, text="Height:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.height_var = tk.StringVar(value=str(self.height))
        self.height_entry = ttk.Entry(dim_frame, textvariable=self.height_var, width=8)
        self.height_entry.grid(row=1, column=1, padx=5, pady=2)
        self.update_dim_button = ttk.Button(dim_frame, text="Update Dimensions", command=self.update_dimensions)
        self.update_dim_button.grid(row=2, column=0, columnspan=2, pady=5)

        # --- Background Image ---
        bg_frame = ttk.LabelFrame(self.control_frame, text="Background Image")
        bg_frame.pack(fill=tk.X, pady=5)
        self.bg_status_label = ttk.Label(bg_frame, text="Status: No Image Loaded")
        self.bg_status_label.pack(pady=(2, 4))
        load_button = ttk.Button(bg_frame, text="Load Background Image...", command=self.load_background_image)
        load_button.pack(fill=tk.X, padx=5)
        clear_button = ttk.Button(bg_frame, text="Clear Background", command=self.clear_background_image)
        clear_button.pack(fill=tk.X, padx=5, pady=(2, 5))

        # --- Controls ---
        perf_frame = ttk.LabelFrame(self.control_frame, text="Controls")
        perf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(perf_frame, text="Noise Seed:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.seed_var = tk.StringVar(value=str(np.random.randint(0, 10000)))
        self.seed_entry = ttk.Entry(perf_frame, textvariable=self.seed_var, width=8)
        self.seed_entry.grid(row=0, column=1, padx=5, pady=3)
        self.realtime_preview_var = tk.BooleanVar(value=True)
        self.realtime_preview_check = ttk.Checkbutton(perf_frame, text="Real-time Preview", variable=self.realtime_preview_var)
        self.realtime_preview_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(perf_frame, text="Supersampling:").grid(row=2, column=0, padx=5, pady=3, sticky="w")
        self.supersample_var = tk.StringVar()
        self.supersample_combo = ttk.Combobox(perf_frame, textvariable=self.supersample_var, state="readonly", width=10)
        self.supersample_combo['values'] = ("1x (Off)", "2x", "3x", "4x")
        self.supersample_combo.set("1x (Off)")
        self.supersample_combo.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        self.update_preview_button = ttk.Button(perf_frame, text="Update Full Preview", command=self.update_noise)
        self.update_preview_button.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        # --- Sliders ---
        sliders_frame = ttk.LabelFrame(self.control_frame, text="Noise Parameters")
        sliders_frame.pack(fill=tk.X, pady=5)
        self.sliders = {}
        slider_params = {
            "PRNU (Gain FPN)": (0, 5.0, 0), "DSNU (Offset FPN)": (0, 10.0, 0),
            "Shot Noise (Poisson)": (0, 5.0, 0), "Read Noise (Gaussian)": (0, 15.0, 0),
            "Color Noise": (0, 20.0, 0),"Shadow Noise Bias": (0, 5.0, 0),
            "Banding": (0, 0.1, 0), "Bit Depth": (4, 8, 8),
            "Firefly Density (%)": (0, 1.0, 0), "Firefly Intensity": (0, 500.0, 0),
            "Firefly Coloration": (0, 2.0, 0)
        }
        for i, (name, params) in enumerate(slider_params.items()):
            ttk.Label(sliders_frame, text=name).grid(row=i, column=0, sticky="w", padx=5)
            slider = ttk.Scale(sliders_frame, from_=params[0], to=params[1], orient=tk.HORIZONTAL, command=self.on_slider_update)
            slider.set(params[2])
            slider.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            self.sliders[name] = slider
        sliders_frame.columnconfigure(1, weight=1)
        self.sliders["Shadow Noise Bias"].config(state="disabled")

        # --- View & Save ---
        view_save_frame = ttk.LabelFrame(self.control_frame, text="View & Save")
        view_save_frame.pack(fill=tk.X, pady=10)
        zoom_frame = ttk.Frame(view_save_frame, style="Dark.TFrame")
        zoom_frame.pack(fill=tk.X, padx=5, pady=(2,8))
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        self.zoom_var = tk.StringVar()
        self.zoom_combo = ttk.Combobox(zoom_frame, textvariable=self.zoom_var, state="readonly", width=12)
        self.zoom_combo['values'] = ["Fit to Window"] + [f"{z*100:.0f}%" for z in self.zoom_levels]
        self.zoom_var.set("100%"); self.zoom_combo.set("100%")
        self.zoom_combo.pack(side=tk.LEFT, padx=5)
        self.zoom_combo.bind("<<ComboboxSelected>>", self.on_zoom_change)
        self.zoom_button = ttk.Button(view_save_frame, text="Show Detail View", command=self.toggle_zoom_window)
        self.zoom_button.pack(fill=tk.X, padx=5, pady=(0,5))
        save_button = ttk.Button(view_save_frame, text="Save Single Image", command=self.save_image)
        save_button.pack(fill=tk.X, padx=5)

        # --- Sequence Export ---
        export_frame = ttk.LabelFrame(self.control_frame, text="Sequence Export")
        export_frame.pack(fill=tk.X, pady=5)
        ttk.Label(export_frame, text="Export Mode:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.export_mode_var = tk.StringVar()
        self.export_mode_combo = ttk.Combobox(export_frame, textvariable=self.export_mode_var, state="readonly", width=15)
        self.export_mode_combo['values'] = ("Grain Plate Only", "Composited Image")
        self.export_mode_combo.set("Grain Plate Only")
        self.export_mode_combo.grid(row=0, column=1, columnspan=3, padx=5, pady=3, sticky="w")
        ttk.Label(export_frame, text="Prefix:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.prefix_var = tk.StringVar(value="noise_plate")
        self.prefix_entry = ttk.Entry(export_frame, textvariable=self.prefix_var)
        self.prefix_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
        ttk.Label(export_frame, text="Start:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.start_frame_var = tk.StringVar(value="1001")
        self.start_frame_entry = ttk.Entry(export_frame, textvariable=self.start_frame_var, width=8)
        self.start_frame_entry.grid(row=2, column=1, padx=5, pady=2)
        ttk.Label(export_frame, text="End:").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.end_frame_var = tk.StringVar(value="1010")
        self.end_frame_entry = ttk.Entry(export_frame, textvariable=self.end_frame_var, width=8)
        self.end_frame_entry.grid(row=2, column=3, padx=5, pady=2)
        self.export_button = ttk.Button(export_frame, text="Export Sequence", command=self.export_sequence)
        self.export_button.grid(row=3, column=0, columnspan=4, pady=5, sticky="ew")
        self.progress_bar = ttk.Progressbar(export_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=4, column=0, columnspan=4, pady=(5,0), sticky="ew")

    # --- NOISE GENERATION LOGIC ---
    def get_rng_for_frame(self, seed_offset=0):
        master_seed = self.get_master_seed()
        return np.random.default_rng(master_seed + seed_offset)

    def get_supersample_factor(self):
        selection = (self.supersample_var.get() or "").strip().lower()
        try:
            if 'x' in selection: return max(1, int(selection.split('x')[0].strip()))
        except Exception: pass
        return 1

    def _overlay_blend(self, background, grain_plate):
        low_mask = background <= 0.5
        high_mask = ~low_mask
        result = np.zeros_like(background, dtype=np.float32)
        result[low_mask] = 2 * background[low_mask] * grain_plate[low_mask]
        result[high_mask] = 1 - 2 * (1 - background[high_mask]) * (1 - grain_plate[high_mask])
        return result

    def _generate_noise_array(self, seed_offset=0, composite=True):
        luma_mask = None
        shadow_bias_strength = self.sliders["Shadow Noise Bias"].get()

        if self.background_pil_image and shadow_bias_strength > 0:
            luma_img = self.background_pil_image.convert('L')
            luma_arr_float = np.array(luma_img, dtype=np.float32) / 255.0
            inverted_mask = 1.0 - luma_arr_float
            luma_mask = 1.0 + (inverted_mask * shadow_bias_strength)

        factor = self.get_supersample_factor()
        render_width, render_height = self.width * factor, self.height * factor

        if luma_mask is not None and factor > 1:
            mask_img = Image.fromarray(luma_mask)
            luma_mask = np.array(mask_img.resize((render_width, render_height), resample=resampling.BILINEAR))

        grain_plate_arr = self._generate_grain_plate(render_width, render_height, seed_offset, luma_mask)
        
        if factor > 1:
            grain_plate_img = Image.fromarray(grain_plate_arr)
            grain_plate_arr = np.array(grain_plate_img.resize((self.width, self.height), resample=resampling.LANCZOS))

        if composite and self.background_pil_image:
            bg_arr_float = np.array(self.background_pil_image.convert('RGB'), dtype=np.float32) / 255.0
            grain_arr_float = np.array(grain_plate_arr, dtype=np.float32) / 255.0
            composited_arr_float = self._overlay_blend(bg_arr_float, grain_arr_float)
            final_array = np.clip(composited_arr_float * 255.0, 0, 255).astype(np.uint8)
        else: 
            final_array = grain_plate_arr
        return final_array

    def _generate_grain_plate(self, width, height, seed_offset, luma_mask=None):
        rng = self.get_rng_for_frame(seed_offset)
        prnu_map, dsnu_map, banding_map = self._get_fixed_maps_for_resolution(width, height)
        
        luma_image = np.full((height, width), 128.0, dtype=np.float32)
        luma_image *= (1.0 + (prnu_map - 1.0) * self.sliders["PRNU (Gain FPN)"].get())
        luma_image += dsnu_map * self.sliders["DSNU (Offset FPN)"].get()
        
        # --- Get base scalar strengths from sliders ---
        shot_noise_strength = self.sliders["Shot Noise (Poisson)"].get()
        read_noise_strength = self.sliders["Read Noise (Gaussian)"].get()
        color_strength = self.sliders["Color Noise"].get()

        # --- Apply Shot Noise ---
        if shot_noise_strength > 0:
            photon_scale = 50.0
            lam = np.clip(luma_image / 255.0 * photon_scale, 0.0, None)
            noisy_counts = rng.poisson(lam).astype(np.float32)
            
            # <-- FIX: Generate base shot noise array first
            shot_noise = (noisy_counts / photon_scale) * 255.0 - luma_image
            shot_noise *= (shot_noise_strength / 5.0) # Apply scalar strength
            
            # <-- FIX: Apply luma_mask to the noise array, not the scalar
            if luma_mask is not None:
                shot_noise *= luma_mask
            
            luma_image += shot_noise

        # --- Apply Read Noise ---
        if read_noise_strength > 0:
            # <-- FIX: Generate base read noise array first
            read_noise = rng.normal(0, 1, luma_image.shape) * read_noise_strength

            # <-- FIX: Apply luma_mask to the noise array
            if luma_mask is not None:
                read_noise *= luma_mask
            
            luma_image += read_noise

        # --- Apply Banding ---
        luma_image += banding_map * 255 * self.sliders["Banding"].get()
        
        # Convert to RGB for color operations
        final_image = np.stack([luma_image] * 3, axis=-1).astype(np.float32)

        # --- Apply Color Noise ---
        if color_strength > 0:
            # <-- FIX: Generate base color noise array first
            color_noise_map = rng.normal(0.0, 1.0, final_image.shape) * color_strength

            # <-- FIX: Apply luma_mask to the noise array (needs to be 3-channel for color)
            if luma_mask is not None:
                color_noise_map *= np.expand_dims(luma_mask, axis=-1)

            final_image += color_noise_map

        # --- Apply Fireflies ---
        firefly_density = self.sliders["Firefly Density (%)"].get() / 100.0
        if firefly_density > 0:
            num_fireflies = int(width * height * firefly_density)
            if num_fireflies > 0:
                y_coords, x_coords = rng.integers(0, height, size=num_fireflies), rng.integers(0, width, size=num_fireflies)
                base_colors = rng.random((num_fireflies, 3)).astype(np.float32)
                gray = (base_colors @ np.array([0.299, 0.587, 0.114], dtype=np.float32))[:, None]
                coloration = self.sliders["Firefly Coloration"].get()
                colors = gray + (base_colors - gray) * coloration
                intensity = self.sliders["Firefly Intensity"].get()
                colors = np.clip(colors * intensity, 0.0, 255.0).astype(np.float32)
                final_image[y_coords, x_coords, :] = colors

        # --- Apply Bit Depth ---
        bit_depth = int(self.sliders["Bit Depth"].get())
        if bit_depth < 8:
            levels = 2**bit_depth
            final_image = np.round(final_image / 255 * (levels - 1)) * (255 / (levels - 1))
            
        return np.clip(final_image, 0, 255).astype(np.uint8)

    def _get_fixed_maps_for_resolution(self, width, height):
        res_key = f"{width}x{height}"
        if res_key in self._cached_fixed_maps: return self._cached_fixed_maps[res_key]
        
        rng = self.get_rng_for_frame(0)
        prnu_map = 1.0 + (rng.standard_normal(size=(height, width), dtype=np.float32) * 0.005)
        dsnu_map = rng.standard_normal(size=(height, width), dtype=np.float32)
        
        seed = self.get_master_seed()
        perlin = PerlinNoise(octaves=6, seed=seed)
        row_noise = np.array([perlin(x) for x in np.linspace(0, 5, height)], dtype=np.float32)
        banding_map = np.tile(row_noise[:, None], (1, width))
        
        self._cached_fixed_maps[res_key] = (prnu_map, dsnu_map, banding_map)
        return self._cached_fixed_maps[res_key]

    # --- UI UPDATING AND EVENT HANDLING ---
    def update_noise(self, event=None):
        if self.initializing: return
        final_array = self._generate_noise_array(seed_offset=0, composite=True)
        self.pil_image = Image.fromarray(final_array)
        self._update_display_image()
        if self.zoom_window: self.update_zoom_view()

    def _update_display_image(self):
        if not self.pil_image: return
        zoom_level_str = self.zoom_var.get()
        img_w, img_h = self.pil_image.size
        
        if zoom_level_str == "Fit to Window":
            frame_w, frame_h = self.canvas.winfo_width() - 4, self.canvas.winfo_height() - 4
            if frame_w <= 1 or frame_h <= 1: return
            scale = min(frame_w / img_w, frame_h / img_h)
            resample_method = resampling.BILINEAR if scale < 1 else resampling.NEAREST
            new_w, new_h = int(img_w * scale), int(img_h * scale)
        else:
            scale = float(zoom_level_str.replace('%','')) / 100.0
            resample_method = resampling.NEAREST if scale >=1 else resampling.BILINEAR
            new_w, new_h = int(img_w * scale), int(img_h * scale)
            
        if new_w > 0 and new_h > 0:
            display_img = self.pil_image.resize((new_w, new_h), resample=resample_method)
            self.photo_image = ImageTk.PhotoImage(display_img)
            if self.canvas_image_id:
                self.canvas.itemconfig(self.canvas_image_id, image=self.photo_image)
            else:
                self.canvas_image_id = self.canvas.create_image(0, 0, anchor='nw', image=self.photo_image)
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def on_slider_update(self, event=None):
        if self.initializing: return
        if self.realtime_preview_var.get() or self.zoom_window:
            self.update_noise()

    def on_zoom_change(self, event=None):
        zoom_str = self.zoom_var.get()
        if zoom_str != "Fit to Window":
            target_zoom = float(zoom_str.replace('%','')) / 100.0
            self.current_zoom_index = min(range(len(self.zoom_levels)), key=lambda i: abs(self.zoom_levels[i]-target_zoom))
        self._update_display_image()

    def on_frame_resize(self, event=None):
        if self.zoom_var.get() == "Fit to Window":
            self.master.after(50, self._update_display_image)

    def update_dimensions(self):
        try:
            new_width, new_height = int(self.width_var.get()), int(self.height_var.get())
            if new_width > 0 and new_height > 0:
                self.master.config(cursor="watch"); self.update_dim_button.config(state="disabled")
                self.master.update_idletasks()
                self.width, self.height = new_width, new_height
                self._cached_fixed_maps.clear()
                self.update_noise()
            else:
                raise ValueError("Dimensions must be positive")
        except ValueError:
            logging.error("Invalid dimensions entered.")
        finally:
            self.master.config(cursor=""); self.update_dim_button.config(state="normal")

    def load_background_image(self):
        filetypes = [("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All files", "*.*")]
        filepath = filedialog.askopenfilename(title="Select Background Image", filetypes=filetypes)
        if not filepath: return
        try:
            img = Image.open(filepath).convert('RGB')
            self.background_pil_image = img
            w, h = img.size
            self.width, self.height = w, h
            self.width_var.set(str(w)); self.height_var.set(str(h))
            self.width_entry.config(state="disabled"); self.height_entry.config(state="disabled")
            self.update_dim_button.config(state="disabled")
            self.bg_status_label.config(text=f"Loaded: {os.path.basename(filepath)}")
            self.sliders["Shadow Noise Bias"].config(state="normal")
            self.update_noise()
        except Exception as e:
            logging.error(f"Failed to load image: {e}")
            self.clear_background_image()

    def clear_background_image(self):
        self.background_pil_image = None
        self.width_entry.config(state="normal"); self.height_entry.config(state="normal")
        self.update_dim_button.config(state="normal")
        self.bg_status_label.config(text="Status: No Image Loaded")
        self.sliders["Shadow Noise Bias"].set(0)
        self.sliders["Shadow Noise Bias"].config(state="disabled")
        self.update_noise()

    def export_sequence(self):
        try:
            prefix = self.prefix_var.get()
            start_frame, end_frame = int(self.start_frame_var.get()), int(self.end_frame_var.get())
            if start_frame > end_frame or not prefix:
                logging.error("Invalid sequence parameters.")
                return
        except ValueError:
            logging.error("Frame numbers must be integers.")
            return
        
        filepath = filedialog.askdirectory(title="Select Export Directory")
        if not filepath: return
        
        self.export_button.config(state="disabled"); self.master.config(cursor="watch")
        self.progress_bar["maximum"] = end_frame - start_frame + 1
        self.progress_bar["value"] = 0
        
        threading.Thread(target=self._export_worker, args=(filepath, start_frame, end_frame, prefix), daemon=True).start()

    def _export_worker(self, filepath, start_frame, end_frame, prefix):
        export_mode = self.export_mode_var.get()
        do_composite = (export_mode == "Composited Image") and self.background_pil_image
        
        for i, frame_num in enumerate(range(start_frame, end_frame + 1)):
            final_array = self._generate_noise_array(seed_offset=frame_num, composite=do_composite)
            img_to_save = Image.fromarray(final_array)
            os.makedirs(filepath, exist_ok=True)
            save_path = os.path.join(filepath, f"{prefix}.{frame_num:04d}.png")
            img_to_save.save(save_path)
            self.master.after(0, self._update_progress, i + 1)
            
        self.master.after(0, self._export_done_ui_cleanup)

    def _update_progress(self, value): self.progress_bar["value"] = value
    
    def _export_done_ui_cleanup(self):
        self.export_button.config(state="normal")
        self.master.config(cursor="")
        self.progress_bar["value"] = 0

    def save_image(self):
        if not self.pil_image: return
        filetypes = [("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=filetypes)
        if not filepath: return
        
        export_mode = self.export_mode_var.get()
        do_composite = (export_mode == "Composited Image") and self.background_pil_image

        if do_composite:
            self.pil_image.save(filepath)
            logging.info(f"Saved composited image to {filepath}")
        else:
            grain_plate_array = self._generate_noise_array(seed_offset=0, composite=False)
            Image.fromarray(grain_plate_array).save(filepath)
            logging.info(f"Saved grain plate to {filepath}")

    def get_master_seed(self):
        try: return int(self.seed_var.get())
        except (ValueError, TypeError): return 0

    def update_zoom_view(self):
        if not self.zoom_window or not self.pil_image: return
        crop_size = int(self.ZOOM_VIEW_SIZE / self.ZOOM_FACTOR)
        img_w, img_h = self.pil_image.size
        center_x, center_y = img_w // 2, img_h // 2
        
        x1, y1 = max(0, center_x - crop_size // 2), max(0, center_y - crop_size // 2)
        x2, y2 = min(img_w, x1 + crop_size), min(img_h, y1 + crop_size)
        box = (x1, y1, x2, y2)
        
        pil_crop = self.pil_image.crop(box)
        zoomed_image = pil_crop.resize((self.ZOOM_VIEW_SIZE, self.ZOOM_VIEW_SIZE), resample=resampling.NEAREST)
        
        self.zoom_photo_image = ImageTk.PhotoImage(zoomed_image)
        self.zoom_label.config(image=self.zoom_photo_image)
        self.zoom_label.image = self.zoom_photo_image

    def toggle_zoom_window(self):
        if self.zoom_window:
            self.on_zoom_window_close()
        else:
            self.zoom_window = tk.Toplevel(self.master)
            self.zoom_window.title(f"Detail View ({self.ZOOM_FACTOR * 100:.0f}%)")
            self.zoom_window.geometry(f"{self.ZOOM_VIEW_SIZE}x{self.ZOOM_VIEW_SIZE}")
            self.zoom_window.resizable(False, False)
            
            self.zoom_label = ttk.Label(self.zoom_window)
            self.zoom_label.pack(fill=tk.BOTH, expand=True)
            
            self.zoom_window.protocol("WM_DELETE_WINDOW", self.on_zoom_window_close)
            self.zoom_button.config(text="Hide Detail View")
            self.update_noise()

    def on_zoom_window_close(self):
        if self.zoom_window:
            self.zoom_window.destroy()
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_button.config(text="Show Detail View")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrganicGrainGeneratorApp(root)
    root.mainloop()
