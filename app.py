# ---- TOMBOL GENERATE PDF ----
st.markdown("---")
if st.button("📄 Generate & Download PDF SPH", type="primary", use_container_width=True):
    cust_data = df_customer[df_customer['Nama Outlet'] == selected_outlet].iloc[0]
    
    class PDF(FPDF):
        def header(self):
            # Desain Kop Surat Modern
            self.set_font('Arial', 'B', 16)
            self.set_text_color(220, 20, 60) # Merah Dexa
            self.cell(0, 8, 'PT DEXA MEDICA', 0, 1, 'L')
            
            self.set_font('Arial', 'I', 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, 'Expertise for the Promotion of Health', 0, 1, 'L')
            
            # Garis pemisah kop surat
            self.set_draw_color(220, 20, 60)
            self.set_line_width(0.8)
            self.line(20, 25, 190, 25) # Menyesuaikan margin kiri 20mm
            self.set_line_width(0.2)
            self.line(20, 26, 190, 26)
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    
    # 5. Margin kiri dibuat 2 cm (20 mm), atas 15 mm, kanan 15 mm
    pdf.set_margins(left=20, top=15, right=15)
    pdf.add_page()
    
    tgl_sekarang = datetime.datetime.now().strftime("%d %B %Y")
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    # 1. Boyolali diganti Surakarta
    pdf.cell(0, 8, f'Surakarta, {tgl_sekarang}', 0, 1, 'R')
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, 'Perihal : Penawaran Harga', 0, 1, 'L')
    pdf.ln(5)
    
    pdf.cell(0, 5, 'Kepada Yth.', 0, 1)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, sanitize_text(cust_data.get('Direktur', '-')), 0, 1)
    pdf.cell(0, 5, sanitize_text(cust_data.get('Nama Outlet', '-')), 0, 1)
    
    # 2. Bawah nama outlet ditambahi "di Tempat"
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, 'di Tempat', 0, 1)
    pdf.ln(5)
    
    pdf.cell(0, 6, 'Dengan hormat,', 0, 1)
    pdf.multi_cell(0, 5, 'Semoga Bapak/Ibu dalam keadaan sehat dan sukses selalu. Bersama surat ini, kami dari PT Dexa Medica bermaksud menyampaikan penawaran harga khusus untuk produk kami sebagai berikut:')
    pdf.ln(5)
    
    # Header Tabel - Desain Modern (Header Merah, Teks Putih)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(220, 20, 60) 
    pdf.set_text_color(255, 255, 255) 
    pdf.set_draw_color(200, 200, 200) 
    
    pdf.cell(60, 8, 'Nama Produk', 1, 0, 'C', 1)
    pdf.cell(25, 8, 'Kemasan', 1, 0, 'C', 1)
    pdf.cell(30, 8, 'HNA (Rp)', 1, 0, 'C', 1)
    pdf.cell(15, 8, 'Disc', 1, 0, 'C', 1)
    pdf.cell(45, 8, 'Harga Jadi (Rp)', 1, 1, 'C', 1)
    
    # Isi Tabel - Zebra Stripes (Belang-belang)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    
    fill = False
    pdf.set_fill_color(245, 245, 245) # Warna abu-abu terang untuk baris tabel
    
    for item in st.session_state.keranjang:
        nama = sanitize_text(item['Nama Produk'])[:30]
        kemasan = sanitize_text(item['Kemasan'])[:12]
        
        pdf.cell(60, 8, nama, 1, 0, 'L', fill)
        pdf.cell(25, 8, kemasan, 1, 0, 'C', fill)
        pdf.cell(30, 8, f"{item['HNA']:,.0f}", 1, 0, 'R', fill)
        pdf.cell(15, 8, f"{item['Diskon']:g}%", 1, 0, 'C', fill)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(45, 8, f"{item['Harga Jadi']:,.0f}", 1, 1, 'R', fill)
        pdf.set_font('Arial', '', 9)
        
        fill = not fill # Ganti warna latar untuk baris berikutnya
        
    # 3. Halaman Indikasi (Lampiran Hal 2) Dihapus total dari kode
    
    pdf.ln(5)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, f'Besar harapan kami agar penawaran ini dapat menjadi langkah awal dari kerjasama yang baik antara PT Dexa Medica dengan {sanitize_text(cust_data.get("Nama Outlet", "-"))}.')
    pdf.ln(8)
    
    pdf.cell(0, 6, 'Hormat kami,', 0, 1)
    
    # 4. Sisipkan file qr-code.png sebagai ganti tanda tangan teks
    x_pos = pdf.get_x()
    y_pos = pdf.get_y()
    
    try:
        # Menyisipkan gambar QR Code (lebar 25 mm). Pastikan file bernama persis qr-code.png
        pdf.image('qr-code.png', x=x_pos, y=y_pos + 2, w=25)
        pdf.ln(30) # Beri ruang vertikal agar teks di bawahnya tidak tertindih QR
    except Exception as e:
        # Jika file qr-code.png tidak ditemukan/error, beri jarak kosong standar
        pdf.ln(20) 
        
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, 'Ade Budi Susetyo', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, 'Regional Lead (PIMDA)', 0, 1)
    pdf.cell(0, 5, 'PT Dexa Medica', 0, 1)
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    
    st.success("✅ SPH Berhasil Dibuat!")
    st.download_button(
        label="📥 DOWNLOAD SPH SEKARANG",
        data=pdf_bytes,
        file_name=f"SPH_{selected_outlet.replace(' ', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True)
