import os
import sys
import threading
import webview
from app import app  # importa tu Flask app

# Ajuste de rutas para PyInstaller
def resource_path(relative_path):
    """Obtiene la ruta absoluta, funciona con PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def start_flask():
    app.run(debug=False, port=5000)

if __name__ == "__main__":
    # Inicia Flask en un hilo
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    # Abre la ventana de escritorio
    webview.create_window("Inventarios", "http://127.0.0.1:5000")
    webview.start()
