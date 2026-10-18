import libsql
import streamlit as st


@st.cache_resource
def get_connection():
  # Dia otomatis nyari kunci aman dari brankas Secrets Streamlit
  url = st.secrets["TURSO_URL"]
  token = st.secrets["TURSO_TOKEN"]

  con = libsql.connect(database="hris.db", sync_url=url, auth_token=token)
  con.sync()
  return con