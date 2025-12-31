import pandas as pd 
import os


DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "otel.csv")
DATA_PATH = os.path.abspath(DATA_PATH)

def load_hotels():
    df = pd.read_csv(DATA_PATH) 
    #otel.csv dosyasını okuyup dataframe olarak döner
    return df

def filter_hotels(sehir,max_fiyat,min_puan):
    #Kullanıcının kritelerine göre otelleri filtreler
    df= load_hotels()

    filtered = df[
        (df["sehir"]== sehir) &
        (df["fiyat_gece"] <= max_fiyat) &
        (df["puan"] >= min_puan)
        ]
    
    return filtered

if __name__ == "__main__":
    print("✅ Otel verisi yükleniyor...\n")
    
    oteller = load_hotels()
    print(oteller)

    print("\n✅ Filtrelenmiş oteller (Antalya, max 2000 TL, min 4.0 puan):\n")
    
    sonuc = filter_hotels(
        sehir="Antalya",
        max_fiyat=2000,
        min_puan=4.0
    )

    print(sonuc)
