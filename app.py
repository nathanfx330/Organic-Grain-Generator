import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
from PIL import Image, ImageTk
from perlin_noise import PerlinNoise
import time
import threading
import logging

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
        self.master.title("Organic Grain Generator (Supersampling Edition)")
        self.master.geometry("1400x800")

        # --- Core Properties ---
        self.initializing = True
        self.width = 1920
        self.height = 1080
        # Fixed maps are now managed dynamically based on render resolution
        self._cached_fixed_maps = {}
        self.pil_image = None # Full-resolution image

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

        self.image_frame = ttk.Frame(self.master, padding="10", style='Dark.TFrame')
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.image_label = ttk.Label(self.image_frame, style='Dark.TLabel')
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.photo_image = None # Display image

        self.create_widgets()
        
        self.initializing = False
        self.master.after(100, self.update_noise)
        self.image_frame.bind("<Configure>", self.on_frame_resize)

    def create_widgets(self):
        # ... (Dimension widget code is unchanged)
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


        # Controls
        perf_frame = ttk.LabelFrame(self.control_frame, text="Controls")
        perf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(perf_frame, text="Noise Seed:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.seed_var = tk.StringVar(value=str(np.random.randint(0, 10000)))
        self.seed_entry = ttk.Entry(perf_frame, textvariable=self.seed_var, width=8)
        self.seed_entry.grid(row=0, column=1, padx=5, pady=3)
        self.realtime_preview_var = tk.BooleanVar(value=True)
        self.realtime_preview_check = ttk.Checkbutton(perf_frame, text="Real-time Preview", variable=self.realtime_preview_var)
        self.realtime_preview_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5)

        # NEW: Supersampling Option
        ttk.Label(perf_frame, text="Supersampling:").grid(row=2, column=0, padx=5, pady=3, sticky="w")
        self.supersample_var = tk.StringVar()
        self.supersample_combo = ttk.Combobox(perf_frame, textvariable=self.supersample_var, state="readonly", width=10)
        self.supersample_combo['values'] = ("1x (Off)", "2x", "3x", "4x")
        self.supersample_combo.set("1x (Off)")
        self.supersample_combo.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        self.update_preview_button = ttk.Button(perf_frame, text="Update Full Preview", command=self.update_noise)
        self.update_preview_button.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        
        # ... (Other widgets are unchanged)
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

        view_save_frame = ttk.LabelFrame(self.control_frame, text="View & Save")
        view_save_frame.pack(fill=tk.X, pady=10)
        zoom_frame = ttk.Frame(view_save_frame)
        zoom_frame.pack(fill=tk.X, padx=5, pady=(2,8))
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        self.zoom_var = tk.StringVar()
        self.zoom_combo = ttk.Combobox(zoom_frame, textvariable=self.zoom_var, state="readonly", width=12)
        self.zoom_combo['values'] = ("Fit to Window", "100%", "50%", "25%")
        self.zoom_combo.set("Fit to Window")
        self.zoom_combo.pack(side=tk.LEFT, padx=5)
        self.zoom_combo.bind("<<ComboboxSelected>>", self.on_zoom_change)
        self.zoom_button = ttk.Button(view_save_frame, text="Show Detail View", command=self.toggle_zoom_window)
        self.zoom_button.pack(fill=tk.X, padx=5, pady=(0,5))
        save_button = ttk.Button(view_save_frame, text="Save Single Image", command=self.save_image)
        save_button.pack(fill=tk.X, padx=5)
        
        export_frame = ttk.LabelFrame(self.control_frame, text="Sequence Export")
        export_frame.pack(fill=tk.X, pady=5)
        ttk.Label(export_frame, text="Prefix:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.prefix_var = tk.StringVar(value="noise_plate")
        self.prefix_entry = ttk.Entry(export_frame, textvariable=self.prefix_var)
        self.prefix_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=2, sticky="ew")
        ttk.Label(export_frame, text="Start:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.start_frame_var = tk.StringVar(value="1001")
        self.start_frame_entry = ttk.Entry(export_frame, textvariable=self.start_frame_var, width=8)
        self.start_frame_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(export_frame, text="End:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.end_frame_var = tk.StringVar(value="1010")
        self.end_frame_entry = ttk.Entry(export_frame, textvariable=self.end_frame_var, width=8)
        self.end_frame_entry.grid(row=1, column=3, padx=5, pady=2)
        self.export_button = ttk.Button(export_frame, text="Export Sequence", command=self.export_sequence)
        self.export_button.grid(row=2, column=0, columnspan=4, pady=5, sticky="ew")
        self.progress_bar = ttk.Progressbar(export_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=3, column=0, columnspan=4, pady=(5,0), sticky="ew")

    # --- RNG and Supersampling Helpers ---
    def get_rng_for_frame(self, seed_offset=0):
        master_seed = self.get_master_seed()
        return np.random.default_rng(master_seed + seed_offset)

    def get_supersample_factor(self):
        selection = self.supersample_var.get()
        return int(selection.split('x')[0]) if 'x' in selection else 1

    # --- Core Noise Generation (Refactored for Supersampling) ---
    def _generate_noise_array(self, seed_offset=0):
        factor = self.get_supersample_factor()
        render_width = self.width * factor
        render_height = self.height * factor

        if factor > 1:
            logging.info(f"Supersampling at {factor}x. Rendering on a {render_width}x{render_height} canvas.")

        # Generate noise at the potentially higher resolution
        high_res_array = self._generate_at_resolution(render_width, render_height, seed_offset)

        if factor > 1:
            # Downsample the high-resolution result for a higher quality final image
            logging.info("Downsampling high-resolution canvas...")
            high_res_image = Image.fromarray(high_res_array, 'RGB')
            # LANCZOS is a high-quality filter for downscaling
            final_image = high_res_image.resize((self.width, self.height), resample=resampling.LANCZOS)
            return np.array(final_image)
        else:
            return high_res_array

    def _generate_at_resolution(self, width, height, seed_offset):
        rng = self.get_rng_for_frame(seed_offset)
        prnu_map, dsnu_map, banding_map = self._get_fixed_maps_for_resolution(width, height)

        luma_image = np.full((height, width), 128.0, dtype=np.float32)
        luma_image *= (1.0 + (prnu_map - 1.0) * self.sliders["PRNU (Gain FPN)"].get())
        luma_image += dsnu_map * self.sliders["DSNU (Offset FPN)"].get()
        
        shot_noise_intensity = self.sliders["Shot Noise (Poisson)"].get()
        if shot_noise_intensity > 0:
            photon_scale = 50.0 * max(1.0, shot_noise_intensity)
            lam = np.clip(luma_image / 255.0 * photon_scale, 0.0, None)
            noisy_counts = rng.poisson(lam).astype(np.float32)
            luma_image = (noisy_counts / photon_scale) * 255.0 * shot_noise_intensity
        
        luma_image += rng.normal(0, self.sliders["Read Noise (Gaussian)"].get(), luma_image.shape)
        luma_image += banding_map * 255 * self.sliders["Banding"].get()

        final_image = np.stack([luma_image] * 3, axis=-1)
        
        color_intensity = self.sliders["Color Noise"].get()
        if color_intensity > 0:
            final_image += rng.normal(0, color_intensity, final_image.shape)

        firefly_density = self.sliders["Firefly Density (%)"].get() / 100.0
        if firefly_density > 0:
            num_fireflies = int(width * height * firefly_density)
            if num_fireflies > 0:
                y_coords = rng.integers(0, height, size=num_fireflies)
                x_coords = rng.integers(0, width, size=num_fireflies)
                base_colors = rng.random((num_fireflies, 3))
                gray = (base_colors @ np.array([0.299, 0.587, 0.114]))[:, None]
                coloration = self.sliders["Firefly Coloration"].get()
                colors = gray + (base_colors - gray) * coloration
                intensity = float(self.sliders["Firefly Intensity"].get())
                colors = np.clip(colors * intensity, 0, 255)
                final_image[y_coords, x_coords] = colors.astype(np.uint8)

        bit_depth = int(self.sliders["Bit Depth"].get())
        if bit_depth < 8:
            levels = 2**bit_depth
            final_image = np.round(final_image / 255 * (levels - 1)) * (255 / (levels - 1))
        
        return np.clip(final_image, 0, 255).astype(np.uint8)

    def _get_fixed_maps_for_resolution(self, width, height):
        """Generates or retrieves cached fixed noise maps for a specific resolution."""
        res_key = f"{width}x{height}"
        if res_key in self._cached_fixed_maps:
            return self._cached_fixed_maps[res_key]
        
        logging.info(f"Generating new fixed-pattern noise maps for {res_key}...")
        rng = self.get_rng_for_frame(0) # Fixed maps always use the master seed
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
        final_array = self._generate_noise_array(seed_offset=0)
        self.pil_image = Image.fromarray(final_array, 'RGB')
        logging.info(f"Noise data generated in {time.time() - start_time:.3f} seconds.")
        self._update_display_image()
        if self.zoom_window:
            self.update_zoom_view()

    def _update_display_image(self):
        # This method remains largely unchanged
        if not self.pil_image: return
        zoom_level = self.zoom_var.get()
        img_w, img_h = self.pil_image.size
        display_img = None
        if zoom_level == "Fit to Window":
            frame_w, frame_h = self.image_frame.winfo_width(), self.image_frame.winfo_height()
            if frame_w <= 1 or frame_h <= 1: return
            scale = min(frame_w / img_w, frame_h / img_h)
            if scale < 1:
                new_w, new_h = int(img_w * scale), int(img_h * scale)
                display_img = self.pil_image.resize((new_w, new_h), resample=resampling.BILINEAR)
            else:
                display_img = self.pil_image
        else:
            scale = float(zoom_level.replace('%','')) / 100.0
            new_w, new_h = int(img_w * scale), int(img_h * scale)
            if new_w > 0 and new_h > 0:
                display_img = self.pil_image.resize((new_w, new_h), resample=resampling.NEAREST)
            else:
                display_img = self.pil_image
        if display_img:
            self.photo_image = ImageTk.PhotoImage(display_img)
            self.image_label.config(image=self.photo_image, anchor="center")
            self.image_label.image = self.photo_image

    # --- Event Handlers ---
    def on_slider_update(self, event=None):
        # This method remains largely unchanged
        if self.initializing: return
        if self.realtime_preview_var.get():
            self.update_preview_button.config(state="disabled")
            self.update_noise()
        else:
            self.update_preview_button.config(state="normal")
            if self.zoom_window:
                final_array = self._generate_noise_array(seed_offset=0)
                self.pil_image = Image.fromarray(final_array, 'RGB')
                self.update_zoom_view()
            
    def on_zoom_change(self, event=None):
        self._update_display_image()

    def on_frame_resize(self, event=None):
        if self.zoom_var.get() == "Fit to Window":
            self._update_display_image()

    def update_dimensions(self):
        try:
            new_width, new_height = int(self.width_var.get()), int(self.height_var.get())
            if new_width > 0 and new_height > 0:
                self.master.config(cursor="watch"); self.update_dim_button.config(state="disabled")
                self.master.update_idletasks()
                self.width, self.height = new_width, new_height
                # Clear cached maps so they regenerate at the new size
                self._cached_fixed_maps.clear()
                self.update_noise()
                self.master.config(cursor=""); self.update_dim_button.config(state="normal")
        except ValueError:
            logging.error("Invalid dimensions. Please enter integers.")

    # --- Export Logic (Unchanged, now automatically uses supersampling if selected) ---
    def export_sequence(self):
        try:
            prefix = self.prefix_var.get()
            start_frame = int(self.start_frame_var.get())
            end_frame = int(self.end_frame_var.get())
            if start_frame > end_frame or not prefix:
                logging.error("Invalid sequence parameters.")
                return
        except ValueError:
            logging.error("Invalid frame numbers. Please enter integers.")
            return
        filepath = filedialog.askdirectory(title="Select Export Directory")
        if not filepath: return
        
        self.export_button.config(state="disabled")
        self.master.config(cursor="watch")
        total_frames = end_frame - start_frame + 1
        self.progress_bar["maximum"] = total_frames
        self.progress_bar["value"] = 0
        
        export_thread = threading.Thread(
            target=self._export_worker, 
            args=(filepath, start_frame, end_frame, prefix),
            daemon=True
        )
        export_thread.start()

    def _export_worker(self, filepath, start_frame, end_frame, prefix):
        logging.info(f"Starting sequence export to {filepath}...")
        for i, frame_num in enumerate(range(start_frame, end_frame + 1)):
            logging.info(f"Generating frame {frame_num}...")
            # This now automatically handles supersampling based on the UI setting
            final_array = self._generate_noise_array(seed_offset=frame_num)
            img = Image.fromarray(final_array, 'RGB')
            filename = f"{prefix}.{frame_num:04d}.png"
            img.save(f"{filepath}/{filename}")
            
            self.master.after(0, self._update_progress, i + 1)
        
        self.master.after(0, self._export_done_ui_cleanup)

    def _update_progress(self, value):
        self.progress_bar["value"] = value

    def _export_done_ui_cleanup(self):
        logging.info("Sequence export complete.")
        self.export_button.config(state="normal")
        self.master.config(cursor="")
        self.progress_bar["value"] = 0

    def save_image(self):
        if self.pil_image:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png", 
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            if filepath:
                # The self.pil_image already has supersampling applied from the last update_noise call
                self.pil_image.save(filepath)
                logging.info(f"Image saved to {filepath}")

    # --- Utility and Helper Methods (Unchanged) ---
    def get_master_seed(self):
        try: return int(self.seed_var.get())
        except (ValueError, TypeError): return 0

    def update_zoom_view(self):
        if not self.zoom_window or not self.pil_image: return
        crop_size = int(self.ZOOM_VIEW_SIZE / self.ZOOM_FACTOR)
        img_w, img_h = self.pil_image.size # Use the final image size
        center_x, center_y = img_w // 2, img_h // 2
        x1 = max(0, center_x - crop_size // 2)
        y1 = max(0, center_y - crop_size // 2)
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
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_button.config(text="Show Detail View")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrganicGrainGeneratorApp(root)
    root.mainloop()
