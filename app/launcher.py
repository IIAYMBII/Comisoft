import subprocess
import os
import sys

# Obtener la ruta base
if getattr(sys, 'frozen', False):
    # Si estamos ejecutando el launcher como .exe
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# Ruta al script run.py
run_path = os.path.join(base_path, "run.py")

# Ejecutar run.py usando el mismo intérprete de Python
try:
    subprocess.Popen([sys.executable, run_path])
except FileNotFoundError:
    print(f"No se encontró el archivo: {run_path}")
