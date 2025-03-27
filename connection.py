from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainterPath, QPen, QColor, QLinearGradient

class ConnectionItem(QGraphicsPathItem):
    def __init__(self, start_port=None, end_port=None, parent=None):
        super().__init__(parent)
        self.start_port = start_port
        self.end_port = end_port
        
        # Set flags
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        
        # Colors for different states
        self.color_default = QColor("#6D6D6D")  # Dark gray
        self.color_selected = QColor("#FF9800")  # Orange
        self.color_valid = QColor("#4CAF50")     # Green
        self.color_invalid = QColor("#F44336")   # Red
        
        # Create pens for different states
        self.pen_default = QPen(self.color_default)
        self.pen_default.setWidth(4.5)
        self.pen_default.setStyle(Qt.PenStyle.SolidLine)
        
        self.pen_selected = QPen(self.color_selected)
        self.pen_selected.setWidth(5.5)
        self.pen_selected.setStyle(Qt.PenStyle.SolidLine)
        
        # Set initial pen
        self.setPen(self.pen_default)
        self.setZValue(-1)  # Draw behind nodes
        
        # Temporary points for drawing during drag
        self.temp_start_pos = QPointF(0, 0)
        self.temp_end_pos = QPointF(0, 0)

        if self.start_port:
            self.temp_start_pos = self.start_port.scenePos()
        if self.end_port:
            self.temp_end_pos = self.end_port.scenePos()

        self.update_path()

    def set_start_port(self, port):
        self.start_port = port
        self.temp_start_pos = self.start_port.scenePos()
        self.update_path()

    def set_end_port(self, port):
        self.end_port = port
        self.temp_end_pos = self.end_port.scenePos()
        self.update_path()

    def set_temp_start_pos(self, pos):
        self.temp_start_pos = pos
        self.update_path()

    def set_temp_end_pos(self, pos):
        self.temp_end_pos = pos
        self.update_path()

    def update_path(self):
        path = QPainterPath()
        start_pos = self.temp_start_pos
        end_pos = self.temp_end_pos

        if self.start_port:
            start_pos = self.start_port.scenePos()
        if self.end_port:
            end_pos = self.end_port.scenePos()

        # Calculate the horizontal and vertical distances
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        
        # Determine if we're in the middle of creating a connection (dragging)
        is_creating = self.start_port and not self.end_port
        
        # Adjust the curve behavior based on whether we're creating or have a complete connection
        if is_creating:
            # During creation, use a simpler curve that follows the mouse more directly
            # Calculate the midpoint between start and end
            mid_x = (start_pos.x() + end_pos.x()) / 2
            
            # Create control points that make a smoother curve during dragging
            cp1 = QPointF(mid_x, start_pos.y())
            cp2 = QPointF(mid_x, end_pos.y())
        else:
            # For complete connections, use a more sophisticated curve
            
            # Base control distance on the greater of horizontal or vertical distance
            # This creates more balanced curves regardless of node positions
            control_distance = max(abs(dx) * 0.5, abs(dy) * 0.3)
            
            # Minimum control distance to ensure curves don't look too tight
            min_distance = 40
            control_distance = max(control_distance, min_distance)
            
            # Create control points based on port types
            if self.start_port and self.start_port.is_output:
                # From output port (right side)
                cp1 = QPointF(start_pos.x() + control_distance, start_pos.y())
            else:
                # From input port (left side) or temporary point
                cp1 = QPointF(start_pos.x() - control_distance, start_pos.y())
                
            if self.end_port and not self.end_port.is_output:
                # To input port (left side)
                cp2 = QPointF(end_pos.x() - control_distance, end_pos.y())
            else:
                # To output port (right side) or temporary point
                cp2 = QPointF(end_pos.x() + control_distance, end_pos.y())
        
        # Draw a cubic Bezier curve
        path.moveTo(start_pos)
        path.cubicTo(cp1, cp2, end_pos)
        self.setPath(path)

    def paint(self, painter, option, widget=None):
        """Override paint to handle selection state"""
        if self.isSelected():
            self.setPen(self.pen_selected)
        else:
            self.setPen(self.pen_default)
        
        super().paint(painter, option, widget)
    
    # Update path when connected nodes move
    def update_positions(self):
        if self.start_port and self.end_port:
            self.update_path()
    
    def to_dict(self):
        """Serialize the connection to a dictionary."""
        if not self.start_port or not self.end_port:
            return None  # Cannot serialize incomplete connection
        
        return {
            'id': id(self),
            'start_node_id': id(self.start_port.parentItem()),
            'start_port_index': self.start_port.parentItem().outputs.index(self.start_port) if self.start_port.is_output else self.start_port.parentItem().inputs.index(self.start_port),
            'start_port_is_output': self.start_port.is_output,
            'end_node_id': id(self.end_port.parentItem()),
            'end_port_index': self.end_port.parentItem().outputs.index(self.end_port) if self.end_port.is_output else self.end_port.parentItem().inputs.index(self.end_port),
            'end_port_is_output': self.end_port.is_output
        }
    
    @classmethod
    def from_dict(cls, data, nodes_dict):
        """Create a connection from serialized data and a dictionary of nodes."""
        # Get the nodes
        start_node = nodes_dict.get(data['start_node_id'])
        end_node = nodes_dict.get(data['end_node_id'])
        
        if not start_node or not end_node:
            return None  # Cannot create connection if nodes don't exist
        
        # Get the ports
        start_port = start_node.outputs[data['start_port_index']] if data['start_port_is_output'] else start_node.inputs[data['start_port_index']]
        end_port = end_node.outputs[data['end_port_index']] if data['end_port_is_output'] else end_node.inputs[data['end_port_index']]
        
        # Create the connection
        connection = cls(start_port, end_port)
        
        # Register the connection with the ports
        start_port.add_connection(connection)
        end_port.add_connection(connection)
        
        return connection