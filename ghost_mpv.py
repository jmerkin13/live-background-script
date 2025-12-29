import sys
import os
import argparse
import logging
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette

import ghost_utils
from python_mpv_jsonipc import MPV

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ghost_mpv')

class GhostWindow(QWidget):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.mpv = None

        # Window setup
        self.setWindowTitle("Ghost Window (MPV)")
        self.resize(800, 600) # Default size, usually you'd want full screen
        
        # Remove standard frame/borders
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Set black background
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        self.setPalette(palette)

    def showEvent(self, event):
        super().showEvent(event)
        # We need to wait a tiny bit for the window to be truly created and mapped by X11
        # before we can set the Atoms or launch MPV attached to it.
        QTimer.singleShot(100, self.setup_ghost_mode)

    def setup_ghost_mode(self):
        win_id = int(self.winId())
        logger.info(f"Window ID: {win_id}")

        # 1. Set X11 Atoms (Desktop, Below, Skip Taskbar)
        ghost_utils.set_ghost_window_atoms(win_id)

        # 2. Make Click-Through (Input Transparent)
        # passing geometry is not strictly needed for the 'empty' shape logic but kept for interface
        ghost_utils.make_window_clickthrough(win_id, self.x(), self.y(), self.width(), self.height())

        # 3. Launch MPV
        self.start_mpv(win_id)

    def start_mpv(self, win_id):
        if not os.path.exists(self.video_path):
            logger.error(f"Video file not found: {self.video_path}")
            return

        logger.info(f"Starting MPV for video: {self.video_path}")
        
        # MPV Arguments
        mpv_args = [
            f"--wid={win_id}",
            "--hwdec=nvdec",   # Hardware acceleration
            "--loop=inf",      # Loop forever
            "--no-input-default-bindings", # Disable MPV's own input handling
            "--keep-open=yes"
        ]

        try:
            # We use a unique socket for this instance
            socket_path = f"/tmp/ghost_mpv_{win_id}.sock"
            if os.path.exists(socket_path):
                os.remove(socket_path)

            self.mpv = MPV(start_mpv=True, ipc_socket=socket_path, mpv_args=mpv_args)
            
            # Play the file
            self.mpv.play(self.video_path)
            
            # Example of IPC: Set speed to 1.0 (normal)
            self.mpv.speed = 1.0
            logger.info("MPV started successfully.")
            
        except Exception as e:
            logger.error(f"Failed to start MPV: {e}")

    def closeEvent(self, event):
        # Cleanup MPV
        if self.mpv:
            logger.info("Terminating MPV...")
            try:
                self.mpv.terminate()
            except:
                pass
        super().closeEvent(event)

def main():
    parser = argparse.ArgumentParser(description="Ghost Window MPV Player")
    parser.add_argument("video_path", help="Path to the video file to play")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    
    window = GhostWindow(args.video_path)
    window.show() # Initially show normal, then ghost_mode kicks in
    
    # If we wanted full screen desktop:
    # window.showFullScreen()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
