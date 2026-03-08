from dash import Dash
import dash_bootstrap_components as dbc
from src.dash_app.layout import create_layout
from src.dash_app.callbacks import register_callbacks
from src.data_loader import load_all_data

# Pre cargo datos
print("Cargando datos...")
load_all_data()
print("Datos cargados.")

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True
)

app.layout = create_layout()
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
