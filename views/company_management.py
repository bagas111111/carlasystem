import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def render_company_management():
  con = get_connection()
  st.title("🏢 Manajemen Perusahaan (Companies)")
  st.markdown(
      "Kelola daftar perusahaan yang terdaftar dalam ekosistem sistem HRIS"
      " multi-tenant ini."
  )

  tab_list, tab_add, tab_edit = st.tabs(
      [
          "📋 Daftar Perusahaan",
          "➕ Tambah Perusahaan Baru",
          "✏️ Edit Perusahaan",
      ]
  )

  # --- TAB 1: DAFTAR PERUSAHAAN ---
  with tab_list:
    st.subheader("Daftar Tenant Perusahaan")

    df_comp = pd.read_sql("SELECT * FROM hris_companies", con)

    if not df_comp.empty:
      st.dataframe(df_comp, use_container_width=True, hide_index=True)
    else:
      st.info(
          "Belum ada data perusahaan. Silakan tambahkan perusahaan melalui tab"
          " sebelah."
      )

  # --- TAB 2: TAMBAH PERUSAHAAN ---
  with tab_add:
    st.subheader("Formulir Tambah Perusahaan Baru")

    with st.form("form_tambah_company"):
      col1, col2 = st.columns(2)
      with col1:
        company_name = st.text_input("Nama Perusahaan / PT *Wajib")
        company_code = st.text_input(
            "Kode Unik Perusahaan (Misal: PTMS, MJS) *Wajib"
        )
        address = st.text_area("Alamat Perusahaan")
      with col2:
        phone_number = st.text_input("Nomor Telepon Perusahaan")
        email = st.text_input("Email Resmi Perusahaan")

      submitted_comp = st.form_submit_button("💾 Simpan Perusahaan Baru")

      if submitted_comp:
        if not company_name or not company_code:
          st.error("⚠️ Nama Perusahaan dan Kode Unik wajib diisi!")
        else:
          try:
            comp_id = str(uuid.uuid4())
            con.execute(
                """
                            INSERT INTO hris_companies (id, company_code, company_name, address, phone_number, email)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                (
                    comp_id,
                    company_code,
                    company_name,
                    address,
                    phone_number,
                    email,
                ),
            )
            con.commit()
            con.sync()
            st.success(
                f"🎉 Perusahaan **{company_name}** berhasil ditambahkan!"
            )
            st.rerun()
          except Exception as e:
            st.error(f"❌ Gagal menyimpan perusahaan: {str(e)}")

  # --- TAB 3: EDIT PERUSAHAAN ---
  with tab_edit:
    st.subheader("Formulir Edit Data Perusahaan")

    df_list = pd.read_sql(
        "SELECT id, company_name, company_code FROM hris_companies", con
    )

    if df_list.empty:
      st.warning("Belum ada data perusahaan untuk diedit.")
      return

    comp_options = {
        f"{row['company_name']} ({row['company_code']})": row["id"]
        for index, row in df_list.iterrows()
    }
    selected_comp_name = st.selectbox(
        "Pilih Perusahaan yang akan Diedit:", list(comp_options.keys())
    )
    selected_comp_id = comp_options[selected_comp_name]

    # Ambil data detail perusahaan yang dipilih
    df_curr = pd.read_sql(
        f"SELECT * FROM hris_companies WHERE id = '{selected_comp_id}'", con
    )

    if df_curr.empty:
      st.error("Data perusahaan tidak ditemukan.")
      return

    curr = df_curr.iloc[0]

    with st.form(f"form_edit_company_{selected_comp_id}"):
      col1, col2 = st.columns(2)
      with col1:
        e_company_name = st.text_input(
            "Nama Perusahaan / PT *Wajib",
            value=str(curr.get("company_name") or ""),
        )
        e_company_code = st.text_input(
            "Kode Unik Perusahaan *Wajib",
            value=str(curr.get("company_code") or ""),
        )
        e_address = st.text_area(
            "Alamat Perusahaan", value=str(curr.get("address") or "")
        )
      with col2:
        e_phone_number = st.text_input(
            "Nomor Telepon Perusahaan",
            value=str(curr.get("phone_number") or ""),
        )
        e_email = st.text_input(
            "Email Resmi Perusahaan", value=str(curr.get("email") or "")
        )

      submitted_edit = st.form_submit_button("💾 Simpan Perubahan Perusahaan")

      if submitted_edit:
        if not e_company_name or not e_company_code:
          st.error("⚠️ Nama Perusahaan dan Kode Unik wajib diisi!")
        else:
          try:
            con.execute(
                """
                            UPDATE hris_companies SET 
                                company_code = ?, company_name = ?, address = ?, 
                                phone_number = ?, email = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """,
                (
                    e_company_code,
                    e_company_name,
                    e_address,
                    e_phone_number,
                    e_email,
                    selected_comp_id,
                ),
            )
            con.commit()
            con.sync()
            st.success(f"🎉 Perusahaan **{e_company_name}** berhasil diperbarui!")
            st.rerun()
          except Exception as e:
            st.error(f"❌ Gagal memperbarui perusahaan: {str(e)}")