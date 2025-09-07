from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from datetime import datetime
import os
import sys

app = Flask(__name__)

#def resource_path(relative_path):
#    try:
#        base_path = sys._MEIPASS
#    except Exception:
#        base_path = os.path.abspath(".")
#    return os.path.join(base_path, relative_path)


#app = Flask(
#    __name__,
#    template_folder=resource_path("templates"),
#    static_folder=resource_path("static")
#)


app.secret_key = 'mi_clave_secreta'  # Necesario para sesiones


import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_DIR, "database")  # Carpeta externa
os.makedirs(DB_FOLDER, exist_ok=True)
DB_PATH = os.path.join(DB_FOLDER, "database.db")

# Crear base de datos con tablas necesarias
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabla usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            contraseña TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    ''')
    # Crear un usuario admin de ejemplo
    cursor.execute("SELECT * FROM usuarios WHERE nombre='admin'")
    if not cursor.fetchone():
        hashed = generate_password_hash('admin123', method='sha256')
        cursor.execute("INSERT INTO usuarios (nombre, contraseña, rol) VALUES (?, ?, ?)", 
                       ('admin', hashed, 'admin'))

    # Tabla supervisores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supervisores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            comision_por_pieza REAL NOT NULL
        )
    ''')

    # Tabla empleados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            id_supervisor INTEGER,
            FOREIGN KEY (id_supervisor) REFERENCES supervisores(id)
        )
    ''')

    # Tabla productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL
        )
    ''')

    # Tabla ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER,
            id_empleado INTEGER,
            id_supervisor INTEGER,
            vendidas_paq REAL,
            vendidas_piezas REAL,
            precio_unitario REAL,
            total_venta REAL,
            comision REAL,
            ganancia REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_producto) REFERENCES productos(id),
            FOREIGN KEY (id_empleado) REFERENCES empleados(id),
            FOREIGN KEY (id_supervisor) REFERENCES supervisores(id)
        )
    ''')

    conn.commit()
    conn.close()


# Inicializar la base al arrancar la app
init_db()


# Página login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form['nombre']
        contraseña = request.form['contraseña']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE nombre=?", (nombre,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], contraseña):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_rol'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')
# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Conectar a la base de datos para obtener estadísticas
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total de productos (unidades)
    cursor.execute("SELECT SUM(cantidad) FROM productos")
    total_productos = cursor.fetchone()[0] or 0

    # Valor total en bodega (cantidad * precio_unitario)
    cursor.execute("SELECT SUM(cantidad * precio_unitario) FROM productos")
    total_bodega = cursor.fetchone()[0] or 0.0

    # Contar empleados
    cursor.execute("SELECT COUNT(*) FROM empleados")
    total_empleados = cursor.fetchone()[0]

    # Contar supervisores
    cursor.execute("SELECT COUNT(*) FROM supervisores")
    total_supervisores = cursor.fetchone()[0]

    # Ganancia total
    cursor.execute("SELECT SUM(ganancia) FROM ventas")
    total_ventas = cursor.fetchone()[0] or 0.0

    # 🔹 Ventas y rendimiento últimos 5 días
    cursor.execute("""
        SELECT strftime('%Y-%m-%d', fecha) as dia,
               SUM(total_venta) as total_ventas,
               SUM(total_venta - comision) as rendimiento
        FROM ventas
        WHERE fecha >= date('now', '-5 days')
        GROUP BY dia
        ORDER BY dia ASC
    """)
    data = cursor.fetchall()

    conn.close()

    # Preparar datos para la gráfica
    dias = [row[0] for row in data]
    ventas = [row[1] for row in data]
    rendimiento = [row[2] for row in data]

    return render_template(
        'dashboard.html', 
        nombre=session['user_name'], 
        rol=session['user_rol'],
        total_productos=total_productos,
        total_bodega=total_bodega,
        total_empleados=total_empleados,
        total_supervisores=total_supervisores,
        total_ventas=total_ventas,
        dias=dias,
        ventas=ventas,
        rendimiento=rendimiento
    )


# --- Productos CRUD ---
@app.route('/productos', methods=['GET', 'POST'])
def productos():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Crear tabla productos si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL
        )
    ''')

    # Agregar producto
    if request.method == 'POST' and request.form.get('action') == 'agregar':
        nombre = request.form['nombre']
        cantidad = int(request.form['cantidad'])
        precio = float(request.form['precio'])
        try:
            cursor.execute("INSERT INTO productos (nombre, cantidad, precio_unitario) VALUES (?, ?, ?)",
                           (nombre, cantidad, precio))
            conn.commit()
            flash('Producto agregado correctamente', 'success')
        except sqlite3.IntegrityError:
            flash('El producto ya existe', 'danger')

    # Modificar producto
    if request.method == 'POST' and request.form.get('action') == 'modificar':
        prod_id = int(request.form['id'])
        nombre = request.form['nombre']
        cantidad = int(request.form['cantidad'])
        precio = float(request.form['precio'])
        contraseña = request.form['contraseña']

        # Verificar contraseña
        cursor.execute("SELECT contraseña FROM usuarios WHERE id=?", (session['user_id'],))
        hashed = cursor.fetchone()[0]
        if not check_password_hash(hashed, contraseña):
            flash('Contraseña incorrecta. No se pudo modificar.', 'danger')
        else:
            cursor.execute("UPDATE productos SET nombre=?, cantidad=?, precio_unitario=? WHERE id=?",
                           (nombre, cantidad, precio, prod_id))
            conn.commit()
            flash('Producto modificado correctamente', 'success')

    # Eliminar producto
    if request.method == 'POST' and request.form.get('action') == 'eliminar':
        prod_id = int(request.form['id'])
        contraseña = request.form['contraseña']

        cursor.execute("SELECT contraseña FROM usuarios WHERE id=?", (session['user_id'],))
        hashed = cursor.fetchone()[0]
        if not check_password_hash(hashed, contraseña):
            flash('Contraseña incorrecta. No se pudo eliminar.', 'danger')
        else:
            cursor.execute("DELETE FROM productos WHERE id=?", (prod_id,))
            conn.commit()
            flash('Producto eliminado correctamente', 'success')

    # Obtener todos los productos
    cursor.execute("SELECT * FROM productos")
    productos_list = cursor.fetchall()
    conn.close()
    return render_template('productos.html', productos=productos_list)

