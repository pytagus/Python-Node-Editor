import sys
import json
import os
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QToolBar,
    QFileDialog, QMessageBox, QTextEdit, QSplitter, QInputDialog,
    QLabel, QDockWidget
)
from PySide6.QtCore import Qt, QPointF, QSettings, QTimer
from PySide6.QtGui import QMouseEvent, QPainter, QAction, QFont, QColor, QKeyEvent, QKeySequence

from node import NodeItem, PortItem, ViewerNodeItem # Import NodeItem and PortItem
from connection import ConnectionItem # Import ConnectionItem

class NodeCanvas(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing) # Smoother lines
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag) # Allow selecting multiple items
        
        # Enable smooth scrolling
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.temp_connection = None
        self.start_port = None
        
        # Variables pour la fonctionnalité de copier-coller
        self.copied_nodes = []
        
        # Activer la gestion du presse-papier
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Activer le glisser-déposer
        self.setAcceptDrops(True)
    
    # Méthodes pour le drag & drop de fichiers JSON
    def dragEnterEvent(self, event):
        """Accepter les événements de drag si ce sont des fichiers JSON"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith('.json'):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dragMoveEvent(self, event):
        """Accepter les mouvements de drag pour les fichiers JSON"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith('.json'):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        """Gérer le drop d'un fichier JSON"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith('.json'):
                    main_window = self.window()
                    if hasattr(main_window, 'merge_graph_from_file'):
                        main_window.merge_graph_from_file(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, PortItem):
                # Start drawing a connection
                self.start_port = item
                self.temp_connection = ConnectionItem(self.start_port)
                self.scene().addItem(self.temp_connection)
                self.temp_connection.set_temp_end_pos(self.mapToScene(event.pos()))
                return # Consume event
        elif event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.pos())
            if isinstance(item, (NodeItem, ConnectionItem)):
                self.scene().removeItem(item)
                if isinstance(item, ConnectionItem):
                    if item.start_port:
                        item.start_port.remove_connection(item)
                    if item.end_port:
                        item.end_port.remove_connection(item)
                elif isinstance(item, NodeItem):
                    for port in item.inputs + item.outputs:
                        for connection in list(port.connections):
                            if connection.start_port != port:
                                connection.start_port.remove_connection(connection)
                            else:
                                connection.end_port.remove_connection(connection)
                            self.scene().removeItem(connection)
                    main_window = self.window()
                    if hasattr(main_window, 'nodes'):
                        if item in main_window.nodes:
                            main_window.nodes.remove(item)
                main_window = self.window()
                if hasattr(main_window, 'console_output'):
                    main_window.console_output.append_output(
                        f"Item '{item}' deleted", "#FF9800"
                    )
                return # Consume event
        super().mousePressEvent(event) # Default behavior for other items/background

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.temp_connection:
            # Update the end position of the temporary connection line
            self.temp_connection.set_temp_end_pos(self.mapToScene(event.pos()))
            return # Consume event

        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click events to expand/collapse nodes"""
        # Pass the event to the item under the cursor
        item = self.itemAt(event.pos())
        if item:
            # Let the scene handle the event (which will pass it to the item)
            super().mouseDoubleClickEvent(event)
        else:
            # If no item is clicked, let the parent handle it
            super().mouseDoubleClickEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        # Vérification directe: sommes-nous en train d'éditer le code d'un nœud?
        # On parcourt tous les nœuds pour voir si leur éditeur est visible
        for node in self.scene().items():
            if isinstance(node, NodeItem):
                if node.is_expanded and node.code_editor_proxy.isVisible():
                    # Si nous éditons un nœud, transmettre l'événement
                    super().keyPressEvent(event)
                    return
        
        # Si on arrive ici, aucun nœud n'est en édition
        # Donc on peut gérer les raccourcis de copier-coller pour les nœuds
        
        # Copier - Ctrl+C
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            self.copy_selected_nodes()
            event.accept()
            return
            
        # Coller - Ctrl+V
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_V:
            self.paste_nodes()
            event.accept()
            return
        
        super().keyPressEvent(event)
    
    def copy_selected_nodes(self):
        """Copier les nœuds sélectionnés et leurs connexions"""
        selected_nodes = [item for item in self.scene().selectedItems() if isinstance(item, NodeItem)]
        
        if not selected_nodes:
            return
        
        # Stocker les informations des nœuds copiés
        self.copied_nodes = []
        
        # Dictionnaire pour mapper les IDs originaux aux indices dans self.copied_nodes
        node_id_to_index = {}
        
        # Première étape : copier les données des nœuds
        for i, node in enumerate(selected_nodes):
            # Créer une copie des données du nœud
            node_data = {
                'title': node.title,
                'code': node.get_code(),
                'is_expanded': node.is_expanded,
                'rel_x': node.pos().x(),  # Position relative
                'rel_y': node.pos().y(),
                'original_id': id(node),  # Stocker l'ID original pour référence
                'connections': [],  # Sera rempli avec les connexions
                'is_viewer': isinstance(node, ViewerNodeItem)  # Conserver le type de nœud
            }
            self.copied_nodes.append(node_data)
            node_id_to_index[id(node)] = i
        
        # Deuxième étape : trouver et copier les connexions entre les nœuds sélectionnés
        for node in selected_nodes:
            # Parcourir tous les ports de ce nœud
            for port in node.inputs + node.outputs:
                for connection in port.connections:
                    # Vérifier si la connexion relie deux nœuds sélectionnés
                    start_node = connection.start_port.parentItem()
                    end_node = connection.end_port.parentItem()
                    
                    if start_node in selected_nodes and end_node in selected_nodes:
                        # Si cette connexion est entre deux nœuds sélectionnés
                        start_node_index = node_id_to_index[id(start_node)]
                        end_node_index = node_id_to_index[id(end_node)]
                        
                        # Ajouter la connexion seulement une fois (depuis le nœud de départ)
                        if start_node == node:
                            connection_data = {
                                'start_node_index': start_node_index,
                                'end_node_index': end_node_index,
                                'start_port_is_output': connection.start_port.is_output,
                                'start_port_index': start_node.outputs.index(connection.start_port) if connection.start_port.is_output else start_node.inputs.index(connection.start_port),
                                'end_port_is_output': connection.end_port.is_output,
                                'end_port_index': end_node.outputs.index(connection.end_port) if connection.end_port.is_output else end_node.inputs.index(connection.end_port)
                            }
                            
                            self.copied_nodes[start_node_index]['connections'].append(connection_data)
        
        # Log to console if available
        main_window = self.window()
        if hasattr(main_window, 'console_output'):
            # Compter le nombre total de connexions copiées
            connection_count = sum(len(node_data['connections']) for node_data in self.copied_nodes)
            viewer_count = sum(1 for node_data in self.copied_nodes if node_data['is_viewer'])
            main_window.console_output.append_output(
                f"Copied {len(self.copied_nodes)} node(s) ({viewer_count} viewer(s)) with {connection_count} connection(s)", "#2196F3"
            )
    
    def paste_nodes(self):
        """Coller les nœuds précédemment copiés et leurs connexions"""
        if not self.copied_nodes:
            return
        
        # Déselectionner tous les éléments
        for item in self.scene().selectedItems():
            item.setSelected(False)
        
        # Obtenir le point de vue actuel pour déterminer où coller
        view_center = self.mapToScene(self.viewport().rect().center())
        
        # Calculer l'offset pour centrer les nœuds collés
        if len(self.copied_nodes) > 0:
            avg_x = sum(node['rel_x'] for node in self.copied_nodes) / len(self.copied_nodes)
            avg_y = sum(node['rel_y'] for node in self.copied_nodes) / len(self.copied_nodes)
            offset_x = view_center.x() - avg_x
            offset_y = view_center.y() - avg_y
        else:
            offset_x = offset_y = 0
        
        # Créer les nouveaux nœuds
        new_nodes = []
        
        main_window = self.window()
        
        # Première étape : créer tous les nœuds
        for node_data in self.copied_nodes:
            # Créer le bon type de nœud selon si c'est un visualiseur ou non
            if node_data.get('is_viewer', False):
                new_node = ViewerNodeItem(node_data['title'])
            else:
                new_node = NodeItem(node_data['title'])
            
            # Configurer le nœud
            new_node.set_code(node_data['code'])
            new_node.setPos(node_data['rel_x'] + offset_x, node_data['rel_y'] + offset_y)
            
            # Définir l'état d'expansion
            if node_data['is_expanded'] != new_node.is_expanded:
                new_node.toggle_expanded()
            
            # Ajouter au canevas
            self.scene().addItem(new_node)
            new_node.setSelected(True)
            
            # Ajouter à la liste des nœuds de la fenêtre principale
            if hasattr(main_window, 'nodes'):
                main_window.nodes.append(new_node)
            
            new_nodes.append(new_node)
        
        # Deuxième étape : créer les connexions entre les nouveaux nœuds
        connection_count = 0
        for i, node_data in enumerate(self.copied_nodes):
            for conn_data in node_data['connections']:
                # Obtenir les nœuds source et destination
                start_node = new_nodes[conn_data['start_node_index']]
                end_node = new_nodes[conn_data['end_node_index']]
                
                # Obtenir les ports source et destination
                if conn_data['start_port_is_output']:
                    start_port = start_node.outputs[conn_data['start_port_index']]
                else:
                    start_port = start_node.inputs[conn_data['start_port_index']]
                    
                if conn_data['end_port_is_output']:
                    end_port = end_node.outputs[conn_data['end_port_index']]
                else:
                    end_port = end_node.inputs[conn_data['end_port_index']]
                
                # Créer une nouvelle connexion
                new_connection = ConnectionItem(start_port, end_port)
                self.scene().addItem(new_connection)
                
                # Enregistrer la connexion avec les ports
                start_port.add_connection(new_connection)
                end_port.add_connection(new_connection)
                
                connection_count += 1
        
        # Log to console if available
        if hasattr(main_window, 'console_output'):
            viewer_count = sum(1 for node_data in self.copied_nodes if node_data.get('is_viewer', False))
            main_window.console_output.append_output(
                f"Pasted {len(new_nodes)} node(s) ({viewer_count} viewer(s)) with {connection_count} connection(s)", "#4CAF50"
            )
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.temp_connection:
            item = self.itemAt(event.pos())
            if isinstance(item, PortItem) and item != self.start_port:
                # Complete the connection if released on a valid port
                # Basic validation: prevent output-to-output or input-to-input
                if self.start_port.is_output != item.is_output:
                    # Set the end port
                    self.temp_connection.set_end_port(item)
                    
                    # Register the connection with both ports
                    self.start_port.add_connection(self.temp_connection)
                    item.add_connection(self.temp_connection)
                    
                    # Log to console if available
                    main_window = self.window()
                    if hasattr(main_window, 'console_output'):
                        main_window.console_output.append_output(
                            f"Connection created between {self.start_port.parentItem().title} and {item.parentItem().title}",
                            "#4CAF50"
                        )
                    else:
                        print(f"Connection created between {self.start_port.parentItem().title} and {item.parentItem().title}")
                else:
                    # Invalid connection (e.g., output to output)
                    self.scene().removeItem(self.temp_connection)
                    print("Invalid connection attempt.")
            else:
                # Released on empty space or same port, remove temporary line
                self.scene().removeItem(self.temp_connection)

            self.temp_connection = None
            self.start_port = None
            return # Consume event

        super().mouseReleaseEvent(event)

class ConsoleOutput(QTextEdit):
    """Widget to display console output"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 10))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3E3E3E;
            }
        """)
    
    def append_output(self, text, color=None):
        """Append text to the console with optional color"""
        if color:
            self.setTextColor(QColor(color))
        else:
            self.setTextColor(QColor("#D4D4D4"))  # Default light gray
        
        self.append(text)
        # Scroll to the bottom
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Node Editor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Load settings
        self.settings = QSettings("PythonNodeEditor", "NodeEditor")
        self.python_path = self.settings.value("python_path", "")

        # Create toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        # Add node button
        self.add_node_action = QAction("Add Node", self)
        self.add_node_action.triggered.connect(self.add_node)
        self.toolbar.addAction(self.add_node_action)

        # Add viewer node button
        self.add_viewer_action = QAction("Add Viewer", self)
        self.add_viewer_action.triggered.connect(self.add_viewer_node)
        self.toolbar.addAction(self.add_viewer_action)

        # Execute button
        self.execute_action = QAction("Execute", self)
        self.execute_action.triggered.connect(self.execute_graph)
        self.toolbar.addAction(self.execute_action)
        
        # Save button
        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self.save_graph)
        self.toolbar.addAction(self.save_action)
        
        # Load button
        self.load_action = QAction("Load", self)
        self.load_action.triggered.connect(self.load_graph)
        self.toolbar.addAction(self.load_action)
        
        # Ajout des boutons copier/coller
        self.copy_action = QAction("Copy", self)
        self.copy_action.setShortcut("Ctrl+C")
        self.copy_action.triggered.connect(self.copy_selected_nodes)
        self.toolbar.addAction(self.copy_action)
        
        self.paste_action = QAction("Paste", self)
        self.paste_action.setShortcut("Ctrl+V")
        self.paste_action.triggered.connect(self.paste_nodes)
        self.toolbar.addAction(self.paste_action)
        
        # Python path button
        self.python_path_action = QAction("Set Python Path", self)
        self.python_path_action.triggered.connect(self.set_python_path)
        self.toolbar.addAction(self.python_path_action)

        self.toolbar.addSeparator()
        
        # Auto-execute checkbox
        self.auto_execute_action = QAction("Auto-Execute", self)
        self.auto_execute_action.setCheckable(True)
        self.auto_execute_action.triggered.connect(self.toggle_auto_execute)
        self.toolbar.addAction(self.auto_execute_action)
        
        # Interval selection
        self.interval_action = QAction("Set Interval", self)
        self.interval_action.triggered.connect(self.set_execute_interval)
        self.toolbar.addAction(self.interval_action)
        
        # Timer pour l'exécution automatique
        self.execute_timer = QTimer(self)
        self.execute_timer.timeout.connect(self.execute_graph)
        
        # Intervalle par défaut en millisecondes (1 seconde = 1000 ms)
        self.execute_interval = 1000  # 1 seconde par défaut

        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)
        
        # Left side - Node canvas
        self.canvas_widget = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_widget)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scene = QGraphicsScene()
        self.canvas = NodeCanvas(self.scene)
        self.canvas_layout.addWidget(self.canvas)
        
        # Right side - Console output
        self.console_dock = QDockWidget("Console Output", self)
        self.console_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                     QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.console_output = ConsoleOutput()
        self.console_dock.setWidget(self.console_output)
        
        # Add widgets to splitter
        self.main_splitter.addWidget(self.canvas_widget)
        
        # Add dock widget to right side
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.console_dock)
        
        # Set initial splitter sizes (70% canvas, 30% console)
        self.main_splitter.setSizes([int(self.width() * 0.7), int(self.width() * 0.3)])

        # Store all nodes for execution
        self.nodes = []

        # Add two sample nodes
        node1 = self.add_node()
        node1.set_code("# Python code here\ndef process(input=None):\n    return 42")
        
        node2 = self.add_node()
        node2.set_code("# Python code here\ndef process(input=None):\n    return input * 2 if input else 0")
        node2.setPos(350, 50)  # Position to the right of the first node
        
        # Welcome message
        self.console_output.append_output("=== Python Node Editor ===", "#4CAF50")
        self.console_output.append_output("Double-click on nodes to edit their code.")
        self.console_output.append_output("Connect nodes by dragging from output to input ports.")
        self.console_output.append_output("Use Ctrl+C to copy selected nodes and Ctrl+V to paste them.")
        self.console_output.append_output("Drag and drop .json files to merge nodes without clearing the canvas.")

    # Fonctions de copier-coller qui délèguent à la toile
    def copy_selected_nodes(self):
        """Copier les nœuds sélectionnés via la toolbar"""
        self.canvas.copy_selected_nodes()
    
    def paste_nodes(self):
        """Coller les nœuds via la toolbar"""
        self.canvas.paste_nodes()

    def add_node(self):
        """Add a new node to the scene."""
        node = NodeItem(f"Node {len(self.nodes) + 1}")
        self.scene.addItem(node)
        
        # Stagger positions with more space between nodes
        node.setPos(100 + len(self.nodes) * 80, 100 + len(self.nodes) * 60)
        
        # Make sure the node is in collapsed state by default
        if node.is_expanded:
            node.toggle_expanded()
            
        self.nodes.append(node)
        return node
    
    def add_viewer_node(self):
        """Ajoute un nœud visualiseur au graphe"""
        viewer = ViewerNodeItem(f"Viewer {len([n for n in self.nodes if isinstance(n, ViewerNodeItem)]) + 1}")
        self.scene.addItem(viewer)
        
        # Positionner le nœud visualiseur à droite du canvas
        view_rect = self.canvas.viewport().rect()
        scene_pos = self.canvas.mapToScene(view_rect.width() - 250, 100 + len(self.nodes) * 60)
        viewer.setPos(scene_pos)
        
        # S'assurer que le nœud est en état réduit
        if viewer.is_expanded:
            viewer.toggle_expanded()
            
        self.nodes.append(viewer)
        
        # Log dans la console
        self.console_output.append_output(
            f"Viewer node '{viewer.title}' added",
            "#9C27B0"  # Violet, comme la couleur du nœud
        )
        
        return viewer
    
    def toggle_auto_execute(self, checked):
        """Activer ou désactiver l'exécution automatique"""
        if checked:
            # Démarrer le timer avec l'intervalle configuré
            self.execute_timer.start(self.execute_interval)
            self.console_output.append_output(
                f"Auto-execute enabled with interval {self.execute_interval/1000} seconds",
                "#4CAF50"  # Green
            )
        else:
            # Arrêter le timer
            self.execute_timer.stop()
            self.console_output.append_output(
                "Auto-execute disabled",
                "#FF9800"  # Orange
            )
    
    def set_execute_interval(self):
        """Permettre à l'utilisateur de définir l'intervalle d'exécution"""
        current_interval = self.execute_interval / 1000  # Convertir en secondes pour l'affichage
        
        interval, ok = QInputDialog.getDouble(
            self, "Set Auto-Execute Interval",
            "Enter interval in seconds:",
            current_interval, 0.1, 3600, 1  # Min 0.1s, max 1h, 1 décimale
        )
        
        if ok:
            # Convertir en millisecondes pour le timer
            self.execute_interval = int(interval * 1000)
            
            # Si le timer est en cours d'exécution, le redémarrer avec le nouvel intervalle
            if self.auto_execute_action.isChecked():
                self.execute_timer.stop()
                self.execute_timer.start(self.execute_interval)
            
            self.console_output.append_output(
                f"Auto-execute interval set to {interval} seconds",
                "#2196F3"  # Blue
            )

    def set_python_path(self):
        """Set the path to the Python interpreter"""
        current_path = self.python_path if self.python_path else sys.executable
        
        path, ok = QInputDialog.getText(
            self, "Set Python Path",
            "Enter the path to your Python interpreter:",
            text=current_path
        )
        
        if ok and path:
            self.python_path = path
            self.settings.setValue("python_path", path)
            self.console_output.append_output(f"Python path set to: {path}", "#4CAF50")
    
    def execute_graph(self):
        """Execute all nodes in the graph in topological order."""
        self.console_output.append_output("\n=== Executing Graph ===", "#FFC107")
        
        # Check if Python path is set
        if not self.python_path:
            result = QMessageBox.question(
                self, "Python Path Not Set",
                "Python path is not set. Would you like to set it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                self.set_python_path()
            else:
                self.console_output.append_output("Execution cancelled: Python path not set", "#F44336")
                return
        
        # Reset all node results
        for node in self.nodes:
            node.result = None
        
        # Simple topological sort based on connections
        # Start with nodes that have no input connections
        executed = set()
        
        # Keep executing until all nodes are processed or no progress is made
        progress = True
        while progress and len(executed) < len(self.nodes):
            progress = False
            
            for node in self.nodes:
                if node in executed:
                    continue
                
                # Check if all input nodes have been executed
                can_execute = True
                for port in node.inputs:
                    for connection in port.connections:
                        if connection.start_port != port:  # This port is the end port
                            source_node = connection.start_port.parentItem()
                            if source_node not in executed:
                                can_execute = False
                                break
                        else:  # This port is the start port
                            source_node = connection.end_port.parentItem()
                            if source_node not in executed:
                                can_execute = False
                                break
                    
                    if not can_execute:
                        break
                
                if can_execute:
                    # Execute the node
                    try:
                        result = node.execute_code()
                        self.console_output.append_output(
                            f"Node '{node.title}' executed with result: {result}",
                            "#4CAF50"  # Green for success
                        )
                        executed.add(node)
                        progress = True
                    except Exception as e:
                        self.console_output.append_output(
                            f"Error executing node '{node.title}': {str(e)}",
                            "#F44336"  # Red for error
                        )
        
        self.console_output.append_output(
            f"Execution complete. {len(executed)}/{len(self.nodes)} nodes executed.",
            "#2196F3"  # Blue for info
        )
    
    def serialize_graph(self):
        """Serialize the entire graph to a dictionary."""
        # Serialize nodes
        nodes_data = []
        for node in self.nodes:
            nodes_data.append(node.to_dict())
        
        # Serialize connections
        connections_data = []
        for node in self.nodes:
            for port in node.inputs + node.outputs:
                for connection in port.connections:
                    # Only serialize each connection once
                    if port == connection.start_port:  # Only process from start port
                        conn_data = connection.to_dict()
                        if conn_data:
                            connections_data.append(conn_data)
        
        return {
            'nodes': nodes_data,
            'connections': connections_data
        }
    
    def merge_graph_from_file(self, file_path):
        """Fusionner un graphe depuis un fichier JSON sans effacer le graphe existant."""
        try:
            # Charger le fichier JSON
            with open(file_path, 'r') as f:
                graph_data = json.load(f)
            
            # Créer un décalage aléatoire pour éviter que les nouveaux nœuds
            # ne soient exactement au même endroit que d'éventuels nœuds existants
            offset_x = 50
            offset_y = 50
            
            # Créer un dictionnaire pour mapper les anciens IDs aux nouveaux objets
            imported_nodes_dict = {}
            
            # Désélectionner tous les éléments
            for item in self.scene.selectedItems():
                item.setSelected(False)
            
            # Créer les nouveaux nœuds
            for node_data in graph_data['nodes']:
                # Vérifier si c'est un nœud visualiseur
                if 'node_type' in node_data and node_data['node_type'] == 'viewer':
                    new_node = ViewerNodeItem(node_data['title'])
                else:
                    new_node = NodeItem(node_data['title'])
                    
                new_node.set_code(node_data['code'])
                new_node.setPos(node_data['pos_x'] + offset_x, node_data['pos_y'] + offset_y)
                
                # Ajouter au graphe
                self.scene.addItem(new_node)
                self.nodes.append(new_node)
                
                # Sélectionner ce nouveau nœud
                new_node.setSelected(True)
                
                # Mapper l'ancien ID au nouveau nœud
                imported_nodes_dict[node_data['id']] = new_node
            
            # Créer les connexions
            for conn_data in graph_data['connections']:
                # Vérifier si les deux nœuds concernés ont été importés
                if conn_data['start_node_id'] in imported_nodes_dict and conn_data['end_node_id'] in imported_nodes_dict:
                    start_node = imported_nodes_dict[conn_data['start_node_id']]
                    end_node = imported_nodes_dict[conn_data['end_node_id']]
                    
                    # Obtenir les ports
                    start_port = start_node.outputs[conn_data['start_port_index']] if conn_data['start_port_is_output'] else start_node.inputs[conn_data['start_port_index']]
                    end_port = end_node.outputs[conn_data['end_port_index']] if conn_data['end_port_is_output'] else end_node.inputs[conn_data['end_port_index']]
                    
                    # Créer une nouvelle connexion
                    connection = ConnectionItem(start_port, end_port)
                    self.scene.addItem(connection)
                    
                    # Enregistrer la connexion avec les ports
                    start_port.add_connection(connection)
                    end_port.add_connection(connection)
            
            # Informer l'utilisateur
            node_count = len(graph_data['nodes'])
            connection_count = len([c for c in graph_data['connections'] 
                                if c['start_node_id'] in imported_nodes_dict 
                                and c['end_node_id'] in imported_nodes_dict])
            
            self.console_output.append_output(
                f"Merged {node_count} node(s) and {connection_count} connection(s) from {file_path}",
                "#4CAF50"  # Green for success
            )
            
        except Exception as e:
            # En cas d'erreur, informer l'utilisateur
            error_msg = f"Failed to merge graph from {file_path}: {str(e)}"
            self.console_output.append_output(error_msg, "#F44336")  # Rouge pour erreur
            QMessageBox.critical(self, "Error", error_msg)

    def deserialize_graph(self, data):
        """Deserialize and recreate the graph from a dictionary."""
        # Clear the current graph
        self.clear_graph()
        
        # Create a dictionary to map node IDs to node objects
        nodes_dict = {}
        
        # Create nodes
        for node_data in data['nodes']:
            # Vérifier si c'est un nœud visualiseur
            if 'node_type' in node_data and node_data['node_type'] == 'viewer':
                node = ViewerNodeItem.from_dict(node_data, self.scene)
            else:
                node = NodeItem.from_dict(node_data, self.scene)
                
            self.nodes.append(node)
            nodes_dict[node_data['id']] = node
        
        # Create connections
        for conn_data in data['connections']:
            connection = ConnectionItem.from_dict(conn_data, nodes_dict)
            if connection:
                self.scene.addItem(connection)
    
    def clear_graph(self):
        """Clear all nodes and connections from the graph."""
        self.scene.clear()
        self.nodes.clear()
    
    def save_graph(self):
        """Save the graph to a JSON file."""
        # Serialize the graph
        graph_data = self.serialize_graph()
        
        # Get the file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Graph", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return  # User cancelled
        
        # Add .json extension if not present
        if not file_path.endswith('.json'):
            file_path += '.json'
        
        try:
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(graph_data, f, indent=2)
            
            QMessageBox.information(self, "Success", f"Graph saved to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save graph: {str(e)}")
    
    def load_graph(self):
        """Load a graph from a JSON file."""
        # Get the file path
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Graph", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Load from file
            with open(file_path, 'r') as f:
                graph_data = json.load(f)
            
            # Deserialize the graph
            self.deserialize_graph(graph_data)
            
            QMessageBox.information(self, "Success", f"Graph loaded from {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load graph: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())