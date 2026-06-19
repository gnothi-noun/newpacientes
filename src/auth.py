"""Autenticación por usuario/contraseña para la app Dash.

Diseño (prototipo en LAN):
- Login con sesión de Flask (Dash corre sobre Flask). Sin sesión válida, toda
  la app redirige a /login.
- Usuarios en `users.json` con contraseñas hasheadas (werkzeug). NO en git.
- La creación de usuarios se hace por CLI (gestionar_usuarios.py), que se corre
  por SSH en la Pi: como solo el admin tiene SSH, solo el admin crea usuarios.
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from flask import Response, redirect, render_template_string, request, session
from werkzeug.security import check_password_hash, generate_password_hash

# Rutas configurables. Por defecto, relativas al directorio de trabajo (la raíz
# del repo, tanto en la PC como en la Pi).
USERS_PATH = os.environ.get("VITAICARE_USERS", "users.json")
SECRET_PATH = os.environ.get("VITAICARE_SECRET", ".flask_secret")

# Rutas accesibles sin estar logueado.
PUBLIC_PREFIXES = ("/login", "/logout")


# --------------------------- almacén de usuarios ---------------------------
def _load_users() -> dict[str, str]:
    p = Path(USERS_PATH)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict[str, str]) -> None:
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    try:
        os.chmod(USERS_PATH, 0o600)  # solo el dueño puede leer los hashes
    except OSError:
        pass


def add_user(username: str, password: str) -> None:
    """Crea o actualiza un usuario con contraseña hasheada."""
    users = _load_users()
    users[username] = generate_password_hash(password)
    _save_users(users)


def delete_user(username: str) -> bool:
    users = _load_users()
    if username in users:
        del users[username]
        _save_users(users)
        return True
    return False


def list_users() -> list[str]:
    return sorted(_load_users().keys())


def user_exists(username: str) -> bool:
    return username in _load_users()


def verify(username: str, password: str) -> bool:
    """Valida credenciales contra el hash guardado."""
    stored = _load_users().get(username)
    return bool(stored and check_password_hash(stored, password))


# --------------------------- secret key persistente ---------------------------
def _get_secret_key() -> str:
    """Lee (o genera) una secret key estable para firmar las cookies de sesión.

    Persistirla evita que todos los usuarios queden deslogueados en cada
    reinicio del servicio.
    """
    p = Path(SECRET_PATH)
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    p.write_text(key, encoding="utf-8")
    try:
        os.chmod(SECRET_PATH, 0o600)
    except OSError:
        pass
    return key


# --------------------------- página de login ---------------------------
LOGIN_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VITAICARE - Ingreso</title>
  <style>
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; display:flex; align-items:center;
           justify-content:center; background:#222; color:#fff;
           font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
    .card { background:#303030; padding:2rem 2.25rem; border-radius:8px;
            width:100%; max-width:340px; box-shadow:0 6px 24px rgba(0,0,0,.4); }
    h1 { font-size:1.25rem; margin:0 0 1.25rem; text-align:center; }
    label { display:block; font-size:.85rem; margin:0 0 .25rem; color:#bbb; }
    input { width:100%; padding:.55rem .65rem; margin-bottom:1rem; border:none;
            border-radius:4px; background:#454545; color:#fff; font-size:1rem; }
    button { width:100%; padding:.6rem; border:none; border-radius:4px;
             background:#375a7f; color:#fff; font-size:1rem; cursor:pointer; }
    button:hover { background:#2b4763; }
    .error { background:#5a2b2b; border:1px solid #8b3a3a; color:#ffd5d5;
             padding:.55rem .65rem; border-radius:4px; margin-bottom:1rem;
             font-size:.85rem; text-align:center; }
  </style>
</head>
<body>
  <form class="card" method="post" action="/login">
    <h1>Residencia Asturiana</h1>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <label for="username">Usuario</label>
    <input id="username" name="username" autocomplete="username" autofocus required>
    <label for="password">Contraseña</label>
    <input id="password" name="password" type="password"
           autocomplete="current-password" required>
    <button type="submit">Ingresar</button>
  </form>
</body>
</html>
"""


# --------------------------- integración con la app ---------------------------
def init_auth(app) -> None:
    """Registra login/logout y el guard de sesión sobre el servidor Flask de Dash."""
    server = app.server
    server.secret_key = _get_secret_key()
    server.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    @server.route("/login", methods=["GET", "POST"])
    def login():
        error = ""
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            if verify(username, password):
                session["user"] = username
                return redirect("/")
            error = "Usuario o contraseña incorrectos."
        return render_template_string(LOGIN_HTML, error=error)

    @server.route("/logout")
    def logout():
        session.clear()
        return redirect("/login")

    @server.before_request
    def require_login():
        path = request.path
        if path.startswith(PUBLIC_PREFIXES):
            return None
        if session.get("user"):
            return None
        # Peticiones internas de Dash (XHR): devolver 401 en vez de redirigir.
        if path.startswith("/_dash") or path.startswith("/_reload"):
            return Response(status=401)
        return redirect("/login")
