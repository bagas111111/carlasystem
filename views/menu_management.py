import uuid
from database import get_connection
import pandas as pd
import streamlit as st


def render_menu_management():
  con = get_connection()
  company_id = st.session_state.get("company_id")

  st.title("📌 Kelola Pintasan Menu & Shortcut Perusahaan")
  st.markdown(
      "Tambahkan, ubah, atau hapus kelompok tautan menu cepat (seperti Google"
      " Drive, Form Eksternal, Panduan, dll.) yang akan tampil di Dashboard"
      " utama perusahaan Anda."
  )

  tab_list, tab_add = st.tabs(
      ["📋 Daftar & Edit Menu Pintasan", "➕ Tambah Menu Baru"]
  )

  # --- TAB 1: DAFTAR, EDIT & HAPUS MENU ---
  with tab_list:
    st.subheader("Daftar Pintasan Menu Aktif")

    df_menus = pd.read_sql(
        f"""
            SELECT id, menu_group, menu_title, menu_url, image_url, sort_order 
            FROM hris_company_menus 
            WHERE company_id = '{company_id}' 
            ORDER BY menu_group ASC, sort_order ASC
        """,
        con,
    )

    if df_menus.empty:
      st.info(
          "Belum ada pintasan menu yang dibuat. Silakan tambah melalui tab"
          " sebelah."
      )
    else:
      # Tampilkan sebagai tabel dengan fitur download bawaan Streamlit
      st.dataframe(df_menus, use_container_width=True, hide_index=True)

      st.divider()
      st.subheader("⚙️ Edit atau Hapus Menu Tertentu")

      menu_options = {
          f"[{row['menu_group']}] {row['menu_title']} (Urutan: {row['sort_order']})": row[
              "id"
          ]
          for _, row in df_menus.iterrows()
      }
      selected_label = st.selectbox(
          "Pilih Menu yang Ingin Dikelola:", list(menu_options.keys())
      )
      selected_menu_id = menu_options[selected_label]

      curr_data = pd.read_sql(
          f"SELECT * FROM hris_company_menus WHERE id = '{selected_menu_id}'",
          con,
      ).iloc[0]

      with st.form(f"form_edit_menu_{selected_menu_id}"):
        c1, c2 = st.columns(2)
        with c1:
          e_group = st.text_input(
              "Kelompok / Kategori Menu",
              value=str(curr_data["menu_group"] or "Utama"),
          )
          e_title = st.text_input(
              "Judul Menu", value=str(curr_data["menu_title"] or "")
          )
          e_url = st.text_input(
              "URL Tujuan (Link Drive, Form, dll.)",
              value=str(curr_data["menu_url"] or ""),
          )
        with c2:
          e_image = st.text_input(
              "URL Gambar / Ikon (Opsional)",
              value=str(curr_data["image_url"] or ""),
          )
          e_order = st.number_input(
              "Urutan Tampil (Sort Order)",
              min_value=0,
              value=int(curr_data["sort_order"] or 0),
          )

        col_b1, col_b2 = st.columns(2)
        update_btn = col_b1.form_submit_button("💾 Simpan Perubahan Menu")
        delete_btn = col_b2.form_submit_button("🗑️ Hapus Menu Ini")

        if update_btn:
          if not e_title or not e_url:
            st.error("⚠️ Judul Menu dan URL Tujuan wajib diisi!")
          else:
            try:
              con.execute(
                  """
                                UPDATE hris_company_menus 
                                SET menu_group = ?, menu_title = ?, menu_url = ?, image_url = ?, sort_order = ?
                                WHERE id = ?
                            """,
                  (e_group, e_title, e_url, e_image, int(e_order), selected_menu_id),
              )
              con.commit()
              con.sync()
              st.success("🎉 Menu berhasil diperbarui!")
              st.rerun()
            except Exception as e:
              st.error(f"❌ Gagal update menu: {e}")

        if delete_btn:
          try:
            con.execute(
                "DELETE FROM hris_company_menus WHERE id = ?",
                (selected_menu_id,),
            )
            con.commit()
            con.sync()
            st.success("🗑️ Menu berhasil dihapus!")
            st.rerun()
          except Exception as e:
            st.error(f"❌ Gagal menghapus menu: {e}")

  # --- TAB 2: TAMBAH MENU BARU ---
  with tab_add:
    st.subheader("➕ Tambah Pintasan Menu Baru")

    with st.form("form_tambah_menu"):
      c1, c2 = st.columns(2)
      with c1:
        new_group = st.text_input(
            "Kelompok / Kategori Menu",
            value="Utama",
            placeholder="Contoh: Dokumen SOP, Absensi, Operasional",
        )
        new_title = st.text_input(
            "Judul Menu", placeholder="Contoh: Form Pengajuan Lembur"
        )
        new_url = st.text_input(
            "URL Tujuan",
            placeholder="https://docs.google.com/spreadsheets/d/...",
        )
      with c2:
        new_image = st.text_input(
            "URL Gambar / Ikon (Opsional)",
            placeholder="https://example.com/icon.png",
        )
        new_order = st.number_input(
            "Urutan Tampil (Sort Order)", min_value=0, value=0, step=1
        )

      submitted_menu = st.form_submit_button("💾 Simpan Menu Baru")

      if submitted_menu:
        if not new_title or not new_url:
          st.error("⚠️ Judul Menu dan URL Tujuan wajib diisi!")
        else:
          try:
            menu_id = str(uuid.uuid4())
            con.execute(
                """
                            INSERT INTO hris_company_menus (id, company_id, menu_group, menu_title, menu_url, image_url, sort_order)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                (
                    menu_id,
                    company_id,
                    new_group,
                    new_title,
                    new_url,
                    new_image,
                    int(new_order),
                ),
            )
            con.commit()
            con.sync()
            st.success(f"🎉 Menu **{new_title}** berhasil ditambahkan!")
            st.rerun()
          except Exception as e:
            st.error(f"❌ Gagal menyimpan menu: {e}")