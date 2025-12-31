import sys
import os

sys.path.append(os.path.dirname(__file__))

from hotel_agent import filter_hotels
from food_agent import get_restaurant_recommendations

def run_full_recommendation_flow():
    print("=== OTEL & RESTORAN ÖNERİ SİSTEMİ ===\n")

    sehir = input("Şehir giriniz (örn: Antalya): ")
    max_fiyat = int(input("Maksimum gecelik fiyat (örn: 2000): "))
    min_puan = float(input("Minimum otel puanı (örn: 4.0): "))

    mutfak_turu = input("İstediğiniz mutfak türü (boş bırakabilirsiniz): ")

    if mutfak_turu.strip() == "":
        mutfak_turu = None

    print("\n🔎 Uygun oteller aranıyor...\n")   

    uygun_oteller = filter_hotels(sehir, max_fiyat, min_puan)

    if uygun_oteller.empty:
        print("❌ Kriterlerinize uygun otel bulunamadı.")
        return
    
    secilen_otel = uygun_oteller.iloc[0]

    print("✅ Seçilen Otel:")
    print(f"- {secilen_otel['isim']} | {secilen_otel['sehir']} | {secilen_otel['fiyat_gece']} TL | {secilen_otel['puan']} puan")
    print(f"- Açıklama: {secilen_otel['konum_aciklama']}")

    otel_id = int(secilen_otel["id"])

    
    print("\n🍽 Bu otele göre restoran önerileri:\n")

    restoranlar = get_restaurant_recommendations(otel_id, mutfak_turu)

    if restoranlar.empty:
        print("❌ Bu otele göre uygun restoran bulunamadı.")
        return

    for _, rest in restoranlar.iterrows():
        print(f"- {rest['isim']} | {rest['mutfak_turu']} | {rest['puan']} puan")
        print(f"  → {rest['konum_aciklama']}")
    
if __name__ == "__main__":
    run_full_recommendation_flow()