import datetime
from database import get_connection
import pandas as pd
import streamlit as st


def render_edit_employee():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("✏️ Edit Data Master Karyawan")
  st.markdown(
      "Pilih karyawan yang ingin diperbarui datanya. Seluruh kolom master"
      " pegawai dapat disunting di sini."
  )

  df_list = pd.read_sql(
      f"SELECT id, full_name, employee_code FROM hris_employees WHERE company_id = '{company_id}'",
      con,
  )

  if df_list.empty:
    st.warning("Belum ada data karyawan di database untuk perusahaan ini.")
    return

  emp_options = {
      f"{row['full_name']} ({row['employee_code']})": row["id"]
      for index, row in df_list.iterrows()
  }
  selected_name = st.selectbox(
      "Pilih Karyawan yang akan Diedit:", list(emp_options.keys())
  )
  selected_id = emp_options[selected_name]

  st.divider()

  emp_query = f"SELECT * FROM hris_employees WHERE id = '{selected_id}' AND company_id = '{company_id}'"
  df_emp = pd.read_sql(emp_query, con)

  if df_emp.empty:
    st.error("Data karyawan tidak ditemukan.")
    return

  emp = df_emp.iloc[0]

  def parse_date(val, default_date=datetime.date(1990, 1, 1)):
    if pd.notnull(val) and val != "" and val != "None" and val is not None:
      try:
        return pd.to_datetime(val).date()
      except Exception:
        return default_date
    return default_date

  min_general_date = datetime.date(1970, 1, 1)
  max_general_date = datetime.date(2050, 12, 31)

  with st.form(f"form_edit_employee_{selected_id}"):
    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Info Pekerjaan & Status",
            "👤 Data Pribadi & Kontak",
            "🎓 Pendidikan & Alamat",
        ]
    )

    with tab1:
      st.subheader("Edit Informasi Pekerjaan & Kepegawaian")
      col1, col2 = st.columns(2)

      with col1:
        employee_code = st.text_input(
            "NIP / Kode Karyawan", value=str(emp.get("employee_code") or "")
        )
        device_pin = st.text_input(
            "PIN Absen Mesin (Fingerprint)",
            value=str(emp.get("device_pin") or ""),
        )
        branch = st.text_input(
            "Cabang (Branch)", value=str(emp.get("branch") or "")
        )
        department = st.text_input(
            "Departemen", value=str(emp.get("department") or "")
        )
        job_title = st.text_input(
            "Jabatan / Job Title", value=str(emp.get("job_title") or "")
        )

        loc_types = ["ON_SITE", "HYBRID", "REMOTE", "FIELD_WORK"]
        curr_loc = (
            emp.get("work_location_type")
            if emp.get("work_location_type") in loc_types
            else "ON_SITE"
        )
        work_location_type = st.selectbox(
            "Tipe Lokasi Kerja", loc_types, index=loc_types.index(curr_loc)
        )

        emp_statuses = [
            "PERMANENT",
            "CONTRACT",
            "PROBATION",
            "INTERN",
            "FREELANCE",
        ]
        curr_estat = (
            emp.get("employment_status")
            if emp.get("employment_status") in emp_statuses
            else "CONTRACT"
        )
        employment_status = st.selectbox(
            "Status Kepegawaian",
            emp_statuses,
            index=emp_statuses.index(curr_estat),
        )

      with col2:
        statuses = ["ACTIVE", "SUSPENDED", "RESIGNED", "TERMINATED"]
        curr_stat = (
            emp.get("status") if emp.get("status") in statuses else "ACTIVE"
        )
        status = st.selectbox(
            "Status Sistem Karyawan",
            statuses,
            index=statuses.index(curr_stat),
        )

        join_date = st.date_input(
            "Tanggal Bergabung",
            value=parse_date(emp.get("join_date")),
            min_value=min_general_date,
            max_value=max_general_date,
        )
        contract_end_date = st.date_input(
            "Akhir Kontrak",
            value=parse_date(emp.get("contract_end_date")),
            min_value=min_general_date,
            max_value=max_general_date,
        )
        resign_date = st.date_input(
            "Tanggal Resign",
            value=parse_date(emp.get("resign_date")),
            min_value=min_general_date,
            max_value=max_general_date,
        )

        exit_type = st.text_input(
            "Tipe Keluar (Exit Type)", value=str(emp.get("exit_type") or "")
        )
        exit_reason = st.text_input(
            "Alasan Keluar (Exit Reason)",
            value=str(emp.get("exit_reason") or ""),
        )

        is_rejoin_val = int(emp.get("is_rejoin") or 0)
        is_rejoin = st.selectbox(
            "Apakah Karyawan Rejoin?",
            [0, 1],
            index=is_rejoin_val,
            format_func=lambda x: "Ya (Rejoin)" if x == 1 else "Tidak",
        )
        rejoin_count = st.number_input(
            "Jumlah Rejoin",
            min_value=0,
            value=int(emp.get("rejoin_count") or 0),
            step=1,
        )

    with tab2:
      st.subheader("Edit Data Pribadi & Kontak")
      col3, col4 = st.columns(2)

      with col3:
        full_name = st.text_input(
            "Nama Lengkap *Wajib", value=str(emp.get("full_name") or "")
        )
        nick_name = st.text_input(
            "Nama Panggilan", value=str(emp.get("nick_name") or "")
        )

        genders = ["MALE", "FEMALE"]
        curr_gen = (
            emp.get("gender") if emp.get("gender") in genders else "MALE"
        )
        gender = st.selectbox(
            "Gender", genders, index=genders.index(curr_gen)
        )

        marital_statuses = ["SINGLE", "MARRIED", "DIVORCED", "WIDOWED"]
        curr_mar = (
            emp.get("marital_status")
            if emp.get("marital_status") in marital_statuses
            else "SINGLE"
        )
        marital_status = st.selectbox(
            "Status Pernikahan",
            marital_statuses,
            index=marital_statuses.index(curr_mar),
        )

        place_of_birth = st.text_input(
            "Tempat Lahir", value=str(emp.get("place_of_birth") or "")
        )

        raw_dob = emp.get("date_of_birth")
        str_dob = str(raw_dob) if pd.notnull(raw_dob) and raw_dob != "None" else ""
        date_of_birth_input = st.text_input(
            "Tanggal Lahir (Format: YYYY-MM-DD)",
            value=str_dob,
            placeholder="1990-08-17",
        )

      with col4:
        phone_number = st.text_input(
            "Nomor Telepon / WhatsApp",
            value=str(emp.get("phone_number") or ""),
        )
        email = st.text_input(
            "Alamat Email", value=str(emp.get("email") or "")
        )

        id_types = ["KTP", "PASSPORT", "SIM"]
        curr_idt = (
            emp.get("identity_type")
            if emp.get("identity_type") in id_types
            else "KTP"
        )
        identity_type = st.selectbox(
            "Tipe Identitas", id_types, index=id_types.index(curr_idt)
        )

        identity_number = st.text_input(
            "Nomor Identitas / KTP",
            value=str(emp.get("identity_number") or ""),
        )
        family_card_number = st.text_input(
            "Nomor Kartu Keluarga (KK)",
            value=str(emp.get("family_card_number") or ""),
        )

    with tab3:
      st.subheader("Edit Pendidikan & Alamat Domisili")
      col5, col6 = st.columns(2)

      with col5:
        identity_address = st.text_area(
            "Alamat Sesuai KTP", value=str(emp.get("identity_address") or "")
        )

        is_same_val = int(emp.get("is_same_as_identity_address") or 1)
        is_same_as_identity_address = st.selectbox(
            "Alamat Tinggal Sama dengan KTP?",
            [1, 0],
            index=0 if is_same_val == 1 else 1,
            format_func=lambda x: "Ya" if x == 1 else "Tidak",
        )
        residential_address = st.text_area(
            "Alamat Domisili / Tinggal Saat Ini",
            value=str(emp.get("residential_address") or ""),
        )

      with col6:
        edu_levels = ["SD", "SMP", "SMA/SMK", "D3", "S1", "S2", "S3", "Lainnya"]
        curr_edu = (
            emp.get("last_education_level")
            if emp.get("last_education_level") in edu_levels
            else "S1"
        )
        last_education_level = st.selectbox(
            "Jenjang Pendidikan Terakhir",
            edu_levels,
            index=edu_levels.index(curr_edu),
        )

        last_education_institution = st.text_input(
            "Nama Institusi / Sekolah",
            value=str(emp.get("last_education_institution") or ""),
        )
        last_education_major = st.text_input(
            "Jurusan / Program Studi",
            value=str(emp.get("last_education_major") or ""),
        )
        last_education_year = st.number_input(
            "Tahun Lulus",
            min_value=1950,
            max_value=2030,
            value=int(emp.get("last_education_year") or 2020),
            step=1,
        )

    submitted_update = st.form_submit_button("💾 Simpan Perubahan Data Karyawan")

    if submitted_update:
      if not full_name or not device_pin:
        st.error(
            "⚠️ Harap isi minimal Nama Lengkap dan PIN Absen Mesin (Device PIN)!"
        )
      else:
        try:
          join_str = join_date.strftime("%Y-%m-%d") if join_date else None
          contract_end_str = (
              contract_end_date.strftime("%Y-%m-%d")
              if contract_end_date
              else None
          )
          resign_str = resign_date.strftime("%Y-%m-%d") if resign_date else None
          dob_str = (
              date_of_birth_input.strip() if date_of_birth_input else None
          )

          con.execute(
              """
                        UPDATE hris_employees SET 
                            employee_code = ?, device_pin = ?, full_name = ?, nick_name = ?,
                            branch = ?, department = ?, job_title = ?, work_location_type = ?,
                            employment_status = ?, contract_end_date = ?, join_date = ?, resign_date = ?,
                            status = ?, exit_type = ?, exit_reason = ?, is_rejoin = ?, rejoin_count = ?,
                            identity_type = ?, identity_number = ?, gender = ?, place_of_birth = ?,
                            date_of_birth = ?, phone_number = ?, email = ?, identity_address = ?,
                            is_same_as_identity_address = ?, residential_address = ?, marital_status = ?,
                            family_card_number = ?, last_education_level = ?, last_education_institution = ?,
                            last_education_major = ?, last_education_year = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND company_id = ?
                    """,
              (
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
                  resign_str,
                  status,
                  exit_type,
                  exit_reason,
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
                  selected_id,
                  company_id,
              ),
          )

          con.commit()
          con.sync()
          st.success(
              f"🎉 Data master karyawan **{full_name}** berhasil diperbarui!"
          )
          st.rerun()  # Auto reload setelah update
        except Exception as e:
          st.error(f"❌ Gagal memperbarui data karyawan: {str(e)}")