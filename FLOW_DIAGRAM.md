# VITAICARE - Application Flow Diagram

## 1. High-Level Architecture

```mermaid
graph TB
    subgraph DATA_SOURCE["Data Source"]
        RA_SQL["RA.sql<br/>(MySQL Dump)"]
        PARSE["parse_mysql_dump.py"]
        RA_JSON["RA.json<br/>(patients + wearabledata)"]
        RA_SQL -->|one-time conversion| PARSE --> RA_JSON
    end

    subgraph BACKEND["Backend (Python)"]
        APP["app.py<br/>(Entry Point)"]
        CONFIG["config.py<br/>(Metrics, IMEI, Thresholds)"]
        LOADER["data_loader.py<br/>(Load, Filter, Aggregate)"]
        CALLBACKS["callbacks.py<br/>(User Interactions)"]
        FIGURES["figures.py<br/>(Plotly Charts)"]
    end

    subgraph FRONTEND["Frontend (Dash)"]
        LAYOUT["layout.py<br/>(Navbar + Routing)"]
        DASHBOARD["dashboard.py<br/>(Home Page)"]
        PATIENT["patient_monitor.py<br/>(Detail Page)"]
        CSS["custom.css<br/>(Styles)"]
    end

    BROWSER["Browser<br/>localhost:8050"]

    RA_JSON --> LOADER
    CONFIG --> LOADER
    CONFIG --> FIGURES
    CONFIG --> DASHBOARD
    CONFIG --> PATIENT

    APP --> LOADER
    APP --> LAYOUT
    APP --> CALLBACKS

    CALLBACKS --> LOADER
    CALLBACKS --> FIGURES
    CALLBACKS --> DASHBOARD
    CALLBACKS --> PATIENT

    LAYOUT --> BROWSER
    DASHBOARD --> BROWSER
    PATIENT --> BROWSER
    CSS --> BROWSER
```

## 2. Application Startup Sequence

```mermaid
sequenceDiagram
    participant User
    participant App as app.py
    participant Loader as data_loader.py
    participant Layout as layout.py
    participant Callbacks as callbacks.py
    participant Browser

    User->>App: python app.py
    App->>Loader: load_all_data()
    Loader->>Loader: Read RA.json (cached with @lru_cache)
    Loader->>Loader: Convert timestamps UTC → Buenos Aires
    Loader-->>App: (patients_df, wearable_df)
    App->>Layout: create_layout()
    Layout-->>App: Dash HTML structure
    App->>Callbacks: register_callbacks(app)
    App->>Browser: Serve on port 8050
    Browser->>App: GET /
    App->>Callbacks: display_page("/")
    Callbacks->>Loader: get_patients_summary()
    Callbacks->>Loader: get_patients_with_alerts()
    Callbacks-->>Browser: Render Dashboard
```

## 3. Data Flow

```mermaid
flowchart LR
    subgraph STORAGE["Storage"]
        JSON["RA.json"]
    end

    subgraph LOADING["Data Loading (Cached)"]
        LOAD["load_all_data()"]
        PAT_DF["patients_df"]
        WEAR_DF["wearable_df"]
        LOAD --> PAT_DF
        LOAD --> WEAR_DF
    end

    subgraph PROCESSING["Data Processing"]
        GET_LIST["get_patient_list()"]
        GET_INFO["get_patient_info(id)"]
        GET_FILT["get_filtered_data()<br/>(imei, metric, dates)"]
        GET_SUMM["get_patients_summary()<br/>(last 7 days alerts)"]
        GET_ALERT["get_patients_with_alerts()"]
        GET_HIST["get_patient_alarm_history()"]
    end

    subgraph VISUALIZATION["Visualization"]
        OVERLAY["create_overlaid_figure()"]
        SUBPLOT["create_subplot_figure()"]
        STATS["calculate_stats()<br/>(min, max, avg)"]
    end

    JSON --> LOAD
    PAT_DF --> GET_LIST
    PAT_DF --> GET_INFO
    WEAR_DF --> GET_FILT
    WEAR_DF --> GET_SUMM
    GET_SUMM --> GET_ALERT
    WEAR_DF --> GET_HIST

    GET_FILT --> OVERLAY
    GET_FILT --> SUBPLOT
    GET_FILT --> STATS
```

## 4. Page Routing & Navigation

