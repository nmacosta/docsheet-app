import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import pandas as pd # Opcional: para mostrar data

# --- Configuración Inicial ---
st.set_page_config(page_title="Log de Ejecución CitaMedVoz", layout="wide")
st.title("Interfaz para [citamedVOZ] Log de Ejecucion")
st.markdown("Presiona el botón para agregar una fila de prueba al Google Sheet.")

# --- Conexión a Google Sheets ---

# Define los alcances (scopes) necesarios
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file' # Necesario para encontrar el archivo por nombre
]

# Función para cargar credenciales y conectar
def connect_to_gsheet():
    """Carga las credenciales desde los secretos de Streamlit y conecta con gspread."""
    try:
        # Recupera el secreto. La depuración indica que es un <class 'str'>
        creds_json_str = st.secrets["GOOGLE_CREDENTIALS_JSON"]

        # --- ¡CAMBIO CLAVE (Volver a como estaba)! ---
        # Como st.secrets nos da un string, NECESITAMOS parsearlo a un diccionario
        try:
            creds_dict = json.loads(creds_json_str)
        except json.JSONDecodeError as json_err:
             # Error si el string NO es JSON válido
             st.error(f"Error Crítico: No se pudo decodificar el JSON recuperado de los secretos.")
             st.error(f"Detalle: {json_err}")
             st.error("Revisa CUIDADOSAMENTE la sintaxis del valor de GOOGLE_CREDENTIALS_JSON en tu archivo secrets.toml.")
             st.error("Asegúrate de que empieza con '{' y termina con '}' y que todo el contenido entre las ''' es JSON válido.")
             # Muestra parte del string problemático para ayudar a depurar
             st.text_area("Inicio del string JSON problemático:", creds_json_str[:500] + "...", height=150)
             return None # Detiene la ejecución aquí

        # Ahora SÍ podemos pasar el diccionario a from_service_account_info
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

        gc = gspread.authorize(creds)
        return gc

    except KeyError:
        # Si las claves no están en secrets.toml
        st.error("Error: Asegúrate de haber configurado 'GOOGLE_CREDENTIALS_JSON' y 'GOOGLE_SHEET_NAME' correctamente en tu archivo .streamlit/secrets.toml.")
        return None
    except Exception as e:
        # Otros errores (p.ej., credenciales inválidas después de parsear, problemas de red)
        st.error(f"Error al conectar con Google API (posiblemente después de parsear JSON): {e}")
        # Repetir el tipo para confirmar si cambió algo (no debería)
        creds_secret_value = st.secrets.get("GOOGLE_CREDENTIALS_JSON")
        st.error(f"Tipo de objeto recuperado de st.secrets: {type(creds_secret_value)}")
        return None


# Función para obtener la hoja de cálculo
def get_worksheet(gc):
    """Obtiene la hoja de cálculo específica por nombre."""
    try:
        sheet_name = st.secrets["GOOGLE_SHEET_NAME"]

        st.info(f"DEBUG: Intentando abrir hoja con nombre leído del secreto: '{sheet_name}'")

        spreadsheet = gc.open(sheet_name)
        # Asume que los datos están en la primera hoja
        worksheet = spreadsheet.sheet1
        return worksheet
    except gspread.SpreadsheetNotFound:
        st.error(f"Error: No se encontró la hoja de cálculo con el nombre '{st.secrets.get('GOOGLE_SHEET_NAME', 'NO_CONFIGURADO')}'. ¿Está bien escrito y compartido con la cuenta de servicio?")
        return None
    except Exception as e:
        st.error(f"Error al acceder a la hoja de cálculo: {e}")
        return None

# --- Lógica del Botón ---

# Columnas esperadas en el Google Sheet (EN ORDEN)
# Asegúrate de que este orden coincida EXACTAMENTE con tu hoja
EXPECTED_COLUMNS = [
    "Timestamp", "Filename", "Model", "Status", "Message", "MotivoConsulta",
    "EnfermedadActual", "Antecedentes", "ExamenFisico", "DiasReposo",
    "SignosVitales_Resumen", "Examenes_Resumen", "Diagnosticos_Resumen",
    "850mg", "PlanDeAccion_Resumen", "ComentariosModelo", "Literal",
    "JSON_Completo"
]

