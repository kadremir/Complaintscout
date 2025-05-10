import cloudscraper
from bs4 import BeautifulSoup
import csv
import time
import requests
import re

# Kullanıcıdan kelime ve sayfa sayısı al
anahtar_kelime = input("Hangi kelimeyi içeren şikayetler çekilsin? ").lower().strip()
sayfa_sayisi = int(input("Kaç sayfa taransın? "))

scraper = cloudscraper.create_scraper()

def analiz_yap(metin):
    """Ollama API'si kullanarak metin analizi yapar"""
    prompt = f"""Aşağıdaki şikayet metnini analiz ederek Türkçe olarak:
1. Duygu Durumu: (Olumlu, Olumsuz, Nötr, Öfke, Memnuniyet vb.)
2. Anahtar Kelimeler: (virgülle ayrılmış)
3. Çözüm Önerisi: (kısa ve öz)

Metin: {metin}

Lütfen cevabı tam olarak şu formatta ver:
Duygu Durumu: ...
Anahtar Kelimeler: ...
Çözüm Önerisi: ..."""

    try:
        response = requests.post(
            '[YOUR-API-URL(OLLAMA SERVE)]',
            json={
                'model': 'mistral',
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3}
            }
        )
        
        if response.status_code == 200:
            return response.json()['response']
        return None
        
    except Exception as e:
        print(f"Analiz hatası: {e}")
        return None

def analiz_ayir(metin):
    """Model çıktısını ayrıştırma"""
    duygu = re.search(r"Duygu Durumu:\s*(.+?)\n", metin)
    anahtar = re.search(r"Anahtar Kelimeler:\s*(.+?)\n", metin)
    cozum = re.search(r"Çözüm Önerisi:\s*(.+?)(\n|$)", metin)
    
    return (
        duygu.group(1).strip() if duygu else "Belirlenemedi",
        anahtar.group(1).strip() if anahtar else "Yok",
        cozum.group(1).strip() if cozum else "Yok"
    )

with open("sikayetler.csv", mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Başlık", "İçerik", "Duygu Durumu", "Anahtar Kelimeler", "Çözüm Önerisi"])

    for sayfa in range(1, sayfa_sayisi + 1):
        print(f"📄 Sayfa {sayfa} işleniyor...")
        url = f"https://www.sikayetvar.com/sikayetler?page={sayfa}"
        response = scraper.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.find_all(class_='complaint-title')

            for title in titles:
                başlık = title.get_text(strip=True)
                link_tag = title.find('a')

                if anahtar_kelime in başlık.lower() and link_tag and link_tag['href']:
                    detay_link = "https://www.sikayetvar.com" + link_tag['href']
                    detay_response = scraper.get(detay_link)

                    if detay_response.status_code == 200:
                        detay_soup = BeautifulSoup(detay_response.text, 'html.parser')
                        detay = detay_soup.find(class_='complaint-detail-description')
                        içerik = detay.get_text(strip=True) if detay else "İçerik bulunamadı."

                        # Yapay zeka analizi
                        analiz_sonucu = analiz_yap(içerik)
                        
                        if analiz_sonucu:
                            duygu, anahtar, cozum = analiz_ayir(analiz_sonucu)
                            writer.writerow([başlık, içerik, duygu, anahtar, cozum])
                            print(f"✅ Analiz edildi: {başlık}")
                        else:
                            writer.writerow([başlık, içerik, "Hata", "Hata", "Hata"])
                        
                        time.sleep(1.5)  # Ollama için bekleme süresi
        else:
            print(f"❌ Sayfa alınamadı: {url}")

        time.sleep(2.5)

print("\n✅ Analizler tamamlandı! sikayetler.csv dosyasını kontrol edin.")