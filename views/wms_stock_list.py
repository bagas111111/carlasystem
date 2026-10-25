from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from database import get_connection


def render_wms_stock_list():
  st.title("📋 Kartu Stok & Pelacakan Bin Lokasi (WMS)")
  st.markdown(
      "Pantau riwayat mutasi stok secara real-time atau lacak posisi stok"
      " berdasarkan Rak / Bin Lokasi."
  )

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error("⚠️ Session company_id tidak ditemukan. Silakan login ulang.")
    return

  con = get_connection()

  # ---------------------------------------------------------
  # TAB MENU UTAMA
  # ---------------------------------------------------------
  tab_card, tab_bin = st.tabs([
      "📋 Riwayat Kartu Stok",
      "📍 Pelacakan Stok per Bin Lokasi (Free Bin)",
  ])

  # =========================================================
  # TAB 1: RIWAYAT KARTU STOK (FITUR LAMA YANG DIPERTAHANKAN)
  # =========================================================
  with tab_card:
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
          key="card_search",
      )
    with col_f2:
      wh_options = {"-- Semua Gudang --": ""}
      for w in warehouses:
        wh_options[w[1]] = w[0]
      selected_wh_filter = st.selectbox(
          "Filter Gudang", list(wh_options.keys()), key="card_wh"
      )
    with col_f3:
      type_options = {
          "-- Semua Jenis Mutasi --": "",
          "IN (Barang Masuk)": "IN",
          "OUT (Barang Keluar)": "OUT",
          "ADJUSTMENT (Koreksi/Opname)": "ADJUSTMENT",
      }
      selected_type_filter = st.selectbox(
          "Filter Jenis Transaksi", list(type_options.keys()), key="card_type"
      )

    col_f4, col_f5, col_f6 = st.columns(3)
    with col_f4:
      pic_options = {"-- Semua PIC / Petugas --": ""}
      for p in pics:
        if p[0]:
          pic_options[p[0]] = p[0]
      selected_pic_filter = st.selectbox(
          "Filter Petugas (PIC)", list(pic_options.keys()), key="card_pic"
      )
    with col_f5:
      start_date = st.date_input(
          "Dari Tanggal",
          value=datetime.today() - timedelta(days=30),
          key="card_start",
      )
    with col_f6:
      end_date = st.date_input(
          "Sampai Tanggal", value=datetime.today(), key="card_end"
      )

    col_btn1, _ = st.columns([1, 4])
    with col_btn1:
      btn_search = st.button(
          "🔍 Tampilkan Kartu Stok", type="primary", use_container_width=True
      )

    st.divider()

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
    else:
      query = """
            SELECT 
                l.id,
                l.transaction_date,
                w.warehouse_name,
                i.sku,
                i.item_name,
                l.transaction_type,
                l.quantity,
                COALESCE(l.bin_location, i.bin_location, '-') AS bin_location,
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
        params.extend([
            f"%{search_query.strip()}%",
            f"%{search_query.strip()}%",
            f"%{search_query.strip()}%",
        ])

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
                "Bin Lokasi",
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
        st.dataframe(
            df.drop(columns=["ID"]), use_container_width=True, hide_index=True
        )
      else:
        st.warning(
            "⚠️ Tidak ada data mutasi stok yang ditemukan sesuai filter tersebut."
        )

  # =========================================================
  # TAB 2: PELACAKAN STOK PER BIN LOKASI (FREE BIN & STOK AKTIF)
  # =========================================================
  with tab_bin:
    st.markdown("#### 📍 Cari Posisi Barang Berdasarkan Bin / Rak Gudang")
    st.markdown(
        "Menu ini melacak sisa stok aktual yang saat ini tersimpan di setiap"
        " Bin / Rak (terutama untuk sistem Free Bin)."
    )

    try:
      warehouses_bin = con.execute(
          "SELECT id, warehouse_name FROM wms_warehouses WHERE company_id = ? ORDER BY warehouse_name ASC",
          (company_id,),
      ).fetchall()
    except Exception:
      warehouses_bin = []

    col_b1, col_b2 = st.columns(2)
    with col_b1:
      wh_bin_options = {"-- Pilih Gudang Terlebih Dahulu --": ""}
      for w in warehouses_bin:
        wh_bin_options[w[1]] = w[0]
      selected_wh_bin_label = st.selectbox(
          "Pilih Gudang *", list(wh_bin_options.keys())
      )
      selected_wh_bin_id = wh_bin_options[selected_wh_bin_label]
    with col_b2:
      bin_search_query = st.text_input(
          "Filter / Cari Nama Bin atau SKU Barang",
          placeholder="Cth: Rak-A1 atau SKU...",
      )

    if not selected_wh_bin_id:
      st.info(
          "💡 **Silakan pilih gudang di atas** untuk memuat daftar stok dan"
          " posisi bin lokasinya."
      )
    else:
      # Query menghitung sisa stok per item dan per bin_location yang aktif (> 0)
      bin_query = """
                SELECT 
                    w.warehouse_name,
                    i.sku,
                    i.item_name,
                    COALESCE(l.bin_location, i.bin_location, 'FIX/DEFAULT') AS active_bin,
                    (
                        SUM(CASE WHEN l.transaction_type = 'IN' THEN l.quantity ELSE 0 END) -
                        SUM(CASE WHEN l.transaction_type = 'OUT' THEN l.quantity ELSE 0 END) +
                        SUM(CASE WHEN l.transaction_type = 'ADJUSTMENT' THEN l.quantity ELSE 0 END)
                    ) AS remaining_qty,
                    i.unit
                FROM wms_stock_logs l
                JOIN wms_warehouses w ON l.warehouse_id = w.id
                JOIN wms_items i ON l.item_id = i.id
                WHERE l.company_id = ? AND l.warehouse_id = ?
            """
      bin_params = [company_id, selected_wh_bin_id]

      # Kelompokkan per item dan per bin_location
      bin_query += " GROUP BY l.warehouse_id, l.item_id, active_bin HAVING remaining_qty > 0"
      bin_query += " ORDER BY active_bin ASC, i.sku ASC"

      bin_raw = con.execute(bin_query, bin_params).fetchall()

      if bin_raw:
        df_bin = pd.DataFrame(
            bin_raw,
            columns=[
                "Gudang",
                "SKU",
                "Nama Barang",
                "Bin Lokasi",
                "Stok Aktual di Bin",
                "Satuan",
            ],
        )

        # Filter tambahan berdasarkan text input pencarian bin/sku
        if bin_search_query.strip():
          q_val = bin_search_query.strip().lower()
          df_bin = df_bin[
              df_bin["Bin Lokasi"].str.lower().str.contains(q_val)
              | df_bin["SKU"].str.lower().str.contains(q_val)
              | df_bin["Nama Barang"].str.lower().str.contains(q_val)
          ]

        st.success(
            f"📍 Ditemukan {len(df_bin)} record penempatan barang aktif di"
            f" gudang **{selected_wh_bin_label}**."
        )
        st.dataframe(df_bin, use_container_width=True, hide_index=True)
      else:
        st.warning(
            "⚠️ Belum ada data penempatan stok aktif di gudang ini (atau"
            " seluruh stok sudah bernilai 0)."
        )