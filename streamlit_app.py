import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
# 2. Nueva variable de texto
nuevo_nombre = st.text_input(
    'Introduce tu nombre (Nueva variable)', # Título del widget
    'Escribe aquí' # Texto por defecto
