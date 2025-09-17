# Organic Grain Generator

![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)

**Organic Grain Generator** is a desktop application for procedurally generating realistic, organic digital camera noise. It provides a highly interactive "workbench" for artists, developers, and technicians to model and craft specific noise patterns and export them as grain plates for compositing, texturing, and VFX workflows.

Instead of using a simple overlay, this tool simulates the distinct components of a digital camera sensor's noise profile, giving you fine-grained control over the final look.

---

## Key Features

### VFX Pipeline Ready
- **Reproducible Noise Seed**: Ensure noise patterns are deterministic and repeatable for consistent results.
- **Frame Sequence Export**: Export noise plates as numbered image sequences (`plate.1001.png`, `plate.1002.png`, etc.) with custom prefixes, start and end frames.
- **Custom Resolution**: Generate plates at HD, 4K, 8K, or any resolution.

### Advanced Noise Model
- **Component-Based Simulation**:
  - **Fixed-Pattern Noise (FPN)**: Simulates PRNU gain and DSNU offset.
  - **Random Noise**: Shot (Poisson) + Read (Gaussian) noise.
  - **Color Noise**: Independent chrominance noise for rich grain.
  - **"Firefly" Noise**: Hot pixels (e.g., GH4 high ISO look) with density, intensity, and coloration controls.
  - **Banding Noise**: Horizontal pattern noise via Perlin noise.
  - **Quantization**: Simulates bit-depth reduction.

### Optimized for High Resolutions
- **Performance Controls**: Disable "Real-time Preview" to avoid lag at 4K+. Regenerate manually when needed.
- **Scalable Preview**: Zoom dropdown (`Fit to Window`, 100%, 50%, 25%).
- **Live Detail View**: 500% zoom window for pixel-level analysis.

---

## Why Use This Tool?

Adding realistic camera noise helps to:
- Integrate CG elements into live-action footage.
- Add realism and consistency across shots.
- Generate unique procedural textures.
- Study and replicate digital sensor noise components.

---

## Installation

### Prerequisites
- Python 3.9+

### Install Dependencies
```bash
pip install numpy Pillow perlin-noise
````

---

## Usage

Run the application:

```bash
python app.py
```

### Workflow

1. **Set Core Parameters**: Enter Width, Height, and Noise Seed. Click *Update Dimensions*.
2. **Craft the Noise**: Adjust sliders for different noise components.
3. **Control Preview**:

   * Use Zoom dropdown for scaling.
   * Disable *Real-time Preview* at high resolutions; refresh manually.
4. **Inspect Details**: Open *Show Detail View* for 500% zoom.
5. **Export Plates**:

   * Single shot: *Save Single Image*.
   * Sequence: Fill export fields → *Export Sequence*.

---

## Contributing

Contributions are welcome!
Open an issue or submit a pull request for:

* New features
* Bug fixes
* Performance improvements

### Potential Future Features

* **Presets**: Save/load configurations for camera profiles.
* **More Banding Types**: Vertical or structured patterns.
* **Anamorphic Grain**: Non-square pixel aspect ratios.

---

## License

This project is licensed under the **MIT License**.
See the [LICENSE](LICENSE) file for details.
