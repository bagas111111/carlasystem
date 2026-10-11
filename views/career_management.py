import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def sync_employee_profile(con, employee_id):
  """Fungsi helper untuk menyinkronkan profil utama hris_employees

  berdasarkan riwayat karier yang aktif (is_current = 1 dan created_at terbaru).
  """
  try:
    df_curr = pd.read_sql(
        f"""
            SELECT job_title, department, employment_status, end_date 
            FROM hris_employee_careers 
            WHERE employee_id = '{employee_id}' AND is_current = 1 
            ORDER BY created_at DESC, start_date DESC 
            LIMIT 1
        """,
        con,
    )

    if not df_curr.empty:
      row = df_curr.iloc[0]
      j_title = row["job_title"]
      dept = row["department"]
      emp_status = row["employment_status"]
      end_date = row["end_date"]

      if (
          end_date
          and str(end_date).strip() not in ["", "nan", "None", "NaT", "NAT"]
      ):
        con.execute(
            """
                UPDATE hris_employees 
                SET job_title = ?, department = ?, employment_status = ?, contract_end_date = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """,
            (j_title, dept, emp_status, end_date, employee_id),
        )
      else:
        con.execute(
            """
                UPDATE hris_employees 
                SET job_title = ?, department = ?, employment_status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """,
            (j_title, dept, emp_status, employee_id),
        )
      con.commit()
  except Exception as e:
    print(f"Gagal sinkronisasi profil: {e}")


