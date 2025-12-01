import json
import os
from core.producto import Producto
from .historial import Historial


class GestorInventario:
    def __init__(self, archivo="data/inventario.json"):
        self.archivo = archivo
        self.historial = Historial()  # Inicializar historial

        # Crear carpeta data si no existe
        if not os.path.exists("data"):
            os.makedirs("data")

        # Crear archivo JSON si no existe
        if not os.path.exists(self.archivo):
            self._guardar_json({})

        # Cargar inventario
        self.inventario = self._cargar_json()

    def _cargar_json(self):
        with open(self.archivo, "r", encoding="utf-8") as f:
            return json.load(f)

    def _guardar_json(self, data):
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def guardar(self):
        """Guardar el inventario actual en el archivo JSON"""
        self._guardar_json(self.inventario)

    # --------------------------------------------
    # CRUD DEL INVENTARIO
    # --------------------------------------------

    def agregar_producto(self, id_prod, nombre, categoria, cantidad, unidad, estado, foto):
        """Agrega un producto al inventario"""
        if id_prod in self.inventario:
            return False  # El producto ya existe

        # Crear producto
        producto = Producto(id_prod, nombre, cantidad, 0)  # Ajusta si Product tiene precio
        self.inventario[id_prod] = {
            "id": id_prod,
            "nombre": nombre,
            "categoria": categoria,
            "cantidad": cantidad,
            "unidad": unidad,
            "estado": estado,
            "foto": foto
        }

        self.guardar()

        # Registrar entrada en historial
        self.historial.registrar(id_prod, nombre, cantidad, "entrada", unidad, "Producto agregado al inventario")
        return True

    def eliminar_producto(self, id_prod):
        """Elimina un producto por ID"""
        if id_prod not in self.inventario:
            return False

        del self.inventario[id_prod]
        self.guardar()
        return True

    def actualizar_stock(self, id_prod, nueva_cantidad):
        """Actualiza la cantidad de un producto y registra en historial"""
        if id_prod not in self.inventario:
            return False

        prod = self.inventario[id_prod]
        diferencia = nueva_cantidad - prod["cantidad"]

        if diferencia > 0:
            tipo = "entrada"
            motivo = "Aumento de stock"
        elif diferencia < 0:
            tipo = "salida"
            motivo = "Salida de inventario"
        else:
            return True  # No hay cambio

        # Registrar movimiento
        self.historial.registrar(id_prod, prod["nombre"], abs(diferencia), tipo, prod["unidad"], motivo)

        prod["cantidad"] = nueva_cantidad
        self.guardar()
        return True

    def buscar_producto(self, id_prod):
        """Devuelve un producto por ID"""
        return self.inventario.get(id_prod)

    def listar_productos(self):
        """Devuelve todo el inventario"""
        return self.inventario

   
