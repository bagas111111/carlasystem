import libsql
import streamlit as st


@st.cache_resource
def get_connection():
  url = "libsql://hris-bagasturso.aws-ap-south-1.turso.io"
  token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3OTE3MjM2NTIsImlhdCI6MTc5MTYzNzI1MiwiaWQiOiIwMWExMjVjZS02ZjAxLTc3Y2EtODQwMS1jZGViNjk1MTk3NmUiLCJraWQiOiIyUmJUWUtrWk5oTmVxa1F5bVBDWTRhM1pOZ1Y4amRIOVgyM1U0WkJqMm5vIiwicmlkIjoiZTJhOGE0NTgtOTgyNi00ZmZlLTg5YjgtZGQ5NTVlZmRhNjMxIn0.XJmqS8g29gAJAmghUZGoR4MToHbQONYnqts62xLRsgTa0R7QjPeZYMIljYzMUQkFRjAf_RDKnHt84bfY0BWYCQ"

  con = libsql.connect(database="hris.db", sync_url=url, auth_token=token)
  con.sync()
  return con