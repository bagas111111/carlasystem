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

  # Tombol Manual Refresh Data (Opsional jika ingin memaksa tarik data terbaru dari Turso)
  col_title, col_btn = st.columns([4, 1])
  with col_btn:
    if st.button("🔄 Muat Ulang Data"):
      st.rerun()

  search_query = st.text_input(
      "🔍 Cari Berdasarkan Nama, NIP, atau Departemen:", ""
  )

  # Ambil data karyawan khusus untuk company_id yang sedang login
  # Menggunakan parameter tambahan agar tidak tersangkut cache lama
  query = f"SELECT * FROM hris_employees WHERE company_id = '{company_id}'"

  # Membaca data langsung dari koneksi aktif (fresh query)
  df_employees = pd.read_sql(query, con)

  if not df_employees.empty:
    # Filter pencarian
    if search_query:
      df_filtered = df_employees[
          df_employees["full_name"]
          .str.contains(search_query, case=False, na=False)
          | df_employees["employee_code"]
          .str.contains(search_query, case=False, na=False)
          | df_employees["department"]
          .str.contains(search_query, case=False, na=False)
      ]
    else:
      df_filtered = df_employees

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