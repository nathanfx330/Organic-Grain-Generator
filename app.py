import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
from PIL import Image, ImageTk
from perlin_noise import PerlinNoise
import time
import threading
import logging
import os

# --- Setup professional logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Compatibility for Pillow resampling (Image.Resampling fallback) ---
try:
    resampling = Image.Resampling
except AttributeError:
    # Pillow < 9.1 fallback
    class _Res:
        NEAREST = Image.NEAREST
        BILINEAR = Image.BILINEAR
        LANCZOS = Image.LANCZOS
    resampling = _Res()

class OrganicGrainGeneratorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Organic Grain Generator (Compositing Edition)")
        self.master.geometry("1400x800")

        # --- Core Properties ---
        self.initializing = True
        self.width = 1920
        self.height = 1080
        self.background_pil_image = None # Loaded background image
        self._cached_fixed_maps = {}
        self.pil_image = None # Full-resolution image for display/saving

        # --- Zoom Window ---
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_photo_image = None
        self.ZOOM_FACTOR = 5.0
        self.ZOOM_VIEW_SIZE = 256

        # --- GUI Layout & Styling ---
        style = ttk.Style(self.master)
        style.configure('Dark.TFrame', background='#282828')
        style.configure('Dark.TLabel', background='#282828')

        self.control_frame = ttk.Frame(self.master, padding="10", width=350)
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.control_frame.pack_propagate(False)

        # --- Image Frame with Canvas and Scrollbars ---
        self.image_frame = ttk.Frame(self.master, padding="10", style='Dark.TFrame')
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
        
        self.photo_image = None # Display image

        self.create_widgets()
        
        self.initializing = False
        self.master.after(100, self.update_noise)
        self.image_frame.bind("<Configure>", self.on_frame_resize)
        
        # --- Middle Mouse Pan Bindings ---
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)

    def _pan_start(self, event):
        """Records the starting position for panning."""
        self.canvas.scan_mark(event.x, event.y)

    def _pan_move(self, event):
        """Moves the canvas view based on mouse drag."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def create_widgets(self):
        # ... All widget creation code remains the same, no changes needed here ...
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

        # --- Background Image Compositing ---
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
        
        # --- Noise Sliders ---
        sliders_frame = ttk.LabelFrame(self.control_frame, text="Noise Parameters")
        sliders_frame.pack(fill=tk.X, pady=5)
        self.sliders = {}
        slider_params = {
            "PRNU (Gain FPN)": (0, 5.0, 0), "DSNU (Offset FPN)": (0, 10.0, 0),
            "Shot Noise (Poisson)": (0, 5.0, 0), "Read Noise (Gaussian)": (0, 15.0, 0),
            "Color Noise": (0, 20.0, 0), "Banding": (0, 0.1, 0), "Bit Depth": (4, 8, 8),
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

        # --- View and Save ---
        view_save_frame = ttk.LabelFrame(self.control_frame, text="View & Save")
        view_save_frame.pack(fill=tk.X, pady=10)
        zoom_frame = ttk.Frame(view_save_frame)
        zoom_frame.pack(fill=tk.X, padx=5, pady=(2,8))
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        self.zoom_var = tk.StringVar()
        self.zoom_combo = ttk.Combobox(zoom_frame, textvariable=self.zoom_var, state="readonly", width=12)
        self.zoom_combo['values'] = ("Fit to Window", "200%", "100%", "50%", "25%")
        self.zoom_combo.set("Fit to Window")
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


    # --- RNG and Supersampling Helpers (Unchanged) ---
    def get_rng_for_frame(self, seed_offset=0):
        master_seed = self.get_master_seed()
        return np.random.default_rng(master_seed + seed_offset)

    def get_supersample_factor(self):
        selection = (self.supersample_var.get() or "").strip().lower()
        try:
            if 'x' in selection:
                val = selection.split('x')[0].strip()
                return max(1, int(val))
        except Exception:
            pass
        return 1

    # --- Core Noise and Compositing Logic (Unchanged) ---
    def _overlay_blend(self, background, grain_plate):
        low_mask = background <= 0.5
        high_mask = ~low_mask
        result = np.zeros_like(background)
        result[low_mask] = 2 * background[low_mask] * grain_plate[low_mask]
        result[high_mask] = 1 - 2 * (1 - background[high_mask]) * (1 - grain_plate[high_mask])
        return result

    def _generate_noise_array(self, seed_offset=0, composite=True):
        factor = self.get_supersample_factor()
        render_width, render_height = self.width * factor, self.height * factor
        if factor > 1:
            logging.info(f"Supersampling at {factor}x. Rendering grain on a {render_width}x{render_height} canvas.")
        grain_plate_arr = self._generate_grain_plate(render_width, render_height, seed_offset)
        if factor > 1:
            logging.info("Downsampling high-resolution grain plate...")
            grain_plate_img = Image.fromarray(grain_plate_arr)
            final_grain_plate = grain_plate_img.resize((self.width, self.height), resample=resampling.LANCZOS)
            grain_plate_arr = np.array(final_grain_plate)
        if composite and self.background_pil_image:
            logging.info("Compositing grain over background image.")
            bg_arr_float = np.array(self.background_pil_image, dtype=np.float32) / 255.0
            grain_arr_float = np.array(grain_plate_arr, dtype=np.float32) / 255.0
            composited_arr_float = self._overlay_blend(bg_arr_float, grain_arr_float)
            final_array = np.clip(composited_arr_float * 255.0, 0, 255).astype(np.uint8)
        else:
            final_array = grain_plate_arr
        return final_array

    def _generate_grain_plate(self, width, height, seed_offset):
        rng = self.get_rng_for_frame(seed_offset)
        prnu_map, dsnu_map, banding_map = self._get_fixed_maps_for_resolution(width, height)
        luma_image = np.full((height, width), 128.0, dtype=np.float32)
        luma_image *= (1.0 + (prnu_map - 1.0) * self.sliders["PRNU (Gain FPN)"].get())
        luma_image += dsnu_map * self.sliders["DSNU (Offset FPN)"].get()
        shot_noise_intensity = float(self.sliders["Shot Noise (Poisson)"].get())
        if shot_noise_intensity > 0:
            photon_scale = 50.0
            lam = np.clip(luma_image / 255.0 * photon_scale, 0.0, None)
            noisy_counts = rng.poisson(lam).astype(np.float32)
            shot_noise = (noisy_counts / photon_scale) * 255.0 - luma_image
            luma_image = luma_image + shot_noise * (shot_noise_intensity / max(1.0, shot_noise_intensity))
        luma_image += rng.normal(0, self.sliders["Read Noise (Gaussian)"].get(), luma_image.shape)
        luma_image += banding_map * 255 * self.sliders["Banding"].get()
        final_image = np.stack([luma_image] * 3, axis=-1).astype(np.float32)
        color_intensity = float(self.sliders["Color Noise"].get())
        if color_intensity > 0:
            final_image += rng.normal(0.0, color_intensity, final_image.shape).astype(np.float32)
        firefly_density = float(self.sliders["Firefly Density (%)"].get()) / 100.0
        if firefly_density > 0:
            num_fireflies = int(width * height * firefly_density)
            if num_fireflies > 0:
                y_coords, x_coords = rng.integers(0, height, size=num_fireflies), rng.integers(0, width, size=num_fireflies)
                base_colors = rng.random((num_fireflies, 3)).astype(np.float32)
                gray = (base_colors @ np.array([0.299, 0.587, 0.114], dtype=np.float32))[:, None]
                coloration = float(self.sliders["Firefly Coloration"].get())
                colors = gray + (base_colors - gray) * coloration
                intensity = float(self.sliders["Firefly Intensity"].get())
                colors = np.clip(colors * intensity, 0.0, 255.0).astype(np.float32)
                final_image[y_coords, x_coords, :] = colors
        bit_depth = int(self.sliders["Bit Depth"].get())
        if bit_depth < 8:
            levels = 2**bit_depth
            final_image = np.round(final_image / 255 * (levels - 1)) * (255 / (levels - 1))
        return np.clip(final_image, 0, 255).astype(np.uint8)

    def _get_fixed_maps_for_resolution(self, width, height):
        res_key = f"{width}x{height}"
        if res_key in self._cached_fixed_maps:
            return self._cached_fixed_maps[res_key]
        logging.info(f"Generating new fixed-pattern noise maps for {res_key}...")
        rng = self.get_rng_for_frame(0)
        prnu_map = 1.0 + (rng.standard_normal(size=(height, width)) * 0.005)
        dsnu_map = rng.standard_normal(size=(height, width))
        master_seed = self.get_master_seed()
        perlin = PerlinNoise(octaves=6, seed=master_seed)
        xs = np.linspace(0, 5, height)
        row_noise = np.array([perlin(x) for x in xs], dtype=np.float32)
        banding_map = np.tile(row_noise[:, None], (1, width))
        self._cached_fixed_maps[res_key] = (prnu_map, dsnu_map, banding_map)
        logging.info("...fixed map generation complete.")
        return self._cached_fixed_maps[res_key]

    # --- UI Update and Display Logic ---
    def update_noise(self, event=None):
        if self.initializing: return
        start_time = time.time()
        final_array = self._generate_noise_array(seed_offset=0, composite=True)
        self.pil_image = Image.fromarray(final_array)
        logging.info(f"Noise data generated in {time.time() - start_time:.3f} seconds.")
        self._update_display_image()
        if self.zoom_window:
            self.update_zoom_view()

    def _update_display_image(self):
        """Displays the current self.pil_image on the canvas with correct zoom and scrolling."""
        if not self.pil_image: return
        
        zoom_level = self.zoom_var.get()
        img_w, img_h = self.pil_image.size
        display_img = None
        
        if zoom_level == "Fit to Window":
            # Scale down to fit the canvas viewable area
            # A small buffer is subtracted to prevent scrollbars from appearing due to rounding
            frame_w = self.canvas.winfo_width() - 4
            frame_h = self.canvas.winfo_height() - 4
            if frame_w <= 1 or frame_h <= 1: return # Not visible yet

            scale = min(frame_w / img_w, frame_h / img_h)
            if scale < 1:
                new_w, new_h = int(img_w * scale), int(img_h * scale)
                display_img = self.pil_image.resize((new_w, new_h), resample=resampling.BILINEAR)
            else:
                display_img = self.pil_image
        else:
            # Scale based on percentage
            scale = float(zoom_level.replace('%','')) / 100.0
            new_w, new_h = int(img_w * scale), int(img_h * scale)
            if new_w > 0 and new_h > 0:
                # Use NEAREST for crisp pixels when zooming in
                display_img = self.pil_image.resize((new_w, new_h), resample=resampling.NEAREST)
            else:
                display_img = self.pil_image

        if display_img:
            # Keep a reference to prevent garbage collection
            self.photo_image = ImageTk.PhotoImage(display_img)
            self.canvas.delete("all")
            # Place image on canvas and update scroll region
            self.canvas.create_image(0, 0, anchor='nw', image=self.photo_image)
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    # --- Event Handlers (Unchanged) ---
    def on_slider_update(self, event=None):
        if self.initializing: return
        if self.realtime_preview_var.get():
            self.update_preview_button.config(state="disabled")
            self.update_noise()
        else:
            self.update_preview_button.config(state="normal")
            if self.zoom_window:
                final_array = self._generate_noise_array(seed_offset=0, composite=True)
                self.pil_image = Image.fromarray(final_array)
                self.update_zoom_view()

    def on_zoom_change(self, event=None): self._update_display_image()
    def on_frame_resize(self, event=None):
        if self.zoom_var.get() == "Fit to Window": self._update_display_image()

    def update_dimensions(self):
        try:
            new_width, new_height = int(self.width_var.get()), int(self.height_var.get())
            if new_width > 0 and new_height > 0:
                self.master.config(cursor="watch"); self.update_dim_button.config(state="disabled")
                self.master.update_idletasks()
                self.width, self.height = new_width, new_height
                self._cached_fixed_maps.clear()
                self.update_noise()
                self.master.config(cursor=""); self.update_dim_button.config(state="normal")
        except ValueError: logging.error("Invalid dimensions. Please enter integers.")

    def load_background_image(self):
        filepath = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if not filepath: return
        try:
            img = Image.open(filepath).convert('RGB')
            self.background_pil_image = img
            w, h = img.size
            self.width, self.height = w, h
            self.width_var.set(str(w))
            self.height_var.set(str(h))
            self.width_entry.config(state="disabled")
            self.height_entry.config(state="disabled")
            self.update_dim_button.config(state="disabled")
            self.bg_status_label.config(text=f"Loaded: {os.path.basename(filepath)}")
            logging.info(f"Loaded background image: {filepath} ({w}x{h})")
            self.update_noise()
        except Exception as e:
            logging.error(f"Failed to load image: {e}")
            self.clear_background_image()

    def clear_background_image(self):
        self.background_pil_image = None
        self.width_entry.config(state="normal")
        self.height_entry.config(state="normal")
        self.update_dim_button.config(state="normal")
        self.bg_status_label.config(text="Status: No Image Loaded")
        logging.info("Background image cleared.")
        self.update_noise()

    # --- Export Logic (Unchanged) ---
    def export_sequence(self):
        try:
            prefix, start_frame, end_frame = self.prefix_var.get(), int(self.start_frame_var.get()), int(self.end_frame_var.get())
            if start_frame > end_frame or not prefix:
                logging.error("Invalid sequence parameters."); return
        except ValueError:
            logging.error("Invalid frame numbers. Please enter integers."); return
        filepath = filedialog.askdirectory(title="Select Export Directory")
        if not filepath: return
        self.export_button.config(state="disabled")
        self.master.config(cursor="watch")
        self.progress_bar["maximum"] = end_frame - start_frame + 1
        self.progress_bar["value"] = 0
        export_thread = threading.Thread(
            target=self._export_worker, 
            args=(filepath, start_frame, end_frame, prefix),
            daemon=True
        )
        export_thread.start()

    def _export_worker(self, filepath, start_frame, end_frame, prefix):
        logging.info(f"Starting sequence export to {filepath}...")
        export_mode = self.export_mode_var.get()
        do_composite = (export_mode == "Composited Image")
        if do_composite and not self.background_pil_image:
            logging.warning("Export mode is 'Composited' but no background is loaded. Exporting grain plate only.")
            do_composite = False
        for i, frame_num in enumerate(range(start_frame, end_frame + 1)):
            logging.info(f"Generating frame {frame_num}...")
            final_array = self._generate_noise_array(seed_offset=frame_num, composite=do_composite)
            img = Image.fromarray(final_array)
            filename = f"{prefix}.{frame_num:04d}.png"
            outpath = os.path.join(filepath, filename)
            img.save(outpath)
            self.master.after(0, self._update_progress, i + 1)
        self.master.after(0, self._export_done_ui_cleanup)

    def _update_progress(self, value): self.progress_bar["value"] = value

    def _export_done_ui_cleanup(self):
        logging.info("Sequence export complete.")
        self.export_button.config(state="normal")
        self.master.config(cursor="")
        self.progress_bar["value"] = 0

    def save_image(self):
        if not self.pil_image:
            logging.warning("No image data to save. Please generate noise first.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png", 
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        if not filepath: return
        export_mode = self.export_mode_var.get()
        do_composite = (export_mode == "Composited Image")
        if do_composite and self.background_pil_image:
            self.pil_image.save(filepath)
            logging.info(f"Composited image saved to {filepath}")
        else:
            grain_plate_array = self._generate_noise_array(seed_offset=0, composite=False)
            img = Image.fromarray(grain_plate_array)
            img.save(filepath)
            logging.info(f"Grain plate saved to {filepath}")

    # --- Utility and Helper Methods (Unchanged) ---
    def get_master_seed(self):
        try: return int(self.seed_var.get())
        except (ValueError, TypeError): return 0

    def update_zoom_view(self):
        if not self.zoom_window or not self.pil_image: return
        crop_size = int(self.ZOOM_VIEW_SIZE / self.ZOOM_FACTOR)
        img_w, img_h = self.pil_image.size
        center_x, center_y = img_w // 2, img_h // 2
        x1, y1 = max(0, center_x - crop_size // 2), max(0, center_y - crop_size // 2)
        box = (x1, y1, x1 + crop_size, y1 + crop_size)
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
        self.zoom_window, self.zoom_label = None, None
        self.zoom_button.config(text="Show Detail View")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrganicGrainGeneratorApp(root)
    root.mainloop()
