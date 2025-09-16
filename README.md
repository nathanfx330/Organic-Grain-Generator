# Organic Grain Generator

![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)

**Organic Grain Generator** is a desktop application for procedurally generating realistic, organic digital camera noise. It provides a highly interactive "workbench" for artists, developers, and technicians to model and craft specific noise patterns and export them as grain plates for compositing, texturing, and VFX workflows.

Instead of using a simple overlay, this tool simulates the distinct components of a digital camera sensor's noise profile, giving you fine-grained control over the final look.

## Key Features

- **Interactive Real-Time Preview**: All noise parameters are controlled by sliders, with the output image updating instantly.
- **Component-Based Noise Model**: Individually control different types of noise for a more realistic result:
  - **Fixed-Pattern Noise (FPN)**: Simulates unique sensor imperfections (PRNU gain and DSNU offset).
  - **Random Noise**: Models signal-dependent Shot (Poisson) noise and signal-independent Read (Gaussian) noise.
  - **Banding Noise**: Creates horizontal pattern noise common in digital sensors, generated with Perlin noise.
  - **Quantization**: Simulates bit-depth reduction for posterization effects.
- **Custom Resolution**: Enter any width and height to generate noise plates suitable for HD, 4K, or any other format.
- **Live Detail View**: Open a separate, 500% zoomed-in "pixel-peeping" window to analyze the grain structure.
- **Save for Compositing**: Export the final noise texture as a PNG or JPG file for use in Nuke, After Effects, Blender, or other compositing software.

## Why Use This Tool?

Adding realistic camera noise is one of the most effective ways to integrate a CG element into live-action footage. It:

- Adds realism to CG renders
- Creates consistent grain across multiple shots
- Generates textures for procedural materials
- Helps study the individual components of digital noise

## Installation

### Prerequisites

- Python 3.9 or newer

### Install Dependencies

```bash
pip install numpy Pillow perlin-noise
````

## Usage

Run the application:

```bash
python app.py
```

1. **Set Dimensions**: Enter your desired width and height, then click "Update".
2. **Adjust Sliders**: Move sliders to modify noise in real-time.
3. **Inspect Details**: Click "Show Detail View" for a 500% zoomed view of the image center.
4. **Save Plate**: Click "Save Image" to export the noise plate.

## Contributing

Contributions are welcome! Open an issue or submit a pull request for new features, bug fixes, or performance improvements.

**Potential Future Features:**

* Color Noise: Independent control for Luminance and Chrominance noise
* Presets: Save and load slider configurations for specific "camera" profiles
* Animation: Generate sequences for animated grain
* More Banding Patterns: Vertical banding or other structured noise

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

```

