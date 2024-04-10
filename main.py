import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class AudioDragDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Drag and Drop Audio Analysis')
        self.setGeometry(100, 100, 400, 200)  # x, y, width, height
        self.setAcceptDrops(True)
        
        # Layout and label for displaying messages
        layout = QVBoxLayout()
        self.label = QLabel('Drag and drop an audio file here', self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            self.label.setText(f'File dropped: {file_path}')
            # Here, you would call your plot function with the dropped file path
            # For example: plot_macro_time_power_graph_colormap(file_path)
            break  # This example only processes the first dropped file

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AudioDragDropWidget()
    ex.show()
    sys.exit(app.exec_())