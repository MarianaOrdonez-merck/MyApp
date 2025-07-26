import streamlit as st
import pandas as pd
import io
import openpyxl

# Configuración de la página
st.set_page_config(
    page_title="Diferencias entre conciliaciones",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
    st.markdown("<h2 style='color: blue;'>Diferencias de Conciliaciones</h2>", unsafe_allow_html=True)
    st.write("Sistema de comparación de archivos")

    st.write("""
        **Paso 1:** Seleccione el tipo de reporte  
        **Paso 2:** Cargue los archivos a comparar  
        **Paso 3:** Visualice y descargue los resultados
    """)

def preprocess_file(df, report_type, report_system):
    try:
        if report_type == "visitas":
            if report_system == "JReview viejo":
                # Headers empiezan en la línea 5 (index 4)
                # Esto se debe manejar en la carga, pero si ya cargaste sin header, aquí ajustamos:
                # Si df ya tiene headers, asumimos que se cargó con header=4
                # Seleccionamos solo las columnas necesarias

                selected_cols = ["Site\nNumber", "Screening\nNumber", "Arm", "Visit Name", "DOV", "Erroneous\nVisit"]
                existing_columns = [col for col in selected_cols if col in df.columns]
                df = df[existing_columns]
            else:  # MAP
                df.columns = df.columns.str.strip()
                selected_cols = ["Study", "Study Site", "Site\nName", "Subject Number", "Visit Name","Visit Mnemonic", "Patient Visit Date"]
                existing_columns = [col for col in selected_cols if col in df.columns]
                df = df[existing_columns]
        elif report_type == "imagenes":
            if len(df) > 9:
                df = df.iloc[10:]
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error al preprocesar el archivo: {str(e)}")
        return None

def load_file(file, report_type, report_system):
    try:
        if file.type == "text/csv":
            # Para JReview viejo + visitas, cargamos con header en fila 4 (index 4)
            if report_type == "visitas" and report_system == "JReview viejo":
                df = pd.read_csv(file, header=4)
            else:
                df = pd.read_csv(file)
        elif file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
            if report_type == "imagenes":
                # Cargar solo la segunda hoja (index 1)
                df = pd.read_excel(file, sheet_name=1, header=8, engine='openpyxl')
            else:
                if report_type == "visitas" and report_system == "JReview viejo":
                    # Headers en fila 5 (index 4)
                    df = pd.read_excel(file, sheet_name=0, header=4, engine='openpyxl')
                else:
                    df = pd.read_excel(file, sheet_name=0, engine='openpyxl')
        else:
            st.error("Tipo de archivo no soportado. Por favor, sube un archivo CSV o XLSX.")
            return None

        if df is not None:
            return preprocess_file(df, report_type, report_system)
        return None
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None

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

        # Primer selectbox: tipo de reporte general
        report_system = st.selectbox("Seleccione el sistema de reporte", ["MAP", "JReview viejo"])

        # Segundo selectbox: tipo de reporte específico
        report_type = st.selectbox("Seleccione el tipo de reporte", ["visitas", "imagenes"])

        with st.container():
            col1, col2 = st.columns(2)

            with col1:
                with st.expander("📁 Archivo 1", expanded=True):
                    file1 = st.file_uploader("Seleccione el primer archivo", type=["csv", "xlsx", "xls"], key="file1")
                    if file1:
                        df1 = load_file(file1, report_type, report_system)
                        if df1 is not None:
                            st.dataframe(df1, use_container_width=True)
                            st.session_state['df1'] = df1

            with col2:
                with st.expander("📁 Archivo 2", expanded=True):
                    file2 = st.file_uploader("Seleccione el segundo archivo", type=["csv", "xlsx", "xls"], key="file2")
                    if file2:
                        df2 = load_file(file2, report_type, report_system)
                        if df2 is not None:
                            st.dataframe(df2, use_container_width=True)
                            st.session_state['df2'] = df2
                            st.session_state['file2_name'] = file2.name

        if all(key in st.session_state for key in ['df1', 'df2']):
            if st.button("Comparar Archivos", use_container_width=True):
                with st.spinner('Procesando comparación...'):
                    differences = compare_files(st.session_state['df1'], st.session_state['df2'])

                    if differences is not None and not differences.empty:
                        st.markdown("<h3 style='color: blue;'>Resultados de la Comparación</h3>", unsafe_allow_html=True)
                        st.dataframe(differences, use_container_width=True)

                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            differences.to_excel(writer, sheet_name='Diferencias', index=False)
                        output.seek(0)

                        file_name = f"{st.session_state['file2_name'].split('.')[0]}_diferencias.xlsx"
                        st.download_button(
                            label="📥 Descargar Resultados",
                            data=output,
                            file_name=file_name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    else:
                        st.info("No se encontraron diferencias entre los archivos.")

    except Exception as e:
        st.error(f"Error en la aplicación: {str(e)}")

if __name__ == "__main__":
    main()
