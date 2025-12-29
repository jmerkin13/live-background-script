import logging
from Xlib import X, display, Xatom
from Xlib.protocol import event

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ghost_utils')

def set_ghost_window_atoms(win_id):
    """
    Sets the necessary EWMH atoms to make the window a desktop background
    and stay at the bottom.
    """
    try:
        d = display.Display()
        window = d.create_resource_object('window', win_id)
        
        # Get atoms
        _NET_WM_WINDOW_TYPE = d.intern_atom('_NET_WM_WINDOW_TYPE')
        _NET_WM_WINDOW_TYPE_DESKTOP = d.intern_atom('_NET_WM_WINDOW_TYPE_DESKTOP')
        _NET_WM_STATE = d.intern_atom('_NET_WM_STATE')
        _NET_WM_STATE_BELOW = d.intern_atom('_NET_WM_STATE_BELOW')
        _NET_WM_STATE_SKIP_TASKBAR = d.intern_atom('_NET_WM_STATE_SKIP_TASKBAR')
        _NET_WM_STATE_SKIP_PAGER = d.intern_atom('_NET_WM_STATE_SKIP_PAGER')
        
        # Set window type to desktop
        logger.info(f"Setting _NET_WM_WINDOW_TYPE_DESKTOP for window ID: {win_id}")
        window.change_property(_NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, [_NET_WM_WINDOW_TYPE_DESKTOP])
        
        # Set state: below, skip taskbar, skip pager
        logger.info("Setting _NET_WM_STATE_BELOW and _NET_WM_STATE_SKIP_TASKBAR")
        window.change_property(_NET_WM_STATE, Xatom.ATOM, 32, [
            _NET_WM_STATE_BELOW,
            _NET_WM_STATE_SKIP_TASKBAR,
            _NET_WM_STATE_SKIP_PAGER
        ])
        
        d.flush()
        d.close()
        logger.info("Atoms set successfully.")
        
    except Exception as e:
        logger.error(f"Failed to set atoms: {e}")


def make_window_clickthrough(win_id, x, y, width, height):
    """
    Sets the window input shape to an empty region, making it transparent to mouse events.
    Uses Xlib ShapeExtension.
    """
    try:
        from Xlib.ext import shape
        
        d = display.Display()
        
        # Check if Shape extension is available
        if not d.has_extension('SHAPE'):
            logger.error("XShape extension not supported by the server.")
            d.close()
            return
        
        window = d.create_resource_object('window', win_id)
        
        logger.info(f"Setting input shape to empty for window ID: {win_id}")
        
        # Set input shape to empty (no rectangles = click-through everywhere)
        # shape.SO.Set = 0, shape.SK.Input = 2
        window.shape_rectangles(
            shape.SO.Set,      # operation: Set
            shape.SK.Input,    # destination kind: Input
            X.YXBanded,        # ordering
            0, 0,              # x_offset, y_offset
            []                 # empty rectangles = fully click-through
        )
        
        d.flush()
        d.close()
        logger.info("Click-through enabled (Input shape cleared).")
        
    except ImportError:
        logger.error("Xlib shape extension not available")
    except Exception as e:
        logger.error(f"Failed to set click-through: {e}")
