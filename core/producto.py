class Producto:
    def __init__(self, id_prod, nombre, cantidad, precio):
        self.id = id_prod
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "cantidad": self.cantidad,
            "precio": self.precio
        }
