from database import get_connection
import pandas as pd
import streamlit as st


def render_employees():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("📋 Data Lengkap Seluruh Karyawan")
  st.markdown(
      "Menampilkan seluruh kolom informasi pegawai sesuai database perusahaan"
      " Anda."
  )

  # Tombol Manual Refresh Data
  col_title, col_btn = st.columns([4, 1])
  with col_btn:
    if st.button("🔄 Muat Ulang Data"):
      st.rerun()

  # Baris Filter: Pencarian Teks & Filter Selectbox
  col1, col2, col3 = st.columns([2, 1, 1])

  with col1:
    search_query = st.text_input(
        "🔍 Cari Berdasarkan Nama, NIP, atau Departemen:", ""
    )

  with col2:
    status_filter = st.selectbox(
        "Filter Status Sistem",
        ["ALL", "ACTIVE", "SUSPENDED", "RESIGNED", "TERMINATED"],
    )

  with col3:
    employment_filter = st.selectbox(
        "Filter Kepegawaian",
        ["ALL", "PERMANENT", "CONTRACT", "PROBATION", "INTERN", "FREELANCE"],
    )

  # Ambil data karyawan khusus untuk company_id yang sedang login
  query = f"SELECT * FROM hris_employees WHERE company_id = '{company_id}'"
  df_employees = pd.read_sql(query, con)

  if not df_employees.empty:
    df_filtered = df_employees.copy()

    # 1. Filter berdasarkan Search Query (Nama / NIP / Departemen)
    if search_query:
      df_filtered = df_filtered[
          df_filtered["full_name"]
          .str.contains(search_query, case=False, na=False)
          | df_filtered["employee_code"]
          .str.contains(search_query, case=False, na=False)
          | df_filtered["department"]
          .str.contains(search_query, case=False, na=False)
      ]

    # 2. Filter berdasarkan Status Sistem (jika tidak pilih ALL)
    if status_filter != "ALL":
      df_filtered = df_filtered[df_filtered["status"] == status_filter]

    # 3. Filter berdasarkan Status Kepegawaian (jika tidak pilih ALL)
    if employment_filter != "ALL":
      df_filtered = df_filtered[
          df_filtered["employment_status"] == employment_filter
      ]

    st.markdown(
        f"Menampilkan **{len(df_filtered)}** dari total **{len(df_employees)}**"
        " data karyawan."
    )

    if "id" in df_filtered.columns:
      display_df = df_filtered.drop(columns=["id"])
    else:
      display_df = df_filtered

    st.dataframe(display_df, use_container_width=True, hide_index=True)
  else:
    st.warning(
        "Belum ada data karyawan di dalam database untuk perusahaan ini."
    )