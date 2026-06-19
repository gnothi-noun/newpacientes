# Despliegue en Raspberry Pi 4

Guía para correr el dashboard VITAICARE en una Raspberry Pi 4 (2 GB),
sin pantalla (headless), accediendo desde el navegador de otra PC en la red.

## Por qué Parquet en lugar del JSON

`RA.json` pesa ~444 MB. Cargarlo con `json.load` + pandas consume varios GB de
RAM, imposible en una Pi de 2 GB. Por eso convertimos los datos a **Parquet**
en la PC de desarrollo (con RAM de sobra) y copiamos a la Pi dos archivos
livianos y ya procesados que `pandas.read_parquet` abre rápido y con poca
memoria.

---

## Requisitos en la Raspberry

- **Raspberry Pi OS de 64 bits** (Bookworm). Importante: con 64 bits se
  instalan wheels precompiladas de pandas/numpy/pyarrow. Verificá con:
  ```bash
  uname -m      # debe decir: aarch64
  ```
- Python 3.11+ (viene con Bookworm) y git:
  ```bash
  sudo apt update && sudo apt install -y python3-venv python3-pip git
  ```

---

## Paso 0 — En tu PC: generar los Parquet

Con el entorno del proyecto activado y `RA.json` presente:

```bash
python convert_to_parquet.py
```

Genera `RA_patients.parquet` y `RA_wearable.parquet` en la carpeta del repo.

---

## Pasos 1 y 2 — Desplegar repo + datos con `deploy/deploy.ps1` (recomendado)

Desde PowerShell en Windows, un solo comando sincroniza el código **y** los
Parquet a la Pi (excluye `.venv`, `.git`, cachés y los datos crudos pesados
`RA.json`/`RA.sql`):

```powershell
.\deploy\deploy.ps1 -Address 192.168.0.50 -User pi
```

Esto deja todo en una ubicación determinista: `~/newpacientes` en la Pi
(`/home/<usuario>/newpacientes`). Opciones útiles:

```powershell
.\deploy\deploy.ps1 -Address raspberrypi.local -User rocio -DryRun   # previsualizar
.\deploy\deploy.ps1 -Address 192.168.0.50 -User pi -Port 2222 -IdentityFile C:\Users\Ro\.ssh\id_ed25519
```

### No requiere instalar nada

El script detecta automáticamente el mejor backend disponible:

1. **rsync nativo** (si está en PATH) — incremental, con `--delete`.
2. **rsync dentro de WSL** (si tenés WSL con rsync) — incremental.
3. **tar + scp** (por defecto) — usa `tar`, `scp` y `ssh`, ya integrados en
   Windows 10/11. **No hay que instalar nada.** Arma la lista de archivos con
   `git` (respeta `.gitignore`), empaqueta, copia el `.tgz` y lo extrae en la Pi.

> rsync es opcional: si lo instalás (`scoop install rsync` / `choco install
> rsync` / WSL) el script lo usa solo y gana sincronización incremental con
> borrado de obsoletos. El backend tar+scp **no** borra archivos viejos en la Pi.

### Alternativa manual (sin el script)

```bash
scp -r ./newpacientes pi@192.168.0.50:/home/pi/
scp RA_patients.parquet RA_wearable.parquet pi@192.168.0.50:/home/pi/newpacientes/
```

(O copiá los `.parquet` por pendrive a la raíz de `newpacientes` en la Pi.)
**No** copies `RA.json`: con los Parquet presentes la app los usa solos.

---

## Paso 3 — Crear el entorno virtual e instalar dependencias

En la Raspberry, dentro de la carpeta del repo:

