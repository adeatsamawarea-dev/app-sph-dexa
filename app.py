import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import math
import re
import os
from PIL import Image
import qrcode

st.set_page_config(page_title="SPH - Solhays 2026", page_icon="📄", layout="centered")

st.title("📄 SPH - Solhays 2026")
st.subheader("Format Portrait (Tanda Tangan & Logo Disempurnakan)")

# --- FUNGSI PENDUKUNG ---
def sanitize_text(text):
    if pd.isna(text): return "-"
    return str(text).replace('•', '- ').encode('latin-1', 'replace').decode('latin-1')

def safe_float(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val_str = str(val).strip()
    val_str = re.sub(r'[^\d,\.\-]', '', val_str)
    
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

def signature_name_lines(name):
    return ["Ade Budi", "Susetyo"] if name == "Ade Budi Susetyo" else [name]

@st.cache_data(ttl=0)
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

if 'keranjang' not in st.session_state:
    st.session_state.keranjang = []

st.markdown("### 1. Pilih Area Manager (AM)")
pilihan_am = ["Ade Budi Susetyo", "Kusriyanto", "Pratama Angga Budiantoro Putro"]
selected_am = st.selectbox("Area Manager:", pilihan_am, label_visibility="collapsed")
upload_ttd = st.file_uploader(f"Upload Tanda Tangan / Paraf untuk {selected_am} (Opsional - PNG/JPG)", type=["png", "jpg", "jpeg"])
st.markdown("---")

st.markdown("### 2. Pilih Outlet / Rumah Sakit")
if 'AM' in df_customer.columns:
    df_filtered_cust = df_customer[df_customer['AM'].astype(str).str.contains(selected_am, case=False, na=False)]
    if df_filtered_cust.empty: df_filtered_cust = df_customer
else:
    df_filtered_cust = df_customer
outlets = df_filtered_cust['Nama Outlet'].dropna().unique().tolist()
selected_outlet = st.selectbox("Outlet:", outlets, label_visibility="collapsed")
st.markdown("---")

st.markdown("### 3. Tambah Produk ke SPH")
produks = df_harga['Nama Produk'].dropna().unique().tolist()
selected_produk = st.selectbox("Pilih Produk Obat:", produks)
prod_data = df_harga[df_harga['Nama Produk'] == selected_produk].iloc[0]
hna_val = safe_float(prod_data.get('HNA', prod_data.get('Harga Hna', 0)))
isi_val = safe_float(prod_data.get('Isi', 1))
if isi_val <= 0: isi_val = 1
kemasan_val = prod_data.get('Kemasan', prod_data.get('Satuan', '-'))
if pd.isna(kemasan_val) or str(kemasan_val).strip() == '': kemasan_val = prod_data.get('Satuan', '-')
link_web_val = prod_data.get('Link Web', '')
if pd.isna(link_web_val): link_web_val = ''
st.info(f"ℹ️ **Info Produk:** HNA: **Rp {hna_val:,.0f}** | Kemasan: **{sanitize_text(kemasan_val)}** | Isi: **{int(isi_val)}")

st.markdown("#### Mode Perhitungan Harga:")
mode_hitung = st.radio("Pilih cara input:", ["Input Diskon (%)", "Input Target Harga Jadi"], horizontal=True, label_visibility="collapsed")
col1, col2 = st.columns([1, 1])
if mode_hitung == "Input Diskon (%)":
    with col1: diskon_input = st.number_input("Diskon (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    harga_jadi_kalkulasi = (hna_val - (hna_val * diskon_input / 100)) * 1.11 / isi_val
    with col2: st.success(f"💡 **Harga Jadi:**\n### Rp {harga_jadi_kalkulasi:,.0f}")
    diskon_final, harga_jadi_final = diskon_input, harga_jadi_kalkulasi
else:
    harga_maksimal = (hna_val * 1.11) / isi_val
    with col1: harga_input = st.number_input("Target Harga Jadi (Rp)", min_value=0.0, value=float(harga_maksimal), step=1000.0)
    diskon_kalkulasi = (1 - ((harga_input * isi_val) / (hna_val * 1.11))) * 100 if hna_val > 0 else 0.0
    with col2: st.success(f"💡 **Diskon Otomatis:**\n### {diskon_kalkulasi:,.2f}%")
    diskon_final, harga_jadi_final = round(diskon_kalkulasi, 2), harga_input

if st.button("➕ Tambah ke SPH", use_container_width=True):
    st.session_state.keranjang.append({'Nama Produk': selected_produk, 'Komposisi': prod_data.get('Komposisi', '-'), 'Indikasi': prod_data.get('Indikasi', '-'), 'Kemasan': str(kemasan_val), 'Isi': int(isi_val), 'HNA': hna_val, 'Diskon': diskon_final, 'Harga Jadi Satuan': harga_jadi_final, 'Link Web': str(link_web_val).strip()})
    st.toast(f"Berhasil menambahkan {selected_produk}!", icon="✅")

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
    st.markdown("### ⚙️ Pengaturan Dokumen PDF")
    tampilkan_lampiran = st.checkbox("📄 Sertakan Halaman Kedua (Lampiran Detail & Website)", value=True)
    if st.button("📄 Generate & Download PDF SPH", type="primary", use_container_width=True):
        cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
        logo_path, logo_png = "PT-DEXA-MEDICA.png", "logo_temp.png"
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255)); background.paste(img, mask=img.split()[-1]); background.save(logo_png, "PNG")
                else: img.save(logo_png, "PNG")
            except: pass
        qr_path = "ttd_qr.png"
        qr = qrcode.QRCode(version=1, box_size=10, border=2); qr.add_data("https://portal.dexagroup.com/ebc/?i=DX013070722"); qr.make(fit=True); qr.make_image(fill_color="black", back_color="white").save(qr_path)
        ttd_path, has_uploaded_ttd = "ttd_upload_temp.png", False
        if upload_ttd is not None:
            try: Image.open(upload_ttd).save(ttd_path, "PNG"); has_uploaded_ttd = True
            except: pass
        class PDF(FPDF):
            def header(self):
                if os.path.exists(logo_png): self.image(logo_png, 30, 14, 55); self.set_y(40)
                else: self.set_y(40); self.set_font('Arial', 'B', 15); self.set_text_color(0, 86, 179); self.cell(0, 8, 'PT DEXA MEDICA', 0, 1, 'L'); self.ln(5)
            def footer(self):
                self.set_y(-30); self.set_font('Arial', 'I', 8); self.set_text_color(128); self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')
        pdf = PDF('P', 'mm', 'A4'); pdf.set_margins(30, 40, 25); pdf.add_page()
        tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
        pdf.set_font('Arial', '', 10); pdf.set_text_color(0, 0, 0); pdf.cell(0, 5, f'Surakarta, {tgl_sekarang}', 0, 1, 'R'); pdf.ln(3)
        pdf.set_font('Arial', 'BU', 11); pdf.cell(0, 5, 'Perihal : Surat Penawaran Harga', 0, 1, 'L'); pdf.ln(6)
        pdf.set_font('Arial', '', 10)
        for text in ['Kepada Yth,', 'Kepala Farmasi', sanitize_text(cust_data.get('Nama Outlet', '-')), 'di Tempat']: pdf.cell(0, 5, text, 0, 1, 'L')
        pdf.ln(5); pdf.cell(0, 5, 'Dengan hormat,', 0, 1, 'L')
        nama_outlet_str = sanitize_text(cust_data.get('Nama Outlet', '-'))
        pdf.multi_cell(0, 6, f"Sebelumnya kami menyampaikan terimakasih kepada {nama_outlet_str} atas kepercayaan dan kerjasama yang telah terjalin dengan baik selama ini dengan PT Dexa Medica. Bersama ini kami sampaikan daftar produk yang dapat kami tawarkan untuk kebutuhan rumah sakit Anda."); pdf.ln(4)
        pdf.set_font('Arial', 'B', 8.5); pdf.set_fill_color(235, 235, 235); pdf.set_text_color(30, 30, 30); pdf.set_draw_color(160, 160, 160)
        col_widths = [35, 45, 18, 9, 21, 27]; headers = ['Nama Produk', 'Komposisi', 'Kemasan', 'Isi', 'HNA (Rp)', 'Harga Jadi\n(Sat/Terkecil)']; start_y = pdf.get_y()
        for i, header in enumerate(headers):
            x, y = pdf.get_x(), pdf.get_y(); pdf.rect(x, y, col_widths[i], 10, style='DF'); pdf.set_xy(x, y + (1.5 if '\n' in header else 3)); pdf.multi_cell(col_widths[i], 3.5 if '\n' in header else 4, header, 0, 'C'); pdf.set_xy(x + col_widths[i], start_y)
        pdf.ln(10); pdf.set_font('Arial', '', 9.5); pdf.set_text_color(0, 0, 0)
        for item in st.session_state.keranjang:
            row = [sanitize_text(item['Nama Produk']), sanitize_text(item['Komposisi']), sanitize_text(item['Kemasan']), str(item['Isi']), f"{item['HNA']:,.0f}", f"{item['Harga Jadi Satuan']:,.0f}"]; max_h = 7
            for i, text in enumerate(row):
                lines = sum(math.ceil(pdf.get_string_width(p) / (col_widths[i] - 2)) if pdf.get_string_width(p) > 0 else 1 for p in str(text).split('\n')); max_h = max(max_h, lines * 6)
            max_h += 5; start_y = pdf.get_y()
            if start_y + max_h > 260: pdf.add_page(); start_y = pdf.get_y()
            for i, text in enumerate(row):
                x, y = pdf.get_x(), pdf.get_y(); pdf.rect(x, y, col_widths[i], max_h); pdf.set_xy(x, y + 2.5); pdf.multi_cell(col_widths[i], 5.5, str(text), 0, 'R' if i in [4, 5] else 'C' if i in [2, 3] else 'L'); pdf.set_xy(x + col_widths[i], start_y)
            pdf.ln(max_h)
        pdf.ln(5); pdf.set_font('Arial', '', 10); pdf.multi_cell(0, 6, 'Kami berharap produk PT. Dexa Medica ini dapat menjadi standard di Rumah Sakit yang Bapak/Ibu pimpin. Demikian surat permohonan ini, atas perhatian dan kerjasamanya kami ucapkan terima kasih.'); pdf.ln(4); pdf.cell(0, 5, 'Salam,', 0, 1, 'L')
        y_ttd = pdf.get_y(); signature_lines = signature_name_lines(selected_am); pdf.set_font('Arial', 'BU', 10); w_name = max(pdf.get_string_width(line) for line in signature_lines); pdf.set_font('Arial', 'I', 8.5); w_block = max(w_name, pdf.get_string_width('Area Manager')) + 5; center_x = 30 + w_block / 2
        if has_uploaded_ttd: pdf.image(ttd_path, center_x - 10, y_ttd + 2, w=20); y_next = y_ttd + 16
        elif os.path.exists(qr_path): pdf.image(qr_path, center_x - 7, y_ttd + 2, w=14); y_next = y_ttd + 18
        else: y_next = y_ttd + 2
        pdf.set_xy(30, y_next); pdf.set_font('Arial', 'BU', 10); pdf.multi_cell(w_block, 5, '\n'.join(signature_lines), 0, 'C'); pdf.set_xy(30, pdf.get_y() + 1); pdf.set_font('Arial', 'I', 8.5); pdf.cell(w_block, 4, 'Area Manager', 0, 1, 'C'); pdf.ln(15)
        if tampilkan_lampiran:
            pdf.add_page(); pdf.set_font('Arial', 'B', 11); pdf.set_text_color(0, 86, 179); pdf.cell(0, 8, 'LAMPIRAN: DETAIL PRODUK', 0, 1, 'C'); pdf.ln(4)
            for idx, item in enumerate(st.session_state.keranjang, start=1):
                pdf.set_font('Arial', 'B', 10); pdf.cell(0, 6, f"{idx}. {sanitize_text(item['Nama Produk'])}", 0, 1, 'L'); pdf.set_text_color(0, 0, 0); pdf.cell(0, 5, 'Indikasi:', 0, 1, 'L'); pdf.set_font('Arial', '', 10); pdf.multi_cell(0, 6, sanitize_text(item['Indikasi']).replace('\n', ' ')); pdf.ln(2)
        pdf_bytes = bytes(pdf.output())
        for path in [logo_png, qr_path, ttd_path]:
            if os.path.exists(path): os.remove(path)
        st.success('✅ SPH Berhasil Dibuat!'); st.download_button(label='📥 DOWNLOAD SPH SEKARANG', data=pdf_bytes, file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf", mime='application/pdf', use_container_width=True)