```mermaid
flowchart TD
    START["User opens localhost:8050"]
    ROUTER{"URL Router<br/>(display_page)"}
    DASH_PAGE["Dashboard Page (/)"]
    PAT_PAGE["Patient Monitor (/patient)"]

    START --> ROUTER
    ROUTER -->|"/"| DASH_PAGE
    ROUTER -->|"/patient"| PAT_PAGE

    subgraph DASHBOARD["Dashboard Page"]
        ALERTS["Alert Cards Panel<br/>(up to 6 critical patients)"]
        TABLE["Patients Summary Table<br/>(all patients + status)"]
        MODAL["Alarm History Modal"]
    end

    subgraph PATIENT_MONITOR["Patient Monitor Page"]
        SIDEBAR["Sidebar Filters"]
        INFO["Patient Info Card"]
        GRAPH["Interactive Graph"]
        STATS_P["Stats Panel<br/>(min/max/avg)"]
    end

    DASH_PAGE --> ALERTS
    DASH_PAGE --> TABLE
    TABLE -->|"Click History btn"| MODAL
    ALERTS -->|"Click alert card"| PAT_PAGE
    TABLE -->|"Click patient row"| PAT_PAGE
    MODAL -->|"Click 'Ver' btn"| PAT_PAGE

    PAT_PAGE --> SIDEBAR
    PAT_PAGE --> INFO
    PAT_PAGE --> GRAPH
    PAT_PAGE --> STATS_P
```

## 5. Callback Interaction Map

```mermaid
flowchart TD
    subgraph ROUTING["Routing Callbacks"]
        URL["URL Change"] --> DISP["display_page()"]
        DISP -->|"/"| RENDER_DASH["Render Dashboard"]
        DISP -->|"/patient"| RENDER_PAT["Render Patient Monitor"]
    end

    subgraph DASHBOARD_CB["Dashboard Callbacks"]
        RENDER_DASH --> UPD_DASH["update_dashboard()"]
        UPD_DASH --> ALERT_PANEL["Alerts Panel"]
        UPD_DASH --> PAT_TABLE["Patients Table"]

        CLICK{"User Clicks"}
        CLICK -->|"Alert Card"| NAV["navigate_to_patient()"]
        CLICK -->|"Patient Row"| NAV
        CLICK -->|"History Button"| TOGGLE_MODAL["toggle_alarm_history_modal()"]
        NAV -->|"Set patient + alarm context"| REDIR["/patient redirect"]

        TOGGLE_MODAL --> POP_HIST["populate_alarm_history()"]
        LOAD_MORE["'Cargar semana anterior'<br/>button"] --> MORE_WEEKS["load_more_weeks()"]
        MORE_WEEKS --> POP_HIST
        POP_HIST -->|"Click 'Ver'"| NAV_ALARM["navigate_from_alarm()"]
        NAV_ALARM -->|"Set alarm context"| REDIR
    end

    subgraph PATIENT_CB["Patient Monitor Callbacks"]
        REDIR --> UPD_INFO["update_patient_info()"]
        UPD_INFO --> INFO_CARD["Patient Info Card"]
        UPD_INFO --> DATE_DEFAULTS["Date/Time Defaults"]
        UPD_INFO --> METRIC_DEFAULTS["Metric Defaults"]

        FILTERS{"Filter Changes"}
        FILTERS -->|"Date range"| UPD_GRAPH["update_graph()"]
        FILTERS -->|"Time range"| UPD_GRAPH
        FILTERS -->|"Metrics"| UPD_GRAPH
        FILTERS -->|"View mode"| UPD_GRAPH

        UPD_GRAPH --> CHART["Plotly Figure"]
        UPD_GRAPH --> STATS_OUT["Stats Panel"]
    end
```

## 6. Alert Detection Flow

```mermaid
flowchart TD
    DATA["Wearable Data<br/>(last 7 days)"] --> CHECK{"For each patient<br/>& metric"}

    CHECK --> COMPARE["Compare value vs<br/>normal range"]

    subgraph RANGES["Normal Ranges (config.py)"]
        HR["HR: 50-120 bpm"]
        SPO2["SpO2: 70-100%"]
        SBP["Systolic: 90-140 mmHg"]
        DBP["Diastolic: 60-90 mmHg"]
        TEMP["Temp: 30-38 C"]
    end

    COMPARE --> LOW{"value < min?"}
    COMPARE --> HIGH{"value > max?"}

    LOW -->|Yes| ALERT_LOW["Alert: LOW"]
    HIGH -->|Yes| ALERT_HIGH["Alert: HIGH"]
    LOW -->|No| OK
    HIGH -->|No| OK["OK"]

    ALERT_LOW --> CARD["Alert Card<br/>(Dashboard)"]
    ALERT_HIGH --> CARD
    CARD -->|"Click"| MONITOR["Patient Monitor<br/>with alarm marker"]
    MONITOR --> MARKER["Red X on graph<br/>at alarm point"]
```

