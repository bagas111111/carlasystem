import pandas as pd
import streamlit as st
from database import get_connection


def render_wms_items_list():
  st.title("📋 Daftar Katalog Inventaris Barang (WMS)")
  st.markdown("Cari, filter, dan pantau seluruh master katalog barang gudang.")

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error("⚠️ Session company_id tidak ditemukan. Silakan login ulang.")
    return

  con = get_connection()

  # ---------------------------------------------------------
  # FILTER & SEARCH PANEL
  # ---------------------------------------------------------
  st.markdown("#### 🔍 Filter & Pencarian Data")

  # Ambil data filter pendukung
  try:
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
    categories, suppliers, materials, bins = [], [], [], []

  col_f1, col_f2, col_f3 = st.columns(3)
  with col_f1:
    search_query = st.text_input(
        "Cari SKU / Nama Barang",
        placeholder="Ketik SKU atau Nama Barang...",
    )
  with col_f2:
    cat_options = {"-- Semua Kategori --": ""}
    for c in categories:
      cat_options[c[1]] = c[0]
    selected_cat_filter = st.selectbox(
        "Filter Kategori Utama", list(cat_options.keys())
    )
  with col_f3:
    sup_options = {"-- Semua Supplier --": ""}
    for s in suppliers:
      sup_options[s[1]] = s[0]
    selected_sup_filter = st.selectbox(
        "Filter Supplier Utama", list(sup_options.keys())
    )

  col_f4, col_f5 = st.columns(2)
  with col_f4:
    mat_options = {"-- Semua Material --": ""}
    for m in materials:
      mat_options[m[0]] = m[0]
    selected_mat_filter = st.selectbox(
        "Filter Material", list(mat_options.keys())
    )
  with col_f5:
    bin_options = {"-- Semua Lokasi Rak --": ""}
    for b in bins:
      bin_options[b[0]] = b[0]
    selected_bin_filter = st.selectbox(
        "Filter Lokasi Rak / Bin", list(bin_options.keys())
    )

  # Tombol aksi pencarian agar tidak load otomatis
  col_btn1, col_btn2 = st.columns([1, 4])
  with col_btn1:
    btn_search = st.button("🔍 Cari Data", type="primary", use_container_width=True)

  st.divider()

  # ---------------------------------------------------------
  # CEK APAKAH USER SUDAH MELAKUKAN PENCARIAN / FILTER
  # ---------------------------------------------------------
  is_filtered = (
      btn_search
      or bool(search_query.strip())
      or bool(cat_options[selected_cat_filter])
      or bool(sup_options[selected_sup_filter])
      or bool(mat_options[selected_mat_filter])
      or bool(bin_options[selected_bin_filter])
  )

  if not is_filtered:
    st.info(
        "💡 **Silakan masukkan kata kunci pencarian (SKU/Nama Barang) atau pilih"
        " salah satu filter di atas, lalu klik tombol 'Cari Data'** untuk"
        " menampilkan daftar katalog barang."
    )
    return

  # ---------------------------------------------------------
  # QUERY DATA DENGAN FILTER DINAMIS
  # ---------------------------------------------------------
  query = """
        SELECT 
            i.id,
            i.sku,
            i.item_name,
            c1.category_name AS kategori_utama,
            COALESCE(c2.category_name, '-') AS sub_kategori,
            COALESCE(i.material, '-') AS material,
            COALESCE(i.specification, '-') AS specification,
            COALESCE(i.variant, '-') AS variant,
            i.unit,
            COALESCE(i.bin_location, '-') AS bin_location,
            COALESCE(s.supplier_name, '-') AS supplier_utama,
            i.minimum_stock,
            i.reorder_point,
            i.maximum_stock,
            i.image_url
        FROM wms_items i
        JOIN wms_categories c1 ON i.category_id = c1.id
        LEFT JOIN wms_categories c2 ON i.sub_category_id = c2.id
        LEFT JOIN wms_suppliers s ON i.supplier_id = s.id
        WHERE i.company_id = ?
    """
  params = [company_id]

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

  query += " ORDER BY i.sku ASC LIMIT 200"  # Batasi max 200 record agar ringan

  items_raw = con.execute(query, params).fetchall()

  if items_raw:
    df = pd.DataFrame(
        items_raw,
        columns=[
            "ID",
            "SKU",
            "Nama Barang",
            "Kategori",
            "Sub-Kategori",
            "Material",
            "Spesifikasi",
            "Varian",
            "Satuan",
            "Lokasi Rak",
            "Supplier Utama",
            "Min Stock",
            "Reorder Point",
            "Max Stock",
            "Image URL",
        ],
    )

    st.success(
        f"📊 Menampilkan {len(df)} item barang sesuai filter / pencarian."
    )
    st.dataframe(df.drop(columns=["ID", "Image URL"]), width="stretch")

    # Preview Gambar
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
        if img_url and img_url.strip():
          st.image(img_url, width=300, caption=f"SKU: {chosen_sku}")
        else:
          st.info("ℹ️ Tidak ada URL gambar untuk barang ini.")
  else:
    st.warning("⚠️ Tidak ada data barang yang ditemukan dengan filter tersebut.")