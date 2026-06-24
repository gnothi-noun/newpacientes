import os
from dash import Dash
import dash_bootstrap_components as dbc
from src.dash_app.layout import create_layout
from src.dash_app.callbacks import register_callbacks
from src.data_loader import load_all_data, get_patients_summary
from src.auth import init_auth

# Pre cargo datos
print("Cargando datos...")
load_all_data()
# Precaliento el resumen del dashboard (cálculo pesado y cacheado): así la
# primera visita al dashboard ya es instantánea en vez de tardar varios seg.
print("Precalculando resumen del dashboard...")
get_patients_summary()
# Precaliento el análisis (línea base + tendencias) por la misma razón.
print("Precalculando análisis de tendencias...")
from src.analytics import get_analysis_overview
get_analysis_overview()
print("Datos cargados.")

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True
)

app.layout = create_layout()
register_callbacks(app)

# Login por usuario/contraseña (protege toda la app).
init_auth(app)

# Servidor WSGI expuesto para gunicorn (systemd) -> "app:server".
server = app.server

if __name__ == "__main__":
    # Ejecución directa (desarrollo o arranque manual en la Raspberry).
    # HOST=0.0.0.0 permite acceder desde otra PC en la red: http://<ip-rasp>:8050
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
