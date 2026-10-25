import uuid
from datetime import datetime
import streamlit as st
from database import get_connection


def get_current_stock(con, company_id, warehouse_id, item_id):
  """Fungsi pembantu untuk menghitung total stok aktual di gudang."""
  query = """
        SELECT 
            COALESCE(SUM(CASE WHEN transaction_type = 'IN' THEN quantity ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN transaction_type = 'OUT' THEN quantity ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN transaction_type = 'ADJUSTMENT' THEN quantity ELSE 0 END), 0) AS current_stock
        FROM wms_stock_logs
        WHERE company_id = ? AND warehouse_id = ? AND item_id = ?
    """
  res = con.execute(query, (company_id, warehouse_id, item_id)).fetchone()
  return res[0] if res else 0


def get_active_bins(con, company_id, warehouse_id, item_id):
  """Mengambil daftar bin/rak yang masih memiliki sisa stok > 0 untuk Mode Free."""
  query = """
        SELECT bin_location, 
               SUM(CASE WHEN transaction_type = 'IN' THEN quantity ELSE 0 END) -
               SUM(CASE WHEN transaction_type = 'OUT' THEN quantity ELSE 0 END) +
               SUM(CASE WHEN transaction_type = 'ADJUSTMENT' THEN quantity ELSE 0 END) AS remaining_qty
        FROM wms_stock_logs
        WHERE company_id = ? AND warehouse_id = ? AND item_id = ? 
          AND bin_location IS NOT NULL AND bin_location != ''
        GROUP BY bin_location
        HAVING remaining_qty > 0
        ORDER BY bin_location ASC
    """
  return con.execute(query, (company_id, warehouse_id, item_id)).fetchall()


