import datetime
from database import get_connection
import pandas as pd
import streamlit as st


def render_leave_management():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("📋 Rekap Data Cuti, Izin & Absensi Karyawan")
  st.markdown(
      "Menampilkan seluruh riwayat pengajuan izin/cuti karyawan dari formulir"
      " publik."
  )

  # --- FILTER TANGGAL & PENCARIAN ---
  col_f1, col_f2, col_f3 = st.columns([2, 2, 3])

  today = datetime.date.today()
  first_day_of_month = today.replace(day=1)

  with col_f1:
    start_date = st.date_input("Dari Tanggal", value=first_day_of_month)
  with col_f2:
    end_date = st.date_input("Sampai Tanggal", value=today)
  with col_f3:
    search_keyword = st.text_input(
        "🔍 Cari Nama, NIP, Cabang, atau Jenis Izin:", ""
    )

  start_str = start_date.strftime("%Y-%m-%d") if start_date else "1970-01-01"
  end_str = end_date.strftime("%Y-%m-%d") if end_date else "2099-12-31"

  # Query mengambil data lengkap termasuk branch dan device_pin
  query = f"""
        SELECT 
            l.id,
            e.full_name AS 'Nama Karyawan',
            e.employee_code AS 'NIP',
            e.device_pin AS 'PIN Absen',
            e.branch AS 'Cabang',
            e.department AS 'Departemen',
            l.submission_type AS 'Tipe Pengajuan',
            l.leave_type AS 'Jenis Izin',
            l.leave_date AS 'Tanggal Izin',
            l.start_time AS 'Jam Mulai',
            l.end_time AS 'Jam Selesai',
            l.notes AS 'Catatan / Alasan',
            l.created_at AS 'Waktu Submit'
        FROM hris_leaves l
        JOIN hris_employees e ON l.employee_id = e.id
        WHERE l.company_id = '{company_id}'
          AND l.leave_date >= '{start_str}' 
          AND l.leave_date <= '{end_str}'
        ORDER BY l.leave_date DESC, l.created_at DESC
    """

  df_leaves = pd.read_sql(query, con)

  if not df_leaves.empty:
    # Filter tambahan kata kunci (Nama, NIP, Cabang, atau Jenis Izin)
    if search_keyword:
      df_filtered = df_leaves[
          df_leaves["Nama Karyawan"]
          .str.contains(search_keyword, case=False, na=False)
          | df_leaves["NIP"].str.contains(search_keyword, case=False, na=False)
          | df_leaves["Cabang"].str.contains(
              search_keyword, case=False, na=False
          )
          | df_leaves["Jenis Izin"].str.contains(
              search_keyword, case=False, na=False
          )
      ]
    else:
      df_filtered = df_leaves

    st.markdown(
        f"Menampilkan **{len(df_filtered)}** data pengajuan dari rentang"
        f" **{start_str}** s.d **{end_str}**."
    )

    # Tampilkan tabel seluruh kolom (sembunyikan id teknis)
    display_df = df_filtered.drop(columns=["id"])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

  else:
    st.info(
        f"Tidak ada data pengajuan izin pada rentang tanggal {start_str} s.d"
        f" {end_str}."
    )