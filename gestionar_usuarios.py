#!/usr/bin/env python3
"""Gestion de usuarios de la app VITAICARE (crear / listar / eliminar).

Se corre desde la raiz del repo (escribe/lee users.json en el dir actual).
Pensado para ejecutarse por SSH en la Raspberry: como solo el admin tiene
acceso SSH, solo el admin puede crear usuarios.

Ejemplos:
    python gestionar_usuarios.py add ro
    python gestionar_usuarios.py list
    python gestionar_usuarios.py delete medica
"""
from __future__ import annotations

import argparse
import getpass
import sys

from src.auth import add_user, delete_user, list_users, user_exists, rename_user


def _cmd_add(username: str) -> int:
    if user_exists(username):
        print(f"El usuario '{username}' ya existe: se actualizara su contrasena.")
    pw = getpass.getpass("Contrasena nueva: ")
    pw2 = getpass.getpass("Repetir contrasena: ")
    if pw != pw2:
        print("Las contrasenas no coinciden.")
        return 1
    if len(pw) < 6:
        print("Usa al menos 6 caracteres.")
        return 1
    add_user(username, pw)
    print(f"Usuario '{username}' guardado.")
    return 0


def _cmd_list() -> int:
    users = list_users()
    if not users:
        print("No hay usuarios todavia. Crea uno con:  python gestionar_usuarios.py add <usuario>")
        return 0
    print("Usuarios:")
    for u in users:
        print(f"  - {u}")
    return 0


def _cmd_delete(username: str) -> int:
    if delete_user(username):
        print(f"Usuario '{username}' eliminado.")
        return 0
    print(f"No existe el usuario '{username}'.")
    return 1


def _cmd_rename(old: str, new: str) -> int:
    if not user_exists(old):
        print(f"No existe el usuario '{old}'.")
        return 1
    if user_exists(new):
        print(f"Ya existe un usuario '{new}'. Elegi otro nombre.")
        return 1
    rename_user(old, new)
    print(f"Usuario '{old}' renombrado a '{new}' (conserva su contrasena).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Gestion de usuarios de VITAICARE.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Crear o actualizar un usuario (pide la contrasena).")
    p_add.add_argument("username")

    sub.add_parser("list", help="Listar usuarios existentes.")

    p_del = sub.add_parser("delete", help="Eliminar un usuario.")
    p_del.add_argument("username")

    p_ren = sub.add_parser("rename", help="Renombrar un usuario (conserva la contrasena).")
    p_ren.add_argument("old", help="nombre actual")
    p_ren.add_argument("new", help="nombre nuevo")

    args = parser.parse_args()

    if args.cmd == "add":
        return _cmd_add(args.username)
    if args.cmd == "list":
        return _cmd_list()
    if args.cmd == "delete":
        return _cmd_delete(args.username)
    if args.cmd == "rename":
        return _cmd_rename(args.old, args.new)
    return 1


if __name__ == "__main__":
    sys.exit(main())