## 7. Session Data Flow

```mermaid
flowchart LR
    subgraph SESSION["dcc.Store (Session Storage)"]
        PAT_STORE["selected-patient-store<br/>(patient_id)"]
        ALARM_STORE["alarm-context-store<br/>(date, metric, value)"]
        HIST_STORE["alarm-history-patient<br/>(patient_id for modal)"]
        WEEKS_STORE["alarm-history-weeks<br/>(number of weeks)"]
        LIST_STORE["alarm-history-list<br/>(alarm records)"]
    end

    DASH_CLICK["Dashboard Click"] -->|"Set patient_id"| PAT_STORE
    DASH_CLICK -->|"Set alarm details"| ALARM_STORE

    PAT_STORE -->|"Load patient info"| PAT_MONITOR["Patient Monitor"]
    ALARM_STORE -->|"Preset date/metric/marker"| PAT_MONITOR

    HIST_CLICK["History Button"] -->|"Set patient_id"| HIST_STORE
    HIST_STORE -->|"Load alarms"| MODAL["Alarm History Modal"]
    WEEKS_STORE -->|"Filter time range"| MODAL
    MODAL -->|"Store alarm list"| LIST_STORE
    LIST_STORE -->|"Navigate with context"| ALARM_STORE
```

## 8. File Dependency Graph

```mermaid
graph TD
    APP["app.py"] --> LAYOUT["src/dash_app/layout.py"]
    APP --> CALLBACKS["src/dash_app/callbacks.py"]
    APP --> LOADER["src/data_loader.py"]

    CALLBACKS --> LOADER
    CALLBACKS --> FIGURES["src/dash_app/figures.py"]
    CALLBACKS --> DASHBOARD["src/dash_app/pages/dashboard.py"]
    CALLBACKS --> PATIENT["src/dash_app/pages/patient_monitor.py"]

    LOADER --> CONFIG["src/config.py"]
    FIGURES --> CONFIG
    DASHBOARD --> CONFIG
    PATIENT --> CONFIG
    PATIENT --> LOADER

    LAYOUT --> |"dash, dbc"| DASH_LIBS["Dash / Bootstrap"]
    FIGURES --> PLOTLY["Plotly"]
    LOADER --> PANDAS["Pandas"]

    style APP fill:#e74c3c,color:#fff
    style CONFIG fill:#f39c12,color:#fff
    style LOADER fill:#3498db,color:#fff
    style CALLBACKS fill:#9b59b6,color:#fff
    style FIGURES fill:#2ecc71,color:#fff
    style DASHBOARD fill:#1abc9c,color:#fff
    style PATIENT fill:#1abc9c,color:#fff
    style LAYOUT fill:#1abc9c,color:#fff
```

## 9. Monitored Metrics Overview

| Metric | Name (Spanish) | Unit | Normal Range | Color |
|--------|---------------|------|-------------|-------|
| `heart_rate` | Frecuencia Cardiaca | bpm | 50 - 120 | ![#FF6B6B](https://placehold.co/15x15/FF6B6B/FF6B6B.png) |
| `blood_oxygen_saturation` | Saturacion O2 | % | 70 - 100 | ![#4ECDC4](https://placehold.co/15x15/4ECDC4/4ECDC4.png) |
| `systolic_blood_pressure` | Presion Sistolica | mmHg | 90 - 140 | ![#45B7D1](https://placehold.co/15x15/45B7D1/45B7D1.png) |
| `diastolic_blood_pressure` | Presion Diastolica | mmHg | 60 - 90 | ![#96CEB4](https://placehold.co/15x15/96CEB4/96CEB4.png) |
| `temperature` | Temperatura | C | 30 - 38 | ![#FFEAA7](https://placehold.co/15x15/FFEAA7/FFEAA7.png) |
| `daily_activity_steps` | Pasos Diarios | steps | 0+ | ![#DDA0DD](https://placehold.co/15x15/DDA0DD/DDA0DD.png) |