def render_wms_stock_cud():
  st.title("⚙️ Kelola Mutasi Stok")
  st.markdown("Tambah, Perbarui, atau Hapus transaksi mutasi stok gudang.")

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error("⚠️ Session company_id tidak ditemukan. Silakan login ulang.")
    return

  con = get_connection()

  action_tab = st.radio(
      "Pilih Aksi",
      ["➕ Tambah Mutasi Stok", "✏️ Edit Transaksi", "🗑️ Hapus Transaksi"],
      horizontal=True,
  )
  st.divider()

  # Master Data Gudang & Items
  warehouses = con.execute(
      "SELECT id, warehouse_name, warehouse_type FROM wms_warehouses WHERE company_id = ? ORDER BY warehouse_name ASC",
      (company_id,),
  ).fetchall()
  if not warehouses:
    st.warning("⚠️ Buat minimal satu Gudang terlebih dahulu di menu Gudang!")
    return
  wh_options = {f"[{w[2]}] {w[1]}": w[0] for w in warehouses}

  items = con.execute(
      "SELECT id, sku, item_name, unit, bin_location FROM wms_items WHERE company_id = ? ORDER BY sku ASC",
      (company_id,),
  ).fetchall()
  if not items:
    st.warning("⚠️ Belum ada barang di katalog! Buat barang dulu di Kelola Barang.")
    return
  
  item_options = {f"[{it[1]}] {it[2]} (Satuan: {it[3]})": it for it in items}

  # ---------------------------------------------------------
  # TAB 1: TAMBAH MUTASI STOK
  # ---------------------------------------------------------
  if action_tab == "➕ Tambah Mutasi Stok":
    st.subheader("➕ Form Tambah Transaksi Mutasi Stok")

    col1, col2 = st.columns(2)
    with col1:
      selected_wh_label = st.selectbox("Pilih Gudang *", list(wh_options.keys()), key="add_wh")
      chosen_warehouse_id = wh_options[selected_wh_label]
    with col2:
      selected_item_label = st.selectbox("Pilih Barang (SKU / Nama) *", list(item_options.keys()), key="add_item")
      item_data = item_options[selected_item_label]
      chosen_item_id = item_data[0]
      default_master_bin = item_data[4]

    # HITUNG DAN TAMPILKAN STOK AKTUAL SAAT INI
    current_qty = get_current_stock(con, company_id, chosen_warehouse_id, chosen_item_id)
    st.info(f"📊 Stok Saat Ini di Gudang Terpilih: **{current_qty}**")

    # PILIHAN JENIS TRANSAKSI & BIN LOKASI (DITARUH DI LUAR FORM AGAR REAKTIF SANGAT INTERAKTIF)
    col3, col4 = st.columns(2)
    with col3:
      transaction_type = st.selectbox(
          "Jenis Transaksi Mutasi *",
          ["IN (Barang Masuk)", "OUT (Barang Keluar)", "ADJUSTMENT (Opname / Koreksi Stok)"],
          key="add_trans_type"
      )
      clean_type_preview = "IN" if "IN" in transaction_type else ("OUT" if "OUT" in transaction_type else "ADJUSTMENT")

    with col4:
      bin_mode = st.radio(
          "Pilih Metode Bin Lokasi *",
          ["Fix Bin (Mengikuti Master Barang)", "Free Bin (Bebas / Multi-Lokasi)"],
          key="add_bin_mode"
      )

    final_bin_location = None

    if bin_mode == "Fix Bin (Mengikuti Master Barang)":
      if default_master_bin:
        st.success(f"📍 Menggunakan Bin Fix Master Barang: **{default_master_bin}**")
      else:
        st.warning("⚠️ Master barang ini belum memiliki Bin Lokasi default.")
      final_bin_location = None
    
    else: # Free Bin Mode
      st.markdown("---")
      st.markdown("##### 📍 Input Rak / Bin Lokasi (Free Bin)")
      if clean_type_preview == "IN":
        final_bin_location = st.text_input(
            "Ketik Lokasi Rak / Bin Tujuan Masuk *",
            placeholder="Cth: Rak-A1-03 atau Zona-Transit",
            key="input_free_bin_in"
        )
      else: # OUT atau ADJUSTMENT mengambil dari bin yang masih aktif ada stoknya
        active_bins = get_active_bins(con, company_id, chosen_warehouse_id, chosen_item_id)
        if not active_bins:
          st.error("❌ Tidak ada bin/rak aktif yang memiliki stok untuk dikeluarkan!")
          bin_options_list = {}
        else:
          bin_options_list = {f"{b[0]} (Stok Tersedia: {b[1]})": b[0] for b in active_bins}
        
        if active_bins:
          selected_bin_label = st.selectbox("Pilih Bin Asal Barang *", list(bin_options_list.keys()), key="select_free_bin_out")
          final_bin_location = bin_options_list[selected_bin_label]
        else:
          final_bin_location = None

    st.markdown("---")

    # BLOK FORM UTAMA UNTUK INPUT DETAIL DAN SUBMIT
    with st.form("form_add_stock_log", clear_on_submit=True):
      if clean_type_preview == "ADJUSTMENT":
        quantity = st.number_input(
            "Kuantitas Adjustment (+ / -) *", 
            step=1, 
            value=0, 
            min_value=-999999,
            help="Isi angka positif (cth: 10) untuk menambah, atau negatif (cth: -4) untuk mengurangi."
        )
      else:
        quantity = st.number_input("Kuantitas (Quantity) *", step=1, value=1, min_value=1)

      col5, col6 = st.columns(2)
      with col5:
        t_date = st.date_input("Tanggal Transaksi *", value=datetime.today())
      with col6:
        t_time = st.time_input("Jam Transaksi *", value=datetime.now().time())

      col7, col8 = st.columns(2)
      with col7:
        reference_number = st.text_input("No. Referensi / Surat Jalan / PO", placeholder="Cth: SJ/2026/10/001")
      with col8:
        pic_name = st.text_input("Nama Petugas / PIC *", placeholder="Cth: Budi Santoso")

      notes = st.text_area("Catatan Tambahan (Opsional)")
      btn_submit = st.form_submit_button("💾 Simpan Transaksi", type="primary")

      if btn_submit:
        clean_type = clean_type_preview
        final_qty = abs(quantity) if clean_type in ["IN", "OUT"] else quantity

        if not pic_name.strip():
          st.error("⚠️ Nama Petugas / PIC wajib diisi!")
        elif clean_type != "ADJUSTMENT" and quantity <= 0:
          st.error("⚠️ Kuantitas harus lebih dari 0!")
        elif clean_type == "ADJUSTMENT" and quantity == 0:
          st.error("⚠️ Kuantitas adjustment tidak boleh 0!")
        elif bin_mode == "Free Bin (Bebas / Multi-Lokasi)" and not final_bin_location:
          st.error("⚠️ Bin Lokasi wajib diisi / dipilih untuk metode Free Bin!")
        elif clean_type == "OUT" and final_qty > current_qty:
          st.error(f"❌ Gagal! Stok total tidak cukup. Stok tersedia: **{current_qty}**, pengeluaran: **{final_qty}**.")
        else:
          try:
            t_datetime = f"{t_date} {t_time.strftime('%H:%M:%S')}"
            log_id = str(uuid.uuid4())
            con.execute(
                """
                    INSERT INTO wms_stock_logs (
                        id, company_id, warehouse_id, item_id, transaction_type, 
                        quantity, bin_location, transaction_date, reference_number, notes, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    company_id,
                    chosen_warehouse_id,
                    chosen_item_id,
                    clean_type,
                    final_qty,
                    final_bin_location,
                    t_datetime,
                    reference_number.strip() if reference_number else None,
                    notes.strip() if notes else None,
                    pic_name.strip(),
                ),
            )
            con.commit()
            con.sync()
            st.success("🎉 Transaksi mutasi stok berhasil dicatat!")
            st.rerun()
          except Exception as e:
            st.error(f"❌ Terjadi kesalahan database: {e}")

  # ---------------------------------------------------------
  # TAB 2: EDIT TRANSAKSI
  # ---------------------------------------------------------
  elif action_tab == "✏️ Edit Transaksi":
    st.subheader("✏️ Form Edit Transaksi Mutasi")

    logs_raw = con.execute(
        """
            SELECT l.id, l.transaction_date, w.warehouse_name, i.sku, i.item_name, l.transaction_type, l.quantity, l.reference_number, l.notes, l.created_by, l.bin_location
            FROM wms_stock_logs l
            JOIN wms_warehouses w ON l.warehouse_id = w.id
            JOIN wms_items i ON l.item_id = i.id
            WHERE l.company_id = ?
            ORDER BY l.transaction_date DESC LIMIT 100
        """,
        (company_id,),
    ).fetchall()

    if not logs_raw:
      st.info("ℹ️ Belum ada transaksi mutasi stok untuk diedit.")
      return

    log_map = {
        f"[{l[1]}] {l[2]} | {l[3]} ({l[4]}) | {l[5]} {l[6]} (Bin: {l[10] or 'Fix/Master'})": l 
        for l in logs_raw
    }
    selected_log_label = st.selectbox("Pilih Transaksi yang Akan Diedit", list(log_map.keys()))
    selected_log = log_map[selected_log_label]

    (
        l_id,
        l_date,
        l_wname,
        l_sku,
        l_iname,
        l_type,
        l_qty,
        l_ref,
        l_notes,
        l_pic,
        l_bin,
    ) = selected_log

    with st.form("form_edit_stock_log"):
      col1, col2 = st.columns(2)
      with col1:
        edit_type = st.selectbox(
            "Jenis Transaksi *",
            ["IN", "OUT", "ADJUSTMENT"],
            index=["IN", "OUT", "ADJUSTMENT"].index(l_type) if l_type in ["IN", "OUT", "ADJUSTMENT"] else 0,
        )
      with col2:
        edit_qty = st.number_input("Kuantitas *", value=int(l_qty), min_value=-999999, step=1)

      edit_bin_loc = st.text_input("Bin Lokasi (Kosongkan jika Fix Bin)", value=l_bin or "")

      col3, col4 = st.columns(2)
      with col3:
        edit_ref = st.text_input("No. Referensi / SJ", value=l_ref or "")
      with col4:
        edit_pic = st.text_input("Nama Petugas / PIC *", value=l_pic or "")

      edit_notes = st.text_area("Catatan", value=l_notes or "")
      btn_update = st.form_submit_button("🔄 Perbarui Transaksi", type="primary")

      if btn_update:
        if not edit_pic.strip():
          st.error("⚠️ Nama Petugas / PIC wajib diisi!")
        else:
          try:
            con.execute(
                """
                    UPDATE wms_stock_logs
                    SET transaction_type = ?, quantity = ?, bin_location = ?, reference_number = ?, notes = ?, created_by = ?
                    WHERE id = ? AND company_id = ?
                """,
                (
                    edit_type,
                    edit_qty,
                    edit_bin_loc.strip() if edit_bin_loc else None,
                    edit_ref.strip() if edit_ref else None,
                    edit_notes.strip() if edit_notes else None,
                    edit_pic.strip(),
                    l_id,
                    company_id,
                ),
            )
            con.commit()
            con.sync()
            st.success("🎉 Transaksi mutasi berhasil diperbarui!")
            st.rerun()
          except Exception as e:
            st.error(f"❌ Kesalahan database: {e}")

  # ---------------------------------------------------------
  # TAB 3: HAPUS TRANSAKSI
  # ---------------------------------------------------------
  elif action_tab == "🗑️ Hapus Transaksi":
    st.subheader("🗑️ Hapus Transaksi Mutasi")

    logs_del_raw = con.execute(
        """
            SELECT l.id, l.transaction_date, w.warehouse_name, i.sku, i.item_name, l.transaction_type, l.quantity, l.bin_location
            FROM wms_stock_logs l
            JOIN wms_warehouses w ON l.warehouse_id = w.id
            JOIN wms_items i ON l.item_id = i.id
            WHERE l.company_id = ?
            ORDER BY l.transaction_date DESC LIMIT 100
        """,
        (company_id,),
    ).fetchall()

    if not logs_del_raw:
      st.info("ℹ️ Tidak ada transaksi mutasi untuk dihapus.")
      return

    log_del_map = {
        f"[{l[1]}] {l[2]} | {l[3]} ({l[4]}) | {l[5]} {l[6]} (Bin: {l[7] or 'Fix/Master'})": l[0]
        for l in logs_del_raw
    }
    selected_del_label = st.selectbox("Pilih Transaksi yang Akan Dihapus", list(log_del_map.keys()))
    selected_del_id = log_del_map[selected_del_label]

    st.warning(f"⚠️ Yakin ingin menghapus transaksi **'{selected_del_label}'**?")

    if st.button("🔴 Ya, Hapus Transaksi Ini"):
      con.execute(
          "DELETE FROM wms_stock_logs WHERE id = ? AND company_id = ?",
          (selected_del_id, company_id),
      )
      con.commit()
      con.sync()
      st.success("🗑️ Transaksi mutasi berhasil dihapus!")
      st.rerun()