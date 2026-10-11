import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def render_add_employee():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("➕ Form Pendaftaran Karyawan Baru (Lengkap)")
  st.markdown(
      "Formulir komprehensif untuk mendaftarkan data pegawai baru beserta"
      " pencatatan riwayat karier awal ke Cloud."
  )

  with st.form("form_tambah_karyawan_lengkap"):
    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Info Pekerjaan & Absensi",
            "👤 Data Pribadi & Kontak",
            "🎓 Pendidikan & Karier Awal",
        ]
    )

    with tab1:
      st.subheader("Informasi Pekerjaan & Kepegawaian")
      col1, col2 = st.columns(2)

      with col1:
        employee_code = st.text_input("NIP / Kode Karyawan (Contoh: EMP001)")
        device_pin = st.text_input("PIN Absen Mesin (Fingerprint) *Wajib")
        branch = st.text_input("Cabang (Branch) (Contoh: Pusat Jakarta)")
        department = st.text_input("Departemen (Contoh: IT & Engineering)")
        job_title = st.text_input(
            "Jabatan / Job Title (Contoh: Software Engineer)"
        )
        work_location_type = st.selectbox(
            "Tipe Lokasi Kerja",
            ["ON_SITE", "HYBRID", "REMOTE", "FIELD_WORK"],
        )

      with col2:
        employment_status = st.selectbox(
            "Status Kepegawaian",
            ["PERMANENT", "CONTRACT", "PROBATION", "INTERN", "FREELANCE"],
        )
        status = st.selectbox(
            "Status Sistem Karyawan",
            ["ACTIVE", "SUSPENDED", "RESIGNED", "TERMINATED"],
        )
        
        # Diubah ke text_input agar fleksibel untuk tanggal lampau / jauh
        join_date = st.text_input(
            "Tanggal Bergabung (Format: YYYY-MM-DD)", placeholder="2025-01-01"
        )
        contract_end_date = st.text_input(
            "Akhir Kontrak (Opsional, Format: YYYY-MM-DD)", placeholder="2027-12-31"
        )
        
        is_rejoin = st.selectbox(
            "Apakah Karyawan Rejoin?",
            [0, 1],
            format_func=lambda x: "Ya (Rejoin)" if x == 1 else "Tidak",
        )
        rejoin_count = st.number_input(
            "Jumlah Rejoin", min_value=0, value=0, step=1
        )

    with tab2:
      st.subheader("Data Pribadi, Identitas & Alamat")
      col3, col4 = st.columns(2)

      with col3:
        full_name = st.text_input("Nama Lengkap *Wajib")
        nick_name = st.text_input("Nama Panggilan")
        gender = st.selectbox("Gender", ["MALE", "FEMALE"])
        marital_status = st.selectbox(
            "Status Pernikahan", ["SINGLE", "MARRIED", "DIVORCED", "WIDOWED"]
        )
        place_of_birth = st.text_input("Tempat Lahir")
        
        # Diubah ke text_input agar bebas isi tanggal lahir masa lalu
        date_of_birth = st.text_input(
            "Tanggal Lahir (Format: YYYY-MM-DD)", placeholder="1995-08-17"
        )
        
        phone_number = st.text_input("Nomor Telepon / WhatsApp")
        email = st.text_input("Alamat Email")

      with col4:
        # Pilihan Tipe Identitas sesuai standar sistem
        identity_options = {
            "KTP (NIK)": "KTP",
            "Paspor": "PASSPORT",
            "KITAS / KITAP": "KITAS",
            "KTA (Kartu Tanda Anggota)": "KTA",
            "Lainnya": "OTHER",
        }
        selected_id_label = st.selectbox("Tipe Identitas", list(identity_options.keys()))
        identity_type = identity_options[selected_id_label]

        identity_number = st.text_input("Nomor Identitas / Nomor Kartu")
        family_card_number = st.text_input("Nomor Kartu Keluarga (KK)")
        identity_address = st.text_area("Alamat Sesuai KTP")
        is_same_as_identity_address = st.selectbox(
            "Alamat Tinggal Sama dengan KTP?",
            [1, 0],
            format_func=lambda x: "Ya" if x == 1 else "Tidak",
        )
        residential_address = st.text_area(
            "Alamat Domisili / Tinggal Saat Ini"
        )

    with tab3:
      st.subheader("Riwayat Pendidikan & Catatan Karier Awal")
      col5, col6 = st.columns(2)

      with col5:
        last_education_level = st.selectbox(
            "Jenjang Pendidikan Terakhir",
            ["SD", "SMP", "SMA/SMK", "D3", "S1", "S2", "S3", "Lainnya"],
        )
        last_education_institution = st.text_input("Nama Institusi / Sekolah")

      with col6:
        last_education_major = st.text_input("Jurusan / Program Studi")
        last_education_year = st.number_input(
            "Tahun Lulus", min_value=1950, max_value=2030, value=2020, step=1
        )

      st.divider()
      st.markdown("##### 📝 Catatan Tambahan untuk Karier Pertama (NEW_HIRE)")
      career_notes = st.text_area(
          "Catatan / Keterangan Penempatan Awal",
          value="Pendaftaran awal pegawai baru",
      )

    submitted = st.form_submit_button(
        "💾 Simpan Data Karyawan & Karier ke Cloud"
    )

    if submitted:
      if not full_name or not device_pin:
        st.error(
            "⚠️ Harap isi minimal Nama Lengkap dan PIN Absen Mesin (Device PIN)!"
        )
      else:
        try:
          emp_id = str(uuid.uuid4())
          career_id = str(uuid.uuid4())

          # Pembersihan string tanggal kosong
          join_str = join_date.strip() if join_date and join_date.strip() else None
          contract_end_str = contract_end_date.strip() if contract_end_date and contract_end_date.strip() else None
          dob_str = date_of_birth.strip() if date_of_birth and date_of_birth.strip() else None

          # 1. Insert ke hris_employees dengan company_id aktif
          con.execute(
              """
                        INSERT INTO hris_employees (
                            id, company_id, employee_code, device_pin, full_name, nick_name,
                            branch, department, job_title, work_location_type, employment_status,
                            contract_end_date, join_date, status, is_rejoin, rejoin_count,
                            identity_type, identity_number, gender, place_of_birth, date_of_birth,
                            phone_number, email, identity_address, is_same_as_identity_address,
                            residential_address, marital_status, family_card_number,
                            last_education_level, last_education_institution, last_education_major,
                            last_education_year
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
              (
                  emp_id,
                  company_id,
                  employee_code,
                  device_pin,
                  full_name,
                  nick_name,
                  branch,
                  department,
                  job_title,
                  work_location_type,
                  employment_status,
                  contract_end_str,
                  join_str,
                  status,
                  int(is_rejoin),
                  int(rejoin_count),
                  identity_type,
                  identity_number,
                  gender,
                  place_of_birth,
                  dob_str,
                  phone_number,
                  email,
                  identity_address,
                  int(is_same_as_identity_address),
                  residential_address,
                  marital_status,
                  family_card_number,
                  last_education_level,
                  last_education_institution,
                  last_education_major,
                  int(last_education_year),
              ),
          )

          # 2. Insert Otomatis ke hris_employee_careers
          con.execute(
              """
                        INSERT INTO hris_employee_careers (
                            id, company_id, employee_id, type, employment_status,
                            job_title, department, start_date, is_current, notes
                        ) VALUES (?, ?, ?, 'NEW_HIRE', ?, ?, ?, ?, 1, ?)
                    """,
              (
                  career_id,
                  company_id,
                  emp_id,
                  employment_status,
                  job_title,
                  department,
                  join_str if join_str else "2026-01-01",
                  career_notes,
              ),
          )

          con.commit()
          con.sync()
          st.success(
              f"🎉 Data karyawan **{full_name}** berhasil disimpan!"
          )
          st.rerun()
        except Exception as e:
          st.error(f"❌ Gagal menyimpan data ke database. Error: {str(e)}")