---
name: raspberry-deployment
description: Cómo y dónde está desplegada la app VITAICARE (Raspberry Pi, acceso remoto)
metadata:
  type: project
---

La app se despliega en una **Raspberry Pi 4 (2 GB)** llamada `pececito`, usuario `ro`, IP LAN `192.168.1.88` (acceso SSH con clave, sin contraseña).

- **Datos:** RA.sql → (parse_mysql_dump.py) → RA.json → (convert_to_parquet.py) → RA_*.parquet. En la Pi de 2 GB se cargan los Parquet (no el JSON, que haría OOM). Todo el pipeline + deploy + restart se corre con `deploy/actualizar-datos.ps1` desde la PC Windows.
- **Servicio:** gunicorn (1 worker) vía systemd (`vitaicare.service`), puerto 8050, autostart. Reiniciar tras desplegar datos nuevos para limpiar la caché (`get_patients_summary` usa `@lru_cache`).
- **Deploy:** `deploy/deploy.ps1` desde Windows; usa tar+scp (no rsync). Excluye `.venv`/`RA.json`/`RA.sql`; manda los Parquet.
- **Login:** usuarios en `users.json` (hashes werkzeug, gitignored), administrados con `gestionar_usuarios.py` por SSH. Secret de sesión en `.flask_secret`.
- **Acceso remoto:** rpi-connect (terminal de la admin, vía connect.raspberrypi.com). El dashboard sale público en `https://vitaicare.whittileaks.com` (HTTPS, protegido por el login). La Pi y la laptop `msi` están en la misma tailnet de Tailscale (IPs 100.99.247.65 y 100.86.97.72).

Pendiente verificado a medias: que el túnel que expone el dominio arranque solo tras `reboot`.
