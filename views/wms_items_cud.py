import uuid
import streamlit as st
from database import get_connection


def render_wms_items_cud():
  st.title("⚙️ Kelola Katalog Barang")
  st.markdown("Tambah, Perbarui, atau Hapus master barang inventaris gudang.")

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error("⚠️ Session company_id tidak ditemukan. Silakan login ulang.")
    return

  con = get_connection()

  action_tab = st.radio(
      "Pilih Aksi",
      ["➕ Tambah Barang Baru", "✏️ Edit Barang", "🗑️ Hapus Barang"],
      horizontal=True,
  )
  st.divider()

  # 1. Ambil data kategori utama dengan aman
  try:
    main_cats = con.execute(
        "SELECT id, category_name FROM wms_categories WHERE company_id = ? AND parent_id IS NULL ORDER BY category_name ASC",
        (company_id,),
    ).fetchall()
  except Exception:
    main_cats = []

  if not main_cats:
    st.warning(
        "⚠️ Belum ada Kategori Utama yang terdaftar! Harap buat minimal 1"
        " Kategori Utama terlebih dahulu di menu **WMS - Manajemen Kategori**"
        " sebelum mengelola barang."
    )
    return

  main_cat_options = {mc[1]: mc[0] for mc in main_cats}

  # 2. Ambil data supplier dengan aman
  try:
    suppliers = con.execute(
        "SELECT id, supplier_code, supplier_name FROM wms_suppliers WHERE company_id = ? ORDER BY supplier_name ASC",
        (company_id,),
    ).fetchall()
  except Exception:
    suppliers = []

  supplier_options = {"-- Tanpa Supplier Utama (Generik) --": None}
  for sup in suppliers:
    supplier_options[f"[{sup[1]}] {sup[2]}"] = sup[0]

  # ---------------------------------------------------------
  # TAB 1: TAMBAH BARANG BARU (CREATE)
  # ---------------------------------------------------------
  if action_tab == "➕ Tambah Barang Baru":
    st.subheader("➕ Form Tambah Katalog Barang")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
      selected_main_cat_label = st.selectbox(
          "Pilih Kategori Utama * (Menentukan Sub-Kategori)",
          list(main_cat_options.keys()),
          key="add_main_cat_select",
      )
      chosen_main_cat_id = main_cat_options[selected_main_cat_label]

    with col_c2:
      try:
        sub_cats = con.execute(
            "SELECT id, category_name FROM wms_categories WHERE company_id = ? AND parent_id = ? ORDER BY category_name ASC",
            (company_id, chosen_main_cat_id),
        ).fetchall()
      except Exception:
        sub_cats = []

      sub_cat_options = {"-- Tidak Ada Sub-Kategori --": None}
      for sc in sub_cats:
        sub_cat_options[sc[1]] = sc[0]

      selected_sub_cat_label = st.selectbox(
          "Pilih Sub-Kategori (Opsional)",
          list(sub_cat_options.keys()),
          key="add_sub_cat_select",
      )
      chosen_sub_cat_id = sub_cat_options[selected_sub_cat_label]

    with st.form("form_add_item_clean", clear_on_submit=True):
      col1, col2 = st.columns(2)
      with col1:
        sku = st.text_input(
            "SKU (Stock Keeping Unit) *",
            placeholder="Cth: RM-BZT-304-08",
            help="Unik per perusahaan.",
        )
      with col2:
        item_name = st.text_input(
            "Nama Barang *", placeholder="Cth: Baut Stainless Steel"
        )

      col3, col4 = st.columns(2)
      with col3:
        st.info(f"📁 Kategori Utama Terpilih: **{selected_main_cat_label}**")
      with col4:
        selected_supplier_label = st.selectbox(
            "Supplier Utama (Opsional)", list(supplier_options.keys())
        )
        chosen_supplier_id = supplier_options[selected_supplier_label]

      st.divider()
      col5, col6, col7 = st.columns(3)
      with col5:
        material = st.text_input(
            "Material", placeholder="Cth: Stainless Steel 304"
        )
      with col6:
        specification = st.text_input(
            "Spesifikasi", placeholder="Cth: Panjang 200mm, M8"
        )
      with col7:
        variant = st.text_input("Varian", placeholder="Cth: Warna Hitam / 100ml")

      col8, col9 = st.columns(2)
      with col8:
        unit = st.text_input(
            "Satuan Dasar (Base Unit) *",
            value="PCS",
            placeholder="Cth: PCS, KG, LITER, ROLL, SET, CM, BOX",
        )
      with col9:
        bin_location = st.text_input(
            "Lokasi Rak / Bin Gudang", placeholder="Cth: Rak-A1-03"
        )

      st.divider()
      st.markdown("##### ⚙️ Pengaturan Batas Stok")
      col10, col11, col12 = st.columns(3)
      with col10:
        minimum_stock = st.number_input(
            "Minimum Stock (Safety)", min_value=0, value=5
        )
      with col11:
        reorder_point = st.number_input(
            "Reorder Point (Titik Pesan)", min_value=0, value=10
        )
      with col12:
        maximum_stock = st.number_input(
            "Maximum Stock (Batas Max)", min_value=0, value=100
        )

      image_url = st.text_input(
          "Image URL (Opsional)",
          placeholder="Cth: Link langsung gambar (lh3.googleusercontent.com)",
      )

      btn_submit = st.form_submit_button("💾 Simpan Barang Baru")

      if btn_submit:
        if not sku or not item_name:
          st.error("⚠️ SKU dan Nama Barang wajib diisi!")
        else:
          try:
            new_id = str(uuid.uuid4())
            final_unit = unit.strip().upper() if unit else "PCS"
            con.execute(
                """
                        INSERT INTO wms_items (
                            id, company_id, sku, item_name, category_id, sub_category_id, 
                            material, specification, variant, unit, bin_location, 
                            supplier_id, minimum_stock, reorder_point, maximum_stock, image_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                (
                    new_id,
                    company_id,
                    sku.strip().upper(),
                    item_name,
                    chosen_main_cat_id,
                    chosen_sub_cat_id,
                    material,
                    specification,
                    variant,
                    final_unit,
                    bin_location,
                    chosen_supplier_id,
                    minimum_stock,
                    reorder_point,
                    maximum_stock,
                    image_url,
                ),
            )
            con.commit()
            con.sync()
            st.success(
                f"🎉 Barang SKU '{sku.strip().upper()}' berhasil ditambahkan!"
            )
            st.rerun()
          except Exception as e:
            if "UNIQUE constraint failed" in str(e):
              st.error(
                  f"❌ Gagal: SKU '{sku}' sudah terdaftar di perusahaan ini!"
              )
            else:
              st.error(f"❌ Terjadi kesalahan database: {e}")

  # ---------------------------------------------------------
  # TAB 2: EDIT BARANG (UPDATE)
  # ---------------------------------------------------------
  elif action_tab == "✏️ Edit Barang":
    st.subheader("✏️ Form Edit Katalog Barang")

    try:
      items_edit_raw = con.execute(
          "SELECT id, sku, item_name, category_id, sub_category_id, material, specification, variant, unit, bin_location, supplier_id, minimum_stock, reorder_point, maximum_stock, image_url FROM wms_items WHERE company_id = ? ORDER BY sku ASC",
          (company_id,),
      ).fetchall()
    except Exception:
      items_edit_raw = []

    if not items_edit_raw:
      st.info(
          "ℹ️ Belum ada data barang di katalog yang dapat diedit. Silakan"
          " tambahkan terlebih dahulu."
      )
      return

    item_map = {f"[{it[1]}] {it[2]}": it for it in items_edit_raw}
    selected_item_label = st.selectbox(
        "Pilih Barang yang Akan Diedit", list(item_map.keys())
    )
    selected_item = item_map[selected_item_label]

    (
        it_id,
        it_sku,
        it_name,
        it_cat_id,
        it_sub_id,
        it_mat,
        it_spec,
        it_var,
        it_unit,
        it_bin,
        it_sup_id,
        it_min,
        it_rop,
        it_max,
        it_img,
    ) = selected_item

    default_main_label = list(main_cat_options.keys())[0]
    for name, cid in main_cat_options.items():
      if cid == it_cat_id:
        default_main_label = name
        break

    col_e1, col_e2 = st.columns(2)
    with col_e1:
      try:
        default_main_index = list(main_cat_options.keys()).index(
            default_main_label
        )
      except ValueError:
        default_main_index = 0

      edit_main_cat_label = st.selectbox(
          "Kategori Utama * (Edit)",
          list(main_cat_options.keys()),
          index=default_main_index,
          key="edit_main_cat_select",
      )
      edit_chosen_main_id = main_cat_options[edit_main_cat_label]

    with col_e2:
      try:
        sub_cats_ed = con.execute(
            "SELECT id, category_name FROM wms_categories WHERE company_id = ? AND parent_id = ? ORDER BY category_name ASC",
            (company_id, edit_chosen_main_id),
        ).fetchall()
      except Exception:
        sub_cats_ed = []

      sub_cat_options_ed = {"-- Tidak Ada Sub-Kategori --": None}
      for sc in sub_cats_ed:
        sub_cat_options_ed[sc[1]] = sc[0]

      default_sub_label = "-- Tidak Ada Sub-Kategori --"
      for name, scid in sub_cat_options_ed.items():
        if scid == it_sub_id:
          default_sub_label = name
          break

      try:
        default_sub_index = list(sub_cat_options_ed.keys()).index(
            default_sub_label
        )
      except ValueError:
        default_sub_index = 0

      edit_sub_label = st.selectbox(
          "Sub-Kategori (Opsional) (Edit)",
          list(sub_cat_options_ed.keys()),
          index=default_sub_index,
          key="edit_sub_cat_select",
      )
      edit_chosen_sub_id = sub_cat_options_ed[edit_sub_label]

    with st.form("form_edit_item_clean"):
      col1, col2 = st.columns(2)
      with col1:
        edit_sku = st.text_input("SKU *", value=it_sku)
      with col2:
        edit_name = st.text_input("Nama Barang *", value=it_name)

      col3, col4 = st.columns(2)
      with col3:
        st.info("✅ Kategori & Sub-Kategori diatur di panel atas form.")
      with col4:
        default_sup_label = "-- Tanpa Supplier Utama (Generik) --"
        for name, supid in supplier_options.items():
          if supid == it_sup_id:
            default_sup_label = name
            break
        try:
          default_sup_index = list(supplier_options.keys()).index(
              default_sup_label
          )
        except ValueError:
          default_sup_index = 0

        edit_sup_label = st.selectbox(
            "Supplier Utama (Opsional)",
            list(supplier_options.keys()),
            index=default_sup_index,
        )
        edit_chosen_sup_id = supplier_options[edit_sup_label]

      st.divider()
      col5, col6, col7 = st.columns(3)
      with col5:
        edit_material = st.text_input("Material", value=it_mat or "")
      with col6:
        edit_spec = st.text_input("Spesifikasi", value=it_spec or "")
      with col7:
        edit_var = st.text_input("Varian", value=it_var or "")

      col8, col9 = st.columns(2)
      with col8:
        edit_unit = st.text_input("Satuan Dasar *", value=it_unit or "PCS")
      with col9:
        edit_bin = st.text_input("Lokasi Rak / Bin", value=it_bin or "")

      st.divider()
      st.markdown("##### ⚙️ Pengaturan Batas Stok")
      col10, col11, col12 = st.columns(3)
      with col10:
        edit_min = st.number_input(
            "Minimum Stock", min_value=0, value=int(it_min or 0)
        )
      with col11:
        edit_rop = st.number_input(
            "Reorder Point", min_value=0, value=int(it_rop or 0)
        )
      with col12:
        edit_max = st.number_input(
            "Maximum Stock", min_value=0, value=int(it_max or 0)
        )

      edit_img = st.text_input("Image URL", value=it_img or "")

      btn_update = st.form_submit_button("🔄 Perbarui Katalog Barang")

      if btn_update:
        if not edit_sku or not edit_name:
          st.error("⚠️ SKU dan Nama Barang wajib diisi!")
        else:
          try:
            final_edit_unit = edit_unit.strip().upper() if edit_unit else "PCS"
            con.execute(
                """
                        UPDATE wms_items 
                        SET sku = ?, item_name = ?, category_id = ?, sub_category_id = ?, 
                            material = ?, specification = ?, variant = ?, unit = ?, 
                            bin_location = ?, supplier_id = ?, minimum_stock = ?, 
                            reorder_point = ?, maximum_stock = ?, image_url = ?
                        WHERE id = ? AND company_id = ?
                    """,
                (
                    edit_sku.strip().upper(),
                    edit_name,
                    edit_chosen_main_id,
                    edit_chosen_sub_id,
                    edit_material,
                    edit_spec,
                    edit_var,
                    final_edit_unit,
                    edit_bin,
                    edit_chosen_sup_id,
                    edit_min,
                    edit_rop,
                    edit_max,
                    edit_img,
                    it_id,
                    company_id,
                ),
            )
            con.commit()
            con.sync()
            st.success("🎉 Data katalog barang berhasil diperbarui!")
            st.rerun()
          except Exception as e:
            if "UNIQUE constraint failed" in str(e):
              st.error(
                  f"❌ Gagal: SKU '{edit_sku}' sudah digunakan oleh barang lain!"
              )
            else:
              st.error(f"❌ Terjadi kesalahan database: {e}")

  # ---------------------------------------------------------
  # TAB 3: HAPUS BARANG (DELETE)
  # ---------------------------------------------------------
  elif action_tab == "🗑️ Hapus Barang":
    st.subheader("🗑️ Form Hapus Katalog Barang")

    try:
      items_del_raw = con.execute(
          "SELECT id, sku, item_name FROM wms_items WHERE company_id = ? ORDER BY sku ASC",
          (company_id,),
      ).fetchall()
    except Exception:
      items_del_raw = []

    if not items_del_raw:
      st.info("ℹ️ Tidak ada data barang untuk dihapus.")
      return

    item_del_map = {f"[{it[1]}] {it[2]}": it[0] for it in items_del_raw}
    selected_del_label = st.selectbox(
        "Pilih Barang yang Akan Dihapus", list(item_del_map.keys())
    )
    selected_del_id = item_del_map[selected_del_label]

    st.warning(
        f"⚠️ Apakah Anda yakin ingin menghapus barang **'{selected_del_label}'**?"
    )

    if st.button("🔴 Ya, Hapus Barang Ini"):
      con.execute(
          "DELETE FROM wms_items WHERE id = ? AND company_id = ?",
          (selected_del_id, company_id),
      )
      con.commit()
      con.sync()
      st.success("🗑️ Barang berhasil dihapus dari katalog!")
      st.rerun()