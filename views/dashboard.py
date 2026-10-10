from database import get_connection
import pandas as pd
import streamlit as st


def render_dashboard():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  # Header & Tombol Refresh Manual
  col_t, col_b = st.columns([4, 1])
  with col_t:
    st.title("🏢 HRIS Dashboard Perusahaan")
  with col_b:
    if st.button("🔄 Muat Ulang"):
      st.rerun()

  st.markdown(
      "Selamat datang di Sistem Informasi SDM. Berikut adalah ringkasan"
      " eksekutif perusahaan Anda."
  )

  # Ambil ringkasan metrik dari database berdasarkan company_id sesi login
  try:
    df_count = pd.read_sql(
        f"""
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN status='ACTIVE' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN employment_status='PERMANENT' THEN 1 ELSE 0 END) as permanent,
                SUM(CASE WHEN employment_status='CONTRACT' THEN 1 ELSE 0 END) as contract
            FROM hris_employees
            WHERE company_id = '{company_id}'
        """,
        con,
    )
    total_emp = df_count["total"].iloc[0] or 0
    active_emp = df_count["active"].iloc[0] or 0
    perm_emp = df_count["permanent"].iloc[0] or 0
    contr_emp = df_count["contract"].iloc[0] or 0
  except Exception:
    total_emp, active_emp, perm_emp, contr_emp = 0, 0, 0, 0

  # Tampilkan Kartu Metrik
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Total Karyawan", f"{total_emp} Orang")
  col2.metric("Karyawan Aktif", f"{active_emp} Orang")
  col3.metric("Karyawan Tetap", f"{perm_emp} Orang")
  col4.metric("Karyawan Kontrak", f"{contr_emp} Orang")

  st.divider()

  st.subheader("⚡ Pintasan Menu Utama")
  c1, c2, c3 = st.columns(3)

  with c1:
    st.info("📋 **Daftar Karyawan**\n\nLihat seluruh data lengkap pegawai.")
  with c2:
    st.success("➕ **Tambah Karyawan**\n\nInput data pegawai baru via web.")
  with c3:
    st.warning("👤 **Profil & Karier**\n\nCek riwayat mutasi dan promosi.")

  st.divider()
  st.markdown(
      "📌 *Gunakan menu navigasi di sebelah kiri (sidebar) untuk berpindah ke"
      " halaman yang diinginkan.*"
  )