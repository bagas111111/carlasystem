import uuid
import pandas as pd
import streamlit as st
from database import get_connection

# Daftar opsi tipe gudang standar manufaktur & operasional
WAREHOUSE_TYPES = [
    "MAIN",
    "RAW_MATERIAL",
    "FINISHED_GOODS",
    "WIP",
    "BRANCH",
    "BONDED",
    "SPAREPART",
    "SAMPLE",
]


def render_wms_warehouses():
  st.title("🏭 Manajemen Gudang (WMS)")
  st.markdown(
      "Kelola lokasi gudang penyimpanan barang yang terisolasi per perusahaan."
  )

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
      "📋 Daftar Gudang",
      "➕ Tambah Gudang",
      "✏️ Edit Gudang",
      "🗑️ Hapus Gudang",
  ])

  # ---------------------------------------------------------
  # TAB 1: DAFTAR GUDANG (READ)
  # ---------------------------------------------------------
  with tab_list:
    st.subheader("📋 Daftar Lokasi Gudang")

    warehouses = con.execute(
        """
            SELECT id, warehouse_name, warehouse_type, address 
            FROM wms_warehouses 
            WHERE company_id = ? 
            ORDER BY warehouse_name ASC
        """,
        (company_id,),
    ).fetchall()

    if warehouses:
      df = pd.DataFrame(
          warehouses,
          columns=[
              "ID Gudang",
              "Nama Gudang",
              "Tipe Gudang",
              "Alamat / Keterangan",
          ],
      )
      st.dataframe(df, use_container_width=True)
    else:
      st.info(
          "ℹ️ Belum ada data gudang yang terdaftar untuk perusahaan ini."
          " Silakan tambah di tab 'Tambah Gudang'."
      )

  # ---------------------------------------------------------
  # TAB 2: TAMBAH GUDANG (CREATE)
  # ---------------------------------------------------------
  with tab_add:
    st.subheader("➕ Tambah Gudang Baru")

    with st.form("form_add_warehouse", clear_on_submit=True):
      warehouse_name = st.text_input(
          "Nama Gudang *",
          placeholder=(
              "Cth: Gudang Bahan Baku A, Gudang Finish Goods, Gudang Bea"
              " Cukai"
          ),
      )
      warehouse_type = st.selectbox(
          "Tipe Gudang *",
          WAREHOUSE_TYPES,
          help=(
              "Pilih jenis peruntukan gudang (Raw Material, WIP, Finished"
              " Goods, dll)"
          ),
      )
      address = st.text_area(
          "Alamat / Detail Lokasi", placeholder="Jl. Industri No. 123..."
      )

      btn_submit = st.form_submit_button("💾 Simpan Gudang Baru")

      if btn_submit:
        if not warehouse_name:
          st.error("⚠️ Nama Gudang wajib diisi!")
        else:
          new_id = str(uuid.uuid4())
          con.execute(
              """
                    INSERT INTO wms_warehouses (id, company_id, warehouse_name, warehouse_type, address)
                    VALUES (?, ?, ?, ?, ?)
                """,
              (new_id, company_id, warehouse_name, warehouse_type, address),
          )
          con.commit()  # <--- WAJIB: Simpan permanen ke DB lokal
          con.sync()  # <--- Sinkronisasi ke Turso Cloud
          st.success(
              f"🎉 Gudang '{warehouse_name}' berhasil ditambahkan!"
          )
          st.rerun()

  # ---------------------------------------------------------
  # TAB 3: EDIT GUDANG (UPDATE)
  # ---------------------------------------------------------
  with tab_edit:
    st.subheader("✏️ Edit Data Gudang")

    warehouses_raw = con.execute(
        """
            SELECT id, warehouse_name, warehouse_type, address 
            FROM wms_warehouses 
            WHERE company_id = ? 
            ORDER BY warehouse_name ASC
        """,
        (company_id,),
    ).fetchall()

    if not warehouses_raw:
      st.info("ℹ️ Tidak ada gudang yang dapat diedit.")
    else:
      options = {
          f"{w[1]} ({w[2]})": {
              "id": w[0],
              "name": w[1],
              "type": w[2],
              "addr": w[3],
          }
          for w in warehouses_raw
      }
      selected_label = st.selectbox(
          "Pilih Gudang yang Ingin Diedit", list(options.keys())
      )
      selected_data = options[selected_label]

      with st.form("form_edit_warehouse"):
        edit_name = st.text_input("Nama Gudang *", value=selected_data["name"])

        # Menentukan index pilihan default pada selectbox
        default_index = (
            WAREHOUSE_TYPES.index(selected_data["type"])
            if selected_data["type"] in WAREHOUSE_TYPES
            else 0
        )
        edit_type = st.selectbox(
            "Tipe Gudang *", WAREHOUSE_TYPES, index=default_index
        )

        edit_address = st.text_area(
            "Alamat / Detail Lokasi", value=selected_data["addr"] or ""
        )

        btn_update = st.form_submit_button("🔄 Perbarui Data Gudang")

        if btn_update:
          if not edit_name:
            st.error("⚠️ Nama Gudang wajib diisi!")
          else:
            con.execute(
                """
                        UPDATE wms_warehouses 
                        SET warehouse_name = ?, warehouse_type = ?, address = ?
                        WHERE id = ? AND company_id = ?
                    """,
                (
                    edit_name,
                    edit_type,
                    edit_address,
                    selected_data["id"],
                    company_id,
                ),
            )
            con.commit()  # <--- WAJIB: Simpan permanen ke DB lokal
            con.sync()  # <--- Sinkronisasi ke Turso Cloud
            st.success("🎉 Data gudang berhasil diperbarui!")
            st.rerun()

  # ---------------------------------------------------------
  # TAB 4: HAPUS GUDANG (DELETE)
  # ---------------------------------------------------------
  with tab_delete:
    st.subheader("🗑️ Hapus Data Gudang")

    warehouses_raw = con.execute(
        """
            SELECT id, warehouse_name, warehouse_type 
            FROM wms_warehouses 
            WHERE company_id = ? 
            ORDER BY warehouse_name ASC
        """,
        (company_id,),
    ).fetchall()

    if not warehouses_raw:
      st.info("ℹ️ Tidak ada data gudang yang dapat dihapus.")
    else:
      options_del = {f"{w[1]} ({w[2]})": w[0] for w in warehouses_raw}
      selected_del_label = st.selectbox(
          "Pilih Gudang yang Akan Dihapus",
          list(options_del.keys()),
          key="select_del_wh",
      )
      selected_del_id = options_del[selected_del_label]

      st.warning(
          f"⚠️ Apakah Anda yakin ingin menghapus gudang **'{selected_del_label}'**?"
          " Data stok/log transaksi yang terkait dengan gudang ini juga dapat"
          " terdampak!"
      )

      if st.button("🔴 Ya, Hapus Gudang Ini"):
        con.execute(
            "DELETE FROM wms_warehouses WHERE id = ? AND company_id = ?",
            (selected_del_id, company_id),
        )
        con.commit()  # <--- WAJIB: Simpan permanen ke DB lokal
        con.sync()  # <--- Sinkronisasi ke Turso Cloud
        st.success("🗑️ Gudang berhasil dihapus!")
        st.rerun()