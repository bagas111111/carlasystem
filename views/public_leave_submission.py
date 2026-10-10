import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def render_public_leave_submission():
  con = get_connection()
  st.title("📝 Portal Pengajuan Absensi, Cuti & Izin")
  st.markdown(
      "Silakan pilih perusahaan, cari nama Anda, lalu lengkapi formulir"
      " pengajuan di bawah ini."
  )

  # 1. Pilih Perusahaan Terlebih Dahulu (Karena form publik)
  df_companies = pd.read_sql(
      "SELECT id, company_name, company_code FROM hris_companies", con
  )

  if df_companies.empty:
    st.warning("⚠️ Belum ada data perusahaan terdaftar di sistem.")
    return

  comp_options = {
      f"{row['company_name']} ({row['company_code']})": row["id"]
      for index, row in df_companies.iterrows()
  }
  selected_comp_label = st.selectbox(
      "🏢 Pilih Perusahaan / Tenant *Wajib", list(comp_options.keys())
  )
  company_id = comp_options[selected_comp_label]

  st.divider()

  # 2. Ambil Daftar Karyawan Berdasarkan Perusahaan yang Dipilih
  df_emp = pd.read_sql(
      f"SELECT id, full_name, employee_code, department FROM hris_employees WHERE company_id = '{company_id}'",
      con,
  )

  if df_emp.empty:
    st.warning(
        "⚠️ Belum ada data karyawan terdaftar untuk perusahaan yang dipilih."
    )
    return

  emp_options = {
      f"{row['full_name']} (NIP: {row['employee_code']} - Dept: {row['department']})": row[
          "id"
      ]
      for index, row in df_emp.iterrows()
  }

  with st.form("form_public_leave"):
    selected_emp_label = st.selectbox(
        "🔍 Cari & Pilih Nama Karyawan *Wajib", list(emp_options.keys())
    )
    employee_id = emp_options[selected_emp_label]

    col1, col2 = st.columns(2)

    with col1:
      submission_type = st.selectbox(
          "Jenis Pengajuan", ["BARU (New)", "PEMBETULAN (Correction)"]
      )
      leave_type = st.selectbox(
          "Jenis Izin / Absensi",
          [
              "SAKIT",
              "IZIN_KELUAR_SEMENTARA",
              "PULANG_AWAL",
              "IZIN_TERLAMBAT",
              "TERLAMBAT_MENDADAK",
              "DINAS_LUAR",
              "CUTI",
              "IJIN_KHUSUS",
          ],
      )
      leave_date = st.date_input("Tanggal Pengajuan *Wajib")

    with col2:
      start_time = st.text_input(
          "Jam Mulai (Format HH:MM, Contoh: 08:00)", placeholder="08:00"
      )
      end_time = st.text_input(
          "Jam Selesai (Format HH:MM, Contoh: 17:00)", placeholder="17:00"
      )
      notes = st.text_area(
          "Catatan / Alasan Pengajuan *Wajib",
          placeholder="Tuliskan keterangan izin atau alasan dengan jelas...",
      )

    submitted_leave = st.form_submit_button(
        "🚀 Kirim Pengajuan Absensi / Izin"
    )

    if submitted_leave:
      if not notes:
        st.error("⚠️ Harap isi catatan atau alasan pengajuan!")
      else:
        try:
          leave_id = str(uuid.uuid4())
          date_str = leave_date.strftime("%Y-%m-%d") if leave_date else None

          con.execute(
              """
                        INSERT INTO hris_leaves (
                            id, company_id, employee_id, submission_type, 
                            leave_type, leave_date, start_time, end_time, notes, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                    """,
              (
                  leave_id,
                  company_id,
                  employee_id,
                  submission_type.split(" ")[0],
                  leave_type,
                  date_str,
                  start_time,
                  end_time,
                  notes,
              ),
          )
          con.commit()
          con.sync()
          st.success(
              "🎉 Pengajuan izin/cuti Anda berhasil dikirim ke sistem! Menunggu"
              " persetujuan HR."
          )
          st.rerun()
        except Exception as e:
          st.error(f"❌ Gagal mengirim pengajuan: {str(e)}")

  # 3. Riwayat Pengajuan Izin Terakhir dari Karyawan Tersebut
  st.divider()
  st.subheader("📋 Riwayat Pengajuan Izin Anda Sebelumnya")
  history_query = f"""
        SELECT 
            leave_type AS 'Jenis Izin',
            submission_type AS 'Tipe',
            leave_date AS 'Tanggal',
            start_time AS 'Jam Mulai',
            end_time AS 'Jam Selesai',
            notes AS 'Catatan',
            status AS 'Status'
        FROM hris_leaves 
        WHERE employee_id = '{employee_id}'
        ORDER BY created_at DESC 
        LIMIT 10
    """
  df_history = pd.read_sql(history_query, con)

  if not df_history.empty:
    st.dataframe(df_history, use_container_width=True, hide_index=True)
  else:
    st.info("Belum ada riwayat pengajuan untuk karyawan yang dipilih.")