def render_career_management():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("📈 Manajemen Riwayat Karier & Mutasi Pegawai")
  st.markdown(
      "Kelola riwayat karier (Tambah, Edit, Update Status Aktif, dan Hapus)"
      " berdasarkan karyawan yang dipilih."
  )

  # Ambil daftar karyawan khusus untuk perusahaan yang sedang login
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
      "Pilih Karyawan untuk Mengelola Karier:", list(emp_options.keys())
  )
  selected_id = emp_options[selected_name]

  st.divider()

  # Daftar pilihan sesuai constraint database (CHECK constraint)
  CAREER_TYPES = [
      "NEW_HIRE",
      "PROMOTED",
      "DEMOTED",
      "CONTRACT_EXTENSION",
      "STATUS_CHANGE",
      "MUTATION",
  ]
  EMPLOYMENT_STATUSES = [
      "PERMANENT",
      "CONTRACT",
      "PROBATION",
      "INTERN",
      "FREELANCE",
  ]

  # Tabs untuk memisahkan Aksi: Edit/Hapus, Tambah Baru, serta Tabel Tampilan Data
  tab_list, tab_add, tab_table = st.tabs(
      [
          "📋 Daftar & Edit Riwayat",
          "➕ Tambah Riwayat Baru",
          "📊 Tabel Riwayat Karier",
      ]
  )

  # --- TAB 1: LIHAT, EDIT, UPDATE is_current, & HAPUS ---
  with tab_list:
    st.subheader(f"Daftar Riwayat Karier: {selected_name.split('(')[0]}")

    career_query = f"""
            SELECT * FROM hris_employee_careers 
            WHERE employee_id = '{selected_id}'
            ORDER BY start_date DESC
        """
    df_career = pd.read_sql(career_query, con)

    if df_career.empty:
      st.info(
          "Belum ada catatan riwayat karier untuk karyawan ini. Silakan tambah"
          " melalui tab di sebelah."
      )
    else:
      for index, row in df_career.iterrows():
        career_id = row["id"]
        job_title = row["job_title"]
        dept = row["department"]
        start = row["start_date"]
        is_curr = row["is_current"]
        c_type = row["type"]

        status_badge = (
            "🟢 [AKTIF SEKARANG]" if is_curr == 1 else "⚪ [RIWAYAT LALU]"
        )

        with st.expander(
            f"{c_type} - {job_title} ({dept}) | Mulai: {start} {status_badge}"
        ):
          with st.form(f"form_edit_career_{career_id}"):
            col1, col2 = st.columns(2)

            with col1:
              e_type = st.selectbox(
                  "Tipe Peristiwa",
                  CAREER_TYPES,
                  index=(
                      CAREER_TYPES.index(c_type)
                      if c_type in CAREER_TYPES
                      else 0
                  ),
              )
              e_status = st.selectbox(
                  "Status Kepegawaian",
                  EMPLOYMENT_STATUSES,
                  index=(
                      EMPLOYMENT_STATUSES.index(row["employment_status"])
                      if row["employment_status"] in EMPLOYMENT_STATUSES
                      else 0
                  ),
              )
              e_job = st.text_input("Jabatan / Job Title", value=job_title)
              e_dept = st.text_input("Departemen", value=str(dept))

            with col2:
              d_start = (
                  pd.to_datetime(row["start_date"]).date()
                  if pd.notnull(row["start_date"])
                  else None
              )
              d_end = (
                  pd.to_datetime(row["end_date"]).date()
                  if pd.notnull(row["end_date"])
                  else None
              )

              e_start = st.date_input(
                  "Tanggal Mulai", value=d_start, key=f"start_{career_id}"
              )
              e_end = st.date_input(
                  "Tanggal Selesai (Opsional)",
                  value=d_end,
                  key=f"end_{career_id}",
              )
              e_ref = st.text_input(
                  "No. Surat Keputusan / Referensi",
                  value=str(row["reference_letter_number"] or ""),
              )
              e_is_current = st.selectbox(
                  "Status Jabatan Saat Ini (is_current)",
                  [1, 0],
                  index=0 if is_curr == 1 else 1,
                  format_func=lambda x: (
                      "Ya (Jabatan Aktif)" if x == 1 else "Tidak (Masa Lalu)"
                  ),
                  key=f"curr_{career_id}",
              )

            e_notes = st.text_area(
                "Catatan Mutasi / Promosi",
                value=str(row["notes"] or ""),
                key=f"notes_{career_id}",
            )

            col_btn1, col_btn2 = st.columns(2)
            update_submitted = col_btn1.form_submit_button(
                "💾 Simpan Perubahan"
            )
            delete_submitted = col_btn2.form_submit_button(
                "🗑️ Hapus Riwayat Ini"
            )

            if update_submitted:
              try:
                start_str = e_start.strftime("%Y-%m-%d") if e_start else None
                end_str = e_end.strftime("%Y-%m-%d") if e_end else None

                if e_is_current == 1:
                  con.execute(
                      """
                                    UPDATE hris_employee_careers 
                                    SET is_current = 0, updated_at = CURRENT_TIMESTAMP 
                                    WHERE employee_id = ?
                                """,
                      (selected_id,),
                  )

                con.execute(
                    """
                                UPDATE hris_employee_careers 
                                SET type = ?, employment_status = ?, job_title = ?, department = ?, 
                                    start_date = ?, end_date = ?, reference_letter_number = ?, 
                                    is_current = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """,
                    (
                        e_type,
                        e_status,
                        e_job,
                        e_dept,
                        start_str,
                        end_str,
                        e_ref,
                        int(e_is_current),
                        e_notes,
                        career_id,
                    ),
                )
                con.commit()
                sync_employee_profile(con, selected_id)
                con.sync()
                st.success(
                    "🎉 Riwayat karier berhasil diperbarui dan profil utama"
                    " diselaraskan!"
                )
                st.rerun()
              except Exception as e:
                st.error(f"❌ Gagal memperbarui data: {str(e)}")

            if delete_submitted:
              try:
                con.execute(
                    "DELETE FROM hris_employee_careers WHERE id = ?",
                    (career_id,),
                )
                con.commit()
                sync_employee_profile(con, selected_id)
                con.sync()
                st.success("🗑️ Data riwayat karier berhasil dihapus!")
                st.rerun()
              except Exception as e:
                st.error(f"❌ Gagal menghapus data: {str(e)}")

  # --- TAB 2: TAMBAH RIWAYAT KARIER BARU ---
  with tab_add:
    st.subheader(
        f"Tambah Catatan Karier Baru untuk: {selected_name.split('(')[0]}"
    )

    with st.form("form_tambah_career_baru"):
      c1, c2 = st.columns(2)

      with c1:
        new_type = st.selectbox("Tipe Peristiwa Karier", CAREER_TYPES)
        new_employment_status = st.selectbox(
            "Status Kepegawaian", EMPLOYMENT_STATUSES
        )
        new_job_title = st.text_input(
            "Jabatan Baru / Job Title (Contoh: Senior Engineer)"
        )
        new_department = st.text_input(
            "Departemen Baru (Contoh: Product Development)"
        )

      with c2:
        new_start_date = st.date_input("Tanggal Efektif Mulai")
        new_end_date = st.date_input(
            "Tanggal Selesai (Opsional)", value=None
        )
        new_ref = st.text_input(
            "No. SK / Referensi (Opsional)",
            placeholder="SK/001/HR/2026",
        )
        new_is_current = st.selectbox(
            "Jadikan Jabatan Aktif Saat Ini?",
            [1, 0],
            format_func=lambda x: (
                "Ya (Otomatis set aktif & perbarui profil utama)"
                if x == 1
                else "Tidak (Riwayat masa lalu)"
            ),
        )

      new_notes = st.text_area(
          "Catatan / Keterangan Mutasi",
          placeholder="Contoh: Mutasi lintas divisi berdasarkan hasil evaluasi tahunan.",
      )

      submitted_add = st.form_submit_button(
          "💾 Tambahkan Riwayat Karier Baru"
      )

      if submitted_add:
        if not new_job_title or not new_start_date:
          st.error(
              "⚠️ Harap isi minimal Jabatan Baru dan Tanggal Efektif Mulai!"
          )
        else:
          try:
            new_career_id = str(uuid.uuid4())
            start_str = (
                new_start_date.strftime("%Y-%m-%d")
                if new_start_date
                else None
            )
            end_str = (
                new_end_date.strftime("%Y-%m-%d") if new_end_date else None
            )

            if new_is_current == 1:
              con.execute(
                  """
                                UPDATE hris_employee_careers 
                                SET is_current = 0, updated_at = CURRENT_TIMESTAMP 
                                WHERE employee_id = ?
                            """,
                  (selected_id,),
              )

            con.execute(
                """
                            INSERT INTO hris_employee_careers (
                                id, company_id, employee_id, type, employment_status,
                                job_title, department, start_date, end_date, 
                                reference_letter_number, is_current, notes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                (
                    new_career_id,
                    company_id,
                    selected_id,
                    new_type,
                    new_employment_status,
                    new_job_title,
                    new_department,
                    start_str,
                    end_str,
                    new_ref,
                    int(new_is_current),
                    new_notes,
                ),
            )
            con.commit()
            sync_employee_profile(con, selected_id)
            con.sync()
            st.success(
                "🎉 Riwayat karier baru berhasil ditambahkan dan disinkronkan!"
            )
            st.rerun()
          except Exception as e:
            st.error(f"❌ Gagal menyimpan karier baru: {str(e)}")

  # --- TAB 3: TAMPILAN TABEL RIWAYAT (DOWNLOAD BAWAAN STREAMLIT) ---
  with tab_table:
    st.subheader(f"📊 Tabel Riwayat Karier: {selected_name.split('(')[0]}")
    st.markdown(
        "Menampilkan seluruh riwayat karier dalam bentuk tabel. Anda dapat"
        " langsung mengunduhnya melalui ikon *download* di pojok kanan atas"
        " tabel."
    )

    df_table = pd.read_sql(
        f"""
            SELECT 
                type AS 'Tipe Peristiwa',
                employment_status AS 'Status Pegawai',
                job_title AS 'Jabatan',
                department AS 'Departemen',
                start_date AS 'Tanggal Mulai',
                end_date AS 'Tanggal Selesai',
                reference_letter_number AS 'No. SK / Ref',
                CASE WHEN is_current = 1 THEN 'Aktif' ELSE 'Riwayat' END AS 'Status Aktif',
                notes AS 'Catatan'
            FROM hris_employee_careers 
            WHERE employee_id = '{selected_id}'
            ORDER BY start_date DESC
        """,
        con,
    )

    if not df_table.empty:
      st.dataframe(df_table, use_container_width=True, hide_index=True)
    else:
      st.info("Belum ada data karier untuk ditampilkan.")