# --- CRUD Supervisores ---
@app.route('/supervisores', methods=['GET', 'POST'])
def supervisores():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supervisores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            comision_por_pieza REAL NOT NULL
        )
    ''')

    # Agregar supervisor
    if request.method == 'POST' and request.form.get('action') == 'agregar':
        nombre = request.form['nombre']
        comision = float(request.form['comision'])
        try:
            cursor.execute("INSERT INTO supervisores (nombre, comision_por_pieza) VALUES (?, ?)",
                           (nombre, comision))
            conn.commit()
            flash('Supervisor agregado correctamente', 'success')
        except sqlite3.IntegrityError:
            flash('El supervisor ya existe', 'danger')

    # Modificar supervisor
    if request.method == 'POST' and request.form.get('action') == 'editar':
        sup_id = int(request.form['id'])
        nombre = request.form['nombre']
        comision = float(request.form['comision'])
        cursor.execute("UPDATE supervisores SET nombre=?, comision_por_pieza=? WHERE id=?",
                       (nombre, comision, sup_id))
        conn.commit()
        flash('Supervisor actualizado correctamente', 'success')

    # Eliminar supervisor
    if request.method == 'POST' and request.form.get('action') == 'eliminar':
        sup_id = int(request.form['id'])
        cursor.execute("DELETE FROM supervisores WHERE id=?", (sup_id,))
        conn.commit()
        flash('Supervisor eliminado correctamente', 'success')

    # Obtener todos los supervisores
    cursor.execute("SELECT * FROM supervisores")
    supervisores_list = cursor.fetchall()
    conn.close()
    return render_template('supervisores.html', supervisores=supervisores_list)
# --- CRUD Empleados ---
@app.route('/empleados', methods=['GET', 'POST'])
def empleados():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Crear tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            id_supervisor INTEGER,
            FOREIGN KEY (id_supervisor) REFERENCES supervisores(id)
        )
    ''')

    action = request.form.get("action")

    if request.method == "POST":
        if action == "agregar":
            nombre = request.form.get("nombre")
            id_supervisor = request.form.get("id_supervisor")

            cursor.execute("""
                INSERT INTO empleados (nombre, id_supervisor)
                VALUES (?, ?)
            """, (nombre, id_supervisor))
            conn.commit()
            flash("Empleado agregado correctamente", "success")

        elif action == "editar":
            emp_id = request.form.get("id")
            nombre = request.form.get("nombre")
            id_supervisor = request.form.get("id_supervisor")

            cursor.execute("""
                UPDATE empleados
                SET nombre=?, id_supervisor=?
                WHERE id=?
            """, (nombre, id_supervisor, emp_id))
            conn.commit()
            flash("Empleado actualizado correctamente", "success")

        elif action == "borrar":
            emp_id = request.form.get("id")
            cursor.execute("DELETE FROM empleados WHERE id=?", (emp_id,))
            conn.commit()
            flash("Empleado eliminado correctamente", "success")

    # Obtener supervisores
    cursor.execute("SELECT id, nombre, comision_por_pieza FROM supervisores")
    supervisores = cursor.fetchall()

    # Obtener empleados con nombre de supervisor
    cursor.execute("""
        SELECT e.id, e.nombre, s.nombre AS supervisor, s.comision_por_pieza
        FROM empleados e
        LEFT JOIN supervisores s ON e.id_supervisor = s.id
    """)
    empleados = cursor.fetchall()

    conn.close()
    return render_template("empleados.html", empleados=empleados, supervisores=supervisores)


