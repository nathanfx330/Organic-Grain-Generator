# Organic Grain Generator

![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)

**Organic Grain Generator** is a desktop application for procedurally generating realistic, organic digital camera noise. It provides a highly interactive "workbench" for artists, developers, and technicians to model and craft specific noise patterns and export them as grain plates for compositing, texturing, and VFX workflows.

Instead of using a simple overlay, this tool simulates the distinct components of a digital camera sensor's noise profile, giving you fine-grained control over the final look.

---

## ✨ Key Features

### 🎬 VFX Pipeline Ready
- **Reproducible Noise Seed**: Set a master seed to ensure patterns are 100% deterministic and repeatable.  
- **Frame Sequence Export**: Export noise plates as numbered image sequences (e.g., `plate.1001.png`, `plate.1002.png`) with custom prefix, start frame, and end frame.  
- **Custom Resolution**: Generate plates at any resolution (HD, 4K, 8K, etc.).

### 🔬 Advanced Noise Model
Individually control different types of noise for a highly realistic result:
- **Fixed-Pattern Noise (FPN)** – Sensor imperfections (PRNU gain & DSNU offset).  
- **Random Noise** – Signal-dependent Shot (Poisson) noise + signal-independent Read (Gaussian) noise.  
- **Color Noise** – Independent chrominance noise for rich, colorful grain.  
- **Firefly Noise** – Simulates the bright "hot pixels" seen in high ISO footage (e.g., Panasonic GH4).  
- **Banding Noise** – Horizontal noise generated with Perlin noise.  
- **Quantization** – Simulates bit-depth reduction, creating posterization and banding effects.

### ⚡ Optimized for High Resolutions
- **Performance Controls**: Disable "Real-time Preview" when working in 4K+ and update manually.  
- **Scalable Preview**: Zoom options (`Fit to Window`, 100%, 50%, 25%).  
- **Live Detail View**: Separate, 500% zoom "pixel-peeping" window to analyze fine grain structure in real time.

---

## 💡 Why Use This Tool?

Adding realistic camera noise is one of the most effective ways to integrate CG elements into live-action footage. It helps to:  
- Add realism to renders and composites.  
- Ensure consistent grain across multiple shots/artists.  
- Generate unique textures for procedural materials.  
- Study and replicate individual noise components.

---

## 🚀 Installation

### Prerequisites
- Python **3.9+**

### Install Dependencies
```bash
pip install numpy Pillow perlin-noise
````

---

## ▶️ Usage

Run the application:

```bash
python app.py
```

### Workflow

1. **Set Core Parameters**

   * Enter Width, Height, and Noise Seed.
   * Click **Update Dimensions** to generate the base plate.

2. **Craft the Noise**

   * Adjust sliders to control different noise components.
   * Preview updates automatically (if enabled).

3. **Control the Preview**

   * Use the **Zoom dropdown** to resize the main view.
   * Disable **Real-time Preview** for large resolutions and refresh manually.
   * Open **Detail View** for a live 500% zoomed preview.

4. **Export**

   * **Single Image**: Save a single noise plate.
   * **Sequence**: Configure export fields and save a numbered sequence.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
