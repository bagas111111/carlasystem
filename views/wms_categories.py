import uuid
import pandas as pd
import streamlit as st
from database import get_connection


def render_wms_categories():
  st.title("🏷️ Manajemen Kategori Barang (WMS)")
  st.markdown(
      "Kelola kategori utama dan sub-kategori barang yang terisolasi per"
      " perusahaan."
  )

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error(
        "⚠️ Session company_id tidak ditemukan. Silakan login ulang terlebih"
        " dahulu."
    )
    return

  con = get_connection()

  # Tab Navigasi CRUD
  tab_list, tab_add, tab_edit, tab_delete = st.tabs([
      "📋 Daftar Kategori",
      "➕ Tambah Kategori",
      "✏️ Edit Kategori",
      "🗑️ Hapus Kategori",
  ])

  # ---------------------------------------------------------
  # TAB 1: DAFTAR KATEGORI (READ)
  # ---------------------------------------------------------
  with tab_list:
    st.subheader("📋 Daftar Kategori & Sub-Kategori")

    categories = con.execute(
        """
            SELECT 
                c.id, 
                c.category_name AS nama_kategori,
                COALESCE(p.category_name, '-') AS kategori_induk,
                CASE 
                    WHEN c.parent_id IS NULL THEN 'Kategori Utama'
                    ELSE 'Sub-Kategori'
                END AS jenis
            FROM wms_categories c
            LEFT JOIN wms_categories p ON c.parent_id = p.id
            WHERE c.company_id = ?
            ORDER BY COALESCE(p.category_name, c.category_name) ASC, c.parent_id IS NOT NULL ASC, c.category_name ASC
        """,
        (company_id,),
    ).fetchall()

    if categories:
      df = pd.DataFrame(
          categories,
          columns=[
              "ID Kategori",
              "Nama Kategori",
              "Kategori Induk (Parent)",
              "Jenis Level",
          ],
      )
      st.dataframe(df, use_container_width=True)
    else:
      st.info(
          "ℹ️ Belum ada data kategori yang terdaftar. Silakan tambah di tab"
          " 'Tambah Kategori'."
      )

  # ---------------------------------------------------------
  # TAB 2: TAMBAH KATEGORI (CREATE)
  # ---------------------------------------------------------
  with tab_add:
    st.subheader("➕ Tambah Kategori / Sub-Kategori Baru")

    # Ambil daftar Kategori Utama (yang parent_id IS NULL) untuk pilihan Kategori Induk
    main_cats = con.execute(
        """
            SELECT id, category_name 
            FROM wms_categories 
            WHERE company_id = ? AND parent_id IS NULL
            ORDER BY category_name ASC
        """,
        (company_id,),
    ).fetchall()

    parent_options = {"-- Tidak Ada (Jadikan Kategori Utama) --": None}
    for mc in main_cats:
      parent_options[f"📁 {mc[1]}"] = mc[0]

    with st.form("form_add_category", clear_on_submit=True):
      category_name = st.text_input(
          "Nama Kategori *",
          placeholder="Cth: Sparepart Mesin, Baut & Mur, Raw Material",
      )
      selected_parent_label = st.selectbox(
          "Kategori Induk / Parent (Opsional)",
          list(parent_options.keys()),
          help=(
              "Pilih jika kategori ini merupakan sub-kategori dari kategori"
              " utama yang sudah ada."
          ),
      )

      btn_submit = st.form_submit_button("💾 Simpan Kategori Baru")

      if btn_submit:
        if not category_name:
          st.error("⚠️ Nama Kategori wajib diisi!")
        else:
          parent_id = parent_options[selected_parent_label]
          new_id = str(uuid.uuid4())

          con.execute(
              """
                    INSERT INTO wms_categories (id, company_id, category_name, parent_id)
                    VALUES (?, ?, ?, ?)
                """,
              (new_id, company_id, category_name, parent_id),
          )
          con.commit()
          con.sync()
          st.success(f"🎉 Kategori '{category_name}' berhasil ditambahkan!")
          st.rerun()

  # ---------------------------------------------------------
  # TAB 3: EDIT KATEGORI (UPDATE)
  # ---------------------------------------------------------
  with tab_edit:
    st.subheader("✏️ Edit Data Kategori")

    all_cats = con.execute(
        """
            SELECT c.id, c.category_name, c.parent_id, p.category_name 
            FROM wms_categories c
            LEFT JOIN wms_categories p ON c.parent_id = p.id
            WHERE c.company_id = ?
            ORDER BY c.category_name ASC
        """,
        (company_id,),
    ).fetchall()

    if not all_cats:
      st.info("ℹ️ Tidak ada data kategori yang dapat diedit.")
    else:
      cat_map = {}
      for c in all_cats:
        label = (
            f"{c[1]} (Sub dari: {c[3]})" if c[2] else f"📁 {c[1]} (Utama)"
        )
        cat_map[label] = {"id": c[0], "name": c[1], "parent_id": c[2]}

      selected_edit_label = st.selectbox(
          "Pilih Kategori yang Ingin Diedit", list(cat_map.keys())
      )
      selected_edit_data = cat_map[selected_edit_label]

      # Opsi parent baru (tidak boleh memilih dirinya sendiri sebagai parent)
      main_cats_edit = con.execute(
          """
                SELECT id, category_name 
                FROM wms_categories 
                WHERE company_id = ? AND parent_id IS NULL AND id != ?
                ORDER BY category_name ASC
            """,
          (company_id, selected_edit_data["id"]),
      ).fetchall()

      parent_options_edit = {"-- Tidak Ada (Jadikan Kategori Utama) --": None}
      for mc in main_cats_edit:
        parent_options_edit[f"📁 {mc[1]}"] = mc[0]

      # Tentukan index default parent
      default_parent_index = 0
      if selected_edit_data["parent_id"]:
        for idx, (lbl, pid) in enumerate(parent_options_edit.items()):
          if pid == selected_edit_data["parent_id"]:
            default_parent_index = idx
            break

      with st.form("form_edit_category"):
        edit_name = st.text_input(
            "Nama Kategori *", value=selected_edit_data["name"]
        )
        edit_parent_label = st.selectbox(
            "Kategori Induk / Parent (Opsional)",
            list(parent_options_edit.keys()),
            index=default_parent_index,
        )

        btn_update = st.form_submit_button("🔄 Perbarui Kategori")

        if btn_update:
          if not edit_name:
            st.error("⚠️ Nama Kategori wajib diisi!")
          else:
            new_parent_id = parent_options_edit[edit_parent_label]
            con.execute(
                """
                        UPDATE wms_categories 
                        SET category_name = ?, parent_id = ?
                        WHERE id = ? AND company_id = ?
                    """,
                (
                    edit_name,
                    new_parent_id,
                    selected_edit_data["id"],
                    company_id,
                ),
            )
            con.commit()
            con.sync()
            st.success("🎉 Data kategori berhasil diperbarui!")
            st.rerun()

  # ---------------------------------------------------------
  # TAB 4: HAPUS KATEGORI (DELETE)
  # ---------------------------------------------------------
  with tab_delete:
    st.subheader("🗑️ Hapus Data Kategori")

    all_cats_del = con.execute(
        """
            SELECT c.id, c.category_name, c.parent_id, p.category_name 
            FROM wms_categories c
            LEFT JOIN wms_categories p ON c.parent_id = p.id
            WHERE c.company_id = ?
            ORDER BY c.category_name ASC
        """,
        (company_id,),
    ).fetchall()

    if not all_cats_del:
      st.info("ℹ️ Tidak ada data kategori yang dapat dihapus.")
    else:
      cat_del_map = {}
      for c in all_cats_del:
        label = (
            f"{c[1]} (Sub dari: {c[3]})" if c[2] else f"📁 {c[1]} (Utama)"
        )
        cat_del_map[label] = c[0]

      selected_del_label = st.selectbox(
          "Pilih Kategori yang Akan Dihapus",
          list(cat_del_map.keys()),
          key="select_del_cat",
      )
      selected_del_id = cat_del_map[selected_del_label]

      st.warning(
          f"⚠️ Apakah Anda yakin ingin menghapus kategori **'{selected_del_label}'**?"
          "\nJika kategori ini memiliki sub-kategori, sub-kategori terkait"
          " juga akan terhapus otomatis (CASCADE)."
      )

      if st.button("🔴 Ya, Hapus Kategori Ini"):
        con.execute(
            "DELETE FROM wms_categories WHERE id = ? AND company_id = ?",
            (selected_del_id, company_id),
        )
        con.commit()
        con.sync()
        st.success("🗑️ Kategori berhasil dihapus!")
        st.rerun()