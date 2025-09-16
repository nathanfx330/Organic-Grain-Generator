import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
from PIL import Image, ImageTk
from perlin_noise import PerlinNoise

class OrganicGrainGeneratorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Organic Grain Generator")

        self.initializing = True
        self.width = 512
        self.height = 512
        self.prnu_map = None
        self.dsnu_map = None
        self.banding_map = None
        self.pil_image = None

        # Zoom window variables
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_photo_image = None
        self.ZOOM_FACTOR = 5.0
        self.ZOOM_VIEW_SIZE = 256

        # GUI Layout
        self.control_frame = ttk.Frame(self.master, padding="10")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.image_frame = ttk.Frame(self.master, padding="10")
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.photo_image = None

        self.create_widgets()
        self.generate_fixed_noise_maps()
        
        self.initializing = False
        self.update_noise()

    def create_widgets(self):
        # (Dimension widgets are unchanged)
        dim_frame = ttk.LabelFrame(self.control_frame, text="Dimensions")
        dim_frame.pack(fill=tk.X, pady=5)
        # ...

        sliders_frame = ttk.LabelFrame(self.control_frame, text="Noise Parameters")
        sliders_frame.pack(fill=tk.X, pady=5)
        self.sliders = {}
        # --- NEW: Added "Color Noise" slider parameter ---
        slider_params = {
            "PRNU (Gain FPN)": (0, 5.0, 0),
            "DSNU (Offset FPN)": (0, 10.0, 0),
            "Shot Noise (Poisson)": (0, 2.0, 0),
            "Read Noise (Gaussian)": (0, 15.0, 0),
            "Color Noise": (0, 20.0, 0), # <-- NEW
            "Banding": (0, 0.1, 0),
            "Bit Depth": (4, 8, 8)
        }
        for i, (name, params) in enumerate(slider_params.items()):
            ttk.Label(sliders_frame, text=name).grid(row=i, column=0, sticky="w", padx=5)
            slider = ttk.Scale(sliders_frame, from_=params[0], to=params[1], orient=tk.HORIZONTAL, command=self.update_noise)
            slider.set(params[2])
            slider.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            self.sliders[name] = slider
        sliders_frame.columnconfigure(1, weight=1)

        # (View and Save buttons are unchanged)
        view_frame = ttk.LabelFrame(self.control_frame, text="View Options")
        view_frame.pack(fill=tk.X, pady=10)
        # ...

    # (Other methods like toggle_zoom_window, update_dimensions, etc. are unchanged)
    # ...

    def update_noise(self, event=None):
        if self.initializing: return

        # --- MODIFIED: The entire noise pipeline is updated for color ---

        # 1. Start with a 50% grey MONOCHROME image for luminance calculations
        luma_image = np.full((self.height, self.width), 128.0, dtype=np.float32)

        # 2. Apply luminance-based noise components as before
        prnu_intensity = self.sliders["PRNU (Gain FPN)"].get()
        luma_image *= (1.0 + (self.prnu_map - 1.0) * prnu_intensity)

        dsnu_intensity = self.sliders["DSNU (Offset FPN)"].get()
        luma_image += self.dsnu_map * dsnu_intensity

        shot_noise_intensity = self.sliders["Shot Noise (Poisson)"].get()
        if shot_noise_intensity > 0:
            image_scaled = np.maximum(0, luma_image) * shot_noise_intensity
            luma_image = np.random.poisson(image_scaled).astype(np.float32) / shot_noise_intensity
        
        read_noise_intensity = self.sliders["Read Noise (Gaussian)"].get()
        luma_image += np.random.normal(0, read_noise_intensity, luma_image.shape)

        banding_intensity = self.sliders["Banding"].get()
        luma_image += self.banding_map * 255 * banding_intensity

        # 3. --- NEW: Introduce Color Noise ---
        # First, promote our monochrome luminance image to 3-channel RGB
        # by stacking it three times. This is our base grain structure.
        final_image = np.stack([luma_image, luma_image, luma_image], axis=-1)

        # Now, add independent random noise to each channel for color variation
        color_intensity = self.sliders["Color Noise"].get()
        if color_intensity > 0:
            # Create a 3-channel noise pattern
            color_variation = np.random.normal(0, color_intensity, final_image.shape)
            final_image += color_variation

        # 4. Apply Quantization to all channels
        bit_depth = int(self.sliders["Bit Depth"].get())
        if bit_depth < 8:
            levels = 2**bit_depth
            final_image = np.round(final_image / 255 * (levels - 1)) * (255 / (levels - 1))
        
        # 5. Clip, convert to uint8, and display
        final_array = np.clip(final_image, 0, 255).astype(np.uint8)
        
        # The rest of the update/display logic works perfectly with the new RGB array
        self.pil_image = Image.fromarray(final_array, 'RGB') # <-- MODIFIED: Specify RGB mode
        self.photo_image = ImageTk.PhotoImage(self.pil_image)
        self.image_label.config(image=self.photo_image)
        self.image_label.image = self.photo_image

        if self.zoom_window:
            # ... (zoom logic is unchanged, it will now show the color image correctly)
            # ...
            pil_crop = Image.fromarray(crop_array, 'RGB') # <-- MODIFIED: Specify RGB mode


    # (All other methods are unchanged. Here is the full, clean code for copy-pasting)
    def __init__(self, master):
        self.master = master
        self.master.title("Organic Grain Generator")

        self.initializing = True
        self.width = 512
        self.height = 512
        self.prnu_map = None
        self.dsnu_map = None
        self.banding_map = None
        self.pil_image = None

        self.zoom_window = None
        self.zoom_label = None
        self.zoom_photo_image = None
        self.ZOOM_FACTOR = 5.0
        self.ZOOM_VIEW_SIZE = 256

        self.control_frame = ttk.Frame(self.master, padding="10")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.image_frame = ttk.Frame(self.master, padding="10")
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.photo_image = None

        self.create_widgets()
        self.generate_fixed_noise_maps()
        
        self.initializing = False
        self.update_noise()

    def create_widgets(self):
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
        self.update_dim_button = ttk.Button(dim_frame, text="Update", command=self.update_dimensions)
        self.update_dim_button.grid(row=2, column=0, columnspan=2, pady=5)

        sliders_frame = ttk.LabelFrame(self.control_frame, text="Noise Parameters")
        sliders_frame.pack(fill=tk.X, pady=5)
        self.sliders = {}
        slider_params = {
            "PRNU (Gain FPN)": (0, 5.0, 0), "DSNU (Offset FPN)": (0, 10.0, 0),
            "Shot Noise (Poisson)": (0, 2.0, 0), "Read Noise (Gaussian)": (0, 15.0, 0),
            "Color Noise": (0, 20.0, 0),
            "Banding": (0, 0.1, 0), "Bit Depth": (4, 8, 8)
        }
        for i, (name, params) in enumerate(slider_params.items()):
            ttk.Label(sliders_frame, text=name).grid(row=i, column=0, sticky="w", padx=5)
            slider = ttk.Scale(sliders_frame, from_=params[0], to=params[1], orient=tk.HORIZONTAL, command=self.update_noise)
            slider.set(params[2])
            slider.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            self.sliders[name] = slider
        sliders_frame.columnconfigure(1, weight=1)

        view_frame = ttk.LabelFrame(self.control_frame, text="View Options")
        view_frame.pack(fill=tk.X, pady=10)
        self.zoom_button = ttk.Button(view_frame, text="Show Detail View", command=self.toggle_zoom_window)
        self.zoom_button.pack(fill=tk.X)

        save_button = ttk.Button(self.control_frame, text="Save Image", command=self.save_image)
        save_button.pack(fill=tk.X, pady=15)

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
        if self.zoom_window: self.zoom_window.destroy()
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_button.config(text="Show Detail View")

    def update_dimensions(self):
        try:
            new_width, new_height = int(self.width_var.get()), int(self.height_var.get())
            if new_width > 0 and new_height > 0:
                self.update_dim_button.config(state="disabled"); self.master.config(cursor="watch")
                self.master.update_idletasks()
                self.width, self.height = new_width, new_height
                self.generate_fixed_noise_maps()
                self.update_noise()
                self.master.config(cursor=""); self.update_dim_button.config(state="normal")
        except ValueError: print("Invalid dimensions. Please enter integers.")

    def generate_fixed_noise_maps(self):
        print("Generating new fixed-pattern noise maps...")
        self.prnu_map = 1.0 + (np.random.randn(self.height, self.width) * 0.005)
        self.dsnu_map = np.random.randn(self.height, self.width)
        noise = PerlinNoise(octaves=6, seed=np.random.randint(0, 1000))
        row_noise = np.array([noise([i * 0.1, 0]) for i in range(self.height)])
        self.banding_map = np.tile(row_noise, (self.width, 1)).T
        print("...generation complete.")

    def update_noise(self, event=None):
        if self.initializing: return

        luma_image = np.full((self.height, self.width), 128.0, dtype=np.float32)

        luma_image *= (1.0 + (self.prnu_map - 1.0) * self.sliders["PRNU (Gain FPN)"].get())
        luma_image += self.dsnu_map * self.sliders["DSNU (Offset FPN)"].get()
        
        shot_noise_intensity = self.sliders["Shot Noise (Poisson)"].get()
        if shot_noise_intensity > 0:
            image_scaled = np.maximum(0, luma_image) * shot_noise_intensity
            luma_image = np.random.poisson(image_scaled).astype(np.float32) / shot_noise_intensity
        
        luma_image += np.random.normal(0, self.sliders["Read Noise (Gaussian)"].get(), luma_image.shape)
        luma_image += self.banding_map * 255 * self.sliders["Banding"].get()

        final_image = np.stack([luma_image, luma_image, luma_image], axis=-1)
        
        color_intensity = self.sliders["Color Noise"].get()
        if color_intensity > 0:
            final_image += np.random.normal(0, color_intensity, final_image.shape)

        bit_depth = int(self.sliders["Bit Depth"].get())
        if bit_depth < 8:
            levels = 2**bit_depth
            final_image = np.round(final_image / 255 * (levels - 1)) * (255 / (levels - 1))
        
        final_array = np.clip(final_image, 0, 255).astype(np.uint8)
        
        self.pil_image = Image.fromarray(final_array, 'RGB')
        self.photo_image = ImageTk.PhotoImage(self.pil_image)
        self.image_label.config(image=self.photo_image)
        self.image_label.image = self.photo_image

        if self.zoom_window:
            crop_size = int(self.ZOOM_VIEW_SIZE / self.ZOOM_FACTOR)
            center_x, center_y = self.width // 2, self.height // 2
            x1, y1 = max(0, center_x - crop_size // 2), max(0, center_y - crop_size // 2)
            x2, y2 = min(self.width, x1 + crop_size), min(self.height, y1 + crop_size)
            crop_array = final_array[y1:y2, x1:x2]
            pil_crop = Image.fromarray(crop_array, 'RGB')
            zoomed_image = pil_crop.resize((self.ZOOM_VIEW_SIZE, self.ZOOM_VIEW_SIZE), resample=Image.NEAREST)
            self.zoom_photo_image = ImageTk.PhotoImage(zoomed_image)
            self.zoom_label.config(image=self.zoom_photo_image)
            self.zoom_label.image = self.zoom_photo_image

    def save_image(self):
        if self.pil_image:
            filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
            if filepath: self.pil_image.save(filepath); print(f"Image saved to {filepath}")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrganicGrainGeneratorApp(root)
    root.mainloop()
