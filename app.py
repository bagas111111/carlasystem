import streamlit as st
from views.add_employee import render_add_employee
from views.career_management import render_career_management
from views.company_management import render_company_management
from views.dashboard import render_dashboard
from views.edit_employee import render_edit_employee
from views.employees import render_employees
from views.login import render_login
from views.profile import render_profile
from views.public_leave_submission import (
    render_public_leave_submission,
)  # <--- Import Modul Publik
from views.users_management import render_users_management

st.set_page_config(
    page_title="HRIS Turso Cloud", page_icon="🏢", layout="wide"
)

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False

# Pilihan Mode Portal di Sidebar
st.sidebar.title("📌 Navigasi Portal")
portal_mode = st.sidebar.radio(
    "Pilih Halaman",
    ["Portal Internal (Login Admin)", "📝 Form Pengajuan Izin Publik"],
)

st.sidebar.divider()

if portal_mode == "📝 Form Pengajuan Izin Publik":
  # Halaman publik: bisa diakses langsung tanpa perlu login
  render_public_leave_submission()
else:
  # Portal internal yang diproteksi oleh sistem login
  if not st.session_state["logged_in"]:
    render_login()
  else:
    st.sidebar.title(f"👤 Halo, {st.session_state.get('full_name', 'Admin')}")
    st.sidebar.caption(f"Role: {st.session_state.get('role', 'USER')}")

    # Susunan Menu Berdasarkan Hak Akses
    menu_options = [
        "Dashboard Utama",
        "Data Karyawan",
        "Tambah Karyawan Baru",
        "Edit Data Karyawan",
        "Detail & Riwayat Karier",
        "Manajemen Karier",
    ]

    # Jika user adalah SUPER_ADMIN, berikan akses penuh ke manajemen perusahaan dan user
    if st.session_state.get("role") == "SUPER_ADMIN":
      menu_options.extend(["Manajemen Perusahaan", "Manajemen Akun & User"])

    menu = st.sidebar.selectbox("Navigasi Menu", menu_options)

    st.sidebar.divider()
    if st.sidebar.button("🚪 Keluar (Logout)"):
      st.session_state["logged_in"] = False
      st.session_state.clear()
      st.rerun()

    # Routing Halaman Internal
    if menu == "Dashboard Utama":
      render_dashboard()
    elif menu == "Data Karyawan":
      render_employees()
    elif menu == "Tambah Karyawan Baru":
      render_add_employee()
    elif menu == "Edit Data Karyawan":
      render_edit_employee()
    elif menu == "Detail & Riwayat Karier":
      render_profile()
    elif menu == "Manajemen Karier":
      render_career_management()
    elif menu == "Manajemen Perusahaan":
      render_company_management()
    elif menu == "Manajemen Akun & User":
      render_users_management()