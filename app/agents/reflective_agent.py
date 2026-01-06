from app.utils.db_utils import get_recent_feedback

def build_profile_hint(user_id: int) -> str:
    """
    Mock reflective agent:
    - son feedback'lerden eğilim çıkarır
    - bir sonraki önerilerde kullanılacak kısa 'profil ipucu' üretir
    """
    rows = get_recent_feedback(user_id, limit=20)
    if not rows:
        return "Profil: (feedback yok) Genel, dengeli öneri yap."

    ratings = [r[0] for r in rows]
    avg = sum(ratings) / len(ratings)
    likes = sum(1 for x in ratings if x >= 4)
    dislikes = sum(1 for x in ratings if x <= 2)

    hints = [
        f"Profil: son {len(ratings)} geri bildirim ortalaması={avg:.2f}",
        f"beğeni={likes}, beğenmeme={dislikes}",
    ]

    if avg >= 4.2:
        hints.append("yüksek puanlı seçenekleri önceliklendir")
    elif avg <= 3.0:
        hints.append("daha farklı/çeşitli seçenekler dene")
    else:
        hints.append("dengeyi koru (puan/fiyat)")

    # yorumlardan basit anahtar kelimeler
    comments = " ".join((r[1] or "") for r in rows).lower()
    if "sessiz" in comments:
        hints.append("tercih: sessiz/sakin ortam")
    if "aile" in comments:
        hints.append("tercih: aile dostu")
    if "ucuz" in comments or "bütçe" in comments or "butce" in comments:
        hints.append("tercih: bütçe hassasiyeti")

    return " | ".join(hints)
