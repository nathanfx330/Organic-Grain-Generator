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

        # Variables for the zoom window
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
        if self.zoom_window:
            self.zoom_window.destroy()
        self.zoom_window = None
        self.zoom_label = None
        self.zoom_button.config(text="Show Detail View")

    def update_dimensions(self):
        try:
            new_width = int(self.width_var.get())
            new_height = int(self.height_var.get())
            if new_width > 0 and new_height > 0:
                self.update_dim_button.config(state="disabled")
                self.master.config(cursor="watch")
                self.master.update_idletasks()
                self.width = new_width
                self.height = new_height
                self.generate_fixed_noise_maps()
                self.update_noise()
                self.master.config(cursor="")
                self.update_dim_button.config(state="normal")
        except ValueError:
            print("Invalid dimensions. Please enter integers.")

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

        image = np.full((self.height, self.width), 128.0, dtype=np.float32)
        prnu_intensity = self.sliders["PRNU (Gain FPN)"].get()
        image *= (1.0 + (self.prnu_map - 1.0) * prnu_intensity)
        dsnu_intensity = self.sliders["DSNU (Offset FPN)"].get()
        image += self.dsnu_map * dsnu_intensity
        shot_noise_intensity = self.sliders["Shot Noise (Poisson)"].get()
        if shot_noise_intensity > 0:
            image_scaled = np.maximum(0, image) * shot_noise_intensity
            image = np.random.poisson(image_scaled).astype(np.float32) / shot_noise_intensity
        read_noise_intensity = self.sliders["Read Noise (Gaussian)"].get()
        image += np.random.normal(0, read_noise_intensity, image.shape)
        banding_intensity = self.sliders["Banding"].get()
        image += self.banding_map * 255 * banding_intensity
        bit_depth = int(self.sliders["Bit Depth"].get())
        if bit_depth < 8:
            levels = 2**bit_depth
            image = np.round(image / 255 * (levels - 1)) * (255 / (levels - 1))
        
        final_array = np.clip(image, 0, 255).astype(np.uint8)
        
        self.pil_image = Image.fromarray(final_array)
        self.photo_image = ImageTk.PhotoImage(self.pil_image)
        self.image_label.config(image=self.photo_image)
        self.image_label.image = self.photo_image

        if self.zoom_window:
            crop_size = int(self.ZOOM_VIEW_SIZE / self.ZOOM_FACTOR)
            center_x, center_y = self.width // 2, self.height // 2
            x1 = max(0, center_x - crop_size // 2)
            y1 = max(0, center_y - crop_size // 2)
            x2 = min(self.width, x1 + crop_size)
            y2 = min(self.height, y1 + crop_size)
            
            crop_array = final_array[y1:y2, x1:x2]
            
            pil_crop = Image.fromarray(crop_array)
            zoomed_image = pil_crop.resize((self.ZOOM_VIEW_SIZE, self.ZOOM_VIEW_SIZE), resample=Image.NEAREST)
            
            self.zoom_photo_image = ImageTk.PhotoImage(zoomed_image)
            self.zoom_label.config(image=self.zoom_photo_image)
            self.zoom_label.image = self.zoom_photo_image

    def save_image(self):
        if self.pil_image:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
            )
            if filepath:
                self.pil_image.save(filepath)
                print(f"Image saved to {filepath}")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrganicGrainGeneratorApp(root)
    root.mainloop()