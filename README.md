# Python Node Editor

A flexible visual programming environment that lets you create, connect, and execute Python code nodes in an intuitive graphical interface.

![Python Node Editor Screenshot](screenshot.png)

## Features

### Visual Programming
- Create nodes that contain Python code
- Connect nodes through input/output ports to create processing flows
- Execute the graph to process data sequentially
- Expand/collapse nodes to edit or view their code
- Viewer nodes to visualize data in real-time

### Advanced Editing
- Copy and paste nodes with Ctrl+C / Ctrl+V (including connections between selected nodes)
- Double-click on node titles to rename them
- Double-click on node bodies to expand them and edit their Python code
- Right-click to delete nodes and connections

### Project Management
- Save and load entire graphs as JSON files
- Merge nodes from JSON files via drag and drop without clearing the canvas
- Automatic execution at configurable intervals

### Python Integration
- Each node contains a Python function called `process()`
- Nodes have access to many built-in Python modules
- Easy integration with data science libraries if installed

## Getting Started

### Prerequisites

- Python 3.6 or higher
- PySide6

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/python-node-editor.git
cd python-node-editor

# Install dependencies
pip install PySide6
```

### Running the Application

```bash
python main.py
```

## Usage Guide

### Creating Your First Flow

1. **Add Nodes**: Click "Add Node" in the toolbar to create new nodes
2. **Add Viewers**: Click "Add Viewer" to create viewer nodes for visualizing data
3. **Edit Code**: Double-click a node to expand it and edit its Python code
4. **Connect Nodes**: Drag from an output port (right side) to an input port (left side)
5. **Execute**: Click "Execute" to run the flow and see the results in viewer nodes

### Code Examples for Nodes

Here are some examples of code you can use in your nodes:

#### Basic Data Generator
```python
def process(input=None):
    # Generate a list of numbers
    return [i for i in range(10)]
```

#### Mathematical Operations
```python
def process(input=None):
    if input is None:
        return None
        
    # Square each number in the input list
    return [x ** 2 for x in input]
```

#### Text Processing
```python
def process(input=None):
    if input is None:
        return "No input provided"
        
    # Convert to string and capitalize
    return str(input).upper()
```

#### Dictionary Transformation
```python
def process(input=None):
    if input is None:
        return {}
        
    # If input is a list, convert to dictionary
    if isinstance(input, list):
        return {f"item_{i}": value for i, value in enumerate(input)}
    return {"error": "Input is not a list"}
```

#### Random Data Generator
```python
import random

def process(input=None):
    # Generate 5 random numbers
    return [random.randint(1, 100) for _ in range(5)]
```

#### Working with Multiple Inputs
```python
def process(*inputs):
    # Combine multiple inputs
    result = []
    for input_data in inputs:
        if input_data is not None:
            if isinstance(input_data, list):
                result.extend(input_data)
            else:
                result.append(input_data)
    return result
```

### Working with Viewer Nodes

Viewer nodes are special nodes designed to visualize data flowing through your graph:

- They display the data they receive in a formatted way
- Different data types (lists, dictionaries, etc.) are formatted appropriately
- They act as both a pass-through and a visualization tool
- When expanded, you can modify their code for custom processing

### Automatic Execution Mode

The automatic execution mode allows your graph to run continuously at specified intervals:

1. **Enabling Auto-Execute**: Click the "Auto-Execute" button in the toolbar to toggle automatic execution.
2. **Setting the Interval**: Click "Set Interval" to specify how frequently the graph should execute (in seconds).
3. **Use Cases**:
   - Real-time data monitoring through viewer nodes
   - Continuous data processing workflows
   - Simulating dynamic systems
   - Testing graph behavior with changing inputs

Example: Set up a node that generates random data, connect it to a processing node and then to a viewer node, and enable auto-execute with a 0.5 second interval to see real-time data visualization.

### Keyboard Shortcuts

- **Ctrl+C**: Copy selected nodes (with their connections)
- **Ctrl+V**: Paste copied nodes
- **Right-click**: Delete nodes or connections

## Example Workflow: Real-time Data Processing

1. Create a data generator node with code that generates random values:
   ```python
   import random
   import time

   def process(input=None):
       # Add current timestamp
       return {
           "timestamp": time.time(),
           "value": random.randint(1, 100)
       }
   ```

2. Create a processing node that transforms the data:
   ```python
   def process(input=None):
       if input is None or not isinstance(input, dict):
           return None
           
       # Add classification to the data
       result = input.copy()
       value = input.get("value", 0)
       
       if value < 30:
           result["category"] = "low"
       elif value < 70:
           result["category"] = "medium"
       else:
           result["category"] = "high"
           
       return result
   ```

3. Add a viewer node and connect the nodes in sequence

4. Enable Auto-Execute with a 1-second interval to see real-time data processing and visualization

## Project Structure

- `main.py`: Application entry point and main window
- `node.py`: Node item implementation including ViewerNodeItem
- `connection.py`: Connection between nodes
- `code_editor.py`: Python code editor with syntax highlighting

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with PySide6 and Python
- Inspired by node-based programming environments like Blender, Unreal Engine, and Max/MSP
