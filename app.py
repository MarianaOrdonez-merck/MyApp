import streamlit as st
import pandas as pd
import io
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

# Configuración de la página
st.set_page_config(
    page_title="Diferencias de conciliaciones",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Función para derivar una clave de cifrado a partir de la contraseña
def get_encryption_key(password: str) -> bytes:
    salt = b'antropic_fixed_salt'  # Salt fijo para mantener consistencia entre sesiones
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

# Clase para manejar el cifrado/descifrado
class SecureDataHandler:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt_dataframe(self, df: pd.DataFrame) -> bytes:
        csv_data = df.to_csv(index=False).encode()
        return self.fernet.encrypt(csv_data)
    
    def decrypt_dataframe(self, encrypted_data: bytes) -> pd.DataFrame:
        decrypted_data = self.fernet.decrypt(encrypted_data)
        return pd.read_csv(io.StringIO(decrypted_data.decode()))

# Custom CSS con estilos mejorados
def load_css():
    st.markdown("""
        <style>
        .stApp {
            background-color: #f8f9fa;
        }
        .stButton>button {
            background-color: #0066cc;
            color: white;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            border: none;
            transition: background-color 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #0052a3;
        }
        .uploadedFile {
            background-color: white;
            border-radius: 5px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        .stDataFrame {
            background-color: white;
            border-radius: 5px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .info-card {
            background-color: white;
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

def show_home():
    st.markdown("<h2 style='color: blue;'>Diferencias de conciliaciones</h2>", unsafe_allow_html=True)
    st.write("Sistema de comparación de archivos")

    st.write("""
        **Paso 1:** Ingrese su clave de seguridad
        **Paso 2:** Seleccione el tipo de reporte
        **Paso 3:** Cargue los archivos a comparar
        **Paso 4:** Visualice y descargue los resultados
    """)

def preprocess_file(df, report_type):
    try:
        if report_type == "visitas":
            columns_to_drop = ["Country", "Subject Number", "Visit\nOrder", "Type of Visit", "DS01 Status", "Date of \nDisposition", "INEX"]
            existing_columns = [col for col in columns_to_drop if col in df.columns]
            if existing_columns:
                df = df.drop(columns=existing_columns)
            if len(df) > 4:
                df = df.iloc[4:]
        elif report_type == "imagenes":
            columns_to_drop = ["Subject\nNumber", "Sequence\nNumber"]
            existing_columns = [col for col in columns_to_drop if col in df.columns]
            if existing_columns:
                df = df.drop(columns=existing_columns)
            if len(df) > 4:
                df = df.iloc[4:]
        return df
    except Exception as e:
        st.error(f"Error al preprocesar el archivo: {str(e)}")
        return None

def load_file(file, report_type, secure_handler):
    try:
        if file.type == "text/csv":
            df = pd.read_csv(file)
        else:
            if report_type == "visitas":
                df = pd.read_excel(file, sheet_name=0, header=4)
            elif report_type == "imagenes":
                df = pd.read_excel(file, sheet_name=1, header=8)
        
        if df is not None:
            df = preprocess_file(df, report_type)
            # Cifrar el DataFrame procesado
            encrypted_data = secure_handler.encrypt_dataframe(df)
            return encrypted_data, df  # Retornamos ambos para mostrar y almacenar
        return None, None
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None, None

def compare_files(df1, df2):
    try:
        common_columns = df1.columns.intersection(df2.columns)
        if not common_columns.empty:
            df1 = df1[common_columns]
            df2 = df2[common_columns]
            
            df1_tuples = set(df1.apply(tuple, axis=1))
            df2_tuples = set(df2.apply(tuple, axis=1))
            
            diff1 = df1[~df1.apply(tuple, axis=1).map(lambda x: x in df2_tuples)]
            diff2 = df2[~df2.apply(tuple, axis=1).map(lambda x: x in df1_tuples)]
            
            all_diff = pd.concat([diff1, diff2], ignore_index=True)
            all_diff['Fuente'] = ['Archivo 1'] * len(diff1) + ['Archivo 2'] * len(diff2)
            
            return all_diff
        else:
            st.warning("No se encontraron columnas comunes entre los archivos.")
            return None
    except Exception as e:
        st.error(f"Error al comparar los archivos: {str(e)}")
        return None

def main():
    try:
        load_css()
        show_home()

        # Autenticación con clave secreta
        password = st.text_input("Ingrese su clave de seguridad", type="password")
        if not password:
            st.warning("Por favor, ingrese una clave de seguridad para continuar.")
            return

        # Inicializar el manejador de seguridad
        encryption_key = get_encryption_key(password)
        secure_handler = SecureDataHandler(encryption_key)

        # Almacenar la clave en la sesión de forma segura
        if 'secure_handler' not in st.session_state:
            st.session_state['secure_handler'] = secure_handler

        # Selección de tipo de reporte
        report_type = st.selectbox("Seleccione el tipo de reporte", ["visitas", "imagenes"])

        # Sección de carga de archivos
        with st.container():
            col1, col2 = st.columns(2)

            with col1:
                with st.expander("📁 Archivo 1", expanded=True):
                    file1 = st.file_uploader("Seleccione el primer archivo", type=["csv", "xlsx", "xls"], key="file1")
                    if file1:
                        encrypted_data1, df1_display = load_file(file1, report_type, secure_handler)
                        if encrypted_data1 is not None:
                            st.dataframe(df1_display, use_container_width=True)
                            st.session_state['encrypted_df1'] = encrypted_data1

            with col2:
                with st.expander("📁 Archivo 2", expanded=True):
                    file2 = st.file_uploader("Seleccione el segundo archivo", type=["csv", "xlsx", "xls"], key="file2")
                    if file2:
                        encrypted_data2, df2_display = load_file(file2, report_type, secure_handler)
                        if encrypted_data2 is not None:
                            st.dataframe(df2_display, use_container_width=True)
                            st.session_state['encrypted_df2'] = encrypted_data2
                            st.session_state['file2_name'] = file2.name

        # Sección de comparación
        if all(key in st.session_state for key in ['encrypted_df1', 'encrypted_df2']):
            if st.button("Comparar Archivos", use_container_width=True):
                with st.spinner('Procesando comparación...'):
                    # Descifrar datos para comparación
                    df1 = secure_handler.decrypt_dataframe(st.session_state['encrypted_df1'])
                    df2 = secure_handler.decrypt_dataframe(st.session_state['encrypted_df2'])
                    
                    differences = compare_files(df1, df2)
                    
                    if differences is not None and not differences.empty:
                        st.markdown("<h3 style='color: blue;'>Resultados de la Comparación</h3>", unsafe_allow_html=True)
                        st.dataframe(differences, use_container_width=True)

                        # Cifrar resultados antes de la descarga
                        encrypted_differences = secure_handler.encrypt_dataframe(differences)
                        
                        # Preparar archivo cifrado para descarga
                        output = io.BytesIO()
                        output.write(encrypted_differences)
                        output.seek(0)

                        file_name = f"{st.session_state['file2_name'].split('.')[0]}_diferencias_cifrado.bin"
                        st.download_button(
                            label="📥 Descargar Resultados (Cifrados)",
                            data=output,
                            file_name=file_name,
                            mime="application/octet-stream",
                        )
                    else:
                        st.info("No se encontraron diferencias entre los archivos.")

    except Exception as e:
        st.error(f"Error en la aplicación: {str(e)}")

if __name__ == "__main__":
    main()