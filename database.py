import libsql
import streamlit as st


@st.cache_resource
def get_connection():
  url = "libsql://hris-bagasturso.aws-ap-south-1.turso.io"
  token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJnaWQiOiJhNzcxZTJlYy02OWI5LTQzMjctOTc2OC04ODQ2M2FkZDNjMDAiLCJpYXQiOjE3OTIyODQ2NTMsImtpZCI6IjJSYlRZS2taTmhOZXFrUXltUENZNGEzWk5nVjhqZEg5WDIzVTRaQmoybm8iLCJyaWQiOiIwNTg2ZmU0ZC04ODM4LTRiN2UtOWY5NC1iYzQzYzg2ZjNlYjMifQ.Bj0YnN3ThDcNtUfZNWFy94XtPjRQy4VzwqH5ozdwfFTzRgvi0rkqKePFj2FXjbjxG2TusVxp1sB5R3HYs3mUDA"

  con = libsql.connect(database="hris.db", sync_url=url, auth_token=token)
  con.sync()
  return con