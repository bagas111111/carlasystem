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

  # Ambil menu pintasan dari database khusus company_id ini
  try:
    df_menus = pd.read_sql(
        f"""
            SELECT menu_group, menu_title, menu_url, image_url 
            FROM hris_company_menus 
            WHERE company_id = '{company_id}' 
            ORDER BY menu_group ASC, sort_order ASC
        """,
        con,
    )
  except Exception:
    df_menus = pd.DataFrame()

  if not df_menus.empty:
    # Tampilkan menu dalam bentuk grid kolom (3 kolom per baris) menggunakan kontainer natif Streamlit
    cols = st.columns(3)
    for idx, row in df_menus.iterrows():
      col_target = cols[idx % 3]
      with col_target:
        with st.container(border=True):
          # Jika ada image_url, tampilkan sebagai banner lebar di atas kartu
          if row["image_url"] and str(row["image_url"]).strip() != "":
            st.markdown(
                f"""
                    <div style="margin: -15px -15px 12px -15px; overflow: hidden; border-top-left-radius: 8px; border-top-right-radius: 8px; height: 120px;">
                        <img src="{row['image_url']}" style="width: 100%; height: 100%; object-fit: cover;" />
                    </div>
                """,
                unsafe_allow_html=True,
            )

          st.caption(f"📂 {row['menu_group']}")
          st.markdown(f"**{row['menu_title']}**")
          
          # Tombol tautan resmi Streamlit
          st.link_button("Buka Tautan 🚀", row["menu_url"], use_container_width=True)
  else:
    st.info(
        "💡 Belum ada pintasan menu yang diatur untuk perusahaan ini. Silakan"
        " buat melalui halaman Kelola Menu."
    )

  st.divider()
  st.markdown(
      "📌 *Gunakan menu navigasi di sebelah kiri (sidebar) untuk berpindah ke"
      " halaman yang diinginkan.*"
  )