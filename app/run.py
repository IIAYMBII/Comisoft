import os
import sys
import threading
import base64
import webview
from app import app  # importa tu Flask app

# --------------------------
# Ajuste de rutas para PyInstaller
# --------------------------
def resource_path(relative_path):
    """Devuelve la ruta absoluta, válida tanto para .exe como para .py"""
    try:
        base_path = sys._MEIPASS  # Carpeta temporal de PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --------------------------
# Ajustar la base de datos
# --------------------------
# Directorio donde estará la DB (externa al exe)
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "database.db")

# Crear carpeta si no existe
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# Reemplazar DB_PATH en app.py
import app as myapp
myapp.DB_PATH = DB_PATH

# --------------------------
# API para PyWebView
# --------------------------
class Api:
    def guardar_pdf(self, pdf_base64):
        pdf_bytes = base64.b64decode(pdf_base64)
        filename = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="lions-international-ventas.pdf",
            file_types=("PDF files (*.pdf)",)
        )
        if filename:
            with open(filename[0], "wb") as f:
                f.write(pdf_bytes)
            return f"PDF guardado en: {filename[0]}"
        return "Operación cancelada"

    def guardar_excel(self, excel_base64):
        excel_bytes = base64.b64decode(excel_base64)
        filename = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="lions-international-ventas.xlsx",
            file_types=("Excel files (*.xlsx)",)
        )
        if filename:
            with open(filename[0], "wb") as f:
                f.write(excel_bytes)
            return f"Excel guardado en: {filename[0]}"
        return "Operación cancelada"

# --------------------------
# Iniciar Flask
# --------------------------
def start_flask():
    app.run(debug=False, port=5000)

# --------------------------
# Main
# --------------------------
if __name__ == "__main__":
    # Inicia Flask en un hilo
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    # Instancia la API
    api = Api()

    # Crea la ventana PyWebView
    webview.create_window("Inventarios", "http://127.0.0.1:5000", js_api=api)
    webview.start()
