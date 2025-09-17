import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
from PIL import Image, ImageTk, ImageOps
from perlin_noise import PerlinNoise
import time

class OrganicGrainGeneratorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Organic Grain Generator (Enhanced)")
        self.master.geometry("1400x800") # Start with a larger default window size

        # --- Core Properties ---
        self.initializing = True
        self.width = 1920
        self.height = 1080
        self.prnu_map = None
        self.dsnu_map = None
        self.banding_map = None
        self.pil_image = None # This will always store the full-resolution image

        # --- Zoom Window ---
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_photo_image = None
        self.ZOOM_FACTOR = 5.0
        self.ZOOM_VIEW_SIZE = 256

        # --- GUI Layout & Styling ---
        # *** FIX: Define styles for ttk widgets ***
        style = ttk.Style(self.master)
        style.configure('Dark.TFrame', background='#282828')
        style.configure('Dark.TLabel', background='#282828')

        self.control_frame = ttk.Frame(self.master, padding="10", width=350)
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.control_frame.pack_propagate(False) # Prevent frame from shrinking
        
        # *** FIX: Apply style instead of using the 'background' option ***
        self.image_frame = ttk.Frame(self.master, padding="10", style='Dark.TFrame')
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # *** FIX: Apply style to the label as well ***
        self.image_label = ttk.Label(self.image_frame, style='Dark.TLabel')
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.photo_image = None # This stores the (potentially scaled) display image

        self.create_widgets()
        self.generate_fixed_noise_maps()
        
        self.initializing = False
        # Delay initial update to allow window to draw and get correct dimensions for "Fit"
        self.master.after(100, self.update_noise)

        # Bind the resize event for dynamic "Fit to Window"
        self.image_frame.bind("<Configure>", self.on_frame_resize)

    def create_widgets(self):
        # ... (Dimension, Seed, and Performance controls are unchanged)
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

        perf_frame = ttk.LabelFrame(self.control_frame, text="Controls")
        perf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(perf_frame, text="Noise Seed:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.seed_var = tk.StringVar(value=str(np.random.randint(0, 10000)))
        self.seed_entry = ttk.Entry(perf_frame, textvariable=self.seed_var, width=8)
        self.seed_entry.grid(row=0, column=1, padx=5, pady=3)
        self.realtime_preview_var = tk.BooleanVar(value=True)
        self.realtime_preview_check = ttk.Checkbutton(perf_frame, text="Real-time Preview", variable=self.realtime_preview_var)
        self.realtime_preview_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        self.update_preview_button = ttk.Button(perf_frame, text="Update Full Preview", command=self.update_noise)
        self.update_preview_button.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        
        # ... (Noise Parameter sliders are unchanged)
        sliders_frame = ttk.LabelFrame(self.control_frame, text="Noise Parameters")
        sliders_frame.pack(fill=tk.X, pady=5)
        self.sliders = {}
        slider_params = {
            "PRNU (Gain FPN)": (0, 5.0, 0), "DSNU (Offset FPN)": (0, 10.0, 0),
            "Shot Noise (Poisson)": (0, 2.0, 0), "Read Noise (Gaussian)": (0, 15.0, 0),
            "Color Noise": (0, 20.0, 0), "Banding": (0, 0.1, 0), "Bit Depth": (4, 8, 8),
            "Firefly Density (%)": (0, 0.1, 0), "Firefly Intensity": (0, 500.0, 0),
            "Firefly Coloration": (0, 2.0, 0)
        }
        for i, (name, params) in enumerate(slider_params.items()):
            ttk.Label(sliders_frame, text=name).grid(row=i, column=0, sticky="w", padx=5)
            slider = ttk.Scale(sliders_frame, from_=params[0], to=params[1], orient=tk.HORIZONTAL, command=self.on_slider_update)
            slider.set(params[2])
            slider.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            self.sliders[name] = slider
        sliders_frame.columnconfigure(1, weight=1)

        # --- MODIFIED: View & Save with Zoom control ---
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
        
        # ... (Sequence Export is unchanged)
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
    
    # --- NEW: Event handlers for zoom and window resize ---
    def on_zoom_change(self, event=None):
        self._update_display_image()

    def on_frame_resize(self, event=None):
        if self.zoom_var.get() == "Fit to Window":
            self._update_display_image()

    def _update_display_image(self):
        """Scales the full-res self.pil_image to fit the display based on zoom level."""
        if not self.pil_image: return

        zoom_level = self.zoom_var.get()
        img_w, img_h = self.pil_image.size
        display_img = None

        if zoom_level == "Fit to Window":
            frame_w = self.image_frame.winfo_width()
            frame_h = self.image_frame.winfo_height()
            if frame_w <= 1 or frame_h <= 1: return # Frame not drawn yet

            scale = min(frame_w / img_w, frame_h / img_h)
            if scale < 1: # Only scale down
                new_w = int(img_w * scale)
                new_h = int(img_h * scale)
                display_img = self.pil_image.resize((new_w, new_h), resample=Image.Resampling.BILINEAR)
            else: # Image is smaller than frame, show at 100%
                display_img = self.pil_image
        else: # Fixed percentage zoom
            scale = float(zoom_level.replace('%','')) / 100.0
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            if new_w > 0 and new_h > 0:
                display_img = self.pil_image.resize((new_w, new_h), resample=Image.Resampling.NEAREST)
            else:
                display_img = self.pil_image
        
        if display_img:
            self.photo_image = ImageTk.PhotoImage(display_img)
            self.image_label.config(image=self.photo_image, anchor="center")
            self.image_label.image = self.photo_image

    def update_noise(self, event=None):
        if self.initializing: return
        
        # 1. Generate the full-resolution noise image data
        start_time = time.time()
        final_array = self._generate_noise_array(seed_offset=0)
        self.pil_image = Image.fromarray(final_array, 'RGB')
        print(f"Noise data generated in {time.time() - start_time:.3f} seconds.")
        
        # 2. Update the scaled display image in the UI
        self._update_display_image()
        
        # 3. Update the detailed (zoomed) preview window if it's open
        if self.zoom_window:
            self.update_zoom_view()

    # The core noise generation logic is unchanged.
    def _generate_noise_array(self, seed_offset=0):
        # Set seed for this specific frame's random components
        master_seed = self.get_master_seed()
        np.random.seed(master_seed + seed_offset)

        # 1. Start with a 50% grey MONOCHROME image
        luma_image = np.full((self.height, self.width), 128.0, dtype=np.float32)

        # 2. Apply luminance-based noise
        luma_image *= (1.0 + (self.prnu_map - 1.0) * self.sliders["PRNU (Gain FPN)"].get())
        luma_image += self.dsnu_map * self.sliders["DSNU (Offset FPN)"].get()
        
        shot_noise_intensity = self.sliders["Shot Noise (Poisson)"].get()
        if shot_noise_intensity > 0:
            image_scaled = np.maximum(0, luma_image / 255.0) * shot_noise_intensity * 100
            luma_image = np.random.poisson(image_scaled).astype(np.float32) / (shot_noise_intensity * 100) * 255.0
        
        luma_image += np.random.normal(0, self.sliders["Read Noise (Gaussian)"].get(), luma_image.shape)
        luma_image += self.banding_map * 255 * self.sliders["Banding"].get()

        # 3. Promote to RGB and add Color Noise
        final_image = np.stack([luma_image, luma_image, luma_image], axis=-1)
        color_intensity = self.sliders["Color Noise"].get()
        if color_intensity > 0:
            final_image += np.random.normal(0, color_intensity, final_image.shape)

        # 4. NEW: Add Firefly Noise
        firefly_density = self.sliders["Firefly Density (%)"].get() / 100.0
        if firefly_density > 0:
            num_fireflies = int(self.width * self.height * firefly_density)
            if num_fireflies > 0:
                firefly_intensity = self.sliders["Firefly Intensity"].get()
                firefly_coloration = self.sliders["Firefly Coloration"].get()
                y_coords = np.random.randint(0, self.height, num_fireflies)
                x_coords = np.random.randint(0, self.width, num_fireflies)
                colors = np.random.rand(num_fireflies, 3)
                gray = np.dot(colors, [0.299, 0.587, 0.114])[:, np.newaxis]
                colors = gray + (colors - gray) * firefly_coloration
                final_image[y_coords, x_coords] = colors * firefly_intensity

        # 5. Apply Quantization
        bit_depth = int(self.sliders["Bit Depth"].get())
        if bit_depth < 8:
            levels = 2**bit_depth
            final_image = np.round(final_image / 255 * (levels - 1)) * (255 / (levels - 1))
        
        return np.clip(final_image, 0, 255).astype(np.uint8)

    # --- All other helper and utility methods remain unchanged from the previous version ---

    def on_slider_update(self, event=None):
        if self.initializing: return
        # The logic here is now split: generate data, then update display
        if self.realtime_preview_var.get():
            self.update_preview_button.config(state="disabled")
            self.update_noise()
        else: # If not real-time, only update the small detail view
            self.update_preview_button.config(state="normal")
            if self.zoom_window:
                # To make this responsive, we need to regenerate the data first
                final_array = self._generate_noise_array(seed_offset=0)
                self.pil_image = Image.fromarray(final_array, 'RGB')
                self.update_zoom_view()
            
    def get_master_seed(self):
        try: return int(self.seed_var.get())
        except (ValueError, TypeError): return 0

    def generate_fixed_noise_maps(self):
        print("Generating new fixed-pattern noise maps...")
        master_seed = self.get_master_seed()
        np.random.seed(master_seed)
        self.prnu_map = 1.0 + (np.random.randn(self.height, self.width) * 0.005)
        self.dsnu_map = np.random.randn(self.height, self.width)
        noise = PerlinNoise(octaves=6, seed=master_seed)
        row_noise = np.array([noise([i * 0.1, 0]) for i in range(self.height)])
        self.banding_map = np.tile(row_noise, (self.width, 1)).T
        print("...generation complete.")

    def update_dimensions(self):
        try:
            new_width, new_height = int(self.width_var.get()), int(self.height_var.get())
            if new_width > 0 and new_height > 0:
                self.master.config(cursor="watch"); self.update_dim_button.config(state="disabled")
                self.master.update_idletasks()
                self.width, self.height = new_width, new_height
                self.generate_fixed_noise_maps()
                self.update_noise()
                self.master.config(cursor=""); self.update_dim_button.config(state="normal")
        except ValueError:
            print("Invalid dimensions. Please enter integers.")

    def update_zoom_view(self):
        if not self.zoom_window or not self.pil_image: return
        crop_size = int(self.ZOOM_VIEW_SIZE / self.ZOOM_FACTOR)
        center_x, center_y = self.width // 2, self.height // 2
        x1, y1 = max(0, center_x - crop_size // 2), max(0, center_y - crop_size // 2)
        box = (x1, y1, x1 + crop_size, y1 + crop_size)
        pil_crop = self.pil_image.crop(box)
        zoomed_image = pil_crop.resize((self.ZOOM_VIEW_SIZE, self.ZOOM_VIEW_SIZE), resample=Image.Resampling.NEAREST)
        self.zoom_photo_image = ImageTk.PhotoImage(zoomed_image)
        self.zoom_label.config(image=self.zoom_photo_image)
        self.zoom_label.image = self.zoom_photo_image

    def export_sequence(self):
        try:
            prefix = self.prefix_var.get()
            start_frame = int(self.start_frame_var.get())
            end_frame = int(self.end_frame_var.get())
            if start_frame > end_frame or not prefix:
                print("Invalid sequence parameters.")
                return
        except ValueError:
            print("Invalid frame numbers. Please enter integers.")
            return

        filepath = filedialog.askdirectory(title="Select Export Directory")
        if not filepath: return
        
        self.export_button.config(state="disabled")
        self.master.config(cursor="watch")
        
        total_frames = end_frame - start_frame + 1
        self.progress_bar["maximum"] = total_frames
        self.progress_bar["value"] = 0

        for i, frame_num in enumerate(range(start_frame, end_frame + 1)):
            print(f"Generating frame {frame_num}...")
            final_array = self._generate_noise_array(seed_offset=frame_num)
            img = Image.fromarray(final_array, 'RGB')
            filename = f"{prefix}.{frame_num:04d}.png"
            img.save(f"{filepath}/{filename}")
            
            self.progress_bar["value"] = i + 1
            self.master.update_idletasks()
        
        print("Sequence export complete.")
        self.export_button.config(state="normal")
        self.master.config(cursor="")

    def save_image(self):
        if self.pil_image:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png", 
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            if filepath:
                self.pil_image.save(filepath)
                print(f"Image saved to {filepath}")

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
