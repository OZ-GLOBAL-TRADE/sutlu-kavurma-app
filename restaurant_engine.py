import os
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env.txt"))

def get_config_val(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val:
        return val
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default

RESTAURANT_SPREADSHEET_KEY = get_config_val(
    "RESTAURANT_SPREADSHEET_KEY", 
    "1AtS9RMZmQf4dxUl1BO-gJ6IJvtKlCcMxdXHG22ZaMX8"
)

@st.cache_resource(show_spinner=False)
def get_restaurant_sheets_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
    except Exception as e:
        print(f"Secrets okuma uyarısı: {e}")

    sa_path = os.path.join(BASE_DIR, "service_account.json")
    if os.path.exists(sa_path):
        creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
        return gspread.authorize(creds)

    raise FileNotFoundError("Google Service Account kimlik bilgileri bulunamadı.")

def clean_num(val):
    if pd.isna(val) or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    v = str(val).replace("₺", "").replace("$", "").replace("%", "").replace("TL", "").replace(" ", "").strip()
    if "." in v and "," in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0

@st.cache_data(ttl=600, show_spinner=False)
def fetch_restaurant_data():
    try:
        client = get_restaurant_sheets_client()
        spreadsheet = client.open_by_key(RESTAURANT_SPREADSHEET_KEY)
        ranges = ["'SK_GUNLUK_KASA'!A1:I30", "'SK_HAMMADDE'!A1:J30", "'SK_TEDARIKCILER'!A1:I30"]
        batch_res = spreadsheet.values_batch_get(ranges)
        value_ranges = batch_res.get("valueRanges", [])
    except Exception as e:
        print("Restoran E-Tablo batch hatası:", e)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    kasa_records = []
    if len(value_ranges) > 0:
        rows = value_ranges[0].get("values", [])
        for r in rows[5:25]:
            if r and r[0].strip() and not str(r[0]).strip().startswith("="):
                nakit = clean_num(r[2]) if len(r) > 2 else 0.0
                pos = clean_num(r[3]) if len(r) > 3 else 0.0
                paket = clean_num(r[4]) if len(r) > 4 else 0.0
                toplam = clean_num(r[5]) if (len(r) > 5 and r[5] and not r[5].startswith("=")) else (nakit + pos + paket)
                masraf = clean_num(r[6]) if len(r) > 6 else 0.0
                net_kasa = clean_num(r[7]) if (len(r) > 7 and r[7] and not r[7].startswith("=")) else (toplam - masraf)
                kasa_records.append({
                    "Tarih": r[0].strip(),
                    "Gun": r[1].strip() if len(r) > 1 else "",
                    "Nakit": nakit,
                    "Kredi_Karti": pos,
                    "Paket_YemekKarti": paket,
                    "Toplam_Ciro": toplam,
                    "Masraf": masraf,
                    "Net_Nakit_Akisi": net_kasa,
                    "Not": r[8].strip() if len(r) > 8 else ""
                })

    hammadde_records = []
    if len(value_ranges) > 1:
        rows = value_ranges[1].get("values", [])
        for r in rows[5:25]:
            if r and r[0].strip() and not str(r[0]).strip().startswith("="):
                alis_fiyat = clean_num(r[4]) if len(r) > 4 else 0.0
                porsiyon_gr = clean_num(r[5]) if len(r) > 5 else 0.0
                fire_yuzde = clean_num(r[6]) if len(r) > 6 else 0.0
                efektif_kg = clean_num(r[7]) if (len(r) > 7 and r[7] and not r[7].startswith("=")) else (alis_fiyat / (1 - fire_yuzde) if fire_yuzde < 1.0 else alis_fiyat)
                porsiyon_maliyet = clean_num(r[8]) if (len(r) > 8 and r[8] and not r[8].startswith("=")) else ((efektif_kg / 1000.0) * porsiyon_gr if r[3].strip() == "kg" else efektif_kg * porsiyon_gr)
                satis_fiyat = clean_num(r[9]) if len(r) > 9 else 0.0
                
                hammadde_records.append({
                    "Kod": r[0].strip(),
                    "Hammadde": r[1].strip() if len(r) > 1 else "",
                    "Kategori": r[2].strip() if len(r) > 2 else "",
                    "Birim": r[3].strip() if len(r) > 3 else "kg",
                    "Birim_Alis_TL": alis_fiyat,
                    "Porsiyon_Miktari": porsiyon_gr,
                    "Fire_Orani": fire_yuzde * 100 if fire_yuzde <= 1.0 else fire_yuzde,
                    "Porsiyon_Maliyeti_TL": porsiyon_maliyet,
                    "Tavsiye_Satis_TL": satis_fiyat,
                    "Brut_Marj": ((satis_fiyat - porsiyon_maliyet) / satis_fiyat) if satis_fiyat > 0 else 0.0
                })

    tedarik_records = []
    if len(value_ranges) > 2:
        rows = value_ranges[2].get("values", [])
        for r in rows[5:25]:
            if r and r[0].strip() and not str(r[0]).strip().startswith("="):
                tedarik_records.append({
                    "Tedarikci": r[0].strip(),
                    "Kategori": r[1].strip() if len(r) > 1 else "Toptan",
                    "Fatura_No": r[2].strip() if len(r) > 2 else "-",
                    "Tutar_TL": clean_num(r[3]) if len(r) > 3 else 0.0,
                    "Fatura_Tarihi": r[4].strip() if len(r) > 4 else "-",
                    "Vade_Tarihi": r[5].strip() if len(r) > 5 else "-",
                    "Vade_Durumu": r[6].strip() if len(r) > 6 else "-",
                    "Durum": r[7].strip() if len(r) > 7 else "Bekliyor",
                    "Not": r[8].strip() if len(r) > 8 else ""
                })

    return pd.DataFrame(kasa_records), pd.DataFrame(hammadde_records), pd.DataFrame(tedarik_records)

def generate_restaurant_metrics(df_kasa, df_ham, df_ted):
    toplam_ciro = df_kasa["Toplam_Ciro"].sum() if not df_kasa.empty else 0.0
    toplam_masraf = df_kasa["Masraf"].sum() if not df_kasa.empty else 0.0
    net_kasa = df_kasa["Net_Nakit_Akisi"].sum() if not df_kasa.empty else 0.0
    
    bekleyen_borclar = 0.0
    if not df_ted.empty and "Durum" in df_ted.columns:
        bekleyen_borclar = df_ted[df_ted["Durum"].str.contains("Bekliyor|bekliyor", na=False)]["Tutar_TL"].sum()
    
    return {
        "toplam_ciro_tl": toplam_ciro,
        "toplam_masraf_tl": toplam_masraf,
        "net_kasa_tl": net_kasa,
        "bekleyen_tedarikci_borcu_tl": bekleyen_borclar,
        "kasa_gun_sayisi": len(df_kasa),
        "hammadde_cesit_sayisi": len(df_ham),
        "vadesi_gelenler": df_ted[df_ted["Durum"].str.contains("Bekliyor|bekliyor", na=False)].to_dict(orient="records") if not df_ted.empty else [],
        "hammadde_listesi": df_ham.to_dict(orient="records") if not df_ham.empty else []
    }
