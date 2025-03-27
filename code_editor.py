from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout
from PySide6.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter, QKeySequence
from PySide6.QtCore import QRegularExpression, Qt

class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))  # Blue
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda", "None",
            "nonlocal", "not", "or", "pass", "raise", "return", "True",
            "try", "while", "with", "yield"
        ]
        
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlighting_rules.append((pattern, keyword_format))
        
        # Strings (single and double quotes)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))  # Brown
        
        self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))  # Light green
        
        self.highlighting_rules.append((QRegularExpression(r'\b[0-9]+\b'), number_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Green
        
        self.highlighting_rules.append((QRegularExpression(r'#[^\n]*'), comment_format))
        
        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))  # Yellow
        
        self.highlighting_rules.append((QRegularExpression(r'\bdef\s+(\w+)\b'), function_format))
        self.highlighting_rules.append((QRegularExpression(r'\bclass\s+(\w+)\b'), function_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)


class CodeEditor(QTextEdit):
    """Simple code editor widget with syntax highlighting."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set font to monospace
        font = QFont("Courier New", 10)
        self.setFont(font)
        
        # Set colors
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3E3E3E;
            }
        """)
        
        # Add syntax highlighting
        self.highlighter = PythonHighlighter(self.document())
        
        # Set tab width
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))
        
        # Activer explicitement les raccourcis standard pour assurer leur fonctionnement sur toutes les plateformes
        self.setUndoRedoEnabled(True)
        
        # S'assurer que le widget peut recevoir le focus pour les événements clavier
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def keyPressEvent(self, event):
        """Surcharge pour s'assurer que les raccourcis clavier standards fonctionnent correctement"""
        # Vérifier si c'est un raccourci standard
        if event.matches(QKeySequence.StandardKey.Copy) or \
           event.matches(QKeySequence.StandardKey.Paste) or \
           event.matches(QKeySequence.StandardKey.Cut) or \
           event.matches(QKeySequence.StandardKey.SelectAll) or \
           event.matches(QKeySequence.StandardKey.Undo) or \
           event.matches(QKeySequence.StandardKey.Redo):
            # Utiliser l'implémentation standard de QTextEdit
            super().keyPressEvent(event)
        else:
            # Pour les autres touches, comportement normal
            super().keyPressEvent(event)


class CodeEditorWidget(QWidget):
    """Widget that wraps the code editor with a layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = CodeEditor()
        self.layout.addWidget(self.editor)
        
        # Default code
        self.editor.setText("# Python code here\ndef process(input):\n    return input * 2")
    
    def get_code(self):
        """Get the current code from the editor."""
        return self.editor.toPlainText()
    
    def set_code(self, code):
        """Set the code in the editor."""
        self.editor.setText(code)