import base64
import uuid
import requests
import streamlit as st


def upload_image_to_cloud(uploaded_file):
  """Mengunggah gambar ke ImgBB API dan memastikan format URL domain benar."""
  if uploaded_file is None:
    return None

  api_key = st.secrets.get("IMGBB_API_KEY")
  if not api_key:
    st.error("⚠️ Secrets IMGBB_API_KEY belum dikonfigurasi di Streamlit Cloud!")
    return None

  url = "https://api.imgbb.com/1/upload"

  try:
    file_bytes = uploaded_file.getvalue()
    base64_image = base64.b64encode(file_bytes).decode("utf-8")

    file_ext = (
        uploaded_file.name.split(".")[-1]
        if "." in uploaded_file.name
        else "jpg"
    )
    clean_filename = f"img_{uuid.uuid4().hex[:8]}.{file_ext}"

    payload = {
        "key": api_key,
        "image": base64_image,
        "name": clean_filename,
    }

    res = requests.post(url, data=payload, timeout=30)
    res_json = res.json()

    if res.status_code == 200 and res_json.get("success"):
      image_url = res_json["data"]["url"]

      # KOREKSI OTOMATIS: Pastikan domain i.ibb.co berubah menjadi i.ibb.co.com jika gagal dibuka
      if "https://i.ibb.co/" in image_url and ".co.com" not in image_url:
        image_url = image_url.replace(
            "https://i.ibb.co/", "https://i.ibb.co.com/"
        )

      return image_url
    else:
      error_msg = res_json.get("error", {}).get("message", "Unknown error")
      st.error(f"❌ Gagal upload ke ImgBB: {error_msg}")
      return None
  except Exception as e:
    st.error(f"❌ Terjadi kesalahan koneksi upload gambar: {e}")
    return None