# Ghost Window Project

This project implements a "Ghost Window" that sits on your desktop background (behind all other windows) and plays a video using hardware acceleration. It is designed for Linux (X11) and provides two implementations to compare performance:

1.  **MPV Renderer**: Uses `mpv` with `--wid` embedding.
2.  **GStreamer Renderer**: Uses a GStreamer pipeline with `nvh264dec`.

## Requirements

### System Packages (Ubuntu/Debian)
You need to install system dependencies for Python bindings, X11 extensions, and GStreamer.

```bash
sudo apt update
sudo apt install -y \
    python3-dev \
    libcairo2-dev libgirepository1.0-dev \
    mpv \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav gstreamer1.0-tools \
    gir1.2-gst-plugins-base-1.0 gir1.2-gstreamer-1.0
```

*Note: For NVIDIA hardware decoding in GStreamer, ensure you have the NVIDIA drivers and `gstreamer1.0-plugins-bad` installed. The `nvcodec` plugin provides `nvh264dec` and `nvh265dec`.*

### Python Dependencies
Install the required Python packages:

```bash
pip install PyQt6 python-xlib PyGObject
```

**Note:** If installing `PyGObject` fails with `girepository-2.0` errors on Ubuntu 22.04, use an older version:
```bash
pip install PyGObject==3.44.0
```

## Usage

### 1. MPV Implementation
This version launches `mpv` embedded in the window.

```bash
python3 ghost_mpv.py /path/to/your/video.mp4
```

*   **Features:** Hardware decoding (`--hwdec=nvdec`), infinite loop, IPC control socket enabled.
*   **Performance:** Generally very efficient as MPV handles the rendering pipeline highly optimized.

### 2. GStreamer Implementation
This version builds a custom GStreamer pipeline.

```bash
python3 ghost_gstreamer.py /path/to/your/video.mp4
```

*   **Pipeline:** `filesrc ! qtdemux ! h264parse ! nvh264dec ! glimagesink`
*   **Troubleshooting:** If the video does not play, check your GStreamer plugins:
    ```bash
    gst-inspect-1.0 nvcodec
    ```
    You should see `nvh264dec`, `nvh265dec`, `nvh264enc`, etc. If missing, ensure `gstreamer1.0-plugins-bad` is installed with NVIDIA support.

## Architecture

*   **Language:** Python 3 + PyQt6
*   **Window Management:**
    *   **Atoms:** Uses `_NET_WM_WINDOW_TYPE_DESKTOP`, `_NET_WM_STATE_BELOW`, `_NET_WM_STATE_SKIP_TASKBAR` to force the window to the desktop layer.
    *   **Click-Through:** Uses the **X11 Shape Extension** (via `python-xlib`) to set the Input Shape to an empty region, allowing mouse clicks to pass through to desktop icons.
*   **Rendering:**
    *   **MPV:** Subprocess with X11 Window ID embedding.
    *   **GStreamer:** `GstVideoOverlay` interface on the X11 Window ID with NVIDIA hardware decoding (`nvh264dec`).

## Files

*   `ghost_gstreamer.py` - GStreamer-based ghost window player
*   `ghost_mpv.py` - MPV-based ghost window player
*   `ghost_utils.py` - X11 utilities for window atoms and click-through
*   `requirements.txt` - Python dependencies
