import datetime
import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def render_leave_quota_management():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("🌴 Manajemen Kuota & Cuti Khusus / Panjang")
  st.markdown(
      "Kelola kuota cuti tahunan/khusus (Bulk Insert & Expired Update) serta"
      " catat pengajuan cuti berbasis pemotongan kuota aktif (Khusus Karyawan"
      " Aktif)."
  )

  tab_quota, tab_request = st.tabs(
      [
          "📊 Kuota Cuti & Bulk Action",
          "📝 Pengajuan Cuti Panjang & Riwayat",
      ]
  )

  # ==========================================
  # TAB 1: KUOTA CUTI & BULK ACTION (HANYA KARYAWAN ACTIVE)
  # ==========================================
  with tab_quota:
    st.subheader("⚡ Bulk Management Kuota Cuti (Karyawan ACTIVE)")

    action_type = st.radio(
        "Pilih Aksi Massal (Bulk):",
        ["Bulk Insert Kuota Baru (ACTIVE)", "Bulk Update Status (EXPIRED)"],
        horizontal=True,
    )

    with st.form("form_bulk_quota_action"):
      c_b1, c_b2, c_b3 = st.columns(3)
      with c_b1:
        bulk_year = st.number_input(
            "Tahun Kuota",
            min_value=2024,
            max_value=2035,
            value=datetime.date.today().year,
        )
      with c_b2:
        bulk_category = st.selectbox(
            "Jenis Cuti",
            ["TAHUNAN", "HAMIL", "KEGUGURAN", "IBADAH", "KHUSUS"],
            key="bulk_cat",
        )
      with c_b3:
        if action_type == "Bulk Insert Kuota Baru (ACTIVE)":
          bulk_total = st.number_input(
              "Total Jatah Hari", min_value=1, max_value=365, value=12
          )
        else:
          st.info("Seluruh kuota pada Tahun & Jenis Cuti ini akan di-EXPIRED.")
          bulk_total = 0

      submitted_bulk = st.form_submit_button("🚀 Jalankan Aksi Bulk")

      if submitted_bulk:
        try:
          if action_type == "Bulk Insert Kuota Baru (ACTIVE)":
            df_active_emp = pd.read_sql(
                f"SELECT id FROM hris_employees WHERE company_id = '{company_id}' AND status = 'ACTIVE'",
                con,
            )
            if df_active_emp.empty:
              st.warning("Tidak ada karyawan aktif di perusahaan ini.")
            else:
              count_success = 0
              for _, emp_row in df_active_emp.iterrows():
                emp_id = emp_row["id"]
                check_exist = pd.read_sql(
                    f"""
                                    SELECT id FROM hris_leave_quotas 
                                    WHERE company_id = '{company_id}' 
                                      AND employee_id = '{emp_id}' 
                                      AND year = {bulk_year} 
                                      AND leave_category = '{bulk_category}'
                                """,
                    con,
                )

                if check_exist.empty:
                  quota_id = str(uuid.uuid4())
                  con.execute(
                      """
                                        INSERT INTO hris_leave_quotas (id, company_id, employee_id, year, leave_category, total_quota, used_quota, status)
                                        VALUES (?, ?, ?, ?, ?, ?, 0, 'ACTIVE')
                                    """,
                      (
                          quota_id,
                          company_id,
                          emp_id,
                          bulk_year,
                          bulk_category,
                          bulk_total,
                      ),
                  )
                  count_success += 1

              con.commit()
              con.sync()
              st.success(
                  f"🎉 Berhasil insert kuota ACTIVE untuk {count_success}"
                  " karyawan aktif!"
              )
              st.rerun()

          else:  # Bulk Update Status (EXPIRED)
            con.execute(
                f"""
                            UPDATE hris_leave_quotas 
                            SET status = 'EXPIRED'
                            WHERE company_id = '{company_id}' 
                              AND year = {bulk_year} 
                              AND leave_category = '{bulk_category}'
                        """
            )
            con.commit()
            con.sync()
            st.success(
                f"🎉 Seluruh kuota {bulk_category} Tahun {bulk_year} berhasil"
                " diubah menjadi EXPIRED!"
            )
            st.rerun()

        except Exception as e:
          st.error(f"Gagal memproses aksi bulk: {e}")

    st.divider()
    st.subheader("📋 Daftar Kuota Cuti Karyawan Aktif")

    # Filter Wajib: Search Tahun & Jenis Cuti
    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    with f_col1:
      filter_year = st.selectbox(
          "Filter Tahun *Wajib", [2024, 2025, 2026, 2027, 2028], index=2
      )
    with f_col2:
      filter_cat = st.selectbox(
          "Filter Jenis Cuti *Wajib",
          ["TAHUNAN", "HAMIL", "KEGUGURAN", "IBADAH", "KHUSUS"],
      )
    with f_col3:
      search_quota_keyword = st.text_input(
          "🔍 Cari Nama, NIP, atau Departemen:", "", key="search_quota"
      )

    # PERHATIAN: Ditambahkan filter e.status = 'ACTIVE' agar hanya data karyawan aktif yang muncul dan bisa di-CRUD
    quota_query = f"""
            SELECT 
                q.id,
                e.full_name AS 'Nama Karyawan',
                e.employee_code AS 'NIP',
                e.department AS 'Departemen',
                q.year AS 'Tahun',
                q.leave_category AS 'Jenis Cuti',
                q.total_quota AS 'Total Kuota',
                q.used_quota AS 'Terpakai',
                (q.total_quota - q.used_quota) AS 'Sisa Kuota',
                q.status AS 'Status'
            FROM hris_leave_quotas q
            JOIN hris_employees e ON q.employee_id = e.id
            WHERE q.company_id = '{company_id}' 
              AND q.year = {filter_year}
              AND q.leave_category = '{filter_cat}'
              AND e.status = 'ACTIVE'
        """

    df_quotas = pd.read_sql(quota_query, con)

    if not df_quotas.empty:
      if search_quota_keyword:
        df_quotas_filtered = df_quotas[
            df_quotas["Nama Karyawan"].str.contains(
                search_quota_keyword, case=False, na=False
            )
            | df_quotas["NIP"].str.contains(
                search_quota_keyword, case=False, na=False
            )
            | df_quotas["Departemen"].str.contains(
                search_quota_keyword, case=False, na=False
            )
        ]
      else:
        df_quotas_filtered = df_quotas

      st.markdown(
          f"Menampilkan **{len(df_quotas_filtered)}** data kuota karyawan"
          " aktif."
      )
      st.dataframe(
          df_quotas_filtered.drop(columns=["id"]),
          use_container_width=True,
          hide_index=True,
      )

      if not df_quotas_filtered.empty:
        with st.expander("⚙️ Edit Kuota / Status Individual (Karyawan Aktif)"):
          quota_options = {
              f"{row['Nama Karyawan']} (NIP: {row['NIP']}) - {row['Jenis Cuti']} ({row['Tahun']})": row[
                  "id"
              ]
              for index, row in df_quotas_filtered.iterrows()
          }
          selected_q_label = st.selectbox(
              "Pilih Data Kuota:", list(quota_options.keys())
          )
          selected_q_id = quota_options[selected_q_label]

          curr_q_data = pd.read_sql(
              f"SELECT * FROM hris_leave_quotas WHERE id = '{selected_q_id}'",
              con,
          ).iloc[0]

          col_e1, col_e2 = st.columns(2)
          with col_e1:
            new_total = st.number_input(
                "Update Total Kuota",
                min_value=0,
                value=int(curr_q_data["total_quota"]),
            )
          with col_e2:
            new_status = st.selectbox(
                "Update Status",
                ["ACTIVE", "EXPIRED"],
                index=0 if curr_q_data["status"] == "ACTIVE" else 1,
            )

          col_btn1, col_btn2 = st.columns(2)
          if col_btn1.button("💾 Simpan Perubahan"):
            try:
              con.execute(
                  """
                                UPDATE hris_leave_quotas 
                                SET total_quota = ?, status = ? 
                                WHERE id = ?
                            """,
                  (new_total, new_status, selected_q_id),
              )
              con.commit()
              con.sync()
              st.success("Data kuota berhasil diperbarui!")
              st.rerun()
            except Exception as e:
              st.error(f"Gagal update: {e}")

          if col_btn2.button("🗑️ Hapus Kuota Ini"):
            try:
              con.execute(
                  "DELETE FROM hris_leave_quotas WHERE id = ?",
                  (selected_q_id,),
              )
              con.commit()
              con.sync()
              st.success("Kuota berhasil dihapus!")
              st.rerun()
            except Exception as e:
              st.error(f"Gagal menghapus: {e}")
    else:
      st.info("Belum ada data kuota cuti untuk karyawan aktif dengan filter yang dipilih.")

  # ==========================================
  # TAB 2: PENGAJUAN CUTI PANJANG & RIWAYAT (HANYA KARYAWAN ACTIVE)
  # ==========================================
  with tab_request:
    st.subheader("📝 Input Pengajuan Cuti (Pemotongan Kuota Karyawan Aktif)")

    df_emp = pd.read_sql(
        f"SELECT id, full_name, employee_code, department FROM hris_employees WHERE company_id = '{company_id}' AND status = 'ACTIVE'",
        con,
    )

    if df_emp.empty:
      st.warning("Belum ada data karyawan aktif.")
      return

    emp_dict = {
        f"{row['full_name']} (NIP: {row['employee_code']})": row["id"]
        for _, row in df_emp.iterrows()
    }

    with st.form("form_long_leave"):
      selected_emp_req = st.selectbox(
          "Pilih Karyawan Aktif *Wajib", list(emp_dict.keys()), key="req_emp"
      )
      emp_id_req = emp_dict[selected_emp_req]

      c_r1, c_r2, c_r3 = st.columns(3)
      with c_r1:
        req_year = st.number_input(
            "Tahun Kuota *Wajib",
            min_value=2024,
            max_value=2035,
            value=datetime.date.today().year,
        )
      with c_r2:
        req_category = st.selectbox(
            "Jenis Cuti *Wajib",
            ["TAHUNAN", "HAMIL", "KEGUGURAN", "IBADAH", "KHUSUS"],
            key="req_cat",
        )
      with c_r3:
        start_d = st.date_input(
            "Tanggal Mulai Cuti", value=datetime.date.today()
        )

      c_r4, c_r5 = st.columns(2)
      with c_r4:
        end_d = st.date_input(
            "Tanggal Selesai Cuti",
            value=datetime.date.today() + datetime.timedelta(days=1),
        )
      with c_r5:
        calc_days = (end_d - start_d).days + 1 if end_d >= start_d else 0
        st.write(f"**Total Hari:** {calc_days} Hari")

      req_reason = st.text_area(
          "Alasan / Keterangan Cuti *Wajib",
          placeholder="Tuliskan keterangan alasan cuti...",
      )

      submitted_req = st.form_submit_button("🚀 Simpan Pengajuan Cuti")

      if submitted_req:
        if calc_days <= 0:
          st.error(
              "❌ Tanggal selesai tidak boleh lebih awal dari tanggal mulai!"
          )
        elif not req_reason:
          st.error("❌ Harap isi alasan cuti!")
        else:
          df_q_check = pd.read_sql(
              f"""
                        SELECT id, total_quota, used_quota, status 
                        FROM hris_leave_quotas 
                        WHERE company_id = '{company_id}' 
                          AND employee_id = '{emp_id_req}' 
                          AND year = {req_year} 
                          AND leave_category = '{req_category}'
                    """,
              con,
          )

          if df_q_check.empty:
            st.error(
                f"❌ Data Kuota Cuti {req_category} Tahun {req_year} BELUM"
                " DI-INPUT untuk karyawan ini! Silakan buat kuota terlebih"
                " dahulu di Tab 1."
            )
          elif df_q_check.iloc[0]["status"] != "ACTIVE":
            st.error(
                f"❌ Kuota Cuti {req_category} Tahun {req_year} untuk karyawan"
                " ini sudah EXPIRED!"
            )
          else:
            q_row = df_q_check.iloc[0]
            sisa_kuota = q_row["total_quota"] - q_row["used_quota"]

            if calc_days > sisa_kuota:
              st.error(
                  f"❌ Sisa kuota tidak mencukupi! Sisa Kuota: {sisa_kuota}"
                  f" hari, Pengajuan: {calc_days} hari."
              )
            else:
              try:
                req_id = str(uuid.uuid4())
                start_str = start_d.strftime("%Y-%m-%d")
                end_str = end_d.strftime("%Y-%m-%d")

                con.execute(
                    """
                                    INSERT INTO hris_leave_requests (id, company_id, employee_id, year, leave_category, start_date, end_date, total_days, reason)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                    (
                        req_id,
                        company_id,
                        emp_id_req,
                        req_year,
                        req_category,
                        start_str,
                        end_str,
                        calc_days,
                        req_reason,
                    ),
                )

                con.execute(
                    """
                                    UPDATE hris_leave_quotas 
                                    SET used_quota = used_quota + ? 
                                    WHERE id = ?
                                """,
                    (calc_days, q_row["id"]),
                )

                con.commit()
                con.sync()
                st.success(
                    "🎉 Pengajuan cuti berhasil disimpan dan kuota terpotong"
                    " secara akurat!"
                )
                st.rerun()
              except Exception as e:
                st.error(f"Gagal menyimpan pengajuan: {e}")

    st.divider()
    st.subheader("📋 Riwayat Pengajuan Cuti (Karyawan Aktif)")

    r_col1, r_col2, r_col3 = st.columns([2, 2, 3])
    today = datetime.date.today()
    first_day_of_month = today.replace(day=1)

    with r_col1:
      filter_start_d = st.date_input(
          "Dari Tanggal (Mulai)", value=first_day_of_month, key="req_start"
      )
    with r_col2:
      filter_end_d = st.date_input(
          "Sampai Tanggal (Selesai)", value=today, key="req_end"
      )
    with r_col3:
      search_req_keyword = st.text_input(
          "🔍 Cari Nama, NIP, atau Jenis Cuti:", "", key="search_req"
      )

    f_start_str = (
        filter_start_d.strftime("%Y-%m-%d")
        if filter_start_d
        else "1970-01-01"
    )
    f_end_str = (
        filter_end_d.strftime("%Y-%m-%d") if filter_end_d else "2099-12-31"
    )

    # Filter e.status = 'ACTIVE' agar riwayat yang dikelola hanya untuk karyawan aktif
    req_query = f"""
            SELECT 
                r.id,
                e.full_name AS 'Nama Karyawan',
                e.employee_code AS 'NIP',
                e.device_pin AS 'PIN Absen',
                e.department AS 'Departemen',
                r.year AS 'Tahun Kuota',
                r.leave_category AS 'Jenis Cuti',
                r.start_date AS 'Mulai',
                r.end_date AS 'Selesai',
                r.total_days AS 'Jumlah Hari',
                r.reason AS 'Alasan'
            FROM hris_leave_requests r
            JOIN hris_employees e ON r.employee_id = e.id
            WHERE r.company_id = '{company_id}'
              AND e.status = 'ACTIVE'
              AND r.start_date >= '{f_start_str}'
              AND r.start_date <= '{f_end_str}'
            ORDER BY r.start_date DESC
        """
    df_requests = pd.read_sql(req_query, con)

    if not df_requests.empty:
      if search_req_keyword:
        df_req_filtered = df_requests[
            df_requests["Nama Karyawan"].str.contains(
                search_req_keyword, case=False, na=False
            )
            | df_requests["NIP"].str.contains(
                search_req_keyword, case=False, na=False
            )
            | df_requests["Jenis Cuti"].str.contains(
                search_req_keyword, case=False, na=False
            )
        ]
      else:
        df_req_filtered = df_requests

      st.markdown(
          f"Menampilkan **{len(df_req_filtered)}** data riwayat karyawan aktif"
          f" dari rentang **{f_start_str}** s.d **{f_end_str}**."
      )
      st.dataframe(
          df_req_filtered.drop(columns=["id"]),
          use_container_width=True,
          hide_index=True,
      )

      if not df_req_filtered.empty:
        with st.expander("🗑️ Hapus / Batalkan Riwayat Cuti"):
          req_options = {
              f"{row['Nama Karyawan']} (NIP: {row['NIP']}) - {row['Jenis Cuti']} ({row['Mulai']} s.d {row['Selesai']})": row[
                  "id"
              ]
              for index, row in df_req_filtered.iterrows()
          }
          selected_r_label = st.selectbox(
              "Pilih Riwayat Cutinya:", list(req_options.keys())
          )
          selected_r_id = req_options[selected_r_label]

          if st.button("❌ Hapus & Kembalikan Kuota"):
            try:
              r_data = pd.read_sql(
                  f"SELECT * FROM hris_leave_requests WHERE id = '{selected_r_id}'",
                  con,
              ).iloc[0]
              r_emp = r_data["employee_id"]
              r_cat = r_data["leave_category"]
              r_year = int(r_data["year"])
              r_days = int(r_data["total_days"])

              con.execute(
                  """
                                UPDATE hris_leave_quotas 
                                SET used_quota = MAX(0, used_quota - ?) 
                                WHERE company_id = ? AND employee_id = ? AND year = ? AND leave_category = ?
                            """,
                  (r_days, company_id, r_emp, r_year, r_cat),
              )

              con.execute(
                  "DELETE FROM hris_leave_requests WHERE id = ?",
                  (selected_r_id,),
              )
              con.commit()
              con.sync()
              st.success(
                  "Riwayat cuti berhasil dihapus dan kuota dikembalikan secara"
                  " presisi!"
              )
              st.rerun()
            except Exception as e:
              st.error(f"Gagal menghapus riwayat: {e}")
    else:
      st.info(
          f"Tidak ada data riwayat pengajuan cuti karyawan aktif pada rentang"
          f" tanggal {f_start_str} s.d {f_end_str}."
      )