from flask import Flask, render_template, request, redirect, session, send_file, url_for
from core.gestor import GestorInventario
from core.historial import Historial
from core.auth import Auth
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "2345"  # cambia en producción

# Uploads
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs("data", exist_ok=True)

# servicios
gestor = GestorInventario()
hist = Historial()

# ----------------------------
# helper: ruta protegida
# ----------------------------
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# ----------------------------
# RUTAS DE AUTENTICACIÓN
# ----------------------------
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]
        phone = request.form["phone"]

        ok, msg = Auth.create_user(name, username, password, phone)
        if not ok:
            return render_template("registro.html", error=msg)

        # Código de verificación FIJO
        session["codigo_verificacion"] = "501170"
        session["usuario_verificando"] = username

        return redirect(url_for("verificar", username=username))

    return render_template("registro.html")


@app.route("/verificar/<username>", methods=["GET", "POST"])
def verificar(username):
    if request.method == "POST":
        code = request.form["code"]
        if Auth.check_code(username, code):
            # autenticación final: iniciar sesión automático
            users = Auth.load_users()
            user = next((u for u in users if u["username"] == username), None)
            if user:
                session["user"] = user["username"]
                return redirect("/")
            else:
                return "Usuario no encontrado", 404
        return render_template("verificar.html", username=username, error="Código incorrecto")
    return render_template("verificar.html", username=username)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        ok, user = Auth.verify_credentials(username, password)
        if ok:
            session["user"] = user["username"]
            return redirect("/")
        return render_template("login.html", error="Credenciales inválidas")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ----------------------------
# RUTAS INVENTARIO (protegidas)
# ----------------------------
@app.route("/")
@login_required
def inicio():
    productos = list(gestor.listar_productos().values())
    return render_template("index.html", productos=productos)

@app.route("/agregar", methods=["GET", "POST"])
@login_required
def agregar():
    if request.method == "POST":
        idp = request.form["id"]
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        cantidad = int(request.form["cantidad"])
        unidad = request.form["unidad"]
        estado = request.form["estado"]

        foto = request.files.get("foto")
        filename = None
        if foto and foto.filename != "":
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        gestor.agregar_producto(idp, nombre, categoria, cantidad, unidad, estado, filename)

        # registrar en historial
        hist.registrar(idp, nombre, cantidad, "entrada", unidad, "Producto agregado")

        return redirect("/")
    return render_template("agregar.html")

@app.route("/editar/<idp>", methods=["GET", "POST"])
@login_required
def editar(idp):
    prod = gestor.buscar_producto(idp)
    if not prod:
        return "Producto no encontrado", 404
    if request.method == "POST":
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        cantidad = int(request.form["cantidad"])
        unidad = request.form["unidad"]
        estado = request.form["estado"]

        diferencia = cantidad - prod["cantidad"]
        if diferencia != 0:
            tipo = "entrada" if diferencia > 0 else "salida"
            hist.registrar(idp, nombre, abs(diferencia), tipo, unidad, "Ajuste edición")

        gestor.actualizar_producto(idp, nombre, categoria, cantidad, unidad, estado)
        return redirect("/")
    return render_template("editar.html", producto=prod)

@app.route("/eliminar/<idp>")
@login_required
def eliminar(idp):
    prod = gestor.buscar_producto(idp)
    if prod:
        hist.registrar(idp, prod["nombre"], prod["cantidad"], "salida", prod.get("unidad","piezas"), "Eliminación")
    gestor.eliminar_producto(idp)
    return redirect("/")

@app.route("/historial")
@login_required
def historial_view():
    if not os.path.exists("data/historial.json"):
        registros = []
    else:
        with open("data/historial.json", "r", encoding="utf-8") as f:
            registros = json.load(f)
    return render_template("historial.html", registros=registros)

# ----------------------------
# RUTA: Generar PDF del inventario con límite 32 días atrás
# ----------------------------
@login_required
@app.route("/reporte", methods=["GET", "POST"])
def reporte():
    """
    GET -> muestra formulario para elegir fecha final (end_date)
    POST -> genera y envía PDF con inventario desde end_date - 32 hasta end_date
    """
    if request.method == "POST":
        end_str = request.form.get("end_date")
        try:
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
        except Exception:
            return "Fecha inválida", 400

        start_date = end_date - timedelta(days=32)
        # Nota: como el inventario general no tiene timestamps por registro completo (solo historial registra movimientos),
        # aquí consideramos devolver el estado actual del inventario sin imágenes (tal como pediste),
        # y en encabezado ponemos el rango solicitado. Si deseas filtrar por movimientos del historial en ese rango,
        # lo podemos implementar fácilmente.
        productos = list(gestor.listar_productos().values())

        # Crear PDF en memoria
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        y = height - 60
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, f"Reporte Inventario (sin imágenes)")
        c.setFont("Helvetica", 10)
        c.drawString(40, y-18, f"Rango solicitado: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
        y -= 40

        # Tabla encabezado
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, "ID")
        c.drawString(120, y, "Nombre")
        c.drawString(350, y, "Categoría")
        c.drawString(480, y, "Cantidad")
        c.drawString(540, y, "Unidad")
        c.drawString(610, y, "Estado")
        y -= 18
        c.setFont("Helvetica", 10)

        for p in productos:
            if y < 80:
                c.showPage()
                y = height - 60
            c.drawString(40, y, str(p.get("id","")))
            c.drawString(120, y, str(p.get("nombre",""))[:30])
            c.drawString(350, y, str(p.get("categoria",""))[:18])
            c.drawString(480, y, str(p.get("cantidad","")))
            c.drawString(540, y, str(p.get("unidad","")))
            c.drawString(610, y, str(p.get("estado","")))
            y -= 16

        c.showPage()
        c.save()
        buffer.seek(0)

        filename = f"reporte_inventario_{end_date.strftime('%Y%m%d')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

    # GET => mostrar formulario
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("reporte.html", today=today)

# ----------------------------
# run
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
