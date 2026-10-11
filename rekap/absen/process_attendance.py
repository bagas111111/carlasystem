import datetime
import json
import math
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Load Konfigurasi Aturan Main
with open("config.json", "r") as f:
  CONFIG = json.load(f)

# Priority list yang bersih & akurat sesuai database HRIS
PRIORITY_LIST = CONFIG.get(
    "status_priority",
    [
        "TERLAMBAT",
        "TIDAK ABSEN",
        "IZIN_TERLAMBAT",
        "PULANG_AWAL",
        "IZIN_KELUAR_SEMENTARA",
        "SAKIT",
        "IZIN",
        "CUTI",
        "DINAS_LUAR",
        "HADIR",
    ],
)


def get_priority_rank(status_str):
  status_clean = str(status_str).upper()
  for idx, p in enumerate(PRIORITY_LIST):
    if p in status_clean:
      return idx
  return 999


def resolve_status(status_a, status_b):
  rank_a = get_priority_rank(status_a)
  rank_b = get_priority_rank(status_b)
  return status_a if rank_a <= rank_b else status_b


def parse_time_to_minutes(time_str):
  if not time_str or str(time_str).strip() in ["-", "nan", "", "None"]:
    return None
  parts = str(time_str).strip().split(":")
  return int(parts[0]) * 60 + int(parts[1])


def calculate_overtime(last_out_str, shift_end_str):
  out_mins = parse_time_to_minutes(last_out_str)
  end_mins = parse_time_to_minutes(shift_end_str)

  if out_mins is None or end_mins is None:
    return 0.0

  diff_hours = (out_mins - end_mins) / 60.0
  if diff_hours < CONFIG["overtime_min_hours"]:
    return 0.0

  step = CONFIG["overtime_step_hours"]
  return math.floor(diff_hours / step) * step


