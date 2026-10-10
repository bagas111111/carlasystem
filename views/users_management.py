import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def render_users_management():
  con = get_connection()
  st.title("🔐 Manajemen Akun & Pengguna HRIS")
  st.markdown(
      "Kelola akun pengguna, hak akses (role), dan kaitkan dengan perusahaan"
      " (`company_id`) yang sesuai."
  )

  # Ambil daftar perusahaan dengan kolom yang benar (company_name)
  df_companies = pd.read_sql(
      "SELECT id, company_name, company_code FROM hris_companies", con
  )

  if df_companies.empty:
    st.warning(
        "⚠️ Belum ada data perusahaan (hris_companies) di database. Harap"
        " buat data perusahaan terlebih dahulu di menu Manajemen Perusahaan."
    )
    return

  company_options = {
      f"{row['company_name']} ({row['company_code']})": row["id"]
      for index, row in df_companies.iterrows()
  }

  tab_list, tab_add, tab_edit = st.tabs(
      [
          "📋 Daftar Akun Pengguna",
          "➕ Tambah Akun Baru",
          "✏️ Edit Akun Pengguna",
      ]
  )

  # --- TAB 1: LIHAT DAFTAR AKUN ---
  with tab_list:
    st.subheader("Daftar Akun Pengguna Terdaftar")

    users_query = """
            SELECT 
                u.id,
                c.company_name AS 'Nama Perusahaan',
                u.username AS 'Username',
                u.full_name AS 'Nama Lengkap',
                u.role AS 'Hak Akses (Role)',
                u.created_at AS 'Dibuat Pada'
            FROM hris_users u
            JOIN hris_companies c ON u.company_id = c.id
            ORDER BY u.created_at DESC
        """
    df_users = pd.read_sql(users_query, con)

    if not df_users.empty:
      st.dataframe(
          df_users.drop(columns=["id"]),
          use_container_width=True,
          hide_index=True,
      )
    else:
      st.info("Belum ada akun pengguna di database.")

  # --- TAB 2: TAMBAH AKUN BARU ---
  with tab_add:
    st.subheader("Formulir Pendaftaran Akun Pengguna Baru")

    with st.form("form_tambah_user"):
      selected_company_name = st.selectbox(
          "Pilih Perusahaan (Company)", list(company_options.keys())
      )
      company_id = company_options[selected_company_name]

      col1, col2 = st.columns(2)
      with col1:
        username = st.text_input("Username Login *Wajib")
        password = st.text_input("Password *Wajib", type="password")
      with col2:
        full_name = st.text_input("Nama Lengkap Pengguna *Wajib")
        role = st.selectbox(
            "Hak Akses (Role)",
            ["SUPER_ADMIN", "HR_ADMIN", "HR_STAFF", "VIEWER"],
        )

      submitted_user = st.form_submit_button("💾 Simpan Akun Baru")

      if submitted_user:
        if not username or not password or not full_name:
          st.error("⚠️ Harap isi Username, Password, dan Nama Lengkap!")
        else:
          try:
            user_id = str(uuid.uuid4())
            con.execute(
                """
                            INSERT INTO hris_users (id, company_id, username, password, full_name, role)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                (user_id, company_id, username, password, full_name, role),
            )
            con.commit()
            con.sync()
            st.success(
                f"🎉 Akun **{username}** berhasil dibuat dan disinkronkan!"
            )
            st.rerun()
          except Exception as e:
            st.error(
                f"❌ Gagal membuat akun (Kemungkinan username sudah ada):"
                f" {str(e)}"
            )

  # --- TAB 3: EDIT AKUN PENGGUNA ---
  with tab_edit:
    st.subheader("Formulir Edit Akun Pengguna")

    df_user_list = pd.read_sql(
        "SELECT id, username, full_name FROM hris_users", con
    )

    if df_user_list.empty:
      st.warning("Belum ada data akun pengguna untuk diedit.")
      return

    user_options = {
        f"{row['full_name']} (@{row['username']})": row["id"]
        for index, row in df_user_list.iterrows()
    }
    selected_user_label = st.selectbox(
        "Pilih Akun yang akan Diedit:", list(user_options.keys())
    )
    selected_user_id = user_options[selected_user_label]

    # Ambil data detail user terpilih
    df_curr_user = pd.read_sql(
        f"SELECT * FROM hris_users WHERE id = '{selected_user_id}'", con
    )

    if df_curr_user.empty:
      st.error("Data akun tidak ditemukan.")
      return

    curr_u = df_curr_user.iloc[0]

    # Cari indeks perusahaan saat ini di dropdown
    current_comp_id = curr_u.get("company_id")
    comp_keys = list(company_options.keys())
    comp_vals = list(company_options.values())
    default_comp_idx = (
        comp_vals.index(current_comp_id) if current_comp_id in comp_vals else 0
    )

    roles_list = ["SUPER_ADMIN", "HR_ADMIN", "HR_STAFF", "VIEWER"]
    curr_role = curr_u.get("role")
    default_role_idx = (
        roles_list.index(curr_role) if curr_role in roles_list else 1
    )

    with st.form(f"form_edit_user_{selected_user_id}"):
      e_selected_comp_name = st.selectbox(
          "Pilih Perusahaan (Company)",
          comp_keys,
          index=default_comp_idx,
      )
      e_company_id = company_options[e_selected_comp_name]

      col1, col2 = st.columns(2)
      with col1:
        e_username = st.text_input(
            "Username Login *Wajib", value=str(curr_u.get("username") or "")
        )
        e_password = st.text_input(
            "Password Baru (Kosongkan jika tidak diubah)",
            value=str(curr_u.get("password") or ""),
            type="password",
        )
      with col2:
        e_full_name = st.text_input(
            "Nama Lengkap Pengguna *Wajib",
            value=str(curr_u.get("full_name") or ""),
        )
        e_role = st.selectbox(
            "Hak Akses (Role)", roles_list, index=default_role_idx
        )

      submitted_edit_user = st.form_submit_button("💾 Simpan Perubahan Akun")

      if submitted_edit_user:
        if not e_username or not e_password or not e_full_name:
          st.error("⚠️ Username, Password, dan Nama Lengkap wajib diisi!")
        else:
          try:
            con.execute(
                """
                            UPDATE hris_users SET 
                                company_id = ?, username = ?, password = ?, 
                                full_name = ?, role = ?
                            WHERE id = ?
                        """,
                (
                    e_company_id,
                    e_username,
                    e_password,
                    e_full_name,
                    e_role,
                    selected_user_id,
                ),
            )
            con.commit()
            con.sync()
            st.success(f"🎉 Akun **{e_username}** berhasil diperbarui!")
            st.rerun()
          except Exception as e:
            st.error(f"❌ Gagal memperbarui akun: {str(e)}")