import pandas as pd
import streamlit as st
from database import get_connection


def render_wms_dashboard():
  st.title("📦 WMS Dashboard Perusahaan")

  company_id = st.session_state.get("company_id")
  user_id = st.session_state.get("user_id")  # Ambil user_id aktif

  if not company_id:
    st.error("⚠️ Session company_id tidak ditemukan. Silakan login ulang.")
    return

  con = get_connection()

  # Header & Tombol Refresh Manual
  col_t, col_b = st.columns([4, 1])
  with col_t:
    st.markdown(
        "Selamat datang di Modul **Warehouse Management System (WMS)**."
        " Ringkasan eksekutif posisi stok & mutasi inventaris gudang Anda."
    )
  with col_b:
    if st.button("🔄 Muat Ulang", type="primary", use_container_width=True):
      st.rerun()

  # ---------------------------------------------------------
  # 1. PERHITUNGAN RINGKASAN METRIK WMS
  # ---------------------------------------------------------
  try:
    # Total SKU Barang
    total_items = (
        con.execute(
            "SELECT COUNT(*) FROM wms_items WHERE company_id = ?",
            (company_id,),
        ).fetchone()[0]
        or 0
    )

    # Total Supplier
    total_suppliers = (
        con.execute(
            "SELECT COUNT(*) FROM wms_suppliers WHERE company_id = ?",
            (company_id,),
        ).fetchone()[0]
        or 0
    )

    # Total Mutasi Stok Hari Ini
    total_logs_today = (
        con.execute(
            "SELECT COUNT(*) FROM wms_stock_logs WHERE company_id = ? AND"
            " DATE(transaction_date) = DATE('now')",
            (company_id,),
        ).fetchone()[0]
        or 0
    )

    # Total Barang dalam Kondisi Kritis (Stok <= Minimum Stock)
    query_critical = """
            SELECT COUNT(*) FROM (
                SELECT i.id, i.minimum_stock,
                    COALESCE(
                        (SELECT 
                            SUM(CASE WHEN l.transaction_type = 'IN' THEN l.quantity ELSE 0 END) -
                            SUM(CASE WHEN l.transaction_type = 'OUT' THEN l.quantity ELSE 0 END) +
                            SUM(CASE WHEN l.transaction_type = 'ADJUSTMENT' THEN l.quantity ELSE 0 END)
                         FROM wms_stock_logs l
                         WHERE l.item_id = i.id AND l.company_id = i.company_id
                        ), 0
                    ) AS current_stock
                FROM wms_items i
                WHERE i.company_id = ?
            ) WHERE current_stock <= minimum_stock
        """
    critical_items = (
        con.execute(query_critical, (company_id,)).fetchone()[0] or 0
    )

  except Exception:
    total_items, total_suppliers, total_logs_today, critical_items = (
        0,
        0,
        0,
        0,
    )

  # Tampilkan Kartu Metrik WMS
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("📦 Total Katalog Barang", f"{total_items} SKU")
  col2.metric(
      "🚨 Item Kritis (≤ Min Stock)",
      f"{critical_items} Item",
      delta_color="inverse" if critical_items > 0 else "normal",
  )
  col3.metric("🤝 Total Supplier Aktif", f"{total_suppliers} Vendor")
  col4.metric("📊 Transaksi Stok Hari Ini", f"{total_logs_today} Transaksi")

  st.divider()

  # ---------------------------------------------------------
  # 2. PINTASAN MENU UTAMA & SHORTCUT PRIBADI
  # ---------------------------------------------------------
  st.subheader("⚡ Pintasan Menu & Shortcut Pribadi")

  try:
    df_menus = pd.read_sql(
        f"""
            SELECT menu_group, menu_title, menu_url, image_url 
            FROM hris_company_menus 
            WHERE company_id = '{company_id}' AND user_id = '{user_id}' 
            ORDER BY menu_group ASC, sort_order ASC
        """,
        con,
    )
  except Exception:
    df_menus = pd.DataFrame()

  if not df_menus.empty:
    # Grid 3 kolom per baris
    cols = st.columns(3)
    for idx, row in df_menus.iterrows():
      col_target = cols[idx % 3]
      with col_target:
        with st.container(border=True):
          # Tampilkan Banner Gambar dari Catbox / URL jika ada
          if row["image_url"] and str(row["image_url"]).strip() != "":
            st.markdown(
                f"""
                    <div style="margin: -15px -15px 12px -15px; overflow: hidden; border-top-left-radius: 8px; border-top-right-radius: 8px; height: 120px;">
                        <img src="{row['image_url']}" style="width: 100%; height: 100%; object-fit: cover;" />
                    </div>
                """,
                unsafe_allow_html=True,
            )

          st.caption(f"📂 {row['menu_group']}")
          st.markdown(f"**{row['menu_title']}**")

          # Tombol Link Resmi Streamlit
          st.link_button(
              "Buka Tautan 🚀", row["menu_url"], use_container_width=True
          )
  else:
    st.info(
        "💡 Belum ada pintasan menu/shortcut pribadi yang diatur. Silakan buat"
        " melalui menu **Kelola Menu & Pintasan**."
    )

  st.divider()
  st.markdown(
      "📌 *Gunakan navigasi di sebelah kiri (sidebar) untuk mengelola Gudang,"
      " Supplier, Kategori, Barang, dan Transaksi Stok.*"
  )