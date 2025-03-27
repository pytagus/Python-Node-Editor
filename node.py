import sys

from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsProxyWidget,
    QInputDialog, QGraphicsSceneMouseEvent
)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from code_editor import CodeEditorWidget

class NodeTitleItem(QGraphicsTextItem):
    """Custom text item for node titles that can be edited with double-click"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setDefaultTextColor(QColor("#FFFFFF"))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        self.setFont(font)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Make the title item accept mouse events
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        """Handle double-click to edit the title"""
        # Stop event propagation to prevent the node from toggling expanded state
        event.accept()
        
        if self.parentItem():
            self.parentItem().edit_title()

# Port Item with improved design
class PortItem(QGraphicsEllipseItem):
    def __init__(self, parent, is_output=False):
        self.radius = 6
        # Parent is the NodeItem
        super().__init__(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius, parent)
        self.is_output = is_output
        
        # Nicer colors for ports
        if is_output:
            self.setBrush(QBrush(QColor("#4CAF50")))  # Green for output
        else:
            self.setBrush(QBrush(QColor("#2196F3")))  # Blue for input
            
        self.setPen(QPen(QColor("#333333"), 1.5))
        self.setZValue(1)  # Make sure ports are drawn on top
        
        # List of connections attached to this port
        self.connections = []
    
    def add_connection(self, connection):
        """Add a connection to this port"""
        if connection not in self.connections:
            self.connections.append(connection)
    
    def remove_connection(self, connection):
        """Remove a connection from this port"""
        if connection in self.connections:
            self.connections.remove(connection)

class NodeItem(QGraphicsItem):
    def __init__(self, title="Node", parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges) # Important for connections
        self.setAcceptHoverEvents(True)

        # Node states
        self.is_expanded = False  # Closed by default
        
        # Node dimensions
        self.collapsed_width = 180  # Smaller width when collapsed
        self.expanded_width = 400   # Much larger width when expanded
        self.collapsed_height = 60  # Smaller height when collapsed
        self.expanded_height = 500  # Much larger height when expanded
        
        # Start with collapsed dimensions
        self.width = self.collapsed_width
        self.height = self.collapsed_height
        
        # Node appearance
        self.title = title
        self.color = QColor("#3F51B5")  # Indigo
        self.title_color = QColor("#FFFFFF")  # White
        self.title_height = 30
        self.content_color = QColor("#F5F5F5")  # Light gray
        self.border_radius = 8
        
        # Pens
        self.pen_default = QPen(QColor("#303F9F"), 1.5)  # Darker indigo
        self.pen_selected = QPen(QColor("#FF9800"), 2)  # Orange
        self.pen_hover = QPen(QColor("#7986CB"), 1.5)  # Lighter indigo
        
        # Current state
        self.is_hovered = False
        
        # Title Text (using custom NodeTitleItem for editing)
        self.title_item = NodeTitleItem(self.title, self)
        self.title_item.setPos(10, 5)  # Better padding
        
        # Status text (shows when collapsed)
        self.status_text = QGraphicsTextItem("Double-click to edit", self)
        self.status_text.setDefaultTextColor(QColor("#757575"))  # Gray
        status_font = QFont("Arial", 8)
        self.status_text.setFont(status_font)
        self.status_text.setPos(10, self.title_height + 10)

        # Ports
        self.inputs = []
        self.outputs = []

        # Add one input port (positioned at middle height)
        input_port = PortItem(self, is_output=False)
        self.inputs.append(input_port)
        
        # Add one output port (positioned at middle height)
        output_port = PortItem(self, is_output=True)
        self.outputs.append(output_port)
        
        # Position ports at middle height
        self.update_port_positions()

        # Add code editor (hidden by default)
        self.code_editor = CodeEditorWidget()
        self.code_editor_proxy = QGraphicsProxyWidget(self)
        self.code_editor_proxy.setWidget(self.code_editor)
        self.code_editor_proxy.setPos(10, self.title_height + 10)
        
        # Set initial dimensions (will be updated when expanded)
        self.code_editor_proxy.setMinimumWidth(self.expanded_width - 20)
        self.code_editor_proxy.setMaximumWidth(self.expanded_width - 20)
        self.code_editor_proxy.setMinimumHeight(self.expanded_height - self.title_height - 20)
        self.code_editor_proxy.setVisible(False)  # Hidden by default
        
        # Code execution result
        self.result = None

    def get_code(self):
        """Get the current code from the editor."""
        return self.code_editor.get_code()
    
    def set_code(self, code):
        """Set the code in the editor."""
        self.code_editor.set_code(code)
    
    def update_connections(self):
        """Update all connections attached to this node's ports"""
        for port in self.inputs + self.outputs:
            for connection in port.connections:
                connection.update_path()
    
    def update_port_positions(self):
        """Update the positions of all ports to be at the middle height of the node"""
        middle_height = self.title_height + (self.height - self.title_height) / 2
        
        # Position input ports on the left side at middle height
        for i, port in enumerate(self.inputs):
            port.setPos(0, middle_height)
        
        # Position output ports on the right side at middle height
        for i, port in enumerate(self.outputs):
            port.setPos(self.width, middle_height)
    
    def edit_title(self):
        """Open a dialog to edit the node title"""
        if not self.scene():
            return
            
        # Get the main window to use as parent for the dialog
        view = self.scene().views()[0] if self.scene().views() else None
        parent = view.window() if view else None
        
        # Show input dialog
        new_title, ok = QInputDialog.getText(
            parent,
            "Edit Node Title",
            "Enter new title for the node:",
            text=self.title
        )
        
        # Update title if user confirmed
        if ok and new_title:
            self.title = new_title
            self.title_item.setPlainText(new_title)
            
            # Log to console if available
            if parent and hasattr(parent, 'console_output'):
                parent.console_output.append_output(
                    f"Node title changed to: {new_title}",
                    "#2196F3"  # Blue
                )
    
    def execute_code(self):
        """Execute the code in the node and return the result."""
        try:
            # Create a local namespace
            local_namespace = {}
            # Create a global namespace with built-in modules
            global_namespace = {
                '__builtins__': __builtins__,
                # Add commonly used modules here
                # Modules de base
                'random': __import__('random'),         # Nombres aléatoires
                'math': __import__('math'),             # Fonctions mathématiques
                'statistics': __import__('statistics'),  # Statistiques de base
                'time': __import__('time'),             # Fonctions liées au temps
                'datetime': __import__('datetime'),     # Manipulation de dates
                'calendar': __import__('calendar'),     # Fonctions liées au calendrier

                # Système et E/S
                'os': __import__('os'),                 # Interface avec le système d'exploitation
                'sys': __import__('sys'),               # Configuration spécifique au système
                'pathlib': __import__('pathlib'),       # Manipulation de chemins (moderne)
                'io': __import__('io'),                 # Outils d'entrée/sortie
                'tempfile': __import__('tempfile'),     # Fichiers temporaires
                'requests': __import__('requests'),     # Requêtes HTTP

                # Formats de données
                'json': __import__('json'),             # Manipulation JSON
                'csv': __import__('csv'),               # Manipulation CSV
                'xml': __import__('xml'),               # Outils XML
                'configparser': __import__('configparser'), # Fichiers de configuration
                'pickle': __import__('pickle'),         # Sérialisation d'objets Python

                # Texte et expressions régulières
                're': __import__('re'),                 # Expressions régulières
                'string': __import__('string'),         # Manipulation de chaînes
                'textwrap': __import__('textwrap'),     # Formatage de texte

                # Structures de données et algorithmes
                'collections': __import__('collections'), # Conteneurs spécialisés
                'itertools': __import__('itertools'),   # Fonctions pour itérateurs efficaces
                'functools': __import__('functools'),   # Outils pour fonctions et callables
                'heapq': __import__('heapq'),           # Algorithme de tas (file prioritaire)
                'bisect': __import__('bisect'),         # Algorithmes de bissection

                # Multithreading et multiprocessing
                'threading': __import__('threading'),   # Threads
                'multiprocessing': __import__('multiprocessing'), # Processus parallèles
                'concurrent.futures': __import__('concurrent.futures'), # Exécution parallèle

                # Réseau
                'socket': __import__('socket'),         # Interface réseau de bas niveau
                'urllib': __import__('urllib'),         # Manipulation d'URL
                'http': __import__('http'),             # Clients et serveurs HTTP
                'email': __import__('email'),           # Manipulation d'emails

                # Compression
                'gzip': __import__('gzip'),             # Compression gzip
                'zipfile': __import__('zipfile'),       # Manipulation de fichiers ZIP
                'tarfile': __import__('tarfile'),       # Manipulation de fichiers TAR

                # data science
                'numpy': __import__('numpy') if 'numpy' in sys.modules else None,
                'pandas': __import__('pandas') if 'pandas' in sys.modules else None,
                # Add any other modules you might need
            }
            
            # Execute the code with access to these modules
            exec(self.get_code(), global_namespace, local_namespace)
            
            # Check if the 'process' function is defined
            if 'process' in local_namespace:
                # Get input values from input ports
                inputs = []
                for port in self.inputs:
                    # Get values from connected nodes
                    for connection in port.connections:
                        if connection.start_port != port:  # This port is the end port
                            source_node = connection.start_port.parentItem()
                            if source_node.result is not None:
                                inputs.append(source_node.result)
                        else:  # This port is the start port
                            source_node = connection.end_port.parentItem()
                            if source_node.result is not None:
                                inputs.append(source_node.result)
                
                # Call the process function with inputs
                if inputs:
                    self.result = local_namespace['process'](*inputs)
                else:
                    self.result = local_namespace['process'](None)
                
                return self.result
            else:
                print(f"Node '{self.title}': No 'process' function defined")
                return None
        except Exception as e:
            print(f"Error executing code in node '{self.title}': {str(e)}")
            return None

    def toggle_expanded(self):
        """Toggle between expanded and collapsed states"""
        self.is_expanded = not self.is_expanded
        
        # Prepare for geometry change before modifying dimensions
        if self.scene():
            self.prepareGeometryChange()
        
        if self.is_expanded:
            # Expand to larger size
            self.width = self.expanded_width
            self.height = self.expanded_height
            
            # Update code editor size and position
            self.code_editor_proxy.setPos(10, self.title_height + 10)
            self.code_editor_proxy.setMinimumWidth(self.width - 20)
            self.code_editor_proxy.setMaximumWidth(self.width - 20)
            self.code_editor_proxy.setMinimumHeight(self.height - self.title_height - 20)
            
            # Show code editor, hide status text
            self.code_editor_proxy.setVisible(True)
            self.status_text.setVisible(False)
            
            # Reposition output port to right edge of expanded node
            if self.outputs and len(self.outputs) > 0:
                for output_port in self.outputs:
                    output_port.setPos(self.width, output_port.pos().y())
        else:
            # Collapse to smaller size
            self.width = self.collapsed_width
            self.height = self.collapsed_height
            
            # Hide code editor, show status text
            self.code_editor_proxy.setVisible(False)
            self.status_text.setVisible(True)
            
            # Reposition output port to right edge of collapsed node
            if self.outputs and len(self.outputs) > 0:
                for output_port in self.outputs:
                    output_port.setPos(self.width, output_port.pos().y())
        
        # Update all connections attached to this node
        self.update_connections()
        
        # Update the scene
        if self.scene():
            self.update()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to expand/collapse the node"""
        # Check if the click is on the title area
        if event.pos().y() <= self.title_height:
            # If it's on the title, edit the title
            self.edit_title()
        else:
            # If it's on the body, toggle expanded state
            self.toggle_expanded()
        
        # Don't call super to prevent event propagation
        event.accept()
    
    def hoverEnterEvent(self, event):
        """Handle hover enter event"""
        self.is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle hover leave event"""
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def boundingRect(self):
        # Define the bounding rectangle for redraws and collision detection
        return QRectF(0, 0, self.width, self.height).normalized()

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Determine pen based on state
        if self.isSelected():
            painter.setPen(self.pen_selected)
        elif self.is_hovered:
            painter.setPen(self.pen_hover)
        else:
            painter.setPen(self.pen_default)
        
        # Create rounded rectangle path for the entire node
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width, self.height),
                           self.border_radius, self.border_radius)
        
        # Draw node background
        painter.fillPath(path, QBrush(self.content_color))
        
        # Draw title background with rounded top corners
        title_path = QPainterPath()
        title_rect = QRectF(0, 0, self.width, self.title_height)
        title_path.addRoundedRect(title_rect, self.border_radius, self.border_radius)
        
        # Create a clip path to only round the top corners
        clip_path = QPainterPath()
        clip_path.addRect(0, self.title_height/2, self.width, self.title_height/2)
        title_path = title_path.subtracted(clip_path)
        
        # Add the rectangle for the bottom half of the title
        bottom_half = QPainterPath()
        bottom_half.addRect(0, self.title_height/2, self.width, self.title_height/2)
        title_path.addPath(bottom_half)
        
        painter.fillPath(title_path, QBrush(self.color))
        
        # Draw border
        painter.drawPath(path)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update all connections attached to this node's ports
            for port in self.inputs + self.outputs:
                for connection in port.connections:
                    connection.update_path()
        return super().itemChange(change, value)
    
    def to_dict(self):
        """Serialize the node to a dictionary."""
        return {
            'id': id(self),  # Use object id as unique identifier
            'title': self.title,
            'pos_x': self.pos().x(),
            'pos_y': self.pos().y(),
            'code': self.get_code(),
            'input_ports': len(self.inputs),
            'output_ports': len(self.outputs)
        }
    
    @classmethod
    def from_dict(cls, data, scene):
        """Create a node from serialized data."""
        node = cls(data['title'])
        node.setPos(data['pos_x'], data['pos_y'])
        node.set_code(data['code'])
        scene.addItem(node)
        return node
    

