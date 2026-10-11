import uuid
from database import get_connection  # Memanggil koneksi dari database.py
import pandas as pd

# ==========================================
# KONFIGURASI TARGET IMPORT
# ==========================================
TARGET_COMPANY_ID = "comp-uuid-001" 
AUTO_DETECT_COMPANY = True

print("🚀 Menghubungkan ke Turso Cloud...")
con = get_connection()

print("🚀 Memulai proses import data massal berkecepatan tinggi...")

# 1. Tentukan Company ID
company_id = TARGET_COMPANY_ID
if AUTO_DETECT_COMPANY and (not company_id or company_id == "comp-uuid-001"):
  res = con.execute("SELECT id FROM hris_companies LIMIT 1")
  row_comp = res.fetchone()
  if row_comp:
    company_id = row_comp[0]
    print(f"🏢 Menggunakan Perusahaan Otomatis ID: {company_id}")
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
else:
  print(f"🏢 Menggunakan Target Company ID: {company_id}")

# 2. Baca file CSV
csv_filename = "data_karyawan.csv"
try:
  df = pd.read_csv(csv_filename)
  print(f"📂 Membaca {len(df)} data karyawan dari file {csv_filename}...")
except Exception as e:
  print(f"❌ Gagal membaca file {csv_filename}. Pastikan file CSV ada di folder yang sama! Error: {e}")
  exit()

success_count = 0
failed_count = 0

try:
  for index, row in df.iterrows():
    # Ambil data secara aman berdasarkan nama header kolom CSV
    get_val = lambda col_name, default="": str(row[col_name]).strip() if col_name in df.columns and pd.notna(row[col_name]) else default

    full_name = get_val("full_name")
    dev_pin = get_val("device_pin")

    # Validasi wajib: Nama lengkap dan PIN absen tidak boleh kosong
    if not full_name or not dev_pin or full_name.lower() == "nan" or dev_pin.lower() == "nan":
      print(f"   ⚠️ Baris ke-{index+1} dilewati: 'full_name' atau 'device_pin' kosong.")
      failed_count += 1
      continue

    emp_id = str(uuid.uuid4())
    career_id = str(uuid.uuid4())

    # Mapping lengkap sesuai struktur tabel hris_employees
    emp_code = get_val("employee_code")
    nick_name = get_val("nick_name")
    branch = get_val("branch", "Pusat")
    department = get_val("department", "Umum")
    job_title = get_val("job_title", "Staff")
    work_location_type = get_val("work_location_type", "ON_SITE")
    employment_status = get_val("employment_status", "CONTRACT")
    contract_end_date = get_val("contract_end_date") or None
    join_date = get_val("join_date", "2026-01-01")
    status = get_val("status", "ACTIVE")
    is_rejoin = int(get_val("is_rejoin", 0))
    rejoin_count = int(get_val("rejoin_count", 0))
    identity_type = get_val("identity_type", "KTP")
    identity_number = get_val("identity_number")
    gender = get_val("gender", "MALE")
    place_of_birth = get_val("place_of_birth")
    date_of_birth = get_val("date_of_birth") or None
    phone_number = get_val("phone_number")
    email = get_val("email")
    identity_address = get_val("identity_address")
    is_same_as_identity_address = int(get_val("is_same_as_identity_address", 1))
    residential_address = get_val("residential_address")
    marital_status = get_val("marital_status", "SINGLE")
    family_card_number = get_val("family_card_number")
    last_education_level = get_val("last_education_level", "SMA/SMK")
    last_education_institution = get_val("last_education_institution")
    last_education_major = get_val("last_education_major")
    last_education_year = int(get_val("last_education_year", 2020))

    # A. Insert lengkap ke hris_employees
    con.execute(
        """
            INSERT INTO hris_employees (
                id, company_id, employee_code, device_pin, full_name, nick_name,
                branch, department, job_title, work_location_type, employment_status,
                contract_end_date, join_date, status, is_rejoin, rejoin_count,
                identity_type, identity_number, gender, place_of_birth, date_of_birth,
                phone_number, email, identity_address, is_same_as_identity_address,
                residential_address, marital_status, family_card_number,
                last_education_level, last_education_institution, last_education_major,
                last_education_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            contract_end_date,
            join_date,
            status,
            is_rejoin,
            rejoin_count,
            identity_type,
            identity_number,
            gender,
            place_of_birth,
            date_of_birth,
            phone_number,
            email,
            identity_address,
            is_same_as_identity_address,
            residential_address,
            marital_status,
            family_card_number,
            last_education_level,
            last_education_institution,
            last_education_major,
            last_education_year,
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
    print(f"   ✔️ Berhasil menyiapkan: {full_name} (PIN: {dev_pin})")

  # Commit transaksi massal sekali di akhir
  con.commit()
  con.sync()
  con.close()
  print(f"\n🎉 Selesai!")
  print(f"   - Berhasil diimpor: {success_count} data")
  print(f"   - Gagal/Dilewati: {failed_count} data")

except Exception as e:
  print(f"❌ Terjadi kesalahan sistem saat import: {e}")