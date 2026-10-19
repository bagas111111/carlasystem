import requests
import streamlit as st

def upload_image_to_cloud(uploaded_file):
    """
    Mengunggah gambar ke Catbox.moe secara anonim.
    Mengembalikan direct URL gambar (cth: https://files.catbox.moe/abc123.jpg).
    """
    if uploaded_file is None:
        return None

    url = "https://catbox.moe/user/api.php"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        file_bytes = uploaded_file.getvalue()
        # Reset posisi pointer file
        uploaded_file.seek(0)
        
        files = {
            "fileToUpload": (uploaded_file.name, file_bytes, uploaded_file.type)
        }
        data = {
            "reqtype": "fileupload"
        }

        response = requests.post(url, headers=headers, data=data, files=files, timeout=30)

        if response.status_code == 200 and response.text.strip().startswith("http"):
            return response.text.strip()
        else:
            st.error(f"❌ Gagal upload (HTTP {response.status_code}): {response.text[:200]}")
            return None
    except Exception as e:
        st.error(f"❌ Terjadi kesalahan koneksi upload gambar: {e}")
        return None