import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import math
import re
import os
from PIL import Image
import qrcode

st.set_page_config(page_title="SPH Dexa Medica", page_icon="📄", layout="centered")

st.title("📄 Cetak SPH - Mobile")
st.subheader("Format Portrait (Elegan & Auto Rekap)")

# --- FUNGSI PENDUKUNG ---
def sanitize_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '- ').encode('latin-1', 'replace').decode('latin-1')

def safe_float(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).strip()
    val_str = re.sub(r'[^\d,\.-]', '', val_str)
    
    if '.' in val_str and ',' in val_str:
        if val_str.rfind('.') > val_str.rfind(','): val_str = val_str.replace(',', '')
        else: val_str = val_str.replace('.', '').replace(',', '.')
    else:
        if val_str.count('.') > 1: val_str = val_str.replace('.', '')
        elif val_str.count(',') > 1: val_str = val_str.replace(',', '')
        else:
            if ',' in val_str:
                parts = val_str.split(',')
                if len(parts[1]) == 3: val_str = val_str.replace(',', '')
                else: val_str = val_str.replace(',', '.')
            elif '.' in val_str:
                parts = val_str.split('.')
                if len(parts[1]) == 3: val_str = val_str.replace('.', '')
    try: return float(val_str)
    except: return 0.0

@st.cache_data
def load_data():
    df_cust = pd.read_csv("SPH2026_Customer.csv")
    df_prod = pd.read_csv("SPH2026_Master_Obat.csv")
    df_cust.columns = df_cust.columns.str.strip()
    df_prod.columns = df_prod.columns.str.strip()
    return df_cust, df_prod

try:
    df_customer, df_harga = load_data()
except Exception as e:
    st.error(f"Gagal memuat file CSV: {e}")
    st.stop()

outlets = df_customer['Nama Outlet'].dropna().unique().tolist()
produks = df_harga['Nama Produk'].dropna().unique().tolist()

if 'keranjang' not in st.session_state:
    st.session_state.keranjang = []

# --- FILE REKAP CSV ---
REKAP_FILE = "Rekap_SPH.csv"

def simpan_ke_rekap(data_rows):
    new_df = pd.DataFrame(data_rows)
    if os.path.exists(REKAP_FILE):
        try:
            existing_df = pd.read_csv(REKAP_FILE)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_csv(REKAP_FILE, index=False)
        except:
            new_df.to_csv(REKAP_FILE, index=False)
    else:
        new_df.to_csv(REKAP_FILE, index=False)

def cek_riwayat_outlet(outlet_name):
    if os.path.exists(REKAP_FILE):
        try:
            df_rekap = pd.read_csv(REKAP_FILE)
            if not df_rekap.empty and 'Outlet' in df_rekap.columns:
                matched = df_rekap[df_rekap['Outlet'] == outlet_name]
                if len(matched) > 0:
                    return len(matched), matched.iloc[-1]['Tanggal']
        except:
            pass
    return 0, None

# --- ANTARMUKA APLIKASI ---
st.markdown("### 1. Pilih Outlet / Rumah Sakit")
selected_outlet = st.selectbox("Outlet:", outlets, label_visibility="collapsed")

jumlah_riwayat, tgl_terakhir = cek_riwayat_outlet(selected_outlet)
if jumlah_riwayat > 0:
    st.warning(f"⚠️ **Perhatian:** Outlet **{selected_outlet}** sudah pernah dibuatkan SPH sebanyak **{jumlah_riwayat} kali** (Terakhir pada: {tgl_terakhir}).")

st.markdown("### 2. Tambah Produk & Metode Diskon")
selected_produk = st.selectbox("Pilih Produk Obat:", produks)

prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
hna_val = 0.0
if 'HNA' in prod_data.index: hna_val = safe_float(prod_data['HNA'])
elif 'Harga Hna' in prod_data.index: hna_val = safe_float(prod_data['Harga Hna'])
isi_val = safe_float(prod_data.get('Isi', 1))
if isi_val <= 0: isi_val = 1

metode_diskon = st.radio("Pilih Cara Input Diskon:", ["Berdasarkan Persen (%)", "Berdasarkan Target Harga Jadi (Satuan)"])

