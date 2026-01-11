import streamlit as st
from typing import Optional

from app.services.recommendation_service import (
    get_hotels,
    get_restaurants_for_hotel,
    compute_metrics,
)
from app.utils.db_utils import (
    get_or_create_user,
    create_session,
    insert_feedback,
    init_db,
)
from app.agents.reflective_agent import build_profile_hint


# --------------------------------------------------
# SABİT LİSTELER
# --------------------------------------------------

SEHIR_LISTESI = [
    "Adana","Adıyaman","Afyonkarahisar","Ağrı","Amasya","Ankara","Antalya","Artvin",
    "Aydın","Balıkesir","Bilecik","Bingöl","Bitlis","Bolu","Burdur","Bursa",
    "Çanakkale","Çankırı","Çorum","Denizli","Diyarbakır","Edirne","Elazığ","Erzincan",
    "Erzurum","Eskişehir","Gaziantep","Giresun","Gümüşhane","Hakkari","Hatay","Isparta",
    "Mersin","İstanbul","İzmir","Kars","Kastamonu","Kayseri","Kırklareli","Kırşehir",
    "Kocaeli","Konya","Kütahya","Malatya","Manisa","Kahramanmaraş","Mardin","Muğla",
    "Muş","Nevşehir","Niğde","Ordu","Rize","Sakarya","Samsun","Siirt","Sinop","Sivas",
    "Tekirdağ","Tokat","Trabzon","Tunceli","Şanlıurfa","Uşak","Van","Yozgat","Zonguldak",
    "Aksaray","Bayburt","Karaman","Kırıkkale","Batman","Şırnak","Bartın","Ardahan",
    "Iğdır","Yalova","Karabük","Kilis","Osmaniye","Düzce"
]


