import json
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash

USERS_FILE = os.path.join("data", "usuarios.json")
PENDING_FILE = os.path.join("data", "pending_codes.json")

def _ensure_files():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)
    if not os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)

_ensure_files()

class Auth:
    @staticmethod
    def load_users():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_users(users):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)

    @staticmethod
    def user_exists(username):
        users = Auth.load_users()
        return any(u["username"] == username for u in users)

    @staticmethod
    def create_user(name, username, password, phone):
        users = Auth.load_users()
        if any(u["username"] == username for u in users):
            return False, "El usuario ya existe"

        hashed = generate_password_hash(password)
        users.append({
            "name": name,
            "username": username,
            "password": hashed,
            "phone": phone
        })
        Auth.save_users(users)
        return True, "Usuario creado"

    @staticmethod
    def verify_credentials(username, password):
        users = Auth.load_users()
        for u in users:
            if u["username"] == username and check_password_hash(u["password"], password):
                return True, u
        return False, None

    # -------------------------
    # Código temporal simulado
    # -------------------------
    @staticmethod
    def send_code_to_number(username, phone_target="9611692015"):
        """
        Genera un código aleatorio y lo guarda en pending_codes.json para verificación.
        Opcional: phone_target se muestra para claridad; no se envía SMS real.
        """
        code = str(random.randint(100000, 999999))
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            pending = json.load(f)
        pending[username] = {"code": code}
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(pending, f, indent=4)
        # Opción B: no mostramos en UI; solo queda en pending_codes.json (y en consola si quieres)
        print(f"[SIMULADO] Código para {username} -> {code} (destino: {phone_target})")
        return code

    @staticmethod
    def check_code(username, code):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            pending = json.load(f)
        entry = pending.get(username)
        if entry and str(entry.get("code")) == str(code):
            # eliminar el código tras usar
            pending.pop(username, None)
            with open(PENDING_FILE, "w", encoding="utf-8") as f:
                json.dump(pending, f, indent=4)
            return True
        return False
