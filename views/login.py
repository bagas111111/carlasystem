from database import get_connection
import streamlit as st


def render_login():
  st.title("🔐 Login Sistem HRIS Turso")
  st.markdown("Silakan masukkan *username* dan *password* akun Anda.")

  with st.form("form_login"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submit_login = st.form_submit_button("🚀 Masuk ke Sistem")

    if submit_login:
      if not username or not password:
        st.error("⚠️ Harap masukkan username dan password!")
      else:
        con = get_connection()
        # Cek database hris_users
        user = con.execute(
            """
                    SELECT id, company_id, username, full_name, role 
                    FROM hris_users 
                    WHERE username = ? AND password = ?
                """,
            (username, password),
        ).fetchone()

        if user:
          # Simpan status sesi ke st.session_state
          st.session_state["logged_in"] = True
          st.session_state["user_id"] = user[0]
          st.session_state["company_id"] = user[1]
          st.session_state["username"] = user[2]
          st.session_state["full_name"] = user[3]
          st.session_state["role"] = user[4]

          st.success(f"🎉 Selamat datang, {user[3]} ({user[4]})!")
          st.rerun()  # Muat ulang aplikasi untuk masuk ke menu utama
        else:
          st.error("❌ Username atau password salah!")