def process_attendance_recap(
    raw_checkin_file, employees_file, leaves_file, requests_file
):
  df_emp = pd.read_csv(employees_file)
  df_leaves = pd.read_csv(leaves_file)
  df_req = pd.read_csv(requests_file)

  # Normalisasi kolom PIN karyawan
  emp_pin_col = "device_pin" if "device_pin" in df_emp.columns else "pin"
  df_emp[emp_pin_col] = df_emp[emp_pin_col].astype(str).str.strip()

  # Load & Clean Ceklok Mentah berdasarkan Config Mapping
  df_raw = pd.read_csv(raw_checkin_file)
  mapping = CONFIG.get("raw_columns_mapping", {})
  
  # Deteksi nama kolom secara dinamis (prioritas config, fallback ke pencarian umum)
  col_pin = mapping.get("pin_col") if mapping.get("pin_col") in df_raw.columns else ("device_pin" if "device_pin" in df_raw.columns else "pin")
  col_time = mapping.get("timestamp_col") if mapping.get("timestamp_col") in df_raw.columns else ("timestamp" if "timestamp" in df_raw.columns else "datetime")

  df_raw[col_pin] = df_raw[col_pin].astype(str).str.strip()
  df_raw["timestamp_dt"] = pd.to_datetime(df_raw[col_time])

  cutoff_hour = CONFIG["cut_off_daily_hour"]
  # Tentukan Tanggal Shift Berdasarkan Cut-Off Daily
  df_raw["shift_date"] = df_raw["timestamp_dt"].apply(
      lambda ts: (
          ts.date() - datetime.timedelta(days=1)
          if ts.hour < cutoff_hour
          else ts.date()
      )
  )
  df_raw["time_str"] = df_raw["timestamp_dt"].dt.strftime("%H:%M")

  # Ringkas data log harian murni: ambil scan paling awal (min) sebagai Masuk dan paling akhir (max) sebagai Pulang
  df_scan = (
      df_raw.groupby([col_pin, "shift_date"])
      .agg(first_in=("time_str", "min"), last_out=("time_str", "max"), total_logs=("time_str", "count"))
      .reset_index()
  )

  results = []
  shift_info = CONFIG["shifts"]["NORMAL"]
  shift_start = shift_info["start"]
  shift_end = shift_info["end"]
  shift_start_mins = parse_time_to_minutes(shift_start)
  late_threshold_mins = shift_start_mins + shift_info["late_tolerance_minutes"]

  all_dates = sorted(df_raw["shift_date"].unique())

  for _, emp in df_emp.iterrows():
    pin = str(emp[emp_pin_col])
    nip = str(emp["employee_code"]).strip()
    name = emp["full_name"]
    branch = emp["branch"]
    dept = emp["department"]

    emp_scans = df_scan[df_scan[col_pin] == pin]

    for date_obj in all_dates:
      date_str = str(date_obj)
      matched_scan = emp_scans[emp_scans["shift_date"] == date_obj]

      cin = "-"
      cout = "-"
      raw_status = "HADIR"
      notes = []

      # 1. Evaluasi Log Mesin Absensi Riil (Tanpa status IN/OUT)
      if matched_scan.empty:
        cin = "-"
        cout = "-"
        raw_status = "TIDAK ABSEN"
      else:
        scan_row = matched_scan.iloc[0]
        cin = scan_row["first_in"]
        # Jika hanya ada 1 kali scan dalam sehari, anggap itu scan masuk saja atau pulang tergantung jamnya, tapi amannya set "-" untuk pulang atau gunakan logika standar
        cout = scan_row["last_out"] if scan_row["total_logs"] > 1 else "-"

        if cin == "-" or cout == "-":
          raw_status = "TIDAK ABSEN"

      # 2. Cek Keterlambatan Fisik Murni
      if raw_status == "HADIR":
        cin_mins = parse_time_to_minutes(cin)
        if cin_mins and cin_mins > late_threshold_mins:
          raw_status = "TERLAMBAT"

      candidate_status = raw_status

      # 3. Evaluasi Form Izin / Dinas Harian (Tabel hris_leaves)
      matched_leave = df_leaves[
          (df_leaves["PIN Absen"].astype(str).str.strip() == pin)
          & (df_leaves["Tanggal Izin"] == date_str)
      ]

      if not matched_leave.empty:
        if "Waktu Submit" in matched_leave.columns:
          matched_leave = matched_leave.sort_values(by="Waktu Submit", ascending=False)
        
        leave_row = matched_leave.iloc[0]
        l_type = str(leave_row["Jenis Izin"]).strip().upper()
        l_start = str(leave_row["Jam Mulai"]).strip()
        l_end = str(leave_row["Jam Selesai"]).strip()

        if l_type == "DINAS_LUAR":
          if l_start == shift_start:
            cin = l_start
          if l_end == shift_end:
            cout = l_end
          candidate_status = resolve_status(candidate_status, "DINAS_LUAR")

        elif l_type in ["SAKIT", "CUTI", "IZIN"]:
          cin = "-"
          cout = "-"
          candidate_status = resolve_status(candidate_status, l_type)

        elif l_type == "IZIN_TERLAMBAT":
          cin_m = parse_time_to_minutes(cin)
          l_start_m = parse_time_to_minutes(l_start)
          leave_tol = CONFIG["leave_tolerance_min"]
          if cin_m and l_start_m and abs(cin_m - l_start_m) <= leave_tol:
            candidate_status = resolve_status(candidate_status, "IZIN_TERLAMBAT")
        
        elif l_type == "TERLAMBAT_MENDADAK":
          candidate_status = resolve_status(candidate_status, "TERLAMBAT")

      # 4. Evaluasi Cuti Panjang (Tabel hris_leave_requests)
      matched_req = df_req[
          (df_req["PIN Absen"].astype(str).str.strip() == pin)
          & (df_req["Mulai"] <= date_str)
          & (df_req["Selesai"] >= date_str)
      ]

      if not matched_req.empty:
        req_row = matched_req.iloc[0]
        candidate_status = resolve_status(candidate_status, f"CUTI ({req_row['Jenis Cuti']})")
        cin = "-"
        cout = "-"

      final_status = candidate_status

      # 5. Hitung Lembur
      overtime_hours = (
          calculate_overtime(cout, shift_end) if final_status in ["HADIR", "TERLAMBAT", "IZIN_TERLAMBAT", "DINAS_LUAR"] else 0.0
      )

      results.append({
          "NIP": nip,
          "PIN Absen": str(pin),
          "Nama Karyawan": name,
          "Cabang": branch,
          "Departemen": dept,
          "Tanggal Shift": datetime.datetime.strptime(date_str, "%Y-%m-%d").date(),
          "Jam Masuk": cin,
          "Jam Pulang": cout,
          "Status Kehadiran": final_status,
          "Jam Lembur (Jam)": overtime_hours,
          "Keterangan": "; ".join(notes) if notes else "-",
      })

  return pd.DataFrame(results)