```bash
cd /home/pi/newpacientes
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Paso 4 — Probar a mano

```bash
source .venv/bin/activate
python app.py
```

Debería imprimir `Cargando datos...` / `Datos cargados.` y levantar el servidor
en el puerto 8050. Desde otra PC en la misma red, abrí:

```
http://<IP-de-la-raspberry>:8050
```

Para conocer la IP de la Pi: `hostname -I`. Cortá con `Ctrl+C`.

---

## Paso 5 — Arranque automático (systemd)

1. Editá `deploy/vitaicare.service` y ajustá `User`, `WorkingDirectory` y la
   ruta de `ExecStart` a tu usuario y a la ruta real del repo.
2. Instalá y activá el servicio:
   ```bash
   sudo cp deploy/vitaicare.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now vitaicare
   ```
3. Comandos útiles:
   ```bash
   sudo systemctl status vitaicare      # estado
   journalctl -u vitaicare -f           # logs en vivo
   sudo systemctl restart vitaicare     # reiniciar
   ```

El servicio usa **gunicorn con 1 solo worker** a propósito (cada worker carga
los datos en RAM; más de uno haría OOM en 2 GB).

---

## Memoria: ampliar el swap (recomendado en 2 GB)

Aunque Parquet reduce muchísimo el consumo, conviene tener swap holgado:

```bash
sudo dphys-swapfile swapoff
sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

Verificá el uso real de RAM con `htop` la primera vez que cargue.

---

## Actualizar datos (cada vez que cambia RA.sql)

Flujo completo: `RA.sql → RA.json → RA_*.parquet → deploy → restart`.

Reemplazá `RA.sql` por el dump nuevo y, **en tu PC**, corré un solo comando:

```powershell
.\deploy\actualizar-datos.ps1
```

Hace los 4 pasos: parsea el SQL, genera los Parquet, los despliega a la Pi y
reinicia el servicio (para que limpie la caché y recargue los datos nuevos).
Tiene la IP y el usuario por defecto; para otra Pi: `-Address <ip> -User <user>`.

> Los pasos de parseo/conversión son pesados en RAM y por eso se hacen en la PC,
> no en la Pi. El `restart` es imprescindible: sin él, el dashboard sigue
> mostrando los datos viejos cacheados.

---

## Autenticación (usuario y contraseña)

La app pide login. Sin sesión válida, todo redirige a `/login`.

- Los usuarios viven en `users.json` (contraseñas **hasheadas**), gitignoreado:
  no se sube a git y el deploy **no lo pisa** en la Pi.
- **Solo el admin crea usuarios**, porque se hace por consola en la Pi (vía
  SSH, que solo vos tenés). No hay registro abierto en la web.

### Crear / listar / borrar usuarios (en la Pi)

```bash
ssh ro@192.168.1.88
cd ~/newpacientes
source .venv/bin/activate

python gestionar_usuarios.py add ro        # te pide la contraseña (oculta)
python gestionar_usuarios.py add medica
python gestionar_usuarios.py add tutor
python gestionar_usuarios.py add cotutor

python gestionar_usuarios.py list          # ver usuarios
python gestionar_usuarios.py delete tutor  # borrar uno
```

Agregar o borrar usuarios tiene efecto al instante (no hace falta reiniciar).
Solo hace falta reiniciar el servicio la **primera vez** que desplegás el
código con login.

> **Seguridad:** la app va por HTTP en la LAN, así que la contraseña viaja sin
> cifrar dentro de la red. Para una red institucional confiable suele alcanzar;
> si querés HTTPS (cifrado de punta a punta) se puede agregar después.

---

## Variables de entorno (opcional)

| Variable                        | Default                 | Descripción                         |
|---------------------------------|-------------------------|-------------------------------------|
| `PORT`                          | `8050`                  | Puerto del servidor.                |
| `HOST`                          | `0.0.0.0`               | Interfaz de escucha.                |
| `VITAICARE_PATIENTS_PARQUET`    | `RA_patients.parquet`   | Ruta al Parquet de pacientes.       |
| `VITAICARE_WEARABLE_PARQUET`    | `RA_wearable.parquet`   | Ruta al Parquet de serie temporal.  |
| `VITAICARE_JSON`                | `RA.json`               | JSON de respaldo (si no hay Parquet).|
| `VITAICARE_USERS`               | `users.json`            | Archivo de usuarios (hashes).       |
| `VITAICARE_SECRET`              | `.flask_secret`         | Secret key para firmar sesiones.    |
