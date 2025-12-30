import sys
import os
import argparse
import logging
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette

import ghost_utils

# Try to import GStreamer bindings
try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstVideo', '1.0')
    from gi.repository import Gst, GstVideo, GLib
    GSTREAMER_AVAILABLE = True
except ImportError:
    GSTREAMER_AVAILABLE = False
    print("Warning: PyGObject/GStreamer not found. Ghost GStreamer script will not function without system dependencies.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ghost_gstreamer')

class GhostWindow(QWidget):
    def __init__(self, video_path, speed=1.0):
        super().__init__()
        self.video_path = video_path
        self.speed = speed
        self.pipeline = None
        self.initial_seek_done = False

        # Window setup
        self.setWindowTitle("Ghost Window (GStreamer)")
        self.resize(1920, 1080)
        
        # Remove standard frame/borders
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Set black background
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.setPalette(palette)

    def showEvent(self, event):
        super().showEvent(event)
        # Wait for window to be mapped
        QTimer.singleShot(100, self.setup_ghost_mode)

    def setup_ghost_mode(self):
        win_id = int(self.winId())
        logger.info(f"Window ID: {win_id}")

        # 1. Set X11 Atoms
        ghost_utils.set_ghost_window_atoms(win_id)

        # 2. Make Click-Through
        ghost_utils.make_window_clickthrough(win_id, self.x(), self.y(), self.width(), self.height())

        # 3. Launch GStreamer Pipeline
        if GSTREAMER_AVAILABLE:
            self.start_pipeline(win_id)
        else:
            logger.error("GStreamer libraries not loaded. Cannot play video.")

    def start_pipeline(self, win_id):
        if not os.path.exists(self.video_path):
            logger.error(f"Video file not found: {self.video_path}")
            return

        logger.info(f"Starting GStreamer pipeline for: {self.video_path}")
        
        Gst.init(None)
        
        # Construct Pipeline
        # Pipeline: filesrc ! qtdemux ! h264parse ! nvdec ! glimagesink
        # We add 'videoconvert' sometimes before sink just in case nvdec format isn't compatible with glimagesink directly 
        # (though nvdec usually outputs something usable or glimagesink handles it).
        # We will try the strict pipeline requested.
        
        # Note: nvdec plugin is often named 'nvdec' or 'nvh264dec' depending on version. 
        # 'nvdec' is the modern one in gst-plugins-bad.
        
        pipeline_str = (
            f"filesrc location=\"{self.video_path}\" ! "
            "qtdemux ! h264parse ! nvh264dec ! glimagesink"
        )
        
        try:
            logger.info(f"Pipeline: {pipeline_str}")
            self.pipeline = Gst.parse_launch(pipeline_str)
            
            # Bus handling
            bus = self.pipeline.get_bus()
            bus.enable_sync_message_emission()
            bus.connect('sync-message::element', self.on_sync_message)
            
            # We also need to listen for EOS (End of Stream) to loop
            bus.add_signal_watch()
            bus.connect('message', self.on_bus_message)
            
            # Start playing
            self.pipeline.set_state(Gst.State.PLAYING)
            logger.info(f"GStreamer pipeline started. Waiting for state change to set speed {self.speed}...")
            
        except Exception as e:
            logger.error(f"Failed to launch pipeline: {e}")
            logger.info("Tip: Make sure 'gstreamer1.0-plugins-bad' and NVIDIA drivers are installed.")

    def on_sync_message(self, bus, msg):
        # This function is called synchronously from the streaming thread.
        # It allows us to embed the video into our window handle.
        if msg.get_structure().get_name() == 'prepare-window-handle':
            logger.info("Received prepare-window-handle message")
            sink = msg.src
            
            # GstVideo.VideoOverlay works slightly differently in Python depending on version
            # But normally we just look for the method set_window_handle on the element 
            # if it implements the interface, or use the GstVideo helper.
            
            try:
                # Modern PyGObject way
                win_id = int(self.winId())
                sink.set_window_handle(win_id)
            except Exception as e:
                logger.error(f"Failed to set window handle: {e}")

    def on_bus_message(self, bus, msg):
        msg_type = msg.type
        if msg_type == Gst.MessageType.EOS:
            logger.info("End of stream. Looping...")
            # When looping, we also want to preserve the speed
            if self.speed != 1.0:
                self.pipeline.seek(
                    self.speed,
                    Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                    Gst.SeekType.SET, 0,
                    Gst.SeekType.NONE, 0
                )
            else:
                self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)

        elif msg_type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            logger.error(f"GStreamer Error: {err} - {debug}")
            self.pipeline.set_state(Gst.State.NULL)

        elif msg_type == Gst.MessageType.STATE_CHANGED:
            # Check if the message comes from the pipeline
            if msg.src == self.pipeline:
                old_state, new_state, pending_state = msg.parse_state_changed()
                # Once we are in PLAYING state (or PAUSED), we can seek
                if new_state == Gst.State.PLAYING and not self.initial_seek_done and self.speed != 1.0:
                    logger.info(f"Pipeline in PLAYING state. Setting speed to {self.speed}...")
                    rc = self.pipeline.seek(
                        self.speed,
                        Gst.Format.TIME,
                        Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                        Gst.SeekType.SET, 0,
                        Gst.SeekType.NONE, 0
                    )
                    if rc:
                        self.initial_seek_done = True
                        logger.info("Playback speed set successfully.")
                    else:
                        logger.warning("Failed to set playback speed in STATE_CHANGED.")

    def closeEvent(self, event):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        super().closeEvent(event)

def main():
    parser = argparse.ArgumentParser(description="Ghost Window GStreamer Player")
    parser.add_argument("video_path", help="Path to the video file to play")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed (default: 1.0)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    
    window = GhostWindow(args.video_path, args.speed)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
