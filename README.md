# Organic Grain Generator

![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)

**Organic Grain Generator** is a desktop application for procedurally generating realistic, organic digital camera noise. It provides a highly interactive workbench for artists, developers, and technicians to model and craft specific noise patterns and export them as grain plates for compositing, texturing, and VFX workflows.

Unlike simple overlay noise tools, this generator simulates the distinct components of a digital camera sensor's noise profile, giving you fine-grained control over the final look.

---

## ✨ Key Features

### 🎬 VFX Pipeline Ready

* **Reproducible Noise Seed** – Ensure patterns are 100% deterministic and repeatable.
* **Frame Sequence Export** – Export noise plates as numbered image sequences (e.g., `plate.1001.png`) with custom prefix, start frame, and end frame.
* **Custom Resolution** – Generate plates at any resolution (HD, 4K, 8K, etc.).

### 🔬 Advanced Sensor Noise Model

Individually control different types of sensor noise for highly realistic results:

* **Fixed-Pattern Noise (FPN)** – Sensor imperfections (PRNU gain & DSNU offset).
* **Random Noise** – Signal-dependent Shot (Poisson) noise and signal-independent Read (Gaussian) noise.
* **Color Noise** – Independent chrominance noise for rich, colorful grain.
* **Firefly Noise** – Simulates bright “hot pixels” seen in high ISO footage.
* **Banding Noise** – Horizontal noise patterns.
* **Quantization** – Simulates bit-depth reduction, creating posterization and banding effects.

### 🌀 Grain Texture Control

* **Frequency of Detail** – Control the fineness or coarseness of noise patterns.
* **Erosion / Blending** – Adjust how grain integrates across the frame for subtler or more aggressive appearance.
* **Perlin Gain** – Modulate structured noise for richer detail or controlled patterning.

### ⚡ Optimized for High Resolutions

* **Performance Controls** – Disable "Real-time Preview" for 4K+ and update manually.
* **Scalable Preview** – Zoom options (`Fit to Window`, 100%, 50%, 25%).
* **Live Detail View** – Separate 500% zoom window for analyzing fine grain structure in real time.

---

## 💡 Why Use This Tool?

Adding realistic camera noise is one of the most effective ways to integrate CG elements into live-action footage. It helps to:

* Add realism to renders and composites.
* Ensure consistent grain across multiple shots or artists.
* Generate unique textures for procedural materials.
* Study and replicate individual noise components for technical or artistic purposes.

---

## 🚀 Installation

### Prerequisites

* Python **3.9+**
* Conda (recommended)

### Create a Dedicated Conda Environment

```bash
conda create --name grain_gen_env -c conda-forge python=3.9 "numpy<2.0" pillow opencv
conda activate grain_gen_env
pip install perlin-noise
```

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

   * Adjust sliders to control individual sensor noise components.
   * Use frequency, erosion, and Perlin gain to sculpt the grain texture.
   * Preview updates automatically if enabled.

3. **Control the Preview**

   * Use the **Zoom dropdown** to resize the main view.
   * Disable **Real-time Preview** for large resolutions and refresh manually.
   * Open **Detail View** for a live 500% zoomed preview.

4. **Export**

   * **Single Image** – Save a single noise plate.
   * **Sequence** – Configure prefix, start, and end frames to export a numbered sequence.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).


