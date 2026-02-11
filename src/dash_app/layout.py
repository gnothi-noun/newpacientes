"""Main layout with navigation and routing."""
from dash import html, dcc
import dash_bootstrap_components as dbc


def create_navbar():
    """Create navigation bar."""
    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand("VITAICARE", href="/", className="ms-2"),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Dashboard", href="/", active="exact")),
                dbc.NavItem(dbc.NavLink("Monitor Paciente", href="/patient", active="exact")),
            ], className="ms-auto", navbar=True)
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-0"
    )


def create_layout():
    """Create the main app layout with routing support."""
    return html.Div([
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='selected-patient-store', storage_type='session'),
        create_navbar(),
        html.Div(id='page-content', className="bg-dark", style={"minHeight": "calc(100vh - 56px)"})
    ], className="bg-dark")
