import base64
import requests
import streamlit as st


def upload_image_to_cloud(uploaded_file):
  """Mengunggah gambar ke ImgBB API secara otomatis menggunakan Secrets

  IMGBB_API_KEY.

  Mengembalikan direct URL gambar (cth: https://i.ibb.co/abc123/image.png).
  """
  if uploaded_file is None:
    return None

  api_key = st.secrets.get("IMGBB_API_KEY")
  if not api_key:
    st.error(
        "⚠️ Secrets IMGBB_API_KEY belum dikonfigurasi di Streamlit Cloud!"
    )
    return None

  url = "https://api.imgbb.com/1/upload"

  try:
    file_bytes = uploaded_file.getvalue()
    base64_image = base64.b64encode(file_bytes).decode("utf-8")

    payload = {
        "key": api_key,
        "image": base64_image,
        "name": uploaded_file.name,
    }

    res = requests.post(url, data=payload, timeout=30)
    res_json = res.json()

    if res.status_code == 200 and res_json.get("success"):
      return res_json["data"]["url"]
    else:
      error_msg = res_json.get("error", {}).get("message", "Unknown error")
      st.error(f"❌ Gagal upload ke ImgBB: {error_msg}")
      return None
  except Exception as e:
    st.error(f"❌ Terjadi kesalahan koneksi upload gambar: {e}")
    return None