diskon = 0.0
if metode_diskon == "Berdasarkan Persen (%)":
    diskon = float(st.number_input("Masukkan Diskon (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1))
else:
    target_harga_jadi = st.number_input("Masukkan Target Harga Jadi / Satuan (Inc PPN & Dibagi Isi):", min_value=0.0, value=0.0, step=100.0)
    if target_harga_jadi > 0:
        net_target = (target_harga_jadi * isi_val) / 1.11
        if hna_val > 0:
            diskon = max(0.0, min(100.0, ((hna_val - net_target) / hna_val) * 100))
            st.info(f"💡 Diskon otomatis dihitung: **{diskon:.2f}%**")

if st.button("➕ Tambah ke SPH", use_container_width=True):
    harga_net = hna_val - (hna_val * diskon / 100)
    harga_total_ppn = harga_net * 1.11 
    harga_jadi_satuan = harga_total_ppn / isi_val
    
    st.session_state.keranjang.append({
        'Nama Produk': selected_produk,
        'Komposisi': prod_data.get('Komposisi', '-'),
        'Indikasi': prod_data.get('Indikasi', '-'),
        'Kemasan': prod_data.get('Kemasan', '-'),
        'Isi': int(isi_val),
        'HNA': hna_val,
        'Diskon': round(diskon, 2),
        'Harga Jadi Satuan': harga_jadi_satuan
    })
    st.success(f"Berhasil menambahkan {selected_produk} (Diskon: {diskon:.1f}%)!")

if len(st.session_state.keranjang) > 0:
    st.markdown("### 📋 Daftar Produk di SPH:")
    df_keranjang = pd.DataFrame(st.session_state.keranjang)
    
    df_tampil = df_keranjang[['Nama Produk', 'Diskon', 'Harga Jadi Satuan']].copy()
    df_tampil['Harga Jadi Satuan'] = df_tampil['Harga Jadi Satuan'].apply(lambda x: f"Rp {x:,.0f}")
    df_tampil['Diskon'] = df_tampil['Diskon'].apply(lambda x: f"{x}%")
    st.table(df_tampil)
    
    if st.button("🗑️ Hapus Semua Produk", type="secondary"):
        st.session_state.keranjang = []
        st.rerun()

    st.markdown("---")
    
    # Opsi Tambahan untuk Lampiran di Halaman 2
    tampilkan_lampiran = st.checkbox("Sertakan Halaman Lampiran (Indikasi & Brosur)", value=True)

    # --- GENERATE PDF & LOGGING REKAP ---
    if st.button("📄 Generate & Download PDF SPH", type="primary", use_container_width=True):
        cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
        
        logo_path = "logoDX.webp"
        logo_png = "logo_temp.png"
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img.save(logo_png, "PNG")
            
        qr_path = "ttd_qr.png"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data("https://portal.dexagroup.com/ebc/?i=DX013070722")
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr.save(qr_path)
        
        no_dokumen = f"SPH/{datetime.datetime.now().strftime('%Y%m%d/%H%M%S')}"
        tgl_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        rekap_rows = []
        for item in st.session_state.keranjang:
            rekap_rows.append({
                'Nomor Dokumen': no_dokumen,
                'Tanggal': tgl_str,
                'Outlet': selected_outlet,
                'Produk': item['Nama Produk'],
                'Diskon (%)': f"{item['Diskon']}%",
                'Harga Jadi Satuan (Inc PPN)': f"Rp {item['Harga Jadi Satuan']:,.0f}"
            })
        simpan_ke_rekap(rekap_rows)

        class PDF(FPDF):
            def header(self):
                if os.path.exists(logo_png):
                    self.image(logo_png, 30, 12, 60)
                    self.set_y(33)
                else:
                    self.set_y(30)
                    self.set_font('Arial', 'B', 15)
                    self.set_text_color(0, 86, 179)
                    self.cell(0, 8, 'PT DEXA MEDICA', 0, 1, 'L')
                    self.ln(5)

            def footer(self):
                self.set_y(-25)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

        # === HALAMAN 1: SURAT UTAMA (Format Elegan Sesuai Permintaan Anda) ===
        pdf = PDF('P', 'mm', 'A4')
        pdf.set_margins(25, 30, 25)
        pdf.add_page()

        tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, f'Surakarta, {tgl_sekarang}', 0, 1, 'R')

        pdf.ln(3)
        pdf.set_font('Arial', 'BU', 11)
        pdf.cell(0, 5, f'Perihal : Surat Penawaran Harga ({no_dokumen})', 0, 1, 'L')

        pdf.ln(8) 
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'Kepada Yth,', 0, 1, 'L')
        pdf.cell(0, 5, 'Kepala Farmasi', 0, 1, 'L')
        nama_outlet_str = sanitize_text(cust_data.get('Nama Outlet', '-'))
        pdf.cell(0, 5, nama_outlet_str, 0, 1, 'L')
        pdf.cell(0, 5, 'di Tempat', 0, 1, 'L')

        pdf.ln(6) 
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'Dengan hormat,', 0, 1, 'L')

        kalimat_pembuka = f"Sebelumnya kami menyampaikan terimakasih kepada {nama_outlet_str} atas kepercayaan dan kerjasama yang telah terjalin dengan baik selama ini dengan PT Dexa Medica . Bersama surat ini kami PT. Dexa Medica mengajukan penawaran harga untuk produk berikut :"
        pdf.multi_cell(0, 5, kalimat_pembuka)
        pdf.ln(4)

        # === TABEL HEADER ===
        pdf.set_font('Arial', 'B', 8.5)
        pdf.set_fill_color(235, 235, 235) 
        pdf.set_text_color(30, 30, 30)
        pdf.set_draw_color(160, 160, 160) 

        col_widths = [35, 55, 16, 8, 20, 24] 
        headers = ['Nama Produk', 'Komposisi', 'Kemasan', 'Isi', 'HNA (Rp)', 'Harga Per Unit']

        start_x = pdf.get_x()
        start_y = pdf.get_y()
        max_h_header = 10 

        for i in range(len(headers)):
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.rect(x, y, col_widths[i], max_h_header, style='DF')
            if '\n' in headers[i]:
                pdf.set_xy(x, y + 1.5)
                pdf.multi_cell(col_widths[i], 3.5, headers[i], 0, 'C')
            else:
                pdf.set_xy(x, y + 3)
                pdf.multi_cell(col_widths[i], 4, headers[i], 0, 'C')
            pdf.set_xy(x + col_widths[i], start_y)

        pdf.ln(max_h_header)

        # === TABEL ISI ===
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(0, 0, 0)

        for item in st.session_state.keranjang:
            row = [
                sanitize_text(item['Nama Produk']),
                sanitize_text(item['Komposisi']),
                sanitize_text(item['Kemasan']),
                str(item['Isi']),
                f"{item['HNA']:,.0f}",
                f"{item['Harga Jadi Satuan']:,.0f}"
            ]

            max_h = 6
            for i, text in enumerate(row):
                lines = 0
                for paragraph in str(text).split('\n'):
                    w = pdf.get_string_width(paragraph)
                    lines += math.ceil(w / (col_widths[i] - 2)) if w > 0 else 1
                h = lines * 4.5 
                if h > max_h: max_h = h

            max_h = max_h + 4 
            start_x = pdf.get_x()
            start_y = pdf.get_y()

            if start_y + max_h > 265: 
                pdf.add_page()
                start_y = pdf.get_y()

            for i in range(len(row)):
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.rect(x, y, col_widths[i], max_h)
                align = 'R' if i in [4, 5] else 'C' if i in [2, 3] else 'L'
                pdf.set_xy(x, y + 2) 
                pdf.multi_cell(col_widths[i], 4.5, str(row[i]), 0, align)
                pdf.set_xy(x + col_widths[i], start_y)

            pdf.ln(max_h)

        pdf.ln(6)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 5, 'Kami berharap produk PT. Dexa Medica ini dapat menjadi standard di Rumah Sakit yang Bapak/Ibu pimpin. Demikian surat permohonan ini, atas perhatian dan kerjasamanya kami ucapkan terimakasih.')

        pdf.ln(6) 
        pdf.cell(0, 5, 'Salam,', 0, 1, 'L')

        y_qr = pdf.get_y()
        if os.path.exists(qr_path):
            pdf.image(qr_path, 30, y_qr + 2, 20)

        pdf.ln(24)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 5, 'Ade Budi Susetyo', 0, 1, 'L')

        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 4, 'Area Manager', 0, 1, 'L') 

        # === HALAMAN 2: LAMPIRAN (Hanya dicetak jika Checkbox dicentang) ===
        if tampilkan_lampiran:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(0, 86, 179)
            pdf.cell(0, 8, 'LAMPIRAN: DETAIL PRODUK', 0, 1, 'C')
            pdf.ln(4)

            for idx, item in enumerate(st.session_state.keranjang, start=1):
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(0, 86, 179)
                pdf.cell(0, 6, f"{idx}. {sanitize_text(item['Nama Produk'])}", 0, 1, 'L')

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 5, "Indikasi:", 0, 1, 'L')
                pdf.set_font('Arial', '', 10)
                indikasi_bersih = sanitize_text(item['Indikasi']).replace('\n', ' ')
                pdf.multi_cell(0, 5, indikasi_bersih)
                pdf.ln(2)

                clean_prod_name = re.sub(r'[^\w]', '_', item['Nama Produk'])
                brosur_file = f"brosur_{clean_prod_name}.png"
                brosur_file_jpg = f"brosur_{clean_prod_name}.jpg"

                found_brosur = None
                if os.path.exists(brosur_file): found_brosur = brosur_file
                elif os.path.exists(brosur_file_jpg): found_brosur = brosur_file_jpg

                if found_brosur:
                    try:
                        pdf.image(found_brosur, w=155) 
                        pdf.ln(3)
                    except: pass

                pdf.ln(4)
                if pdf.get_y() > 255:
                    pdf.add_page()

        try:
            pdf_bytes = bytes(pdf.output()) 
        except:
            pdf_bytes = pdf.output(dest='S').encode('latin-1') 

        if os.path.exists(logo_png): os.remove(logo_png)
        if os.path.exists(qr_path): os.remove(qr_path)

        st.success("✅ SPH Berhasil Dibuat & Telah Direkap Otomatis!")
        st.download_button(
            label="📥 DOWNLOAD SPH SEKARANG",
            data=pdf_bytes,
            file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- MENU LIHAT REKAP ---
st.markdown("---")
with st.expander("📊 Lihat Rekap SPH Keseluruhan (Database GSheet)"):
    if os.path.exists(REKAP_FILE):
        df_rekap_view = pd.read_csv(REKAP_FILE)
        st.dataframe(df_rekap_view, use_container_width=True)
        
        st.download_button(
            label="📥 Download File Rekap (.csv)",
            data=df_rekap_view.to_csv(index=False).encode('utf-8'),
            file_name="Rekap_SPH_Dexa.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("Belum ada data rekap. Buat SPH pertama Anda untuk mulai merekap.")
