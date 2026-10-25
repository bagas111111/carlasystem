import pandas as pd
import streamlit as st
from database import get_connection


def render_wms_items_list():
  st.title("📋 Rekap Inventaris & Stok Barang (WMS)")
  st.markdown(
      "Cari, filter, dan pantau posisi stok barang aktual bersanding dengan"
      " spesifikasi lengkap dan batas Reorder Point."
  )

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error("⚠️ Session company_id tidak ditemukan. Silakan login ulang.")
    return

  con = get_connection()

  # ---------------------------------------------------------
  # FILTER & SEARCH PANEL
  # ---------------------------------------------------------
  st.markdown("#### 🔍 Filter & Pencarian Data Stok")

  try:
    warehouses = con.execute(
        "SELECT id, warehouse_name FROM wms_warehouses WHERE company_id = ? ORDER BY warehouse_name ASC",
        (company_id,),
    ).fetchall()
    categories = con.execute(
        "SELECT id, category_name FROM wms_categories WHERE company_id = ? ORDER BY category_name ASC",
        (company_id,),
    ).fetchall()
    suppliers = con.execute(
        "SELECT id, supplier_name FROM wms_suppliers WHERE company_id = ? ORDER BY supplier_name ASC",
        (company_id,),
    ).fetchall()
    materials = con.execute(
        "SELECT DISTINCT material FROM wms_items WHERE company_id = ? AND material IS NOT NULL AND material != '' ORDER BY material ASC",
        (company_id,),
    ).fetchall()
    bins = con.execute(
        "SELECT DISTINCT bin_location FROM wms_items WHERE company_id = ? AND bin_location IS NOT NULL AND bin_location != '' ORDER BY bin_location ASC",
        (company_id,),
    ).fetchall()
  except Exception:
    warehouses, categories, suppliers, materials, bins = [], [], [], [], []

  col_f1, col_f2, col_f3 = st.columns(3)
  with col_f1:
    search_query = st.text_input(
        "Cari SKU / Nama Barang",
        placeholder="Ketik SKU atau Nama Barang...",
    )
  with col_f2:
    wh_options = {"-- Semua Gudang (Total All) --": ""}
    for w in warehouses:
      wh_options[w[1]] = w[0]
    selected_wh_label = st.selectbox(
        "Filter Gudang", list(wh_options.keys())
    )
    selected_wh_id = wh_options[selected_wh_label]
  with col_f3:
    cat_options = {"-- Semua Kategori --": ""}
    for c in categories:
      cat_options[c[1]] = c[0]
    selected_cat_filter = st.selectbox(
        "Filter Kategori Utama", list(cat_options.keys())
    )

  col_f4, col_f5, col_f6 = st.columns(3)
  with col_f4:
    sup_options = {"-- Semua Supplier --": ""}
    for s in suppliers:
      sup_options[s[1]] = s[0]
    selected_sup_filter = st.selectbox(
        "Filter Supplier Utama", list(sup_options.keys())
    )
  with col_f5:
    mat_options = {"-- Semua Material --": ""}
    for m in materials:
      mat_options[m[0]] = m[0]
    selected_mat_filter = st.selectbox(
        "Filter Material", list(mat_options.keys())
    )
  with col_f6:
    bin_options = {"-- Semua Lokasi Rak --": ""}
    for b in bins:
      bin_options[b[0]] = b[0]
    selected_bin_filter = st.selectbox(
        "Filter Lokasi Rak / Bin", list(bin_options.keys())
    )

  col_btn1, _ = st.columns([1, 4])
  with col_btn1:
    btn_search = st.button("🔍 Tampilkan Rekap Stok", type="primary", use_container_width=True)

  st.divider()

  # Cek aksi filter
  is_filtered = (
      btn_search
      or bool(search_query.strip())
      or bool(selected_wh_id)
      or bool(cat_options[selected_cat_filter])
      or bool(sup_options[selected_sup_filter])
      or bool(mat_options[selected_mat_filter])
      or bool(bin_options[selected_bin_filter])
  )

  if not is_filtered:
    st.info(
        "💡 **Silakan pilih filter gudang/kategori atau ketik SKU/Nama Barang,"
        " lalu klik tombol 'Tampilkan Rekap Stok'**."
    )
    return

  # ---------------------------------------------------------
  # QUERY REKAP STOK (1 Baris per Item)
  # ---------------------------------------------------------
  wh_subquery_clause = "AND l.warehouse_id = ?" if selected_wh_id else ""

  query = f"""
        SELECT 
            i.id,
            i.sku,
            i.item_name,
            c1.category_name AS kategori_utama,
            COALESCE(c2.category_name, '-') AS sub_kategori,
            COALESCE(i.material, '-') AS material,
            COALESCE(i.specification, '-') AS specification,
            COALESCE(i.variant, '-') AS variant,
            COALESCE(i.bin_location, '-') AS bin_location,
            i.unit,
            COALESCE(
                (SELECT 
                    SUM(CASE WHEN l.transaction_type = 'IN' THEN l.quantity ELSE 0 END) -
                    SUM(CASE WHEN l.transaction_type = 'OUT' THEN l.quantity ELSE 0 END) +
                    SUM(CASE WHEN l.transaction_type = 'ADJUSTMENT' THEN l.quantity ELSE 0 END)
                 FROM wms_stock_logs l
                 WHERE l.item_id = i.id AND l.company_id = i.company_id {wh_subquery_clause}
                ), 0
            ) AS current_stock,
            i.minimum_stock,
            i.reorder_point,
            i.maximum_stock,
            COALESCE(s.supplier_name, '-') AS supplier_utama,
            i.image_url
        FROM wms_items i
        JOIN wms_categories c1 ON i.category_id = c1.id
        LEFT JOIN wms_categories c2 ON i.sub_category_id = c2.id
        LEFT JOIN wms_suppliers s ON i.supplier_id = s.id
        WHERE i.company_id = ?
    """
  
  params = []
  if selected_wh_id:
    params.append(selected_wh_id)
  params.append(company_id)

  if search_query.strip():
    query += " AND (i.sku LIKE ? OR i.item_name LIKE ?)"
    params.extend([f"%{search_query.strip()}%", f"%{search_query.strip()}%"])

  if cat_options[selected_cat_filter]:
    query += " AND i.category_id = ?"
    params.append(cat_options[selected_cat_filter])

  if sup_options[selected_sup_filter]:
    query += " AND i.supplier_id = ?"
    params.append(sup_options[selected_sup_filter])

  if mat_options[selected_mat_filter]:
    query += " AND i.material = ?"
    params.append(mat_options[selected_mat_filter])

  if bin_options[selected_bin_filter]:
    query += " AND i.bin_location = ?"
    params.append(bin_options[selected_bin_filter])

  query += " ORDER BY i.sku ASC LIMIT 200"

  items_raw = con.execute(query, params).fetchall()

  if items_raw:
    processed_data = []
    warehouse_label_col = selected_wh_label if selected_wh_id else "ALL"

    for row in items_raw:
      (
          item_id,
          sku,
          item_name,
          cat_name,
          sub_cat_name,
          mat,
          spec,
          var,
          bin_loc,
          unit,
          stk_qty,
          min_stk,
          rop,
          max_stk,
          sup_name,
          img_url,
      ) = row

      if stk_qty <= min_stk:
        status_stk = "CRITICAL / MINIMUM"
      elif stk_qty <= rop:
        status_stk = "REORDER POINT"
      elif stk_qty >= max_stk:
        status_stk = "OVERSTOCK"
      else:
        status_stk = "AMAN"

      processed_data.append({
          "Gudang / Posisi": warehouse_label_col,
          "SKU": sku,
          "Nama Barang": item_name,
          "Kategori Utama": cat_name,
          "Sub-Kategori": sub_cat_name,
          "Material": mat,
          "Spesifikasi": spec,
          "Varian": var,
          "Lokasi Rak": bin_loc,
          "Stok Saat Ini": stk_qty,
          "Satuan": unit,
          "Status Stok": status_stk,
          "Min Stock": min_stk,
          "ROP": rop,
          "Max Stock": max_stk,
          "Supplier Utama": sup_name,
          "Image URL": img_url,
      })

    df = pd.DataFrame(processed_data)

    st.success(
        f"📊 Menampilkan rekap {len(df)} barang lengkap (Posisi:"
        f" {warehouse_label_col})."
    )

    # Tampilkan tabel lengkap beserta kolom Image URL agar ikut terekspor/bisa di-download
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # Preview Gambar Barang
    with st.expander("🖼️ Preview Gambar Barang"):
      selected_preview_sku = st.selectbox(
          "Pilih SKU untuk melihat gambar",
          df["SKU"] + " - " + df["Nama Barang"],
          key="preview_sku",
      )
      if selected_preview_sku:
        chosen_sku = selected_preview_sku.split(" - ")[0]
        img_row = df[df["SKU"] == chosen_sku].iloc[0]
        img_url = img_row["Image URL"]
        
        # Pengaman ekstra agar tidak crash jika image_url kosong, None, atau tidak valid
        if img_url and str(img_url).strip().lower().startswith(("http://", "https://")):
          try:
            st.image(str(img_url).strip(), width=300, caption=f"SKU: {chosen_sku}")
          except Exception:
            st.info("ℹ️ (Gagal memuat gambar dari URL)")
        else:
          st.info("ℹ️ Tidak ada URL gambar yang valid untuk barang ini.")
  else:
    st.warning("⚠️ Tidak ada data barang yang ditemukan sesuai filter.")