def export_to_professional_excel(df, filename="Hasil_Rekap_Absensi.xlsx"):
  wb = Workbook()
  
  # ==========================================
  # SHEET 1: DETAIL REKAP HARIAN
  # ==========================================
  ws1 = wb.active
  ws1.title = "Detail Rekap Harian"
  ws1.views.sheetView[0].showGridLines = True

  header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
  header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
  align_center = Alignment(horizontal="center", vertical="center")
  align_left = Alignment(horizontal="left", vertical="center")

  thin_border = Border(
      left=Side(style="thin", color="D9D9D9"), right=Side(style="thin", color="D9D9D9"),
      top=Side(style="thin", color="D9D9D9"), bottom=Side(style="thin", color="D9D9D9")
  )

  headers = list(df.columns)
  ws1.append(headers)
  ws1.row_dimensions[1].height = 25

  for col_idx in range(1, len(headers) + 1):
    cell = ws1.cell(row=1, column=col_idx)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = align_center
    cell.border = thin_border

  red_font = Font(name="Calibri", size=11, bold=True, color="C00000")
  yellow_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
  regular_font = Font(name="Calibri", size=11)

  for row_idx, row in df.iterrows():
    row_values = list(row)
    ws1.append(row_values)
    current_row = row_idx + 2
    ws1.row_dimensions[current_row].height = 20

    status_val = str(row["Status Kehadiran"])

    for col_idx in range(1, len(row_values) + 1):
      cell = ws1.cell(row=current_row, column=col_idx)
      cell.font = regular_font
      cell.border = thin_border
      col_name = headers[col_idx - 1]

      if col_name == "NIP":
        cell.number_format = "@"
        cell.alignment = align_center
      elif col_name == "PIN Absen":
        cell.number_format = "@"
        cell.alignment = align_center
      elif col_name == "Tanggal Shift":
        cell.number_format = "YYYY-MM-DD"
        cell.alignment = align_center
      elif col_name == "Status Kehadiran":
        cell.alignment = align_center
        if status_val == "TERLAMBAT":
          cell.font = red_font
        elif "TIDAK ABSEN" in status_val:
          cell.fill = yellow_fill
          cell.font = red_font
      else:
        cell.alignment = align_left

      if "TIDAK ABSEN" in status_val and col_name != "Status Kehadiran":
        cell.fill = yellow_fill

  for col in ws1.columns:
    max_len = max((len(str(cell.value)) for cell in col if cell.value is not None), default=10)
    col_letter = get_column_letter(col[0].column)
    ws1.column_dimensions[col_letter].width = max(max_len + 4, 12)

  # ==========================================
  # SHEET 2: RINGKASAN KELOMPOK
  # ==========================================
  ws2 = wb.create_sheet(title="Ringkasan Status")
  ws2.views.sheetView[0].showGridLines = True

  summary_headers = ["Status Kehadiran", "Tanggal Shift", "NIP", "PIN Absen", "Nama Karyawan", "Departemen"]
  ws2.append(summary_headers)
  ws2.row_dimensions[1].height = 25

  for col_idx in range(1, len(summary_headers) + 1):
    cell = ws2.cell(row=1, column=col_idx)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = align_center
    cell.border = thin_border

  df_summary = df[df["Status Kehadiran"] != "HADIR"].copy()
  df_sorted = df_summary.sort_values(by=["Status Kehadiran", "Tanggal Shift"])

  r_idx = 2
  current_group = None
  group_count = 0

  bold_font = Font(name="Calibri", size=11, bold=True)
  total_fill = PatternFill(start_color="E9EDF4", end_color="E9EDF4", fill_type="solid")

  for _, row in df_sorted.iterrows():
    status_val = row["Status Kehadiran"]

    if current_group is not None and current_group != status_val:
      ws2.append([f"TOTAL {current_group}", "", "", "", "", f"{group_count} orang"])
      ws2.row_dimensions[r_idx].height = 20
      for c_i in range(1, 7):
        tc = ws2.cell(row=r_idx, column=c_i)
        tc.font = bold_font
        tc.fill = total_fill
        tc.border = thin_border
        tc.alignment = align_center if c_i in [1, 6] else align_left
      r_idx += 1
      group_count = 0

    current_group = status_val
    group_count += 1

    ws2.append([
        status_val,
        row["Tanggal Shift"],
        row["NIP"],
        row["PIN Absen"],
        row["Nama Karyawan"],
        row["Departemen"]
    ])
    ws2.row_dimensions[r_idx].height = 20

    for c_i in range(1, 7):
      cell = ws2.cell(row=r_idx, column=c_i)
      cell.border = thin_border
      cell.font = regular_font
      if c_i in [1, 2, 3, 4]:
        cell.alignment = align_center
      else:
        cell.alignment = align_left
        
      if c_i == 1 and status_val == "TERLAMBAT":
        cell.font = red_font
      elif c_i == 1 and "TIDAK ABSEN" in status_val:
        cell.font = red_font
        cell.fill = yellow_fill

    r_idx += 1

  if current_group is not None:
    ws2.append([f"TOTAL {current_group}", "", "", "", "", f"{group_count} orang"])
    ws2.row_dimensions[r_idx].height = 20
    for c_i in range(1, 7):
      tc = ws2.cell(row=r_idx, column=c_i)
      tc.font = bold_font
      tc.fill = total_fill
      tc.border = thin_border
      tc.alignment = align_center if c_i in [1, 6] else align_left

  ws2.column_dimensions["A"].width = 25
  ws2.column_dimensions["B"].width = 15
  ws2.column_dimensions["C"].width = 15
  ws2.column_dimensions["D"].width = 12
  ws2.column_dimensions["E"].width = 25
  ws2.column_dimensions["F"].width = 20

  wb.save(filename)
  print(f"✅ Berhasil! File Excel diperbarui dan disimpan ke: {filename}")


if __name__ == "__main__":
  df_result = process_attendance_recap(
      raw_checkin_file="raw_checkin.csv",
      employees_file="data_karyawan.csv",
      leaves_file="data_leave.csv",
      requests_file="data_cuti.csv",
  )

  print("=== HASIL REKAPITULASI ABSENSI OFFLINE ===")
  print(df_result.to_string())

  export_to_professional_excel(df_result, "Hasil_Rekap_Absensi.xlsx")