# Botón para agregar fila dummy
if st.button("➕ Agregar Fila Dummy"):
    st.write("Intentando agregar fila...")
    gc = connect_to_gsheet()

    if gc:
        worksheet = get_worksheet(gc)
        if worksheet:
            # Generar datos dummy
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dummy_data = [
                timestamp,                        # Timestamp
                "dummy_audio.mp3",                # Filename
                "TestModel_v0.1",                 # Model
                "DUMMY_ADDED",                    # Status
                "Fila de prueba agregada por Streamlit.", # Message
                "Dolor de cabeza de prueba",      # MotivoConsulta
                "Paciente refiere cefalea leve.", # EnfermedadActual
                "Niega alergias (prueba)",       # Antecedentes
                "Examen físico normal (prueba)", # ExamenFisico
                "1",                              # DiasReposo (como string)
                "PA: 120/80, FC: 70, FR: 16, T: 36.5", # SignosVitales_Resumen
                "Hemograma pendiente (prueba)",   # Examenes_Resumen
                "Cefalea tensional (prueba)",     # Diagnosticos_Resumen
                "Paracetamol 500mg si dolor",     # 850mg (o la columna correspondiente)
                "Observación y control (prueba)",# PlanDeAccion_Resumen
                "Modelo funcionó como prueba.",   # ComentariosModelo
                "Este es un texto literal simulado para la prueba...", # Literal
                '{"dummy": true, "source": "streamlit_button"}', # JSON_Completo
            ]

            # Validar que la cantidad de datos coincida con las columnas esperadas
            if len(dummy_data) != len(EXPECTED_COLUMNS):
                st.error(f"Error interno: La cantidad de datos dummy ({len(dummy_data)}) no coincide con las columnas esperadas ({len(EXPECTED_COLUMNS)}). Revisa el script.")
            else:
                try:
                    # Agregar la fila al final de la hoja
                    with st.spinner('Agregando fila al Google Sheet...'):
                        worksheet.append_row(dummy_data, value_input_option='USER_ENTERED')
                    st.success(f"✅ ¡Fila de prueba agregada exitosamente a '{st.secrets['GOOGLE_SHEET_NAME']}'!")
                    st.balloons()

                    # Opcional: Mostrar las últimas N filas para confirmar
                    try:
                        st.subheader("Últimas 5 filas en la hoja:")
                        data = worksheet.get_all_values() # Consume más API quota
                        if len(data) > 1: # Si hay datos además del encabezado
                             # Asume que la primera fila es el encabezado
                            df = pd.DataFrame(data[1:], columns=data[0])
                            st.dataframe(df.tail(5))
                        elif len(data) == 1:
                             st.info("La hoja solo contiene la fila de encabezado.")
                        else:
                            st.info("La hoja parece estar vacía.")

                    except Exception as e_read:
                         st.warning(f"No se pudieron leer las últimas filas: {e_read}")


                except Exception as e:
                    st.error(f"❌ Error al intentar agregar la fila: {e}")
                    st.error("Posibles causas: Permisos insuficientes para la cuenta de servicio, API no habilitada, nombre de hoja incorrecto, cuota de API excedida.")
        else:
            st.warning("No se pudo obtener la hoja de trabajo. No se agregó la fila.")
    else:
        st.warning("No se pudo establecer conexión con Google Sheets. No se agregó la fila.")

# --- Opcional: Mostrar parte del contenido actual ---
st.sidebar.header("Ver Contenido Actual (Opcional)")
if st.sidebar.button("Mostrar Primeras 5 Filas"):
    gc = connect_to_gsheet()
    if gc:
        worksheet = get_worksheet(gc)
        if worksheet:
             with st.spinner('Cargando datos...'):
                try:
                    data = worksheet.get_all_values()
                    if len(data) > 1:
                         # Asume que la primera fila es el encabezado
                        df = pd.DataFrame(data[1:], columns=data[0])
                        st.sidebar.dataframe(df.head(5))
                    elif len(data) == 1:
                        st.sidebar.info("La hoja solo contiene la fila de encabezado.")
                    else:
                        st.sidebar.info("La hoja parece estar vacía.")
                except Exception as e:
                    st.sidebar.error(f"Error al leer datos: {e}")