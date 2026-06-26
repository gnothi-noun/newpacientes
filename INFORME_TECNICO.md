# INFORME TÉCNICO DEL PROYECTO VITAICARE
## Interfaz de Visualización de Datos Biométricos para Monitoreo de Adultos Mayores Institucionalizados

---

**Estudiante:** Rocío Pesoa
**Carrera:** Ingeniería en Bioingeniería
**Institución:** Instituto Tecnológico de Buenos Aires (ITBA)
**Tutor:** Dr. Miguel Aguirre (ITBA)
**Co-tutora:** Ing. Melisa Granda (UAH)
**Colaboradora:** Giuliana Espósito
**Última actualización:** 24 de junio de 2026
**Período de Desarrollo:** Noviembre 2024 - Abril 2025
**Versión del documento:** 2.0

---

## ÍNDICE

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Contexto del Proyecto](#2-contexto-del-proyecto)
3. [Objetivos del Proyecto](#3-objetivos-del-proyecto)
4. [Arquitectura del Sistema](#4-arquitectura-del-sistema)
5. [Pipeline de Datos (SQL → JSON → Parquet → App)](#5-pipeline-de-datos)
6. [Tecnologías Implementadas](#6-tecnologías-implementadas)
7. [Configuración Centralizada (`config.py`)](#7-configuración-centralizada)
8. [Fuentes y Realidad de los Datos](#8-fuentes-y-realidad-de-los-datos)
9. [Sistema de Alarmas](#9-sistema-de-alarmas)
10. [Módulo de Análisis: Línea Base y Tendencias](#10-módulo-de-análisis)
11. [Componentes de Visualización](#11-componentes-de-visualización)
12. [Informes Descargables (PDF / CSV)](#12-informes-descargables)
13. [Autenticación y Seguridad](#13-autenticación-y-seguridad)
14. [Estructura de la Aplicación Dash](#14-estructura-de-la-aplicación-dash)
15. [Despliegue en Raspberry Pi y Acceso Remoto](#15-despliegue-en-raspberry-pi)
16. [Desafíos Técnicos y Decisiones de Ingeniería](#16-desafíos-técnicos)
17. [Resultados y Estado Actual](#17-resultados-y-estado-actual)
18. [Trabajo Futuro](#18-trabajo-futuro)
19. [Conclusiones](#19-conclusiones)
20. [Referencias y Recursos](#20-referencias-y-recursos)
- [Anexos](#anexos)

---

## 1. RESUMEN EJECUTIVO

VITAICARE es una interfaz web interactiva para la visualización y el análisis de datos biométricos obtenidos mediante smartwatches ID Vita, dirigida al equipo médico de la Residencia Asturiana de Buenos Aires. El sistema permite el monitoreo temporal de variables fisiológicas de adultos mayores institucionalizados, facilitando la detección temprana de cambios en el estado de salud y mejorando la toma de decisiones clínicas.

Respecto de la versión inicial (un visualizador de series temporales con filtros), el sistema evolucionó hasta convertirse en una **aplicación de monitoreo completa y desplegada en producción** sobre una Raspberry Pi, con los siguientes subsistemas nuevos:

- **Pipeline de datos en tres etapas** (`RA.sql` → `RA.json` → Parquet) que reduce el dataset de ~520 MB a ~10 MB y permite cargar 2,36 millones de registros con ~280 MB de RAM, requisito indispensable para correr en una Raspberry Pi de 2 GB.
- **Sistema de alarmas** con detección por umbral, enfriamiento (*cooldown*) de 1 hora y agrupación de eventos consecutivos.
- **Módulo de análisis** con línea base personalizada (banda circadiana p10–p90 por paciente) y tendencias semanales con detección de deterioro sostenido (alerta temprana).
- **Generación de informes descargables** en PDF (con `fpdf2` + `matplotlib`) y CSV.
- **Autenticación por usuario y contraseña** con sesiones de Flask y gestión de usuarios por CLI.
- **Despliegue en producción**: `gunicorn` + `systemd` en una Raspberry Pi 4, con acceso remoto vía Tailscale (VPN) y exposición pública HTTPS mediante Tailscale Funnel con dominio propio.

### Logros Principales (estado actual)

- **Interfaz web funcional** con dashboard de cohorte y monitor por paciente.
- **Procesamiento de 2.363.501 registros** biométricos de 22 pacientes monitorizados (26 registros de paciente en total en la tabla `patients`).
- **6 métricas fisiológicas** parametrizadas, con umbrales ajustables por el equipo médico.
- **Detección y agrupación de alarmas**, con historial navegable y enlace directo al gráfico del evento.
- **Análisis de patrones personales y tendencias** para alerta temprana de deterioro.
- **Informes clínicos exportables** (PDF/CSV) por paciente y de cohorte.
- **Manejo correcto de zonas horarias** (UTC → America/Argentina/Buenos_Aires).
- **Sistema desplegado y accesible de forma segura** desde fuera de la institución.

> **Nota metodológica importante:** todos los umbrales clínicos (rangos normales, límites de plausibilidad, pendientes de tendencia) son **valores por defecto razonables, NO validados clínicamente**. Están centralizados y parametrizados para que la tutora y el equipo médico los ajusten. Este informe lo recalca en cada sección correspondiente.

---

## 2. CONTEXTO DEL PROYECTO

### 2.1 Problemática

Los adultos mayores institucionalizados requieren monitoreo clínico cercano para detectar cambios en su salud de manera temprana. Actualmente, los equipos médicos trabajan con información fragmentada en diferentes sistemas, con limitada explotación sistemática de datos.

### 2.2 Solución Propuesta

Desarrollo de una interfaz de usuario clara, usable y clínicamente relevante que permita:

1. Visualizar la evolución temporal de variables fisiológicas de cada residente.
2. Identificar desviaciones de patrones habituales (no solo de umbrales genéricos, sino del patrón propio del paciente).
3. Relacionar cambios en variables con eventos clínicos relevantes.
4. Detectar alarmas y tendencias de deterioro de forma automática.

### 2.3 Colaboradores

- **Universidad de Alcalá (UAH)**, España
- **Equipo médico de Residencia Asturiana** de Buenos Aires
- **Instituto Tecnológico de Buenos Aires (ITBA)**

---

## 3. OBJETIVOS DEL PROYECTO

### 3.1 Objetivo General

Diseñar, implementar y evaluar una interfaz de usuario para visualizar variables fisiológicas y parámetros de actividad registrados por smartwatches en adultos mayores institucionalizados.

### 3.2 Objetivos Específicos Cumplidos

- **Organización de dispositivos:** sistema de trazabilidad mediante mapeo IMEI–Paciente (22 dispositivos con datos; ver `config.py::IMEI`).
- **Recolección de requerimientos:** identificación de variables prioritarias y rangos temporales óptimos; ajuste de umbrales a pedido médico (p. ej. mínimo de temperatura).
- **Arquitectura funcional:** definición de módulos, vistas principales (Dashboard y Monitor) y conjunto de indicadores.
- **Prototipo funcional:** interfaz que permite visualización, alarmas, análisis e informes.
- **Integración de datos:** conexión con el volcado de la base de datos de la Residencia Asturiana mediante un pipeline reproducible.
- **(Objetivo de máxima — escalabilidad)** despliegue real y reproducible sobre hardware de bajo costo (Raspberry Pi), con recomendaciones documentadas para escalar a otros centros.

---

## 4. ARQUITECTURA DEL SISTEMA

### 4.1 Diagrama de Capas

```
┌────────────────────────────────────────────────────────────────────────┐
│ CAPA DE PRESENTACIÓN  (Dash 3 + dash-bootstrap-components, tema DARKLY)  │
│  ┌──────────────────────────┐   ┌────────────────────────────────────┐  │
│  │ Dashboard (cohorte)      │   │ Monitor Paciente (individual)      │  │
│  │ - Panel de alertas       │   │ - Sidebar: filtros + descarga      │  │
│  │ - Tabla resumen          │   │ - Gráfico principal (Plotly)       │  │
│  │ - Modal historial alarmas│   │ - Estadísticas                     │  │
│  │ - Descargar resumen      │   │ - Tendencias y patrones (Collapse) │  │
│  └──────────────────────────┘   └────────────────────────────────────┘  │
│        Login (Flask) intercepta toda petición sin sesión válida          │
└───────────────────────────────────┬──────────────────────────────────────┘
                                     │  callbacks (Python, reactivos)
┌───────────────────────────────────┴──────────────────────────────────────┐
│ CAPA DE LÓGICA / DOMINIO                                                   │
│  data_loader.py  → carga, filtrado, gaps, detección de alarmas            │
│  analytics.py    → línea base personal + tendencias semanales             │
│  reports.py      → PDF/CSV (matplotlib Agg + fpdf2)                       │
│  auth.py         → login, sesiones, guard de rutas                        │
│  figures.py      → construcción de figuras Plotly                         │
│  (caché en memoria con functools.lru_cache en todas las funciones caras)  │
└───────────────────────────────────┬──────────────────────────────────────┘
                                     │
┌───────────────────────────────────┴──────────────────────────────────────┐
│ CAPA DE DATOS                                                              │
│  RA_patients.parquet  (~7,6 KB)     ← preferido en producción             │
│  RA_wearable.parquet  (~10 MB, snappy)                                     │
│  RA.json (~520 MB)                   ← respaldo solo en desarrollo         │
└────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Flujo de Datos de Extremo a Extremo

```
  Smartwatch ID Vita
        │  (mediciones cada ~5 min)
        ▼
  MySQL/MariaDB (Residencia Asturiana)
        │  mysqldump
        ▼
  RA.sql (~495–519 MB)
        │  parse_mysql_dump.py  (parser streaming línea por línea)
        ▼
  RA.json (~520 MB)
        │  convert_to_parquet.py + data_loader.build_dataframes()
        │   - conserva solo columnas usadas de wearable
        │   - UTC → America/Argentina/Buenos_Aires
        │   - value → numérico
        ▼
  RA_patients.parquet  +  RA_wearable.parquet  (snappy)
        │  deploy/deploy.ps1  (tar + scp / rsync)  →  Raspberry Pi
        ▼
  data_loader.load_all_data()  (@lru_cache, read_parquet)
        │
        ├─► get_patients_summary / alarmas  ──► Dashboard
        ├─► get_filtered_data               ──► figures.py ──► Monitor
        ├─► analytics.get_analysis_overview ──► línea base + tendencias
        └─► reports.py                      ──► PDF / CSV descargables
```

El pre-procesamiento pesado (parseo y conversión a Parquet) se ejecuta **en la PC de desarrollo**, donde sobra RAM. La Raspberry Pi sólo lee los Parquet ya procesados.

---

## 5. PIPELINE DE DATOS

Esta es la pieza central de ingeniería que habilita el despliegue en hardware de bajo costo. El pipeline transforma un volcado SQL de medio gigabyte en dos archivos columnar livianos.

### 5.1 Etapa 1 — `RA.sql` → `RA.json` (`parse_mysql_dump.py`)

El volcado MySQL (`mysqldump`) pesa cientos de megabytes y no puede cargarse íntegro en memoria con seguridad. `parse_mysql_dump.py` implementa un **parser streaming que recorre el archivo línea por línea**, sin cargarlo completo:

- `parse_mysql_dump(filepath)` itera el archivo y reconoce dos tipos de sentencia:
  - `CREATE TABLE` → `parse_create_table()` extrae el nombre de la tabla y la lista de columnas (vía expresiones regulares sobre las definiciones de columna ``` `col` tipo ```).
  - `INSERT INTO` → `extract_insert_data()` es un *generador* que produce un `dict` por fila.
- `extract_insert_data()` y `parse_values()` implementan un **analizador de estados a mano** (no un `split` ingenuo) que respeta:
  - comillas simples dentro de cadenas (`in_string`),
  - escapes con `\` (`escape_next`),
  - comillas escapadas `''`,
  - paréntesis anidados y separadores `),(` que pertenecen a strings.
  Esto evita romper filas que contienen comas o paréntesis dentro de valores de texto.
- `parse_value()` convierte cada token a tipo Python: `NULL` → `None`, cadenas entre comillas → `str` (des-escapado), y números → `int`/`float`.
- Se cuentan y reportan las filas descartadas por desajuste de columnas (`rows_skipped`), útil para auditar la integridad del volcado.
- `convert_dump_to_json()` serializa el `dict` resultante a `RA.json` con `json.dump(..., default=str)` (los `datetime` se guardan como texto).

**Uso:** `python parse_mysql_dump.py RA.sql` (o sin argumento, toma `RA.sql` por defecto).

### 5.2 Etapa 2 — `RA.json` → Parquet (`convert_to_parquet.py` + `data_loader.build_dataframes`)

`build_dataframes(data)` (en `data_loader.py`) es la **única fuente de pre-procesamiento**, compartida entre el camino JSON en vivo y el script de conversión, garantizando que ambos produzcan exactamente lo mismo:

1. Construye `patients_df` y `wearable_df` desde el `dict` crudo.
2. **Reduce columnas** de `wearabledata` a las realmente usadas: `["imei", "metric", "record_datetime", "value"]` (`WEARABLE_COLUMNS`). Descartar el resto es clave para el consumo de memoria.
3. **Convierte la zona horaria**: `record_datetime` se interpreta como UTC (`tz_localize("UTC")`) y se convierte a `America/Argentina/Buenos_Aires` (`tz_convert`).
4. **Normaliza `value`** a numérico con `pd.to_numeric(errors="coerce")` (los no convertibles quedan `NaN`).

`convert_to_parquet.py` carga `RA.json`, llama a `build_dataframes()` y escribe:

- `RA_patients.parquet` con `compression="snappy"`,
- `RA_wearable.parquet` con `compression="snappy"`.

**Uso:** `python convert_to_parquet.py` (rutas configurables por `VITAICARE_JSON`, `VITAICARE_PATIENTS_PARQUET`, `VITAICARE_WEARABLE_PARQUET`).

### 5.3 Etapa 3 — Carga en la aplicación (`data_loader.load_all_data`)

```python
@lru_cache(maxsize=1)
def load_all_data():
    if os.path.exists(PARQUET_PATIENTS) and os.path.exists(PARQUET_WEARABLE):
        return pd.read_parquet(PARQUET_PATIENTS), pd.read_parquet(PARQUET_WEARABLE)
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    return build_dataframes(data)
```

- **Prefiere los Parquet** (rápidos y livianos); sólo cae al JSON si no existen (escenario de desarrollo).
- `@lru_cache(maxsize=1)` garantiza una sola carga por proceso: la primera consulta paga el costo, las siguientes son instantáneas.
- Rutas configurables por variables de entorno (`VITAICARE_*`).

### 5.4 Por qué Parquet — la decisión de ingeniería clave

| Métrica | JSON (`RA.json`) | Parquet (`RA_wearable.parquet`) |
|---|---|---|
| Tamaño en disco | ~520 MB | ~10 MB |
| RAM para tener el DataFrame en memoria | varios GB con `json.load` (provoca **OOM** en 2 GB) | ~280 MB |
| Tiempo de carga en la Pi | inviable | segundos |
| Columnas almacenadas | todas | sólo 4 usadas |

**Motivo concreto:** cargar el JSON con `json.load` en una Raspberry Pi de 2 GB agota la memoria (Out-Of-Memory). El formato columnar Parquet con compresión *snappy*, tras descartar columnas innecesarias, hace que el DataFrame completo de **2.363.501 filas** entre en memoria con un consumo modesto. Esta reducción de ~520 MB a ~10 MB en disco (y de varios GB a ~280 MB en RAM) es lo que hace posible el despliegue en hardware de bajo costo.

---

## 6. TECNOLOGÍAS IMPLEMENTADAS

### 6.1 Stack y Versiones (de `requirements.txt`, fijadas y validadas)

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.11+ (Pi) / 3.x (desarrollo) | Lenguaje principal |
| **dash** | 3.3.0 | Framework web reactivo |
| **dash-bootstrap-components** | 2.0.4 | Componentes UI (tema DARKLY) |
| **pandas** | 2.3.3 | Manipulación de series temporales |
| **plotly** | 6.5.2 | Gráficos interactivos |
| **pyarrow** | 18.1.0 | Lectura/escritura de Parquet |
| **gunicorn** | 23.0.0 | Servidor WSGI de producción (systemd) |
| **fpdf2** | 2.8.7 | Generación de PDF (pura-Python) |
| **matplotlib** | 3.10.8 | Gráficos de los informes (backend "Agg") |
| **Flask / Werkzeug** | (deps. de Dash) | Servidor base + hashing de contraseñas |
| **numpy** | (dep. de pandas) | Cálculos del módulo de análisis |

Todas las dependencias tienen *wheels* precompiladas para Raspberry Pi OS de 64 bits (`aarch64`), evitando compilaciones en la Pi. `streamlit`, `weasyprint` y `markdown` se excluyeron a propósito: sólo los usan scripts auxiliares y no hacen falta para correr el dashboard, manteniendo liviana la instalación en la Pi.

### 6.2 Justificación de Elecciones

- **Dash + Plotly:** diseñado para aplicaciones analíticas; integración nativa de gráficos científicos interactivos sin escribir JavaScript; arquitectura reactiva por *callbacks*.
- **Parquet (pyarrow):** formato columnar comprimido, lectura rápida y bajo consumo de RAM (ver §5.4).
- **gunicorn (1 worker):** servidor WSGI estable de producción; un solo worker por la restricción de memoria (ver §15).
- **fpdf2 + matplotlib Agg:** generación de PDF e imágenes sin dependencias de sistema pesadas ni *display* (headless), apropiado para la Pi.

---

## 7. CONFIGURACIÓN CENTRALIZADA

Todo lo parametrizable vive en `src/config.py`, de modo que el equipo médico pueda ajustar umbrales sin tocar la lógica.

### 7.1 Métricas (`METRICS`)

| Clave | Nombre | Color | Unidad | normal_min | normal_max |
|-------|--------|-------|--------|-----------|-----------|
| `heart_rate` | Frecuencia Cardíaca | `#E06464` | bpm | 50 | 120 |
| `blood_oxygen_saturation` | Saturación O2 | `#A268BA` | % | 80 | 100 |
| `systolic_blood_pressure` | Presión Sistólica | `#68c2f6` | mmHg | 90 | 140 |
| `diastolic_blood_pressure` | Presión Diastólica | `#8eb69b` | mmHg | 60 | 90 |
| `temperature` | Temperatura | `#FFEAA7` | °C | 25.0 | 38.0 |
| `daily_activity_steps` | Pasos Diarios | `#DDA0DD` | pasos | 0 | (sin máx.) |

> El mínimo de temperatura se ajustó de 33 °C a **25 °C a pedido del equipo médico**, para no marcar como alarma lecturas bajas habituales del sensor periférico. Los pasos no tienen máximo definido.

### 7.2 Estructuras de Dominio

- **`Alarm` (dataclass):** representa una alarma con `patient_id, metric_key, value, timestamp, alert_type` y metadatos (`metric_name, unit, color`). Métodos: `formatted_date`, `to_context()`/`from_context()` (serialización a/desde `dcc.Store`, cruzando la frontera JSON), y `from_row()` (construcción desde una fila del DataFrame).
- **`AlertType` (Enum):** `LOW` / `HIGH` / `BOTH`, con `display_name` en español ("Bajo" / "Alto" / "Ambos").

### 7.3 Configuración Temporal (`TimeConfig` / `CFG`)

- `sample_period_minutes = 5`
- `gap_threshold_minutes = 5`
- `tz = "America/Argentina/Buenos_Aires"`
- **`alarm_cooldown_minutes = 60`** — enfriamiento de alarmas (ver §9).

### 7.4 Configuración de Análisis (`AnalyticsConfig` / `ACFG`)

- `ANALYSIS_METRICS = ("heart_rate", "blood_oxygen_saturation", "temperature")` — a propósito **sin pasos ni presión**.
- `PLAUSIBILITY`: límites de descarte de artefactos — FC `(30, 200)`, SpO2 `(70, 100)`, temperatura `(28, 43)`.
- `ADVERSE_DIRECTION`: dirección clínicamente adversa — FC `+1` (subir es malo), SpO2 `-1` (bajar es malo), temperatura `+1`.
- `SLOPE_THRESHOLDS`: pendiente mínima por semana para marcar tendencia adversa — FC `1.5` bpm/sem, SpO2 `0.5` %/sem, temperatura `0.1` °C/sem.
- Parámetros de banda/tendencia: percentiles `p10`/`p90`, `circadian_bucket_hours = 2`, `baseline_min_readings = 200`, `baseline_bucket_min = 20`, ventana nocturna `00:00–06:00`, `trend_weeks = 4`, `trend_min_weeks = 3`.

> **Todos** estos umbrales son *defaults* razonables, **NO validados clínicamente**, parametrizados para ajuste por el equipo médico (comentado explícitamente en el código fuente).

---

## 8. FUENTES Y REALIDAD DE LOS DATOS

### 8.1 Hardware y Sensores

**Dispositivo:** ID Vita – Telecare Smartwatch (Intelligent Data). Sensores: PPG (frecuencia cardíaca), oximetría de pulso (SpO2), temperatura, presión arterial y acelerómetro (pasos). Frecuencia de muestreo: ~5 minutos.

### 8.2 Estructura del Volcado (`RA.sql` / `RA.json`)

Tablas presentes en el volcado de la Residencia Asturiana:

| Tabla | Filas | Observación |
|-------|------:|-------------|
| `patients` | 26 (11 columnas) | 22 con datos de wearable asociados |
| `wearabledata` | 2.363.501 | serie temporal de signos vitales |
| `perceivedhealthdata` | 122 | estado autopercibido (no usado en la app actual) |
| `clinicalevents` | 0 | vacía en el volcado |
| `labresults` | 0 | vacía en el volcado |
| `sessionresults` | 0 | vacía en el volcado |

**Distribución de `wearabledata` por métrica** (verificada sobre el Parquet):

| Métrica | Registros |
|---------|----------:|
| temperature | 468.589 |
| diastolic_blood_pressure | 468.589 |
| systolic_blood_pressure | 468.588 |
| heart_rate | 468.587 |
| blood_oxygen_saturation | 468.587 |
| daily_activity_steps | 20.561 |

Esquema mínimo conservado en `RA_wearable.parquet`: `imei, metric, record_datetime, value`. El rango temporal de registros abarca desde 2023 hasta junio de 2026 en el volcado actual, con aproximadamente **6 meses de datos densos por paciente** y muestreo de ~5 minutos.

### 8.3 Limitaciones de los datos que condicionan el análisis

Estas observaciones son relevantes para la interpretación clínica y la redacción de la tesis:

- **Comorbilidades vacías:** `charlson_index`, `barthel_index` y `latest_hemodialysis_date` están vacíos; `diabetes_mellitus` es 0 para todos. No es posible estratificar por comorbilidad.
- **Edad poco confiable:** las fechas de nacimiento son *placeholders*, por lo que la edad calculada no es fiable.
- **Presión arterial sospechosa:** los valores están acotados exactamente a los umbrales configurados, lo que sugiere **datos sintéticos**. Por eso la presión se excluye del módulo de análisis.
- **Pasos excluidos del análisis:** el fabricante no garantiza la exactitud del conteo de pasos, por lo que se excluyen del análisis (aunque sí se pueden visualizar).
- **Cobertura:** 22 pacientes tienen datos de wearable; la tabla `patients` tiene 26 filas.

### 8.4 Gestión de Zona Horaria

Los datos originales están en UTC y deben mostrarse en hora de Argentina (UTC-3) para el equipo médico local. La conversión se centraliza en `build_dataframes()`:

```python
wearable_df["record_datetime"] = (
    pd.to_datetime(wearable_df["record_datetime"])
    .dt.tz_localize("UTC")
    .dt.tz_convert("America/Argentina/Buenos_Aires")
)
```

Todos los filtros y bordes de rango se construyen también *tz-aware* en la misma zona, de modo que las consultas de fecha/hora del usuario y la correlación con eventos clínicos locales sean correctas.

---

## 9. SISTEMA DE ALARMAS

Implementado en `src/data_loader.py`. Una alarma es un cruce de umbral: `value < normal_min` (bajo) o `value > normal_max` (alto), por métrica.

### 9.1 Detección con enfriamiento (`_detect_alarms` + `_with_cooldown`)

El problema: una condición sostenida (p. ej. SpO2 baja durante horas, muestreada cada 5 min) generaría decenas de alarmas redundantes. Solución en dos niveles. El primero, el **enfriamiento (cooldown)**:

- `_with_cooldown(rows_sorted, cooldown)` recorre las lecturas fuera de rango **en orden cronológico** y conserva una alarma sólo si pasó al menos `cooldown` (1 hora, `CFG.alarm_cooldown_minutes`) desde la **última alarma conservada** (no desde las ignoradas).
- En `_detect_alarms()`, el enfriamiento se aplica **por (métrica, tipo)** de forma independiente: las alarmas "bajo" y "alto" de una misma métrica, y las distintas métricas, se enfrían por separado. Así, una métrica que oscila por encima y por debajo no se silencia entre sí.
- `_detect_alarms` es la **única fuente de verdad** de la detección, reutilizada por el dashboard y el historial. Acepta un `metric_filter` opcional. Devuelve las alarmas ordenadas por timestamp descendente.

### 9.2 Agrupación de eventos (`group_consecutive_alarms`)

Segundo nivel de agregación, sobre las alarmas ya enfriadas:

- Colapsa alarmas **consecutivas de la misma (métrica, tipo)** separadas por no más de **1,5× el cooldown** (90 min) en un único **evento** con `start`, `end`, `count` y `extreme_value` (peor valor del evento: mínimo si es "bajo", máximo si es "alto").
- La agrupación se hace por *bucket* `(métrica, tipo)` por separado, de modo que una alarma de otro tipo intercalada **no corta la racha**.
- Cada evento incluye el `context` de la alarma extrema, que el botón "Ver" del historial usa para navegar al gráfico centrado en ese momento.
- Los eventos se devuelven del más reciente al más antiguo.

Resultado clínico: una condición sostenida que dispararía "una alarma por hora" se presenta como **un solo renglón** "de tal hora a tal hora (N alarmas)", mucho más legible.

### 9.3 Resúmenes cacheados

- `get_patients_summary()` (`@lru_cache(1)`): para cada paciente, calcula últimos valores por métrica y estado de alerta sobre los **últimos 7 días**; conserva la alarma más reciente por métrica para las tarjetas del dashboard.
- `get_patients_with_alerts()` (`@lru_cache(1)`): reutiliza el summary y filtra los que tienen alertas.
- `get_patient_alarm_history(patient_id, metric_filter, days)` (`@lru_cache(256)`): historial por paciente, con filtro de métrica y ventana opcional de días (para "cargar más semanas").

Como los datos son estáticos por despliegue (se cargan una vez del Parquet), estos cálculos pesados se hacen una sola vez; al reiniciar el servicio tras desplegar datos nuevos, la caché se limpia sola.

---

## 10. MÓDULO DE ANÁLISIS

Implementado en `src/analytics.py` (subsistema nuevo). Ofrece dos análisis complementarios, ambos sobre `ANALYSIS_METRICS` (FC, SpO2, temperatura) y siempre tras limpiar artefactos.

### 10.1 Limpieza (`_apply_cleaning`)

Única fuente de limpieza: descarta `NaN` y lecturas fuera de los límites de `PLAUSIBILITY` (p. ej. temperatura < 28 °C = reloj fuera del cuerpo). Se aplica de forma vectorizada por métrica.

### 10.2 Línea base personalizada (`compute_personal_baseline`)

Para cada paciente y métrica, calcula su **rango usual propio** en lugar de un umbral genérico igual para todos:

- Banda global de respaldo: percentiles `p10`–`p90` de todo el histórico del paciente.
- **Banda circadiana:** divide el día en franjas de 2 horas (`circadian_bucket_hours`) y calcula `p10`–`p90` por franja, reconociendo que (p. ej.) la FC nocturna difiere de la diurna.
- Requisitos mínimos de datos: 200 lecturas totales (`baseline_min_readings`) y 20 por franja (`baseline_bucket_min`); si una franja no llega, usa la banda global.
- `band_for(df, baseline)` mapea cada fila a su banda según la franja horaria.

Los puntos que caen fuera de la banda personal se resaltan como "fuera de SU patrón".

### 10.3 Tendencia semanal (`compute_weekly_trend`)

Detección de **deterioro sostenido** (alerta temprana):

- **FC:** se usa la **FC en reposo nocturna** = percentil bajo (p10) de las lecturas entre 00:00 y 06:00, agregada por día.
- **SpO2 / temperatura:** mediana diaria.
- Agregación diaria → semanal (mediana, `resample("W")`); se toman las **últimas 4 semanas** (`trend_weeks`), con mínimo de 3 semanas con datos (`trend_min_weeks`).
- **Pendiente** por mínimos cuadrados (`np.polyfit`, grado 1).
- **Anclaje temporal:** la ventana se ancla a la **última fecha de datos del paciente, no a `now()`**, porque los datos son históricos. Esta es una decisión deliberada: usar la fecha actual descartaría datos válidos.
- Se marca `adverse` si el signo de la pendiente coincide con `ADVERSE_DIRECTION` y `|pendiente| ≥ SLOPE_THRESHOLDS[metric]`.

### 10.4 Overview cacheado y optimización (`get_analysis_overview`)

`get_analysis_overview()` (`@lru_cache(1)`) precalcula baseline + tendencia de cada paciente y métrica.

**Optimización clave:** una versión ingenua que filtra el DataFrame de ~2,3 M filas una vez por cada (paciente, métrica) tardaba ~17,7 s. La versión actual hace **un único `groupby` por métrica** (limpia vectorizadamente y agrupa por IMEI), reduciendo el tiempo a ~1,8 s (≈10×). Además, almacena sólo **parámetros de banda y floats semanales** (kilobytes), no las series crudas.

Funciones derivadas: `get_patient_analysis(patient_id)` y `get_adverse_cohort()` (pacientes con alguna tendencia adversa, ordenados por severidad para *triage*).

---

## 11. COMPONENTES DE VISUALIZACIÓN

Todas las figuras se construyen en `src/dash_app/figures.py` con Plotly (`template="plotly_dark"`).

### 11.1 Figuras del Monitor

- **`create_overlaid_figure(data_dict, alarm=None)`:** métricas superpuestas en un eje; leyenda horizontal; `hovermode="x unified"`. Con una sola métrica, ajusta el rango Y con padding.
- **`create_subplot_figure(data_dict, alarm=None)`:** una métrica por subplot con ejes Y independientes; altura `180 * n` (reducida ~10 % respecto de versiones previas para mejor densidad de información); eje X compartido.
- **`create_temperature_alarm_figure(data_dict, alarm)`:** vista especial cuando se navega desde una alarma de temperatura — temperatura sola arriba (con marcador de alarma) y el resto de métricas superpuestas abajo; altura `270 * n_rows`.
- **`_add_alarm_marker(fig, alarm, row=None)`:** dibuja una "X" roja con etiqueta del valor en el punto de la alarma.
- **`_y_range(df)`:** calcula rango Y con 15 % de padding.
- **`calculate_stats(data_dict)`:** mín, máx y promedio por métrica (reutilizado también por los informes).

### 11.2 Figuras del Análisis (nuevas)

- **`create_baseline_figure(df, baseline, metric)`:** banda personal sombreada (relleno `tonexty` entre p10 y p90 por franja), serie de la métrica encima, y puntos fuera del patrón resaltados en naranja (`#db7b65`).
- **`create_trend_figure(trend, metric)`:** valores semanales + recta de pendiente; la recta se colorea según el estado (naranja `#db7b65` si es adversa, verde `#2fc4b2` si no). La recta se reconstruye desde la pendiente guardada (sin recomputar con numpy).
- **`trend_badge(trend)`:** devuelve flecha (↑/↓/→) y color para indicadores compactos.
- **`_empty_dark_fig(height, message)`:** figura vacía con mensaje centrado para estados sin datos.

### 11.3 Manejo de gaps en series temporales

`get_filtered_data()` inserta una fila con `value = NaN` un segundo antes de cada salto temporal mayor al umbral entre lecturas consecutivas. El `NaN` rompe la línea en Plotly, evitando que el personal médico asuma continuidad de signos vitales donde no hubo mediciones.

> **Discrepancia detectada (verificada contra el código):** el informe previo y los comentarios indican un umbral de gaps de 15 minutos, pero el código actual en `get_filtered_data` usa `GAP_THRESHOLD_MINUTES = 30`. Adicionalmente, `config.py::TimeConfig.gap_threshold_minutes = 5`, que **no se usa** en la detección de gaps de los gráficos. Recomendación: unificar este valor leyéndolo desde `CFG` para evitar inconsistencias.

### 11.4 Interactividad y estilo

Plotly aporta zoom, pan, hover, exportación PNG y leyenda interactiva de forma nativa. El estilo oscuro reduce la fatiga visual en guardias. `assets/custom.css` ajusta: color de dropdowns (paciente en tono salmón, horas en azul oscuro), tabla compacta, y el escalado/posición de los calendarios — el de **Fecha Inicio abre a la derecha** y el de **Fecha Fin a la izquierda** (ambos escalados a 0.55) para que no queden tapados.

---

## 12. INFORMES DESCARGABLES

Implementados en `src/reports.py` (subsistema nuevo). Pensados para una Pi *headless*: `matplotlib` usa el backend **"Agg"** (sin display, fijado **antes** de importar `pyplot`) y `fpdf2` es pura-Python. Las figuras se cierran siempre (`plt.close`) para no acumular memoria. Para Unicode (°C, acentos) se usa la fuente **DejaVuSans** que viene con matplotlib.

### 12.1 Informe por paciente

Usa la selección del monitor (paciente, rango de fechas/horas, métricas).

- **`build_patient_csv(...)`:** formato largo con columnas `fecha_hora, metrica, unidad, valor, fuera_de_rango` (la última marca "no"/"bajo"/"alto" según los umbrales).
- **`build_patient_pdf(...)`:** cabecera del paciente (ID, género, edad, hospital, rango, fecha de generación), tabla de estadísticas (mín/máx/prom por métrica), tabla de **eventos de alarma agrupados** y, para cada evento, un mini-gráfico de esa métrica en una ventana de **±2 horas** alrededor del evento (`_render_alarm_chart_png`), con tope de **12 gráficos** (`MAX_ALARM_CHARTS`). El gráfico marca el rango normal sombreado y resalta en rojo los puntos fuera de rango.
- Las alarmas del PDF se obtienen con `get_patient_alarm_history` filtradas al rango y a las métricas seleccionadas, y se agrupan con `group_consecutive_alarms`.

### 12.2 Informe de cohorte (resumen)

- **`build_summary_csv()`** y **`build_summary_pdf()`:** tabla de todos los pacientes con sus últimos valores (FC, SpO2, temperatura, presión sistólica) y estado de alerta; en el PDF, las filas con alerta se resaltan con fondo rojizo.

### 12.3 Mecanismo de descarga

Vía `dcc.Download` en los callbacks (`download_patient_report`, `download_summary_report`):

- **CSV** con **BOM UTF-8** (`"﻿" + df.to_csv()`) para que Excel muestre bien los acentos.
- **PDF** con `dcc.send_bytes`.
- `import reports` es **perezoso** dentro del callback, para no cargar matplotlib en el arranque y bajar la RAM inicial en la Pi.

UI: selector de formato (PDF/CSV) + botón "Descargar" en la barra lateral del monitor; "Descargar resumen" en el dashboard.

---

## 13. AUTENTICACIÓN Y SEGURIDAD

Implementada en `src/auth.py` y `gestionar_usuarios.py` (subsistema nuevo). Login por **sesión de Flask** sobre el mismo servidor que usa Dash.

### 13.1 Guard de sesión (`init_auth`)

- `@server.before_request` (`require_login`) intercepta toda petición: si la ruta no es pública (`/login`, `/logout`) y no hay sesión, redirige a `/login`; para peticiones internas de Dash (`/_dash`, `/_reload`, que son XHR) devuelve **401** en lugar de redirigir, para no romper el front.
- Rutas: `/login` (formulario HTML embebido con estilo propio) y `/logout` (limpia la sesión).
- **Secret key persistente:** se lee/genera en `.flask_secret` (`secrets.token_hex(32)`, permisos 600). Persistirla evita desloguear a todos en cada reinicio del servicio.
- Cookies de sesión con `SESSION_COOKIE_HTTPONLY=True` y `SESSION_COOKIE_SAMESITE="Lax"`.

### 13.2 Almacén de usuarios

- Usuarios en `users.json` con contraseñas hasheadas por `werkzeug.security` (`generate_password_hash` / `check_password_hash`). El archivo está **gitignoreado** (no se sube ni el deploy lo pisa) y se guarda con permisos **600**.
- Funciones: `add_user`, `delete_user`, `list_users`, `user_exists`, `verify`.

### 13.3 Gestión de usuarios por CLI (`gestionar_usuarios.py`)

CLI con subcomandos `add` / `list` / `delete`; la contraseña se pide por `getpass` (oculta) y se valida (coincidencia y longitud mínima de 6). Se ejecuta por SSH en la Pi: **como sólo la administradora tiene acceso SSH, sólo ella crea usuarios** (no hay registro abierto en la web). El navbar incluye el enlace "Cerrar sesión".

### 13.4 Postura de seguridad

La protección efectiva es **el login de la aplicación + el cifrado HTTPS del túnel** (Tailscale Funnel; ver §15). Los datos están anonimizados conforme al protocolo del proyecto. La app sirve HTTP en la Pi; el cifrado lo aporta el túnel de borde.

---

## 14. ESTRUCTURA DE LA APLICACIÓN DASH

### 14.1 Punto de entrada (`app.py`)

- Precarga `load_all_data()` y **precalienta** `get_patients_summary()` y `get_analysis_overview()` al arrancar, de modo que la primera visita ya sea instantánea (los cálculos pesados quedan cacheados).
- Crea la app Dash con tema DARKLY y `suppress_callback_exceptions=True`.
- Llama a `init_auth(app)` para proteger toda la app.
- Expone `server = app.server` para gunicorn (`app:server`).
- `app.run(host, port, debug)` configurable por variables de entorno `HOST` (default `0.0.0.0`), `PORT` (8050), `DEBUG` (false).

### 14.2 Layout y routing (`layout.py`)

`create_layout()` define el navbar (Dashboard, Monitor Paciente, Cerrar sesión), un `dcc.Location` para el routing y dos `dcc.Store` de sesión: `selected-patient-store` y `alarm-context-store`.

### 14.3 Páginas

- **`pages/dashboard.py`:** panel de alertas (tarjetas, máx. 6), tabla resumen de pacientes (FC, SpO2, temperatura, presión sistólica, estado, botón de historial), modal de historial de alarmas (con filtro de métrica y "cargar semana anterior"), y barra de descarga del resumen.
- **`pages/patient_monitor.py`:** barra lateral con paciente, **Fecha Inicio/Fin lado a lado**, **Hora Inicio/Fin lado a lado**, checklist de métricas, modo de visualización (Superpuesto/Subplots) y descarga de informe; área principal con el botón "Tendencias y patrones" arriba, tarjetas de estadística, gráfico principal a **58vh**, y un `dbc.Collapse` con el análisis profundo (línea base personalizada + tendencias semanales del paciente).

### 14.4 Callbacks (`callbacks.py`)

- **Routing** `display_page`: `/patient` → monitor, cualquier otra ruta → dashboard.
- **Dashboard:** `update_dashboard` (paneles de alertas y tabla), `navigate_to_patient` (clic en tarjeta/badge/fila navega al monitor y, si viene de una alarma, fija el contexto).
- **Monitor:** `update_patient_info` (info demográfica, rangos de fecha disponibles, defaults — por defecto últimos 7 días o, si viene de una alarma, ventana ±2 h centrada en el evento) y `update_graph` (valida selección y rango, arma `data_dict`, elige la figura según modo/alarma, calcula estadísticas).
- **Historial de alarmas:** `toggle_alarm_history_modal`, `load_more_weeks`, `populate_alarm_history` (agrupa con `group_consecutive_alarms` y arma la tabla), `navigate_from_alarm` (el botón "Ver" navega al gráfico del evento).
- **Descargas:** `download_patient_report` y `download_summary_report` (import perezoso de `reports`, BOM en CSV, `send_bytes` en PDF).
- **Análisis:** `toggle_deep_analysis` (abre/cierra el Collapse) y `update_deep_analysis` (calcula sólo si está abierto; usa las últimas 2 semanas para el gráfico de banda personal).

---

## 15. DESPLIEGUE EN RASPBERRY PI

Subsistema nuevo y central para el objetivo de escalabilidad.

### 15.1 Hardware y SO

- **Raspberry Pi 4 (2 GB)**, hostname `pececito`, usuario `ro`.
- **Raspberry Pi OS 13 "Trixie"** (basado en Debian), arquitectura **aarch64** (64 bits) — necesaria para instalar *wheels* precompiladas de pandas/numpy/pyarrow.

### 15.2 Servidor de producción (`deploy/vitaicare.service`)

`gunicorn` corriendo como servicio **systemd**, con arranque automático al boot:

```
ExecStart=.../.venv/bin/gunicorn --workers 1 --threads 2 --timeout 120 \
          --bind 0.0.0.0:8050 app:server
Restart=on-failure
```

- **Un solo worker a propósito:** cada worker carga toda la serie en RAM; más de uno provocaría OOM en 2 GB.
- 2 threads para concurrencia de E/S; timeout de 120 s para descargas/PDF pesados.
- Sirve HTTP en el puerto 8050; el cifrado lo aporta el túnel de borde (§15.4).
- Se recomienda ampliar el *swap* a 2 GB en la Pi (documentado en `README_RASPBERRY.md`).

### 15.3 Despliegue desde Windows (PowerShell)

- **`deploy/deploy.ps1`:** sincroniza el repo a `~/newpacientes` en la Pi. Arma la lista de archivos con `git ls-files` (respeta `.gitignore`), **agrega explícitamente los Parquet** (que están gitignoreados) y **descarta archivos borrados aún en el índice** para que `tar` no falle. Autodetecta el backend en orden: **rsync nativo** → **rsync en WSL** → **tar + scp** (este último no requiere instalar nada; usa herramientas integradas de Windows 10/11). Excluye `.git`, `.venv`, `__pycache__`, `RA.json`, `RA.sql`, `.vscode`, `.claude`. Admite `-DryRun`, `-Port`, `-IdentityFile`, `-NoDelete`.
- **`deploy/actualizar-datos.ps1`:** ejecuta todo el ciclo en un comando — `RA.sql → RA.json` (paso 1), `RA.json → Parquet` (paso 2), deploy a la Pi (paso 3) y `systemctl restart vitaicare` (paso 4, imprescindible para limpiar la caché y recargar datos nuevos). Los pasos 1–2 son pesados en RAM y por eso se hacen en la PC, no en la Pi.
- Ambos scripts usan por defecto la **IP de Tailscale `100.99.247.65`** y el usuario `ro`, con **autenticación por clave SSH** (sin contraseña). `actualizar-datos.ps1` documenta `192.168.1.88` como ejemplo de IP local en su ayuda.

> **Discrepancia menor (verificada contra el código):** el comentario de cabecera de `actualizar-datos.ps1` menciona `192.168.1.88` como default de `-Address`, pero el valor por defecto real del parámetro es la IP de Tailscale `100.99.247.65`. El comportamiento efectivo es el de Tailscale.

```
   PC Windows (RAM de sobra)                 Raspberry Pi 4 (2 GB)
 ┌───────────────────────────┐            ┌──────────────────────────┐
 │ RA.sql ─► RA.json ─► .parquet │  SSH/scp │  ~/newpacientes/          │
 │ deploy.ps1 / actualizar-datos │ ───────► │  .venv + Parquet         │
 └───────────────────────────┘            │  systemd → gunicorn:8050 │
                                           └──────────────────────────┘
```

### 15.4 Acceso remoto

Tres mecanismos complementarios:

1. **rpi-connect** (Raspberry Pi Connect): terminal/escritorio remoto de la administradora vía `connect.raspberrypi.com`.
2. **Tailscale** (VPN *mesh* sobre WireGuard): la Pi `pececito` y la laptop `msi` en la misma *tailnet* (IPs `100.x`) para acceso privado dentro y fuera de la institución, con IP estable.
3. **Tailscale Funnel:** expone el dashboard públicamente con **HTTPS** en `https://pececito.tailda6dee.ts.net`, con un **dominio propio** `https://vitaicare.whittileaks.com` al frente.

La protección de extremo a extremo combina el **login de la app** con el **HTTPS del túnel**; los datos están anonimizados.

---

## 16. DESAFÍOS TÉCNICOS

### 16.1 Memoria en hardware de bajo costo (el desafío central)

Cargar 2,36 M de registros desde JSON agota la RAM de una Pi de 2 GB. **Solución:** pipeline a Parquet con reducción de columnas y conversión hecha en la PC (ver §5). Resultado: el DataFrame completo entra con ~280 MB.

### 16.2 Alarmas redundantes en condiciones sostenidas

Una condición fuera de rango muestreada cada 5 min generaría decenas de alarmas. **Solución de dos niveles:** enfriamiento de 1 h por (métrica, tipo) y agrupación de consecutivas en eventos (§9).

### 16.3 Filtrado temporal con rango de horas a través de días

Filtrar fecha y hora por separado deja "huecos" al cruzar la medianoche. **Solución:** combinar fecha + hora en un único `datetime` *tz-aware* y filtrar por un solo intervalo (`get_filtered_data`).

### 16.4 Análisis sobre datos históricos

Anclar la ventana de tendencia a `now()` descartaría datos válidos (los datos no llegan hasta hoy). **Solución:** anclar a la última fecha de datos de cada paciente (§10.3).

### 16.5 Costo del análisis sobre 2,3 M de filas

Filtrar por (paciente, métrica) repetidamente era O(pacientes × métricas) recorridos del DataFrame (~17,7 s). **Solución:** un único `groupby` por métrica (~1,8 s) + caché (§10.4).

### 16.6 Generación de PDF en entorno headless

Sin display ni dependencias de sistema pesadas. **Solución:** matplotlib backend "Agg" + fpdf2 pura-Python + fuente DejaVuSans para Unicode; import perezoso para no cargar matplotlib al arranque (§12).

### 16.7 Acceso seguro desde fuera de la institución

Exponer un dashboard con datos de salud sin infraestructura propia. **Solución:** Tailscale (VPN) + Funnel (HTTPS) + login de la app, sobre datos anonimizados (§15.4).

---

## 17. RESULTADOS Y ESTADO ACTUAL

### 17.1 Funcionalidades completadas

| Área | Estado | Detalle |
|------|--------|---------|
| Pipeline SQL→JSON→Parquet | ✅ | Reproducible en un comando |
| Carga eficiente en la Pi | ✅ | 2,36 M filas, ~280 MB RAM |
| Dashboard de cohorte | ✅ | Alertas + tabla resumen |
| Monitor por paciente | ✅ | Filtros, overlay/subplots, estadísticas |
| Detección de alarmas | ✅ | Umbral + cooldown 1 h |
| Agrupación de eventos | ✅ | Consecutivas ≤ 1,5× cooldown |
| Historial navegable | ✅ | Modal + "Ver" → gráfico del evento |
| Línea base personalizada | ✅ | Banda circadiana p10–p90 |
| Tendencias semanales | ✅ | Pendiente + detección adversa |
| Informes PDF/CSV | ✅ | Por paciente y de cohorte |
| Autenticación | ✅ | Login Flask + CLI de usuarios |
| Despliegue en producción | ✅ | systemd + gunicorn en Pi |
| Acceso remoto seguro | ✅ | Tailscale + Funnel (HTTPS) |
| Manejo de zona horaria | ✅ | UTC → Argentina |
| Detección de gaps | ✅ | Rompe líneas con NaN |

### 17.2 Métricas del proyecto (verificadas)

- **Pacientes:** 26 registros en `patients`, **22 con datos** de wearable.
- **Mediciones:** **2.363.501** registros (`wearabledata`).
- **Métricas:** 6 tipos (distribución en §8.2).
- **Datos:** ~520 MB (JSON) → ~10 MB (Parquet wearable) + ~7,6 KB (Parquet pacientes).
- **Performance del análisis:** ~1,8 s (overview optimizado) frente a ~17,7 s (versión ingenua).

### 17.3 Capturas de pantalla

*(Espacios reservados para incluir capturas en la versión final de la tesis: Dashboard con panel de alertas y tabla; Monitor con gráfico superpuesto; sección "Tendencias y patrones" con banda personal y tendencias; modal de historial; ejemplo de PDF generado; pantalla de login.)*

---

## 18. TRABAJO FUTURO

- **Validación clínica de umbrales:** reemplazar los *defaults* por valores validados por el equipo médico (rangos normales, plausibilidad, pendientes de tendencia).
- **Datos clínicos reales:** integrar `clinicalevents` y `labresults` (hoy vacías) para correlacionar eventos con cambios fisiológicos; superponerlos como anotaciones en los gráficos.
- **Estado autopercibido:** explotar `perceivedhealthdata` (122 registros disponibles).
- **Unificar umbral de gaps:** leer el umbral desde `CFG` (hoy hardcodeado en 30 min; ver §11.3).
- **Roles de usuario:** distinguir médico / enfermero / admin.
- **Logging y auditoría** de accesos y consultas.
- **Detección de anomalías (ML):** sobre la base ya establecida de línea base y tendencias.
- **Evaluación de usabilidad** formal con el equipo médico (tareas, tiempos, errores, encuestas Likert).
- **Escalabilidad multi-institución:** parametrización por centro y guía de instalación replicable.

---

## 19. CONCLUSIONES

VITAICARE evolucionó de un visualizador de series temporales a una **plataforma de monitoreo completa, desplegada y accesible de forma segura** sobre hardware de bajo costo. Los principales logros técnicos son:

1. Un **pipeline de datos reproducible** que hace viable trabajar con 2,36 M de registros en una Raspberry Pi de 2 GB (de ~520 MB a ~10 MB; de OOM a ~280 MB de RAM).
2. Un **sistema de alarmas** con enfriamiento y agrupación que produce información clínica legible en lugar de ruido.
3. Un **módulo de análisis** que mira el patrón propio de cada paciente (línea base circadiana) y detecta deterioro sostenido (tendencias), correctamente anclado a datos históricos.
4. **Informes clínicos exportables** y **autenticación** funcionando en un entorno *headless*.
5. Un **despliegue real** (systemd + gunicorn) con acceso remoto cifrado (Tailscale + Funnel) sobre datos anonimizados.

Aprendizajes clave: la importancia de las decisiones de ingeniería motivadas por restricciones reales (memoria de la Pi), la diferencia entre umbrales genéricos y patrones personalizados para la relevancia clínica, y la necesidad de que todos los umbrales sean parametrizables a la espera de validación médica. La base de código está modularizada, cacheada por rendimiento y versionada con Git, lista para evolución.

---

## 20. REFERENCIAS Y RECURSOS

### 20.1 Bibliografía técnica

1. **Dash Documentation** — Plotly Technologies Inc. — https://dash.plotly.com/
2. **Plotly Python Graphing Library** — https://plotly.com/python/
3. **Pandas Documentation** — https://pandas.pydata.org/docs/
4. **Apache Parquet / PyArrow** — https://arrow.apache.org/docs/python/
5. **Bootswatch DARKLY** — https://bootswatch.com/darkly/
6. **Tailscale (WireGuard mesh VPN) / Tailscale Funnel** — https://tailscale.com/
7. **Raspberry Pi Connect** — https://www.raspberrypi.com/software/connect/

### 20.2 Bibliografía clínica

8. **Manual del reloj ID Vita** — Intelligent Data.
9. **Clark, M. (2023)** — "Single-Use Wearable Wireless Sensors for Vital Sign Monitoring", *Canadian Journal of Health Technologies*.
10. **Moore, K. et al. (2021)** — "Older Adults' Experiences With Using Wearable Devices", *JMIR mHealth and uHealth*.
11. **Khairat, S. S. et al. (2018)** — "The Impact of Visualization Dashboards on Quality of Care", *JMIR Human Factors*.
12. **Dowding, D. et al. (2019)** — "Usability Evaluation of a Dashboard for Home Care Nurses", *CIN: Computers, Informatics, Nursing*.

### 20.3 Recursos del proyecto

- **CLAUDE.md** — contexto y directrices de desarrollo.
- **README_RASPBERRY.md** — guía de despliegue en Raspberry Pi.
- **Anteproyecto VITAICARE** — Pesoa, R. (2024).

### 20.4 Contactos

- **Estudiante:** Rocío Pesoa — ITBA (Bioingeniería).
- **Tutor:** Dr. Miguel Aguirre — ITBA.
- **Co-tutora:** Ing. Melisa Granda — Universidad de Alcalá.
- **Colaboradora:** Giuliana Espósito — ITBA.
- **Institución participante:** Residencia Asturiana de Buenos Aires.

---

## ANEXOS

### Anexo A — Instalación y ejecución

#### A.1 Desarrollo (en la PC)

```bash
git clone <URL_del_repositorio>
cd newpacientes
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Generar los Parquet a partir de RA.json (requiere RA.json presente):
python convert_to_parquet.py     # genera RA_patients.parquet y RA_wearable.parquet

# Ejecutar (toma los Parquet si existen; si no, RA.json):
python app.py                    # http://localhost:8050
```

Si se parte del volcado SQL: `python parse_mysql_dump.py RA.sql` para generar `RA.json`, y luego `convert_to_parquet.py`.

Crear un usuario para poder iniciar sesión:

```bash
python gestionar_usuarios.py add <usuario>   # pide la contraseña (oculta)
python gestionar_usuarios.py list
python gestionar_usuarios.py delete <usuario>
```

#### A.2 Despliegue en la Raspberry Pi

Flujo completo desde Windows (PowerShell), tras reemplazar `RA.sql` por un dump nuevo:

```powershell
.\deploy\actualizar-datos.ps1        # SQL→JSON→Parquet→deploy→restart
# o, para sólo desplegar código + Parquet ya generados:
.\deploy\deploy.ps1 -Address 100.99.247.65 -User ro
```

En la Pi (primera vez): crear `.venv`, `pip install -r requirements.txt`, instalar el servicio systemd (`deploy/vitaicare.service`) y crear usuarios por SSH. Detalle completo en `README_RASPBERRY.md`.

#### A.3 Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Interfaz de escucha |
| `PORT` | `8050` | Puerto del servidor |
| `DEBUG` | `false` | Modo debug de Dash |
| `VITAICARE_PATIENTS_PARQUET` | `RA_patients.parquet` | Parquet de pacientes |
| `VITAICARE_WEARABLE_PARQUET` | `RA_wearable.parquet` | Parquet de serie temporal |
| `VITAICARE_JSON` | `RA.json` | JSON de respaldo |
| `VITAICARE_USERS` | `users.json` | Usuarios (hashes) |
| `VITAICARE_SECRET` | `.flask_secret` | Secret key de sesiones |

### Anexo B — Estructura de archivos (actual)

```
newpacientes/
├── app.py                          # Entrada: precarga datos, init_auth, server=app.server
├── parse_mysql_dump.py             # Etapa 1 del pipeline: RA.sql -> RA.json (streaming)
├── convert_to_parquet.py           # Etapa 2 del pipeline: RA.json -> Parquet
├── gestionar_usuarios.py           # CLI de gestión de usuarios (add/list/delete)
├── requirements.txt                # Dependencias fijadas (wheels aarch64)
│
├── src/
│   ├── config.py                   # METRICS, Alarm/AlertType, CFG, ACFG, umbrales
│   ├── data_loader.py              # Carga (Parquet/JSON), filtrado, gaps, ALARMAS
│   ├── analytics.py                # Línea base personal + tendencias semanales
│   ├── reports.py                  # Informes PDF/CSV (matplotlib Agg + fpdf2)
│   ├── auth.py                     # Login Flask, sesiones, guard de rutas
│   │
│   └── dash_app/
│       ├── layout.py               # Navbar, routing, dcc.Store de sesión
│       ├── callbacks.py            # Toda la lógica reactiva
│       ├── figures.py              # Figuras Plotly (monitor + análisis)
│       └── pages/
│           ├── dashboard.py        # Cohorte: alertas, tabla, modal historial
│           └── patient_monitor.py  # Individual: filtros, gráfico, análisis
│
├── assets/
│   └── custom.css                  # Estilos dark, calendarios, dropdowns
│
├── deploy/
│   ├── deploy.ps1                  # Deploy a la Pi (rsync/WSL/tar+scp)
│   ├── actualizar-datos.ps1        # Ciclo completo de datos + deploy + restart
│   └── vitaicare.service           # Unidad systemd (gunicorn, 1 worker)
│
├── README_RASPBERRY.md             # Guía de despliegue
├── CLAUDE.md                       # Contexto del proyecto
├── INFORME_TECNICO.md              # Este informe
│
├── RA_patients.parquet             # Datos procesados (~7,6 KB)   [gitignored]
├── RA_wearable.parquet             # Datos procesados (~10 MB)    [gitignored]
├── RA.json                         # Respaldo (~520 MB, solo dev) [gitignored]
├── RA.sql                          # Volcado original (~495–519 MB) [gitignored]
├── users.json                      # Usuarios (hashes)  [gitignored, 600]
└── .flask_secret                   # Secret key  [gitignored, 600]
```

### Anexo C — Extracto de configuración de métricas (`config.py`)

```python
METRICS = {
    "heart_rate":              {"name": "Frecuencia Cardíaca", "color": "#E06464",
                                "unit": "bpm",  "normal_min": 50,   "normal_max": 120},
    "blood_oxygen_saturation": {"name": "Saturación O2",       "color": "#A268BA",
                                "unit": "%",    "normal_min": 80,   "normal_max": 100},
    "systolic_blood_pressure": {"name": "Presión Sistólica",   "color": "#68c2f6",
                                "unit": "mmHg", "normal_min": 90,   "normal_max": 140},
    "diastolic_blood_pressure":{"name": "Presión Diastólica",  "color": "#8eb69b",
                                "unit": "mmHg", "normal_min": 60,   "normal_max": 90},
    "temperature":             {"name": "Temperatura",         "color": "#FFEAA7",
                                "unit": "°C",   "normal_min": 25.0, "normal_max": 38.0},
    "daily_activity_steps":    {"name": "Pasos Diarios",       "color": "#DDA0DD",
                                "unit": "pasos","normal_min": 0,    "normal_max": None},
}
```

### Anexo D — Resumen de discrepancias entre la documentación y el código

Verificadas contra el código fuente (en caso de divergencia, prevalece el código):

1. **Umbral de gaps:** documentado como 15 min, pero `get_filtered_data` usa `GAP_THRESHOLD_MINUTES = 30`. Además `CFG.gap_threshold_minutes = 5` no se usa en la detección de gaps de los gráficos.
2. **IP por defecto de `actualizar-datos.ps1`:** la cabecera del script menciona `192.168.1.88`, pero el default real del parámetro `-Address` es la IP de Tailscale `100.99.247.65`.
3. **Tamaños de archivo en disco (verificados):** `RA.sql` ≈ 519 MB, `RA.json` ≈ 520 MB, `RA_wearable.parquet` ≈ 10 MB, `RA_patients.parquet` ≈ 7,6 KB (la consigna estimaba ~495 MB / ~444 MB / ~8,5 MB respectivamente; la diferencia se debe al volcado vigente).
4. **Conteos verificados:** `patients` = 26 filas, `wearabledata` = 2.363.501 filas, 22 IMEIs con datos; coinciden con la consigna.

---

**FIN DEL INFORME TÉCNICO**

*Documento preparado por Rocío Pesoa para entrega académica — ITBA. Versión 2.0, 24 de junio de 2026. Documenta el estado actual del proyecto VITAICARE (módulo newpacientes): pipeline de datos, alarmas, análisis, informes, autenticación y despliegue en Raspberry Pi.*
