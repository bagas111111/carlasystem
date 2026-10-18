import uuid
import pandas as pd
import streamlit as st
from database import get_connection


def render_wms_suppliers():
  st.title("🤝 Manajemen Supplier / Vendor (WMS)")
  st.markdown("Kelola data resmi pemasok dan vendor material perusahaan.")

  company_id = st.session_state.get("company_id")
  if not company_id:
    st.error(
        "⚠️ Session company_id tidak ditemukan. Silakan login ulang terlebih"
        " dahulu."
    )
    return

  con = get_connection()

  # Tab untuk Navigasi CRUD
  tab_list, tab_add, tab_edit, tab_delete = st.tabs([
      "📋 Daftar Supplier",
      "➕ Tambah Supplier",
      "✏️ Edit Supplier",
      "🗑️ Hapus Supplier",
  ])

  # ---------------------------------------------------------
  # TAB 1: DAFTAR SUPPLIER (READ)
  # ---------------------------------------------------------
  with tab_list:
    st.subheader("📋 Daftar Master Supplier")

    suppliers = con.execute(
        """
            SELECT id, supplier_code, supplier_name, contact_person, phone_number, address 
            FROM wms_suppliers 
            WHERE company_id = ? 
            ORDER BY supplier_name ASC
        """,
        (company_id,),
    ).fetchall()

    if suppliers:
      df = pd.DataFrame(
          suppliers,
          columns=[
              "ID Supplier",
              "Kode Supplier",
              "Nama Supplier",
              "Kontak Person",
              "No. Telepon",
              "Alamat",
          ],
      )
      st.dataframe(df, use_container_width=True)
    else:
      st.info(
          "ℹ️ Belum ada data supplier yang terdaftar untuk perusahaan ini."
          " Silakan tambah di tab 'Tambah Supplier'."
      )

  # ---------------------------------------------------------
  # TAB 2: TAMBAH SUPPLIER (CREATE)
  # ---------------------------------------------------------
  with tab_add:
    st.subheader("➕ Tambah Supplier Baru")

    with st.form("form_add_supplier", clear_on_submit=True):
      col1, col2 = st.columns(2)
      with col1:
        supplier_code = st.text_input(
            "Kode Supplier *", placeholder="Cth: SUP-001, PT-MAJU"
        )
      with col2:
        supplier_name = st.text_input(
            "Nama Supplier / Vendor *", placeholder="Cth: PT. Maju Sejahtera"
        )

      col3, col4 = st.columns(2)
      with col3:
        contact_person = st.text_input(
            "Nama Kontak Person", placeholder="Cth: Bpk. Budi"
        )
      with col4:
        phone_number = st.text_input(
            "No. Telepon / WhatsApp", placeholder="Cth: 08123456789"
        )

      address = st.text_area(
          "Alamat Supplier", placeholder="Jl. Raya Industri No. 45, Surabaya..."
      )

      btn_submit = st.form_submit_button("💾 Simpan Supplier Baru")

      if btn_submit:
        if not supplier_code or not supplier_name:
          st.error("⚠️ Kode Supplier dan Nama Supplier wajib diisi!")
        else:
          new_id = str(uuid.uuid4())
          con.execute(
              """
                    INSERT INTO wms_suppliers (id, company_id, supplier_code, supplier_name, contact_person, phone_number, address)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
              (
                  new_id,
                  company_id,
                  supplier_code,
                  supplier_name,
                  contact_person,
                  phone_number,
                  address,
              ),
          )
          con.commit()
          con.sync()
          st.success(
              f"🎉 Supplier '{supplier_name}' berhasil ditambahkan!"
          )
          st.rerun()

  # ---------------------------------------------------------
  # TAB 3: EDIT SUPPLIER (UPDATE)
  # ---------------------------------------------------------
  with tab_edit:
    st.subheader("✏️ Edit Data Supplier")

    suppliers_raw = con.execute(
        """
            SELECT id, supplier_code, supplier_name, contact_person, phone_number, address 
            FROM wms_suppliers 
            WHERE company_id = ? 
            ORDER BY supplier_name ASC
        """,
        (company_id,),
    ).fetchall()

    if not suppliers_raw:
      st.info("ℹ️ Tidak ada data supplier yang dapat diedit.")
    else:
      options = {
          f"[{s[1]}] {s[2]}": {
              "id": s[0],
              "code": s[1],
              "name": s[2],
              "cp": s[3],
              "phone": s[4],
              "addr": s[5],
          }
          for s in suppliers_raw
      }
      selected_label = st.selectbox(
          "Pilih Supplier yang Ingin Diedit", list(options.keys())
      )
      selected_data = options[selected_label]

      with st.form("form_edit_supplier"):
        col1, col2 = st.columns(2)
        with col1:
          edit_code = st.text_input("Kode Supplier *", value=selected_data["code"])
        with col2:
          edit_name = st.text_input("Nama Supplier *", value=selected_data["name"])

        col3, col4 = st.columns(2)
        with col3:
          edit_cp = st.text_input(
              "Nama Kontak Person", value=selected_data["cp"] or ""
          )
        with col4:
          edit_phone = st.text_input(
              "No. Telepon / WhatsApp", value=selected_data["phone"] or ""
          )

        edit_address = st.text_area(
            "Alamat Supplier", value=selected_data["addr"] or ""
        )

        btn_update = st.form_submit_button("🔄 Perbarui Data Supplier")

        if btn_update:
          if not edit_code or not edit_name:
            st.error("⚠️ Kode Supplier dan Nama Supplier wajib diisi!")
          else:
            con.execute(
                """
                        UPDATE wms_suppliers 
                        SET supplier_code = ?, supplier_name = ?, contact_person = ?, phone_number = ?, address = ?
                        WHERE id = ? AND company_id = ?
                    """,
                (
                    edit_code,
                    edit_name,
                    edit_cp,
                    edit_phone,
                    edit_address,
                    selected_data["id"],
                    company_id,
                ),
            )
            con.commit()
            con.sync()
            st.success("🎉 Data supplier berhasil diperbarui!")
            st.rerun()

  # ---------------------------------------------------------
  # TAB 4: HAPUS SUPPLIER (DELETE)
  # ---------------------------------------------------------
  with tab_delete:
    st.subheader("🗑️ Hapus Data Supplier")

    suppliers_raw = con.execute(
        """
            SELECT id, supplier_code, supplier_name 
            FROM wms_suppliers 
            WHERE company_id = ? 
            ORDER BY supplier_name ASC
        """,
        (company_id,),
    ).fetchall()

    if not suppliers_raw:
      st.info("ℹ️ Tidak ada data supplier yang dapat dihapus.")
    else:
      options_del = {f"[{s[1]}] {s[2]}": s[0] for s in suppliers_raw}
      selected_del_label = st.selectbox(
          "Pilih Supplier yang Akan Dihapus",
          list(options_del.keys()),
          key="select_del_sup",
      )
      selected_del_id = options_del[selected_del_label]

      st.warning(
          f"⚠️ Apakah Anda yakin ingin menghapus supplier **'{selected_del_label}'**?"
          " Kolom supplier pada master barang terkait akan berubah menjadi kosong (NULL)."
      )

      if st.button("🔴 Ya, Hapus Supplier Ini"):
        con.execute(
            "DELETE FROM wms_suppliers WHERE id = ? AND company_id = ?",
            (selected_del_id, company_id),
        )
        con.commit()
        con.sync()
        st.success("🗑️ Supplier berhasil dihapus!")
        st.rerun()