@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Crear tabla ventas si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER,
            id_empleado INTEGER,
            id_supervisor INTEGER,
            vendidas_paq REAL,
            vendidas_piezas REAL,
            precio_unitario REAL,
            total_venta REAL,
            comision REAL,
            ganancia REAL,
            fecha TIMESTAMP,
            FOREIGN KEY (id_producto) REFERENCES productos(id),
            FOREIGN KEY (id_empleado) REFERENCES empleados(id),
            FOREIGN KEY (id_supervisor) REFERENCES supervisores(id)
        )
    ''')

    # Obtener productos
    cursor.execute("SELECT id, nombre, cantidad, precio_unitario FROM productos")
    productos = cursor.fetchall()

    # Obtener empleados con sus supervisores
    cursor.execute("""
        SELECT e.id, e.nombre, s.id, s.nombre, s.comision_por_pieza
        FROM empleados e
        LEFT JOIN supervisores s ON e.id_supervisor = s.id
    """)
    empleados = cursor.fetchall()

    if request.method == 'POST':
        for emp_id, prod_id, sup_id, vendidas_paq in zip(
            request.form.getlist('empleado_id'),
            request.form.getlist('producto_id'),
            request.form.getlist('supervisor_id'),
            request.form.getlist('vendidas')
        ):
            vendidas_paq = float(vendidas_paq)
            if vendidas_paq <= 0:
                continue

            # Convertir paquetes a piezas (ajusta según tus reglas)
            vendidas_piezas = vendidas_paq * 2

            # Obtener precio unitario del producto
            cursor.execute("SELECT precio_unitario FROM productos WHERE id=?", (prod_id,))
            precio_unitario = cursor.fetchone()[0]

            # Obtener comisión del supervisor
            comision_por_pieza = 0
            if sup_id:
                cursor.execute("SELECT comision_por_pieza FROM supervisores WHERE id=?", (sup_id,))
                comision_por_pieza = cursor.fetchone()[0]

            total_venta = vendidas_piezas * precio_unitario
            comision = vendidas_piezas * comision_por_pieza
            ganancia = total_venta - comision

            # Fecha actual en hora de CDMX
            cdmx_tz = pytz.timezone('America/Mexico_City')
            fecha_actual = datetime.now(cdmx_tz).strftime('%Y-%m-%d %H:%M:%S')

            # Insertar venta
            cursor.execute("""
                INSERT INTO ventas (id_producto, id_empleado, id_supervisor, vendidas_paq,
                    vendidas_piezas, precio_unitario, total_venta, comision,
                    ganancia, fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (prod_id, emp_id, sup_id, vendidas_paq, vendidas_piezas, precio_unitario,
                  total_venta, comision, ganancia, fecha_actual))

            # Actualizar inventario
            cursor.execute("UPDATE productos SET cantidad = cantidad - ? WHERE id=?", (vendidas_piezas, prod_id))

        conn.commit()
        flash("Ventas registradas correctamente", "success")

    conn.close()
    return render_template('ventas.html', productos=productos, empleados=empleados)

@app.route('/reporte', methods=['GET', 'POST'])
def reporte():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    query = """
        SELECT v.id, e.nombre, p.nombre, v.vendidas_paq, v.vendidas_piezas,
               v.precio_unitario, v.total_venta, v.comision, v.ganancia,
               v.fecha, p.cantidad as piezas_bodega
        FROM ventas v
        JOIN empleados e ON v.id_empleado = e.id
        JOIN productos p ON v.id_producto = p.id
        WHERE 1=1
    """
    params = []

    if fecha_inicio and fecha_fin:
        query += " AND date(v.fecha) BETWEEN ? AND ?"
        params.extend([fecha_inicio, fecha_fin])

    cursor.execute(query, params)
    ventas = cursor.fetchall()

    # Totales de ventas
    if fecha_inicio and fecha_fin:
        cursor.execute("""
            SELECT SUM(vendidas_piezas), SUM(total_venta)
            FROM ventas
            WHERE date(fecha) BETWEEN ? AND ?
        """, (fecha_inicio, fecha_fin))
    else:
        cursor.execute("SELECT SUM(vendidas_piezas), SUM(total_venta) FROM ventas")

    total_piezas, total_venta = cursor.fetchone()

    # Total de piezas en bodega (todos los productos)
    cursor.execute("SELECT SUM(cantidad) FROM productos")
    total_bodega = cursor.fetchone()[0] or 0

    conn.close()
    return render_template('reporte.html',
                           ventas=ventas,
                           total_piezas=total_piezas or 0,
                           total_venta=total_venta or 0.0,
                           total_bodega=total_bodega,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin)
@app.route('/delete_venta/<int:venta_id>', methods=['POST'])
def delete_venta(venta_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verificar que la venta exista (opcional)
    cursor.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,))
    venta = cursor.fetchone()
    if venta:
        cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
        conn.commit()
        flash(f"Registro de venta {venta_id} eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "error")

    conn.close()
    return redirect(url_for('reporte'))
# Cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)