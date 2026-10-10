import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def render_career_management():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("📈 Manajemen Riwayat Karier & Mutasi Pegawai")
  st.markdown(
      "Kelola riwayat karier (Tambah, Edit, Update Status Aktif, atau Hapus)"
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

  # Tabs untuk memisahkan Aksi: Lihat/Edit vs Tambah Baru
  tab_list, tab_add = st.tabs(
      ["📋 Daftar & Edit Riwayat Karier", "➕ Tambah Riwayat Karier Baru"]
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
                  [
                      "NEW_HIRE",
                      "PROMOTION",
                      "DEMOTION",
                      "TRANSFER",
                      "MUTATION",
                      "CONTRACT_EXTENSION",
                  ],
                  index=(
                      [
                          "NEW_HIRE",
                          "PROMOTION",
                          "DEMOTION",
                          "TRANSFER",
                          "MUTATION",
                          "CONTRACT_EXTENSION",
                      ].index(c_type)
                      if c_type
                      in [
                          "NEW_HIRE",
                          "PROMOTION",
                          "DEMOTION",
                          "TRANSFER",
                          "MUTATION",
                          "CONTRACT_EXTENSION",
                      ]
                      else 0
                  ),
              )
              e_status = st.selectbox(
                  "Status Kepegawaian",
                  [
                      "PERMANENT",
                      "CONTRACT",
                      "PROBATION",
                      "INTERN",
                      "FREELANCE",
                  ],
                  index=(
                      [
                          "PERMANENT",
                          "CONTRACT",
                          "PROBATION",
                          "INTERN",
                          "FREELANCE",
                      ].index(row["employment_status"])
                      if row["employment_status"]
                      in [
                          "PERMANENT",
                          "CONTRACT",
                          "PROBATION",
                          "INTERN",
                          "FREELANCE",
                      ]
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
                                    UPDATE hris_employees 
                                    SET job_title = ?, department = ?, employment_status = ?, updated_at = CURRENT_TIMESTAMP 
                                    WHERE id = ? AND company_id = ?
                                """,
                      (e_job, e_dept, e_status, selected_id, company_id),
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
                con.sync()
                st.success("🎉 Riwayat karier berhasil diperbarui!")
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
                con.sync()
                st.success("🗑️ Data riwayat karier berhasil dihapus!")
                st.rerun()
              except Exception as e:
                st.error(f"❌ Gagal menghapus data: {str(e)}")

  # --- TAB 2: TAMBAH RIWAYAT KARIER BARU ---
  with tab_add:
    st.subheader(f"Tambah Catatan Karier Baru untuk: {selected_name.split('(')[0]}")

    with st.form("form_tambah_career_baru"):
      c1, c2 = st.columns(2)

      with c1:
        new_type = st.selectbox(
            "Tipe Peristiwa Karier",
            [
                "PROMOTION",
                "MUTATION",
                "TRANSFER",
                "DEMOTION",
                "CONTRACT_EXTENSION",
                "NEW_HIRE",
            ],
        )
        new_employment_status = st.selectbox(
            "Status Kepegawaian",
            ["PERMANENT", "CONTRACT", "PROBATION", "INTERN", "FREELANCE"],
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
                                UPDATE hris_employees 
                                SET job_title = ?, department = ?, employment_status = ?, updated_at = CURRENT_TIMESTAMP 
                                WHERE id = ? AND company_id = ?
                            """,
                  (
                      new_job_title,
                      new_department,
                      new_employment_status,
                      selected_id,
                      company_id,
                  ),
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
            con.sync()
            st.success(
                "🎉 Riwayat karier baru berhasil ditambahkan dan disinkronkan!"
            )
            st.rerun()  # Auto reload setelah simpan/tambah data karier
          except Exception as e:
            st.error(f"❌ Gagal menyimpan karier baru: {str(e)}")