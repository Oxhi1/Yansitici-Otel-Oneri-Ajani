import pandas as pd 
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "restoran.csv")
DATA_PATH = os.path.abspath(DATA_PATH)

def load_restaurants():
    df = pd.read_csv(DATA_PATH)
    return df 

#Tek bir merkezden veri okumak için bu yol // fazla karmaşıklık ve dosya yolu değişirse değişmesin

def get_restaurants_near_hotel(hotel_id):
    df= load_restaurants()

    def is_near(rest_row):
        yakin_ids = str(rest_row["otellere_yakin_ids"]).split(",")
        return str(hotel_id) in yakin_ids
    
    near_restaurants = df[df.apply(is_near,axis=1)]
    return near_restaurants

def filter_by_cuisine(df,mutfak_turu=None):
    if mutfak_turu is None:
        return df
    
    filtered = df[df["mutfak_turu"]==mutfak_turu]
    return filtered

def get_restaurant_recommendations(hotel_id,mutfak_turu =None):

    near_restaurants= get_restaurants_near_hotel(hotel_id)
    final_list = filter_by_cuisine(near_restaurants,mutfak_turu)
    return final_list

if __name__ == "__main__":
    print("✅ Tüm restoranlar:\n")
    print(load_restaurants())

    print("\n✅ 1 numaralı otele yakın restoranlar:\n")
    yakinlar = get_restaurants_near_hotel(1)
    print(yakinlar)

    print("\n✅ 1 numaralı otel + Türk Mutfağı filtreli:\n")
    filtreli = get_restaurant_recommendations(1, mutfak_turu="Türk Mutfağı")
    print(filtreli)