from selenium import webdriver
import time
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from selenium.webdriver.chrome.options import Options
import json

# Kullanıcıdan input al
pnr_no = input("Lütfen PNR numaranızı giriniz: ")
surname = input("Lütfen soyadınızı giriniz: ")
#PSZXBC
# Soyadı Türkçe karakter içeriyorsa encode et
surname_encoded = urllib.parse.quote(surname)

# URL'yi oluştur
url = f"https://web.flypgs.com/manage-booking?language=TR&pnrNo={pnr_no}&surname={surname_encoded}"

# Selenium ile tarayıcıyı aç (headless ve gerçekçi UA ile)
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # webdriver izini azalt
chrome_options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=chrome_options)
# Daha gerçekçi bir user-agent kullan
driver.execute_cdp_cmd("Network.setUserAgentOverride", {
    "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
})
# navigator.webdriver bayrağını gizle (bazı siteler headless'ı engeller)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

driver.get(url)
time.sleep(1.5)

# Sayfada yolcu sayısını bekle ve al
wait = WebDriverWait(driver, 30)
passenger_el = wait.until(
    EC.visibility_of_element_located((By.CSS_SELECTOR, ".passenger-count .count"))
)
passenger_text = passenger_el.text.strip()  # Örn: "2 Yetişkin"
match = re.search(r"\d+", passenger_text)
adult_count = int(match.group()) if match else None
print(f"Yolcu sayısı (yetişkin):{passenger_text}")

# Uçuş bilgilerini al (çoklu kart desteği)
# Tüm kartları bekle ve listele
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".flight-card-container")))
cards = driver.find_elements(By.CSS_SELECTOR, ".flight-card-container")
print(f"Bulunan uçuş kartı sayısı: {len(cards)}")

flights_data = []

for idx, container in enumerate(cards, start=1):
    # Her kartı ortaya kaydır
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
    time.sleep(0.8)

    def safe_text(by, selector_or_xpath):
        try:
            el = container.find_element(by, selector_or_xpath)
            return el.text.strip()
        except Exception:
            return ""

    # Öncelik: flight-number-wrapper içindeki .bold
    flight_number = safe_text(By.XPATH, ".//div[contains(@class,'flight-number-wrapper')]//div[contains(@class,'bold')]")
    # Tarih: date-wrapper içindeki .bold (ilk eşleşme)
    flight_date   = safe_text(By.XPATH, ".//div[contains(@class,'date-wrapper')]//div[contains(@class,'bold')]")

    # Kalkış bilgileri (return sınıfı OLMAYAN port-column)
    departure_port = safe_text(By.XPATH, ".//div[contains(@class,'port-column') and not(contains(@class,'return'))]//div[contains(@class,'port-name')]")
    departure_time = safe_text(By.XPATH, ".//div[contains(@class,'port-column') and not(contains(@class,'return'))]//div[contains(@class,'time')]")

    # Varış bilgileri (return sınıfı OLAN port-column)
    arrival_port   = safe_text(By.XPATH, ".//div[contains(@class,'port-column') and contains(@class,'return')]//div[contains(@class,'port-name')]")
    arrival_time   = safe_text(By.XPATH, ".//div[contains(@class,'port-column') and contains(@class,'return')]//div[contains(@class,'time')]")

    # Bazı temalarda flight_number üst header'da tekrar olabilir; boşsa alternatif arama dene
    if not flight_number:
        flight_number = safe_text(By.CSS_SELECTOR, ".flight-card-header .flight-number-wrapper .bold")

    print("-" * 50)
    print(f"Uçuş #{idx}")
    print(f"Uçuş No: {flight_number}")
    print(f"Uçuş Tarihi: {flight_date}")
    print(f"Nereden: {departure_port} - Saat: {departure_time}")
    print(f"Nereye: {arrival_port} - Saat: {arrival_time}")

    flight_info = {
        "ucus_no": flight_number,
        "ucus_tarihi": flight_date,
        "nereden": departure_port,
        "saat_nereden": departure_time,
        "nereye": arrival_port,
        "saat_nereye": arrival_time
    }
    flights_data.append(flight_info)

with open("flights_data.json", "w", encoding="utf-8") as f:
    json.dump(flights_data, f, ensure_ascii=False, indent=4)
print("JSON verisi kaydedildi: flights_data.json")
print(json.dumps(flights_data, ensure_ascii=False, indent=4))

try:
    driver.save_screenshot("debug_last_frame.png")
    with open("debug_last_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("[debug] Ekran görüntüsü ve HTML kaydedildi: debug_last_frame.png, debug_last_source.html")
except Exception as e:
    print(f"[debug] Kaydetme sırasında hata: {e}")

print("Sayfa açıldı ✅")
time.sleep(30)  # biraz bekle, sayfa görülsün