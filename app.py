import streamlit as st
import pandas as pd
import io
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.colored_header import colored_header
from streamlit_extras.app_logo import add_logo
from streamlit_option_menu import option_menu
import hydralit_components as hc

# Configure the page
st.set_page_config(
    page_title="Conciliaciones Modernas",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS with improved styling
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
    colored_header(
        label="Conciliaciones Modernas",
        description="Sistema de comparación de archivos",
        color_name="blue-70"
    )

    # Modern info cards with error handling
    try:
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                hc.info_card(
                    title="Paso 1", 
                    content="Seleccione el tipo de reporte",
                    icon="file-earmark-text",
                    theme_override={"bgcolor": "#0066cc", "title_color": "white"}
                )
            
            with col2:
                hc.info_card(
                    title="Paso 2",
                    content="Cargue los archivos a comparar",
                    icon="cloud-upload",
                    theme_override={"bgcolor": "#28a745", "title_color": "white"}
                )
            
            with col3:
                hc.info_card(
                    title="Paso 3",
                    content="Visualice y descargue los resultados",
                    icon="download",
                    theme_override={"bgcolor": "#17a2b8", "title_color": "white"}
                )
    except Exception as e:
        st.error(f"Error al mostrar las tarjetas de información: {str(e)}")

def preprocess_file(df, report_type):
    try:
        if report_type == "visitas":
            columns_to_drop = ["Country", "Subject Number", "Visit\nOrder",
                             "Type of Visit", "DS01 Status", "Date of \nDisposition", "INEX"]
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

def load_file(file, report_type):
    try:
        if file.type == "text/csv":
            df = pd.read_csv(file)
        else:
            if report_type == "visitas":
                df = pd.read_excel(file, sheet_name=0, header=4)
            elif report_type == "imagenes":
                df = pd.read_excel(file, sheet_name=1, header=8)
        
        if df is not None:
            return preprocess_file(df, report_type)
        return None
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None

def compare_files(df1, df2):
    try:
        # Get common columns
        common_columns = df1.columns.intersection(df2.columns)
        if not common_columns.empty:
            df1 = df1[common_columns]
            df2 = df2[common_columns]
            
            # Convert DataFrames to sets of tuples for comparison
            df1_tuples = set(df1.apply(tuple, 1))
            df2_tuples = set(df2.apply(tuple, 1))
            
            # Find differences
            diff1 = df1[~df1.apply(tuple, 1).isin(df2_tuples)]
            diff2 = df2[~df2.apply(tuple, 1).isin(df1_tuples)]
            
            # Combine differences
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

        # Modern navigation menu
        selected = option_menu(
            menu_title=None,
            options=["Visitas", "Imágenes"],
            icons=["calendar-check", "image"],
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
        )

        report_type = "visitas" if selected == "Visitas" else "imagenes"

        # File upload section
        with st.container():
            col1, col2 = st.columns(2)

            with col1:
                with st.expander("📁 Archivo 1", expanded=True):
                    file1 = st.file_uploader(
                        "Seleccione el primer archivo",
                        type=["csv", "xlsx", "xls"],
                        key="file1"
                    )
                    if file1:
                        df1 = load_file(file1, report_type)
                        if df1 is not None:
                            st.dataframe(df1, use_container_width=True)
                            st.session_state['df1'] = df1

            with col2:
                with st.expander("📁 Archivo 2", expanded=True):
                    file2 = st.file_uploader(
                        "Seleccione el segundo archivo",
                        type=["csv", "xlsx", "xls"],
                        key="file2"
                    )
                    if file2:
                        df2 = load_file(file2, report_type)
                        if df2 is not None:
                            st.dataframe(df2, use_container_width=True)
                            st.session_state['df2'] = df2
                            st.session_state['file2_name'] = file2.name

        # Comparison section
        if all(key in st.session_state for key in ['df1', 'df2']):
            if st.button("Comparar Archivos", use_container_width=True):
                with st.spinner('Procesando comparación...'):
                    differences = compare_files(st.session_state['df1'], st.session_state['df2'])
                    
                    if differences is not None and not differences.empty:
                        colored_header(
                            label="Resultados de la Comparación",
                            description="Diferencias encontradas entre los archivos",
                            color_name="blue-70"
                        )
                        
                        st.dataframe(differences, use_container_width=True)

                        # Prepare download button
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