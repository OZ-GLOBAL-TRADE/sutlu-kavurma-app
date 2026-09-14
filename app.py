import streamlit as st
import pandas as pd
import plotly.express as px
import hashlib
from restaurant_engine import fetch_restaurant_data, generate_restaurant_metrics

st.set_page_config(page_title="SÜTLÜ KAVURMA — Restoran Paneli", page_icon="🥩", layout="wide")

@st.cache_data(ttl=600, show_spinner=False)
def get_cached_restaurant_data():
    df_k, df_h, df_t = fetch_restaurant_data()
    sk_m = generate_restaurant_metrics(df_k, df_h, df_t)
    return df_k, df_h, df_t, sk_m

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# İzole Veritabanı: Sadece Restoran Yetkilileri
USERS_DB = {
    "yusuf.oz": {"name": "Yusuf Öz", "role": "ADMIN", "password_hash": hash_pw("OzAdmin2026!")},
    "sutlu.kavurma": {"name": "Restoran Müdürü", "role": "RESTAURANT_MANAGER", "password_hash": hash_pw("Sutlu2026!")}
}

DEV_MODE = True 

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = DEV_MODE
    st.session_state["user_info"] = USERS_DB["yusuf.oz"] if DEV_MODE else None

if not st.session_state["authenticated"]:
    st.markdown("<div style='text-align: center; margin-top: 40px;'>", unsafe_allow_html=True)
    st.markdown("<h2>🥩 SÜTLÜ KAVURMA RESTORAN</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Lütfen personel kimlik bilgilerinizle giriş yapınız.</p></div>", unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        with st.form("login_form"):
            username_input = st.text_input("Kullanıcı Adı:").strip().lower()
            password_input = st.text_input("Şifre:", type="password")
            if st.form_submit_button("🔒 Güvenli Giriş Yap", use_container_width=True):
                user_record = USERS_DB.get(username_input)
                if user_record and user_record["password_hash"] == hash_pw(password_input):
                    st.session_state["authenticated"] = True
                    st.session_state["user_info"] = user_record
                    st.rerun()
                else:
                    st.error("❌ Hatalı kullanıcı adı veya şifre!")
    st.stop()

current_user = st.session_state["user_info"]

st.sidebar.markdown(f"### 👤 {current_user['name']}")
st.sidebar.caption(f"Yetki: **{current_user['role']}**")

if st.sidebar.button("🚪 Güvenli Çıkış Yap"):
    st.session_state["authenticated"] = False
    st.session_state["user_info"] = None
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Verileri Güncelle"):
    st.cache_data.clear()
    st.rerun()

# ANA EKRAN KONSOLİDASYONU
st.title("🥩 SÜTLÜ KAVURMA RESTORAN — Operasyon & Finans Paneli")

df_kasa, df_ham, df_ted, sk_metrics = get_cached_restaurant_data()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Toplam Satış (Ciro)", f"₺{sk_metrics['toplam_ciro_tl']:,.2f}")
k2.metric("Toplam Masraf / Gider", f"₺{sk_metrics['toplam_masraf_tl']:,.2f}")
k3.metric("Net Kasa / Nakit Akışı", f"₺{sk_metrics['net_kasa_tl']:,.2f}")
k4.metric("Bekleyen Tedarikçi Borcu", f"₺{sk_metrics['bekleyen_tedarikci_borcu_tl']:,.2f}")
st.markdown("---")

sk_tab1, sk_tab2, sk_tab3 = st.tabs(["💰 Günlük Kasa & Ciro", "🥩 Hammadde & Porsiyon Maliyetleri", "📅 Tedarikçi & Vade Takvimi"])

with sk_tab1:
    if not df_kasa.empty:
        st.plotly_chart(px.bar(df_kasa, x="Tarih", y=["Nakit", "Kredi_Karti", "Paket_YemekKarti"], title="Günlük Satış Kanal Dağılımı", barmode="stack"), use_container_width=True)
        st.dataframe(df_kasa, use_container_width=True)
with sk_tab2:
    if not df_ham.empty:
        st.dataframe(df_ham.style.format({"Birim_Alis_TL": "₺{:,.2f}", "Porsiyon_Miktari": "{:.0f}", "Fire_Orani": "%{:.1f}", "Porsiyon_Maliyeti_TL": "₺{:,.2f}", "Tavsiye_Satis_TL": "₺{:,.2f}", "Brut_Marj": "%{:.1f}"}), use_container_width=True)
with sk_tab3:
    if not df_ted.empty:
        st.dataframe(df_ted.style.format({"Tutar_TL": "₺{:,.2f}"}), use_container_width=True)
