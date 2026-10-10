from database import get_connection
import pandas as pd
import streamlit as st


def render_profile():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  col_t, col_b = st.columns([4, 1])
  with col_t:
    st.title("👤 Profil & Riwayat Karier Karyawan (Lengkap)")
  with col_b:
    if st.button("🔄 Muat Ulang"):
      st.rerun()

  st.markdown(
      "Pilih karyawan untuk melihat seluruh informasi detail dari database"
      " dan rekam jejak kariernya."
  )

  df_list = pd.read_sql(
      f"SELECT id, full_name, employee_code FROM hris_employees WHERE company_id = '{company_id}'",
      con,
  )

  if df_list.empty:
    st.warning("Belum ada data karyawan di database untuk perusahaan ini.")
  else:
    emp_options = {
        f"{row['full_name']} ({row['employee_code']})": row["id"]
        for index, row in df_list.iterrows()
    }
    selected_name = st.selectbox("Pilih Karyawan:", list(emp_options.keys()))
    selected_id = emp_options[selected_name]

    st.divider()

    emp_query = f"SELECT * FROM hris_employees WHERE id = '{selected_id}' AND company_id = '{company_id}'"
    df_detail = pd.read_sql(emp_query, con)

    if not df_detail.empty:
      emp = df_detail.iloc[0]

      tab_info, tab_pribadi, tab_pendidikan, tab_karier = st.tabs(
          [
              "🏢 Info Pekerjaan & Status",
              "👤 Data Pribadi & Kontak",
              "🎓 Pendidikan",
              "📈 Riwayat Karier (1-to-Many)",
          ]
      )

      with tab_info:
        st.subheader("Informasi Pekerjaan & Kepegawaian Lengkap")
        c1, c2 = st.columns(2)

        with c1:
          st.write(f"**NIP / Kode Karyawan:** {emp.get('employee_code')}")
          st.write(f"**PIN Absen Mesin:** {emp.get('device_pin')}")
          st.write(f"**Cabang (Branch):** {emp.get('branch')}")
          st.write(f"**Departemen:** {emp.get('department')}")
          st.write(f"**Jabatan:** {emp.get('job_title')}")
          st.write(f"**Tipe Lokasi Kerja:** {emp.get('work_location_type')}")
          st.write(f"**Status Kepegawaian:** {emp.get('employment_status')}")

        with c2:
          st.write(f"**Tanggal Bergabung:** {emp.get('join_date')}")
          st.write(f"**Tanggal Akhir Kontrak:** {emp.get('contract_end_date')}")
          st.write(f"**Status Sistem:** {emp.get('status')}")
          st.write(f"**Tanggal Resign:** {emp.get('resign_date')}")
          st.write(f"**Tipe Keluar (Exit Type):** {emp.get('exit_type')}")
          st.write(f"**Alasan Keluar:** {emp.get('exit_reason')}")
          st.write(
              f"**Status Rejoin:** {'Ya' if emp.get('is_rejoin') == 1 else 'Tidak'} (Total: {emp.get('rejoin_count')})"
          )

      with tab_pribadi:
        st.subheader("Data Pribadi, Identitas & Alamat Lengkap")
        c3, c4 = st.columns(2)

        with c3:
          st.write(f"**Nama Lengkap:** {emp.get('full_name')}")
          st.write(f"**Nama Panggilan:** {emp.get('nick_name')}")
          st.write(f"**Gender:** {emp.get('gender')}")
          st.write(f"**Status Pernikahan:** {emp.get('marital_status')}")
          st.write(
              f"**Tempat, Tanggal Lahir:** {emp.get('place_of_birth')},"
              f" {emp.get('date_of_birth')}"
          )
          st.write(f"**Nomor Telepon / WA:** {emp.get('phone_number')}")
          st.write(f"**Alamat Email:** {emp.get('email')}")

        with c4:
          st.write(
              f"**Tipe Identitas:** {emp.get('identity_type')} -"
              f" {emp.get('identity_number')}"
          )
          st.write(
              f"**Nomor Kartu Keluarga (KK):** {emp.get('family_card_number')}"
          )
          st.write(f"**Alamat Sesuai KTP:** {emp.get('identity_address')}")
          st.write(
              f"**Alamat Domisili Sama dengan KTP?:**"
              f" {'Ya' if emp.get('is_same_as_identity_address') == 1 else 'Tidak'}"
          )
          st.write(
              f"**Alamat Domisili Saat Ini:** {emp.get('residential_address')}"
          )

      with tab_pendidikan:
        st.subheader("Riwayat Pendidikan Terakhir")
        st.write(f"**Jenjang Pendidikan:** {emp.get('last_education_level')}")
        st.write(
            f"**Nama Institusi / Sekolah:**"
            f" {emp.get('last_education_institution')}"
        )
        st.write(f"**Jurusan / Program Studi:** {emp.get('last_education_major')}")
        st.write(f"**Tahun Lulus:** {emp.get('last_education_year')}")

      with tab_karier:
        st.subheader("Rekam Jejak Riwayat Karier & Mutasi")
        st.markdown(
            "Menampilkan seluruh data dari tabel `hris_employee_careers` yang"
            " terikat pada pegawai ini."
        )

        career_query = f"""
                    SELECT * 
                    FROM hris_employee_careers 
                    WHERE employee_id = '{selected_id}'
                    ORDER BY start_date DESC
                """
        df_career = pd.read_sql(career_query, con)

        if not df_career.empty:
          cols_to_drop = [
              col
              for col in ["id", "company_id", "employee_id"]
              if col in df_career.columns
          ]
          display_career = df_career.drop(columns=cols_to_drop)

          st.dataframe(
              display_career, use_container_width=True, hide_index=True
          )
        else:
          st.info("Belum ada catatan riwayat karier untuk karyawan ini.")