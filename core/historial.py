import json
from datetime import datetime
import os

class Historial:

    def __init__(self, archivo="historial.json"):
        self.archivo = archivo

        if not os.path.exists(self.archivo):
            with open(self.archivo, "w") as f:
                json.dump([], f)

    def registrar(self, idp, nombre, cantidad, tipo, unidad, motivo=""):
        nuevo = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "id": idp,
            "nombre": nombre,
            "cantidad": cantidad,
            "unidad": unidad,
            "tipo": tipo,   # entrada / salida
            "motivo": motivo
        }

        with open(self.archivo, "r") as f:
            datos = json.load(f)

        datos.append(nuevo)

        with open(self.archivo, "w") as f:
            json.dump(datos, f, indent=4)
