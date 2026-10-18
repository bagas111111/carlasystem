import uuid
from datetime import datetime
import streamlit as st
from database import get_connection


def get_current_stock(con, company_id, warehouse_id, item_id):
  """Fungsi pembantu untuk menghitung stok aktual saat ini di gudang tertentu."""
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


def render_wms_stock_cud():
  st.title("⚙️ Kelola Mutasi Stok (CUD)")
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
      "SELECT id, sku, item_name, unit FROM wms_items WHERE company_id = ? ORDER BY sku ASC",
      (company_id,),
  ).fetchall()
  if not items:
    st.warning("⚠️ Belum ada barang di katalog! Buat barang dulu di Kelola Barang.")
    return
  item_options = {f"[{it[1]}] {it[2]} (Satuan: {it[3]})": it[0] for it in items}

  # ---------------------------------------------------------
  # TAB 1: TAMBAH MUTASI STOK
  # ---------------------------------------------------------
  if action_tab == "➕ Tambah Mutasi Stok":
    st.subheader("➕ Form Tambah Transaksi Mutasi Stok")

    col1, col2 = st.columns(2)
    with col1:
      selected_wh_label = st.selectbox(
          "Pilih Gudang *", list(wh_options.keys()), key="add_wh"
      )
      chosen_warehouse_id = wh_options[selected_wh_label]
    with col2:
      selected_item_label = st.selectbox(
          "Pilih Barang (SKU / Nama) *", list(item_options.keys()), key="add_item"
      )
      chosen_item_id = item_options[selected_item_label]

    # HITUNG DAN TAMPILKAN STOK AKTUAL SAAT INI
    current_qty = get_current_stock(
        con, company_id, chosen_warehouse_id, chosen_item_id
    )
    st.info(f"📊 Stok Saat Ini di Gudang Terpilih: **{current_qty}**")

    with st.form("form_add_stock_log", clear_on_submit=True):
      col3, col4 = st.columns(2)
      with col3:
        transaction_type = st.selectbox(
            "Jenis Transaksi Mutasi *",
            ["IN (Barang Masuk)", "OUT (Barang Keluar)", "ADJUSTMENT (Opname / Koreksi Stok)"],
        )
      with col4:
        quantity = st.number_input("Kuantitas (Quantity) *", step=1, value=1)

      col5, col6 = st.columns(2)
      with col5:
        t_date = st.date_input("Tanggal Transaksi *", value=datetime.today())
      with col6:
        t_time = st.time_input("Jam Transaksi *", value=datetime.now().time())

      col7, col8 = st.columns(2)
      with col7:
        reference_number = st.text_input(
            "No. Referensi / Surat Jalan / PO", placeholder="Cth: SJ/2026/10/001"
        )
      with col8:
        pic_name = st.text_input("Nama Petugas / PIC *", placeholder="Cth: Budi Santoso")

      notes = st.text_area("Catatan Tambahan (Opsional)")
      btn_submit = st.form_submit_button("💾 Simpan Transaksi", type="primary")

      if btn_submit:
        if not pic_name.strip():
          st.error("⚠️ Nama Petugas / PIC wajib diisi!")
        elif quantity == 0:
          st.error("⚠️ Kuantitas tidak boleh 0!")
        else:
          clean_type = "IN" if "IN" in transaction_type else ("OUT" if "OUT" in transaction_type else "ADJUSTMENT")
          abs_qty = abs(quantity) if clean_type in ["IN", "OUT"] else quantity

          # VALIDASI STOK UNTUK BARANG KELUAR (OUT)
          if clean_type == "OUT" and abs_qty > current_qty:
            st.error(
                f"❌ Gagal! Stok tidak cukup. Stok tersedia: **{current_qty}**, pengeluaran yang diminta: **{abs_qty}**."
            )
          elif clean_type == "ADJUSTMENT" and (current_qty + abs_qty) < 0:
            st.error(
                f"❌ Gagal! Adjustment akan membuat total stok minus! (Stok saat ini: {current_qty})"
            )
          else:
            try:
              t_datetime = f"{t_date} {t_time.strftime('%H:%M:%S')}"
              log_id = str(uuid.uuid4())
              con.execute(
                  """
                        INSERT INTO wms_stock_logs (
                            id, company_id, warehouse_id, item_id, transaction_type, 
                            quantity, transaction_date, reference_number, notes, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                  (
                      log_id,
                      company_id,
                      chosen_warehouse_id,
                      chosen_item_id,
                      clean_type,
                      abs_qty,
                      t_datetime,
                      reference_number.strip(),
                      notes.strip(),
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
            SELECT l.id, l.transaction_date, w.warehouse_name, i.sku, i.item_name, l.transaction_type, l.quantity, l.reference_number, l.notes, l.created_by, l.warehouse_id, l.item_id
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
        f"[{l[1]}] {l[2]} - {l[3]} ({l[4]}) | {l[5]} {l[6]}": l for l in logs_raw
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
        l_wid,
        l_iid,
    ) = selected_log

    with st.form("form_edit_stock_log"):
      col1, col2 = st.columns(2)
      with col1:
        edit_type = st.selectbox(
            "Jenis Transaksi *",
            ["IN", "OUT", "ADJUSTMENT"],
            index=["IN", "OUT", "ADJUSTMENT"].index(l_type),
        )
      with col2:
        edit_qty = st.number_input("Kuantitas *", value=int(l_qty))

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
                        SET transaction_type = ?, quantity = ?, reference_number = ?, notes = ?, created_by = ?
                        WHERE id = ? AND company_id = ?
                    """,
                (
                    edit_type,
                    edit_qty,
                    edit_ref.strip(),
                    edit_notes.strip(),
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
            SELECT l.id, l.transaction_date, w.warehouse_name, i.sku, i.item_name, l.transaction_type, l.quantity
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
        f"[{l[1]}] {l[2]} - {l[3]} ({l[4]}) | {l[5]} {l[6]}": l[0]
        for l in logs_del_raw
    }
    selected_del_label = st.selectbox(
        "Pilih Transaksi yang Akan Dihapus", list(log_del_map.keys())
    )
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