class ViewerNodeItem(NodeItem):
    """Node spécialisé pour visualiser les données"""
    def __init__(self, title="Viewer", parent=None):
        super().__init__(title, parent)
        
        # Changer la couleur pour identifier les nœuds visualiseurs
        self.color = QColor("#9C27B0")  # Violet
        self.pen_default = QPen(QColor("#7B1FA2"), 1.5)  # Violet plus foncé
        self.pen_hover = QPen(QColor("#BA68C8"), 1.5)  # Violet plus clair
        
        # Zone de texte pour afficher les données
        self.data_display = QGraphicsTextItem(self)
        self.data_display.setPos(10, self.title_height + 30)
        self.data_display.setDefaultTextColor(QColor("#000000"))
        self.data_display.setFont(QFont("Courier New", 9))
        self.data_display.setPlainText("No data received yet")
        
        # Définir le code par défaut pour un nœud visualiseur
        self.set_code("""# Viewer Node
def process(input=None):
    # Ce nœud passe simplement les données reçues
    return input
""")
    
    def execute_code(self):
        """Exécute le code et met à jour l'affichage des données"""
        result = super().execute_code()
        
        # Mettre à jour l'affichage avec la représentation des données
        if result is not None:
            # Limiter la taille de l'affichage pour éviter les performances lentes
            result_str = str(result)
            if len(result_str) > 1000:  # Limiter à 1000 caractères
                result_str = result_str[:997] + "..."
            
            # Formatter les données selon leur type
            if isinstance(result, dict):
                formatted_result = "Dict:\n"
                for key, value in result.items():
                    formatted_result += f"  {key}: {value}\n"
                self.data_display.setPlainText(formatted_result)
            elif isinstance(result, list):
                formatted_result = f"List[{len(result)}]:\n"
                for i, item in enumerate(result):
                    if i >= 20:  # Limiter à 20 éléments
                        formatted_result += "  ...\n"
                        break
                    formatted_result += f"  {i}: {item}\n"
                self.data_display.setPlainText(formatted_result)
            else:
                self.data_display.setPlainText(f"Data: {result_str}")
        else:
            self.data_display.setPlainText("No data received")
        
        return result
    
    def toggle_expanded(self):
        """Override pour gérer l'affichage des données lors du toggle"""
        super().toggle_expanded()
        
        # Ajuster l'affichage des données selon l'état du nœud
        if self.is_expanded:
            # Quand le nœud est étendu, cacher l'affichage des données car on voit le code
            self.data_display.setVisible(False)
        else:
            # Quand le nœud est réduit, montrer l'affichage des données
            self.data_display.setVisible(True)
            
    def to_dict(self):
        """Serializer avec le type de nœud"""
        data = super().to_dict()
        data['node_type'] = 'viewer'  # Ajouter un identifiant de type
        return data
    
    @classmethod
    def from_dict(cls, data, scene):
        """Créer un nœud visualiseur à partir des données sérialisées"""
        node = cls(data['title'])
        node.setPos(data['pos_x'], data['pos_y'])
        node.set_code(data['code'])
        scene.addItem(node)
        return node