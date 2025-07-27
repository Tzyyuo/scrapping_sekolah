from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)[:30]

# Buka halaman utama Dikmen (SMA/SMK)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://referensi.data.kemdikbud.go.id/pendidikan/dikmen")
wait = WebDriverWait(driver, 20)

time.sleep(2)
# Klik link Jawa Barat
prov_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Jawa Barat')]")))
prov_link.click()
time.sleep(2)

# Klik link KAB. BANDUNG
kab_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'KAB. BANDUNG')]")))
kab_link.click()
time.sleep(2)

# Cari link kecamatan/kelurahan yang mengandung 'Baleendah'
kec_links = driver.find_elements(By.XPATH, "//table//a[contains(@href, '/pendidikan/dikmen/')]")
kec_names = [link.text.strip() for link in kec_links]
print(f"Daftar kecamatan ditemukan: {kec_names}")
kec_baleendah = None
for link in kec_links:
    if 'baleendah' in link.text.lower():
        kec_baleendah = link
        break
if not kec_baleendah:
    driver.save_screenshot("debug_kecamatan_baleendah.png")
    print("Tidak menemukan link kecamatan Baleendah. Cek debug_kecamatan_baleendah.png")
    print(f"Kecamatan yang tersedia: {kec_names}")
    driver.quit()
    exit()
kec_baleendah.click()
time.sleep(2)

# Setelah klik kecamatan, print semua <select> di halaman untuk debug
selects = driver.find_elements(By.TAG_NAME, 'select')
print(f"Jumlah <select> ditemukan: {len(selects)}")
for i, sel in enumerate(selects):
    print(f"Select ke-{i+1}: tag={sel.tag_name}, id={sel.get_attribute('id')}, name={sel.get_attribute('name')}, aria-controls={sel.get_attribute('aria-controls')}")
    options = sel.find_elements(By.TAG_NAME, 'option')
    for opt in options:
        print(f"  Option: {opt.text}")

# Setelah klik kecamatan, print isi kolom baris pertama sebelum set Show 100 entries
try:
    table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    rows = table.find_elements(By.TAG_NAME, "tr")[1:]
    if rows:
        first_cols = [td.text for td in rows[0].find_elements(By.TAG_NAME, "td")]
        print(f"[SEBELUM 100] Isi kolom baris pertama: {first_cols}")
except Exception as e:
    print(f"Gagal print isi kolom sebelum set 100: {e}")

# Setelah klik kecamatan, set Show entries ke 100 (jika ada)
try:
    select_entries = wait.until(EC.presence_of_element_located((By.NAME, 'table1_length')))
    select = Select(select_entries)
    select.select_by_visible_text('100')
    time.sleep(2)  # tunggu tabel reload
    print('Berhasil set Show entries ke 100')
except Exception as e:
    print(f'Gagal set Show entries ke 100: {e}')

# Setelah set 100, print isi kolom baris pertama lagi
try:
    table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    rows = table.find_elements(By.TAG_NAME, "tr")[1:]
    if rows:
        first_cols = [td.text for td in rows[0].find_elements(By.TAG_NAME, "td")]
        print(f"[SETELAH 100] Isi kolom baris pertama: {first_cols}")
except Exception as e:
    print(f"Gagal print isi kolom setelah set 100: {e}")

# Tunggu tabel sekolah muncul dan scraping semua halaman (pagination)
all_rows = []
table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # skip header
print(f"Jumlah baris tabel: {len(rows)}")
all_rows.extend(rows)
print(f"Total baris dari semua halaman: {len(all_rows)}")

# Ambil data utama dan link detail, ambil semua baris tanpa filter SMA/SMK
school_data = []
for row in all_rows:
    cols = row.find_elements(By.TAG_NAME, "td")
    if len(cols) >= 6:
        npsn = cols[1].text
        nama = cols[2].text
        alamat = cols[3].text
        kelurahan = cols[4].text
        status = cols[5].text
        # Link detail sekolah
        link = None
        try:
            link = cols[2].find_element(By.TAG_NAME, "a").get_attribute("href")
        except:
            pass
        school_data.append({
            "npsn": npsn,
            "nama": nama,
            "alamat": alamat,
            "kelurahan": kelurahan,
            "status": status,
            "detail_link": link
        })

# Scrape detail sekolah satu per satu (tab Kontak)
results = []
for i, school in enumerate(school_data):
    print(f"[{i+1}/{len(school_data)}] {school['nama']}")
    email = telp = website = ""
    if school["detail_link"]:
        try:
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[1])
            driver.get(school["detail_link"])
            time.sleep(2)
            # Ambil data tab Kontak langsung dari HTML tanpa klik tab
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            kontak_div = soup.find('div', {'id': lambda x: x and 'kontak' in x, 'class': lambda c: c and 'tab-pane' in c})
            if kontak_div:
                kontak_table = kontak_div.find('table')
                if kontak_table:
                    kontak_rows = kontak_table.find_all('tr')
                    print(f"  [NO-CLICK] Jumlah baris kontak: {len(kontak_rows)}")
                    for drow in kontak_rows:
                        tds = drow.find_all('td')
                        if len(tds) == 2:
                            label = tds[0].get_text(strip=True).lower()
                            value = tds[1].get_text(strip=True)
                            print(f"    {label}: {value}")
                            if "email" in label:
                                email = value
                            elif "telp" in label or "telepon" in label:
                                telp = value
                            elif "website" in label:
                                website = value
                else:
                    print(f"  [NO-CLICK] Tidak menemukan table di tab Kontak")
            else:
                print(f"  [NO-CLICK] Tidak menemukan div tab Kontak")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            print(f"  Gagal ambil detail: {e}")
            try:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except:
                pass
    results.append({
        "npsn": school["npsn"],
        "nama": school["nama"],
        "alamat": school["alamat"],
        "kelurahan": school["kelurahan"],
        "status": school["status"],
        "email": email,
        "telp": telp,
        "website": website
    })

pd.DataFrame(results).to_csv("daftar_sma_smk_baleendah_detail.csv", index=False)
print("Selesai: daftar_sma_smk_baleendah_detail.csv")
driver.quit() 