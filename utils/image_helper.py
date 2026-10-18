import requests
import streamlit as st


def upload_image_to_cloud(uploaded_file):
  """Mengunggah gambar ke Catbox.moe secara anonim tanpa API Key.

  Mengembalikan direct URL gambar (cth: https://files.catbox.moe/abc123.jpg).
  """
  if uploaded_file is None:
    return None

  url = "https://catbox.moe/user/api.php"

  try:
    file_bytes = uploaded_file.getvalue()
    files = {"fileToUpload": (uploaded_file.name, file_bytes)}
    data = {"reqtype": "fileupload"}

    response = requests.post(url, data=data, files=files, timeout=30)

    if response.status_code == 200 and response.text.startswith("http"):
      return response.text.strip()
    else:
      st.error(f"❌ Gagal unggah foto ke Catbox: {response.text}")
      return None
  except Exception as e:
    st.error(f"❌ Terjadi kesalahan koneksi unggah gambar: {e}")
    return None