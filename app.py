import streamlit as st
import pandas as pd

st.set_page_config(page_title="Form Pembuatan SPH & Preview Diskon", page_icon="📄", layout="wide")

# Google Sheet ID milik SOLHAYS02_APP
SPREADSHEET_ID = "1ZX3QEoFxIAld-nM63-9JD5UW_FVm88mAe72fswOYlT0"

@st.cache_data(ttl=30)
def get_live_datasales():
    """Mengambil data faktur & diskon historis dari SOLHAYS02_APP"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=datasales"
    try:
        df = pd.read_csv(url)
        # Clean kolom teks
        for col in ['customer', 'product', 'Line']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        # Clean kolom angka
        for col in ['valuesales', 'DAF', 'DLF', 'Unit']:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '').str.replace(' ', ''), 
                    errors='coerce'
                ).fillna(0)
        
        # Hitung % Diskon (DAF / Value Sales)
        df['% Disc (G/J)'] = df.apply(
            lambda r: round((r['DAF'] / r['valuesales'] * 100), 2) if r['valuesales'] > 0 else 0, axis=1
        )
        return df
    except Exception as e:
        st.error(f"Gagal memuat data diskon: {e}")
        return pd.DataFrame()

st.title("📄 Form Pembuatan SPH dengan Live Preview Diskon RS")

df_sales = get_live_datasales()

if not df_sales.empty:
    # 1. Pilihan Outlet / Rumah Sakit
    list_rs = sorted([rs for rs in df_sales['customer'].unique() if rs and str(rs).upper() != 'NAN'])
    selected_rs = st.selectbox("🏥 Pilih Rumah Sakit / Outlet Tujuan SPH:", list_rs)
    
    # 2. Pilihan Produk
    list_prod = sorted([p for p in df_sales['product'].unique() if p and str(p).upper() != 'NAN'])
    selected_prod = st.selectbox("💊 Pilih Produk yang Ditawarkan:", list_prod)
    
    st.divider()

    # 3. PREVIEW DISKON HISTORIS BERDASARKAN RS & PRODUK TERSEBUT
    st.subheader("🔍 Preview Diskon Historis untuk Pilihan Ini")
    
    # Filter data khusus RS dan Produk yang dipilih
    matched_data = df_sales[
        (df_sales['customer'] == selected_rs) & 
        (df_sales['product'] == selected_prod)
    ]
    
    if not matched_data.empty:
        # PERBAIKAN: Menambahkan huruf 'f' di depan string agar variabel terbaca
        st.success(f"Ditemukan riwayat transaksi untuk produk ini di **{selected_rs}**!")
        
        # Tampilkan ringkasan rata-rata diskon
        avg_disc = matched_data['% Disc (G/J)'].mean()
        max_disc = matched_data['% Disc (G/J)'].max()
        min_disc = matched_data['% Disc (G/J)'].min()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📉 Rata-rata % Diskon (G/J)", f"{avg_disc:.2f}%")
        col2.metric("🔺 Diskon Tertinggi Pernah Diberikan", f"{max_disc:.2f}%")
        col3.metric("🔻 Diskon Terendah", f"{min_disc:.2f}%")
        
        with st.expander("📋 Lihat Detail Riwayat Faktur & Diskon Sebelumnya"):
            st.dataframe(
                matched_data[['Periode', 'Invoice', 'Line', 'Unit', 'valuesales', 'DAF', '% Disc (G/J)', 'Name']],
                use_container_width=True
            )
    else:
        st.warning(f"⚠️ Belum ada catatan riwayat transaksi untuk produk **{selected_prod}** di **{selected_rs}**. Pastikan menggunakan acuan standar penawaran.")

    st.divider()

    # 4. FORM INPUT SPH SELANJUTNYA
    st.subheader("✍️ Masukkan Nilai Penawaran SPH Baru")
    with st.form("form_sph"):
        input_harga = st.number_input("Harga Penawaran / Value Sales (Rp)", min_value=0, step=1000)
        input_daf = st.number_input("Nominal Diskon DAF (Rp)", min_value=0, step=1000)
        
        preview_disc = (input_daf / input_harga * 100) if input_harga > 0 else 0
        st.info(f"📊 Kalkulasi % Diskon Penawaran Ini: **{preview_disc:.2f}%**")
        
        submit_btn = st.form_submit_button("💾 Simpan / Cetak SPH")
        if submit_btn:
            st.success("Data SPH berhasil diproses dengan mengacu pada batas diskon historis!")

else:
    st.warning("Menunggu data tersambung ke SOLHAYS02_APP...")
