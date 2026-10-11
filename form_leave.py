import datetime
import uuid
from database import get_connection
import pandas as pd
import streamlit as st

# Konfigurasi halaman khusus form publik (bersih tanpa riwayat, tanpa sidebar)
st.set_page_config(
    page_title="Form Pengajuan Cuti & Izin", page_icon="📝", layout="centered"
)


def render_form_leave():
  con = get_connection()

  # Inisialisasi status submit di session state
  if "form_submitted" not in st.session_state:
    st.session_state["form_submitted"] = False

  # Tangkap parameter dari URL menggunakan 'id' (Cth: ?id=xxxx-xxxx)
  query_params = st.query_params
  company_id = query_params.get("id")

  st.title("📝 Portal Pengajuan Cuti, Izin & Absensi")

  # Validasi Wajib: Jika URL tidak membawa parameter id, tolak akses
  if not company_id:
    st.error(
        "❌ **Link Form Tidak Valid!**\n\nHarap gunakan tautan (URL) resmi yang"
        " telah dibagikan oleh bagian HR / Personalia perusahaan Anda."
    )
    return

  # Validasi apakah id tersebut benar-benar ada di database hris_companies
  df_check = pd.read_sql(
      f"SELECT company_name, company_code FROM hris_companies WHERE id = '{company_id}'",
      con,
  )
  if df_check.empty:
    st.error(
        "❌ **Perusahaan Tidak Ditemukan!**\n\nID pada tautan tidak valid atau"
        " sudah kadaluarsa."
    )
    return

  comp_name = df_check.iloc[0]["company_name"]
  st.success(f"🏢 Perusahaan: **{comp_name}**")
  st.divider()

  # JIKA SUDAH DISUBMIT: Tampilkan layar selesai (ala Google Form) & kunci form
  if st.session_state["form_submitted"]:
    st.balloons()
    st.success("🎉 **Pengajuan Berhasil Dikirim!**")
    st.info(
        "Terima kasih. Formulir pengajuan cuti/izin Anda telah berhasil"
        " direkam oleh sistem."
    )
    if st.button("🔄 Kirim Pengajuan Lain"):
      st.session_state["form_submitted"] = False
      st.rerun()
    return

  # Ambil Daftar Karyawan HANYA untuk Company ID tersebut secara fresh dari DB
  df_emp = pd.read_sql(
      f"SELECT id, full_name, employee_code, department FROM hris_employees WHERE company_id = '{company_id}'",
      con,
  )

  if df_emp.empty:
    st.warning(
        "⚠️ Belum ada data karyawan terdaftar untuk perusahaan ini. Silakan"
        " hubungi HR Anda."
    )
    return

  emp_options = {
      f"{row['full_name']} (NIP: {row['employee_code']} - Dept: {row['department']})": row[
          "id"
      ]
      for index, row in df_emp.iterrows()
  }

  with st.form("form_leave_standalone"):
    st.markdown(
        "Silakan cari nama Anda dan lengkapi formulir pengajuan di bawah ini."
    )

    selected_emp_label = st.selectbox(
        "🔍 Cari & Pilih Nama Anda *Wajib", list(emp_options.keys())
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
              "IZIN_KHUSUS",
          ],
      )
      leave_date = st.date_input("Tanggal Pengajuan *Wajib")

    with col2:
      # Menggunakan st.time_input agar format jam wajib valid (HH:MM) dan bersih dari karakter ngawur
      start_time_val = st.time_input(
          "Jam Mulai *Wajib", value=datetime.time(8, 0)
      )
      end_time_val = st.time_input(
          "Jam Selesai *Wajib", value=datetime.time(17, 0)
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

          # Ubah objek time menjadi string standar format 'HH:MM'
          start_str = (
              start_time_val.strftime("%H:%M") if start_time_val else None
          )
          end_str = end_time_val.strftime("%H:%M") if end_time_val else None

          con.execute(
              """
                        INSERT INTO hris_leaves (
                            id, company_id, employee_id, submission_type, 
                            leave_type, leave_date, start_time, end_time, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
              (
                  leave_id,
                  company_id,
                  employee_id,
                  submission_type.split(" ")[0],
                  leave_type,
                  date_str,
                  start_str,
                  end_str,
                  notes,
              ),
          )
          con.commit()
          con.sync()

          st.session_state["form_submitted"] = True
          st.rerun()
        except Exception as e:
          st.error(f"❌ Gagal mengirim pengajuan: {str(e)}")


if __name__ == "__main__":
  render_form_leave()