import streamlit as st
from views.add_employee import render_add_employee
from views.career_management import render_career_management
from views.company_management import render_company_management
from views.dashboard import render_dashboard
from views.edit_employee import render_edit_employee
from views.employees import render_employees
from views.leave_management import render_leave_management
from views.leave_quota_management import render_leave_quota_management
from views.login import render_login
from views.menu_management import render_menu_management
from views.profile import render_profile
from views.users_management import render_users_management

# --- IMPORT MODUL WMS ---
from views.wms_categories import render_wms_categories
from views.wms_dashboard import render_wms_dashboard  # <--- Dashboard Khusus WMS
from views.wms_items_cud import render_wms_items_cud
from views.wms_items_list import render_wms_items_list
from views.wms_stock_cud import render_wms_stock_cud
from views.wms_stock_list import render_wms_stock_list
from views.wms_suppliers import render_wms_suppliers
from views.wms_warehouses import render_wms_warehouses

st.set_page_config(
    page_title="HRIS & WMS Mini Cloud", page_icon="📦", layout="wide"
)

# ---------------------------------------------------------
# HIDE STREAMLIT BRANDING & MANAGE APP BUTTON
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* Sembunyikan footer, header, dan menu utama */
    footer {visibility: hidden; display: none !important;}
    #MainMenu {visibility: hidden; display: none !important;}
    header {visibility: hidden; display: none !important;}
    
    /* Paling ampuh: sembunyikan seluruh kontainer pojok kanan bawah (badge/deploy button/status) */
    .stAppDeployButton {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important; visibility: hidden !important;}
    
    /* Sembunyikan elemen float di sudut kanan bawah layar secara mutlak */
    div.eczcs4p0, div[class*="css-1rs6os"], div[class*="viewerBadge"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Target universal untuk semua elemen fixed/absolute di pojok kanan bawah */
    body > div:last-child > div:last-child > div[style*="position: fixed"] {
        display: none !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
  render_login()
else:
  user_role = st.session_state.get("role", "USER")
  st.sidebar.title(f"👤 Halo, {st.session_state.get('full_name', 'Admin')}")
  st.sidebar.caption(f"Role: {user_role}")

  # ---------------------------------------------------------
  # PENYESUAIAN MENU BERDASARKAN ROLE (ISOLASI WMS_ADMIN)
  # ---------------------------------------------------------
  if user_role == "WMS_ADMIN":
    # Menu khusus untuk Administrator WMS / Gudang
    menu_options = [
        "📊 Dashboard WMS",  # <--- Dashboard Utama WMS
        "📌 Kelola Menu & Pintasan",  # <--- Akses Global Shortcut
        "📦 WMS - Manajemen Gudang",
        "🤝 WMS - Manajemen Supplier",
        "🏷️ WMS - Manajemen Kategori",
        "📋 WMS - Master Barang",
        "⚙️ WMS - Kelola Barang",
        "📊 WMS - Kartu Stok & Mutasi",
        "📝 WMS - Input Transaksi Stok",
    ]
  else:
    # Menu standar HRIS
    menu_options = [
        "Dashboard Utama",
        "Kelola Menu & Pintasan",
        "Data Karyawan",
        "Tambah Karyawan Baru",
        "Edit Data Karyawan",
        "Detail & Riwayat Karier",
        "Manajemen Karier",
        "Manajemen Izin & Cuti",
        "Kuota & Cuti Panjang",
    ]

    # Akses khusus SUPER_ADMIN
    if user_role == "SUPER_ADMIN":
      menu_options.extend(["Manajemen Perusahaan", "Manajemen Akun & User"])

  menu = st.sidebar.selectbox("Navigasi Menu", menu_options)

  st.sidebar.divider()
  if st.sidebar.button("🚪 Keluar (Logout)"):
    st.session_state["logged_in"] = False
    st.session_state.clear()
    st.rerun()

  # ---------------------------------------------------------
  # ROUTING HALAMAN
  # ---------------------------------------------------------
  if menu == "📊 Dashboard WMS":
    render_wms_dashboard()
  elif menu == "📌 Kelola Menu & Pintasan" or menu == "Kelola Menu & Pintasan":
    render_menu_management()
  elif menu == "📦 WMS - Manajemen Gudang":
    render_wms_warehouses()
  elif menu == "🤝 WMS - Manajemen Supplier":
    render_wms_suppliers()
  elif menu == "🏷️ WMS - Manajemen Kategori":
    render_wms_categories()
  elif menu == "📋 WMS - Master Barang":
    render_wms_items_list()
  elif menu == "⚙️ WMS - Kelola Barang":
    render_wms_items_cud()
  elif menu == "📊 WMS - Kartu Stok & Mutasi":
    render_wms_stock_list()
  elif menu == "📝 WMS - Input Transaksi Stok":
    render_wms_stock_cud()
  elif menu == "Dashboard Utama":
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
  elif menu == "Manajemen Izin & Cuti":
    render_leave_management()
  elif menu == "Kuota & Cuti Panjang":
    render_leave_quota_management()
  elif menu == "Manajemen Perusahaan":
    render_company_management()
  elif menu == "Manajemen Akun & User":
    render_users_management()