from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from database import get_connection


def render_wms_stock_list():
  st.title("📋 Kartu Stok & Riwayat Mutasi (WMS)")
  st.markdown(
      "Pantau mutasi barang masuk, keluar, dan penyesuaian stok secara real-time"
      " berdasarkan filter."
  )

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error("⚠️ Session company_id tidak ditemukan. Silakan login ulang.")
    return

  con = get_connection()

  # ---------------------------------------------------------
  # FILTER & SEARCH PANEL
  # ---------------------------------------------------------
  st.markdown("#### 🔍 Filter & Pencarian Kartu Stok")

  try:
    warehouses = con.execute(
        "SELECT id, warehouse_name FROM wms_warehouses WHERE company_id = ? ORDER BY warehouse_name ASC",
        (company_id,),
    ).fetchall()
    pics = con.execute(
        "SELECT DISTINCT created_by FROM wms_stock_logs WHERE company_id = ? AND created_by IS NOT NULL ORDER BY created_by ASC",
        (company_id,),
    ).fetchall()
  except Exception:
    warehouses, pics = [], []

  col_f1, col_f2, col_f3 = st.columns(3)
  with col_f1:
    search_query = st.text_input(
        "Cari SKU / Nama Barang / No. Ref",
        placeholder="Ketik SKU, Nama, atau No. Surat Jalan...",
    )
  with col_f2:
    wh_options = {"-- Semua Gudang --": ""}
    for w in warehouses:
      wh_options[w[1]] = w[0]
    selected_wh_filter = st.selectbox(
        "Filter Gudang", list(wh_options.keys())
    )
  with col_f3:
    type_options = {
        "-- Semua Jenis Mutasi --": "",
        "IN (Barang Masuk)": "IN",
        "OUT (Barang Keluar)": "OUT",
        "ADJUSTMENT (Koreksi/Opname)": "ADJUSTMENT",
    }
    selected_type_filter = st.selectbox(
        "Filter Jenis Transaksi", list(type_options.keys())
    )

  col_f4, col_f5, col_f6 = st.columns(3)
  with col_f4:
    pic_options = {"-- Semua PIC / Petugas --": ""}
    for p in pics:
      if p[0]:
        pic_options[p[0]] = p[0]
    selected_pic_filter = st.selectbox(
        "Filter Petugas (PIC)", list(pic_options.keys())
    )
  with col_f5:
    start_date = st.date_input(
        "Dari Tanggal", value=datetime.today() - timedelta(days=30)
    )
  with col_f6:
    end_date = st.date_input("Sampai Tanggal", value=datetime.today())

  col_btn1, col_btn2 = st.columns([1, 4])
  with col_btn1:
    btn_search = st.button("🔍 Tampilkan Kartu Stok", type="primary", use_container_width=True)

  st.divider()

  # Cek apakah user sudah menekan tombol atau melakukan filter
  is_filtered = (
      btn_search
      or bool(search_query.strip())
      or bool(wh_options[selected_wh_filter])
      or bool(type_options[selected_type_filter])
      or bool(pic_options[selected_pic_filter])
  )

  if not is_filtered:
    st.info(
        "💡 **Silakan tentukan filter tanggal, gudang, atau kata kunci pencarian,"
        " lalu klik tombol 'Tampilkan Kartu Stok'** untuk melihat riwayat"
        " mutasi."
    )
    return

  # ---------------------------------------------------------
  # QUERY DATA MUTASI STOK
  # ---------------------------------------------------------
  query = """
        SELECT 
            l.id,
            l.transaction_date,
            w.warehouse_name,
            i.sku,
            i.item_name,
            l.transaction_type,
            l.quantity,
            i.unit,
            COALESCE(l.reference_number, '-') AS reference_number,
            COALESCE(l.notes, '-') AS notes,
            l.created_by
        FROM wms_stock_logs l
        JOIN wms_warehouses w ON l.warehouse_id = w.id
        JOIN wms_items i ON l.item_id = i.id
        WHERE l.company_id = ?
          AND DATE(l.transaction_date) BETWEEN ? AND ?
    """
  params = [company_id, str(start_date), str(end_date)]

  if search_query.strip():
    query += " AND (i.sku LIKE ? OR i.item_name LIKE ? OR l.reference_number LIKE ?)"
    params.extend(
        [
            f"%{search_query.strip()}%",
            f"%{search_query.strip()}%",
            f"%{search_query.strip()}%",
        ]
    )

  if wh_options[selected_wh_filter]:
    query += " AND l.warehouse_id = ?"
    params.append(wh_options[selected_wh_filter])

  if type_options[selected_type_filter]:
    query += " AND l.transaction_type = ?"
    params.append(type_options[selected_type_filter])

  if pic_options[selected_pic_filter]:
    query += " AND l.created_by = ?"
    params.append(pic_options[selected_pic_filter])

  query += " ORDER BY l.transaction_date DESC LIMIT 300"

  logs_raw = con.execute(query, params).fetchall()

  if logs_raw:
    df = pd.DataFrame(
        logs_raw,
        columns=[
            "ID",
            "Waktu Transaksi",
            "Gudang",
            "SKU",
            "Nama Barang",
            "Tipe",
            "Qty",
            "Satuan",
            "No. Referensi",
            "Catatan",
            "PIC",
        ],
    )

    st.success(
        f"📊 Ditemukan {len(df)} catatan mutasi stok pada rentang tanggal"
        f" {start_date} s.d. {end_date}."
    )
    st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
  else:
    st.warning(
        "⚠️ Tidak ada data mutasi stok yang ditemukan sesuai filter tersebut."
    )