import unicodedata

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()

    # Türkçe i/İ özel durumu (genel normalize öncesi güvenli dönüşüm)
    s = s.replace("İ", "I").replace("ı", "i")

    # Unicode normalize + aksanları ayır
    s = unicodedata.normalize("NFKD", s)

    # Aksan işaretlerini kaldır
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Boşlukları standardize et
    s = " ".join(s.split())

    # En sağlam küçük harf dönüşümü
    return s.casefold()