# --------------------------------------------------
# STREAMLIT CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Otel & Restoran Öneri Sistemi",
    layout="wide",
)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    init_db()

    st.title("🏨 Otel & 🍽️ Restoran Öneri Sistemi")
    st.caption("Kişiselleştirilmiş otel ve restoran önerileri, geri bildirimle öğrenen sistem")

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.header("👤 Kullanıcı & Filtreler")

        user_identifier = st.text_input(
            "Kullanıcı adı",
            value="anon",
            help="Profil ve geri bildirimler bu isimle ilişkilendirilir"
        ).strip() or "anon"

        sehir = st.selectbox(
            "Şehir",
            SEHIR_LISTESI,
            index=SEHIR_LISTESI.index("Antalya")
        )

        st.markdown("### 💰 Fiyat & Puan")

        max_fiyat = st.slider(
            "Maksimum gecelik fiyat (₺)",
            min_value=500,
            max_value=20_000,
            value=2_000,
            step=250
        )

        min_puan = st.slider(
            "Minimum otel puanı",
            min_value=1.0,
            max_value=5.0,
            value=4.0,
            step=0.1
        )

        st.markdown("### 🔢 Sonuç Sayısı")

        top_k_hotels = st.slider("Otel sayısı", 3, 7, 5)
        top_k_rest = st.slider("Otel başına restoran", 1, 5, 3)

        st.divider()
        fetch_btn = st.button("🔎 Önerileri Getir", use_container_width=True)

    # ---------------- USER & PROFILE ----------------
    user_id = get_or_create_user(user_identifier)
    profile_hint = build_profile_hint(user_id)

    st.subheader("🧠 Profil İpucu")
    st.info(profile_hint)

    # ---------------- SESSION STATE INIT ----------------
    if "otel_listesi" not in st.session_state:
        st.session_state.otel_listesi = []
        st.session_state.used_places = False
        st.session_state.rest_map = {}

    # ---------------- FETCH ----------------
    if fetch_btn:
        session_id = create_session(user_id, session_token="")
        st.session_state.session_id = session_id

        oteller, used_places = get_hotels(
            sehir=sehir,
            max_fiyat=int(max_fiyat),
            min_puan=float(min_puan),
            profile_hint=profile_hint,
            top_k=int(top_k_hotels),
        )

        st.session_state.otel_listesi = oteller
        st.session_state.used_places = used_places

        rest_map = {}
        for o in oteller:
            recs = get_restaurants_for_hotel(
                otel=o,
                mutfak_turu=None,  # mutfak filtresi KALDIRILDI
                profile_hint=profile_hint,
                top_k=int(top_k_rest),
                used_places=used_places
            )
            rest_map[str(o["id"])] = recs

        st.session_state.rest_map = rest_map

    # ---------------- RESULTS ----------------
    otel_listesi = st.session_state.otel_listesi
    if not otel_listesi:
        st.warning("Sol menüden filtreleri seçip **Önerileri Getir** butonuna bas.")
        return

    metrics = compute_metrics(otel_listesi)

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 Çeşitlilik", f"{metrics['diversity']:.2f}")
    c2.metric("🔁 Tekrar oranı", f"{metrics['repetition']:.2f}")
    c3.metric("🗺️ Kaynak", "Google Places" if st.session_state.used_places else "CSV")

    # ---------------- HOTELS ----------------
    st.subheader("✅ Önerilen Oteller & Restoranlar")

    for idx, o in enumerate(otel_listesi, start=1):
        with st.expander(
            f"{idx}) {o['isim']} — {o.get('puan','-')} puan",
            expanded=(idx == 1)
        ):
            st.write(f"**Şehir:** {o.get('sehir','-')}")
            st.write(f"**Açıklama:** {o.get('konum_aciklama','')}")
            st.write(f"**Önerilme Gerekçesi:** {o.get('gerekce','-')}")

            recs = st.session_state.rest_map.get(str(o["id"]), [])
            if not recs:
                st.write("❌ Bu otel için restoran bulunamadı.")
            else:
                st.markdown("**🍽️ Yakın Restoranlar:**")
                for r in recs:
                    st.write(
                        f"- **{r['isim']}** | "
                        f"{r.get('puan','-')} puan | "
                        f"{r.get('konum_aciklama','')}"
                    )

    # ---------------- FEEDBACK ----------------
    st.divider()
    st.subheader("⭐ Geri Bildirim")

    otel_map = {o["isim"]: o for o in otel_listesi}

    chosen_otel_name = st.selectbox(
        "🏨 Değerlendirdiğin otel",
        list(otel_map.keys())
    )

    chosen_otel = otel_map[chosen_otel_name]
    chosen_otel_id = str(chosen_otel["id"])

    recs_for = st.session_state.rest_map.get(chosen_otel_id, [])
    rest_map = {r["isim"]: r for r in recs_for}

    chosen_rest_name = st.selectbox(
        "🍽️ Restoran (opsiyonel)",
        ["(Seçme)"] + list(rest_map.keys())
    )

    chosen_rest_id: Optional[str] = None
    if chosen_rest_name != "(Seçme)":
        chosen_rest_id = str(rest_map[chosen_rest_name]["id"])

    rating = st.slider(
        "Genel memnuniyet",
        min_value=1,
        max_value=5,
        value=4
    )

    comment = st.text_area(
        "Yorum (opsiyonel)",
        placeholder="Deneyiminle ilgili kısa bir yorum bırakabilirsin…",
        height=100
    )

    if st.button("✅ Feedback Kaydet", use_container_width=True):
        session_id = st.session_state.get("session_id")
        if not session_id:
            session_id = create_session(user_id, session_token="")
            st.session_state.session_id = session_id

        insert_feedback(
            user_id=user_id,
            session_id=int(session_id),
            otel_id=chosen_otel_id,
            restoran_id=chosen_rest_id,
            rating=int(rating),
            comment=comment
        )

        st.success("Feedback kaydedildi! Bir sonraki öneriler buna göre iyileşecek.")


if __name__ == "__main__":
    main()
