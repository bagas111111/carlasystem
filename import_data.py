import uuid
from database import get_connection  # Memanggil koneksi dari database.py
import pandas as pd

print("🚀 Menghubungkan ke Turso Cloud...")
con = get_connection()

print("🚀 Memulai proses import data massal berkecepatan tinggi...")

# 1. Cek atau Buat Perusahaan Utama
res = con.execute("SELECT id FROM hris_companies LIMIT 1")
row_comp = res.fetchone()

if row_comp:
  company_id = row_comp[0]
  print(f"🏢 Menggunakan Perusahaan ID: {company_id}")
else:
  company_id = str(uuid.uuid4())
  con.execute(
      """
        INSERT INTO hris_companies (id, company_code, company_name, address, phone_number, email)
        VALUES (?, 'PT_MAJU', 'PT Maju Sejahtera Bersama', 'Jl. Sudirman No. 123, Jakarta', '021555777', 'hr@ptmaju.com')
    """,
      (company_id,),
  )
  con.commit()
  print("🏢 Perusahaan utama baru berhasil dibuat.")

# 2. Baca file CSV
df = pd.read_csv("data_karyawan.csv")
print(f"📂 Membaca {len(df)} data karyawan dari file CSV...")

success_count = 0

# Mulai transaksi tunggal untuk mengoptimalkan kecepatan (cegah lag jaringan per baris)
try:
  for index, row in df.iterrows():
    emp_id = str(uuid.uuid4())
    career_id = str(uuid.uuid4())

    emp_code = str(row.get("employee_code", ""))
    dev_pin = str(row.get("device_pin", ""))
    full_name = str(row.get("full_name", ""))
    nick_name = str(row.get("nick_name", ""))
    branch = str(row.get("branch", "Pusat"))
    department = str(row.get("department", ""))
    job_title = str(row.get("job_title", ""))
    work_location_type = str(row.get("work_location_type", "ON_SITE"))
    employment_status = str(row.get("employment_status", "CONTRACT"))
    join_date = str(row.get("join_date", "2025-01-01"))
    gender = str(row.get("gender", "MALE"))
    phone_number = str(row.get("phone_number", ""))
    email = str(row.get("email", ""))
    identity_number = str(row.get("identity_number", ""))
    identity_address = str(row.get("identity_address", ""))

    if full_name and dev_pin:
      # A. Insert ke hris_employees (menyesuaikan kolom baru yang lebih lengkap)
      con.execute(
          """
                INSERT INTO hris_employees (
                    id, company_id, employee_code, device_pin, full_name, nick_name,
                    branch, department, job_title, work_location_type, employment_status,
                    join_date, gender, phone_number, email, identity_number, identity_address, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
          (
              emp_id,
              company_id,
              emp_code,
              dev_pin,
              full_name,
              nick_name,
              branch,
              department,
              job_title,
              work_location_type,
              employment_status,
              join_date,
              gender,
              phone_number,
              email,
              identity_number,
              identity_address,
          ),
      )

      # B. Insert otomatis ke hris_employee_careers (NEW_HIRE)
      con.execute(
          """
                INSERT INTO hris_employee_careers (
                    id, company_id, employee_id, type, employment_status,
                    job_title, department, start_date, is_current, notes
                ) VALUES (?, ?, ?, 'NEW_HIRE', ?, ?, ?, ?, 1, 'Import data massal via CSV')
            """,
          (
              career_id,
              company_id,
              emp_id,
              employment_status,
              job_title,
              department,
              join_date,
          ),
      )
      success_count += 1
      print(f"   ✔️ Berhasil menyiapkan: {full_name}")

  # Commit sekali di akhir untuk seluruh data sekaligus
  con.commit()
  # Sinkronisasi akhir ke Turso Cloud (sekali jalan, sangat cepat)
  con.sync()
  con.close()
  print(
      f"🎉 Selesai! Total {success_count} data karyawan berhasil diimpor"
      " dengan cepat ke Turso Cloud."
  )

except Exception as e:
  print(f"❌ Terjadi kesalahan saat import: {e}")