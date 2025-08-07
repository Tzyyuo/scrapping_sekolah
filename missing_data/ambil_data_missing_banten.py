import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MissingDataFinder:
    def __init__(self):
        self.existing_file = 'data_smk_banten.csv'
        self.missing_file = 'data_smk_banten_missing.csv'
        self.complete_file = 'data_smk_banten_complete.csv'
        self.base_url = 'https://referensi.data.kemdikbud.go.id'
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        ]
        self.missing_schools = []
        
        # Setup session dengan SSL verification disabled
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument(f"user-agent={random.choice(self.user_agents)}")
        return webdriver.Chrome(options=chrome_options)
    
    def load_existing_data(self):
        """Load data yang sudah ada"""
        try:
            df = pd.read_csv(self.existing_file)
            print(f"[INFO] Data existing: {len(df)} SMK")
            return df
        except FileNotFoundError:
            print(f"[ERROR] File {self.existing_file} tidak ditemukan!")
            return pd.DataFrame()
    
    def get_all_schools_from_website(self):
        """Ambil semua SMK dari website untuk Banten"""
        print("[INFO] Mengambil semua SMK dari website...")
        
        all_schools = []
        start_url = f"{self.base_url}/pendidikan/dikmen/000000/0/jf/15/all"
        
        try:
            response = self.session.get(start_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Cari BANTEN
            daerah_links = soup.find_all('td', class_='link1')
            banten_daerah = None

            for td in daerah_links:
                link = td.find('a')
                if link and 'dikmen' in link.get('href', ''):
                    daerah_name = link.get_text(strip=True)
                    daerah_url = link.get('href')

                    if 'BANTEN' in daerah_name.upper():
                        banten_daerah = {
                            'nama': daerah_name,
                            'url': daerah_url
                        }
                        break

            if not banten_daerah:
                print("[ERROR] BANTEN tidak ditemukan!")
                return []

            print(f"[INFO] Ditemukan: {banten_daerah['nama']}")

            # Scrape semua kabupaten
            all_schools = self.scrape_all_kabupaten(banten_daerah)

        except Exception as e:
            print(f"[ERROR] Gagal mengakses website: {e}")
            print("[INFO] Mencoba dengan Selenium...")
            
            try:
                driver = self.setup_selenium()
                driver.get(start_url)
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                driver.quit()

                # Cari BANTEN
                daerah_links = soup.find_all('td', class_='link1')
                banten_daerah = None

                for td in daerah_links:
                    link = td.find('a')
                    if link and 'dikmen' in link.get('href', ''):
                        daerah_name = link.get_text(strip=True)
                        daerah_url = link.get('href')

                        if 'BANTEN' in daerah_name.upper():
                            banten_daerah = {
                                'nama': daerah_name,
                                'url': daerah_url
                            }
                            break

                if not banten_daerah:
                    print("[ERROR] BANTEN tidak ditemukan!")
                    return []

                print(f"[INFO] Ditemukan: {banten_daerah['nama']}")

                # Scrape semua kabupaten
                all_schools = self.scrape_all_kabupaten(banten_daerah)

            except Exception as e2:
                print(f"[ERROR] Selenium juga gagal: {e2}")
                return []
        
        return all_schools
    
    def scrape_all_kabupaten(self, daerah):
        """Scrape semua kabupaten untuk mendapatkan daftar sekolah"""
        all_schools = []
        
        try:
            response = self.session.get(daerah['url'], timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ambil daftar kabupaten
            kabupaten_links = soup.find_all('td', class_='link1')
            kabupaten_list = []
            
            for td in kabupaten_links:
                link = td.find('a')
                if link and 'dikmen' in link.get('href', ''):
                    kabupaten_name = link.get_text(strip=True)
                    kabupaten_url = link.get('href')
                    kabupaten_list.append({
                        'nama': kabupaten_name,
                        'url': kabupaten_url
                    })
            
            print(f"[INFO] Ditemukan {len(kabupaten_list)} kabupaten")
            
            for idx, kabupaten in enumerate(kabupaten_list, 1):
                print(f"  [{idx}/{len(kabupaten_list)}] Scraping kabupaten: {kabupaten['nama']}")
                schools_kabupaten = self.scrape_all_kecamatan(kabupaten, daerah['nama'])
                all_schools.extend(schools_kabupaten)
                time.sleep(random.uniform(1, 2))
        
        except Exception as e:
            print(f"[ERROR] Gagal scrape kabupaten: {e}")
        
        return all_schools
    
    def scrape_all_kecamatan(self, kabupaten, nama_daerah):
        """Scrape semua kecamatan untuk mendapatkan daftar sekolah"""
        all_schools = []
        
        try:
            response = self.session.get(kabupaten['url'], timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ambil daftar kecamatan
            kecamatan_links = soup.find_all('td', class_='link1')
            kecamatan_list = []
            
            for td in kecamatan_links:
                link = td.find('a')
                if link and 'dikmen' in link.get('href', ''):
                    kecamatan_name = link.get_text(strip=True)
                    kecamatan_url = link.get('href')
                    kecamatan_list.append({
                        'nama': kecamatan_name,
                        'url': kecamatan_url
                    })
            
            print(f"    [INFO] Ditemukan {len(kecamatan_list)} kecamatan di {kabupaten['nama']}")
            
            for idx, kecamatan in enumerate(kecamatan_list, 1):
                print(f"      [{idx}/{len(kecamatan_list)}] Scraping kecamatan: {kecamatan['nama']}")
                schools_kecamatan = self.scrape_all_sekolah(kecamatan, kabupaten['nama'], nama_daerah)
                all_schools.extend(schools_kecamatan)
                time.sleep(random.uniform(0.5, 1))
        
        except Exception as e:
            print(f"[ERROR] Gagal scrape kecamatan {kabupaten['nama']}: {e}")
        
        return all_schools
    
    def scrape_all_sekolah(self, kecamatan, nama_kabupaten, nama_daerah):
        """Scrape semua sekolah di satu kecamatan"""
        all_schools = []
        
        try:
            response = self.session.get(kecamatan['url'], timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ambil daftar sekolah (NPSN)
            sekolah_links = soup.find_all('td', class_='link1')
            sekolah_list = []
            
            for td in sekolah_links:
                link = td.find('a')
                if link and 'npsn' in link.get('href', ''):
                    npsn = link.get_text(strip=True)
                    sekolah_url = link.get('href')
                    sekolah_list.append({
                        'npsn': npsn,
                        'url': sekolah_url,
                        'kecamatan': kecamatan['nama'],
                        'kabupaten': nama_kabupaten,
                        'provinsi': nama_daerah
                    })
            
            print(f"        [INFO] Ditemukan {len(sekolah_list)} sekolah di {kecamatan['nama']}")
            all_schools.extend(sekolah_list)
        
        except Exception as e:
            print(f"[ERROR] Gagal scrape kecamatan {kecamatan['nama']}: {e}")
        
        return all_schools
    
    def find_missing_schools(self):
        """Temukan sekolah yang hilang"""
        print("[INFO] Mencari data SMK yang hilang...")
        
        # Load data existing
        existing_df = self.load_existing_data()
        if existing_df.empty:
            return
        
        existing_npsn = set(existing_df['npsn'].astype(str))
        print(f"[INFO] NPSN existing: {len(existing_npsn)}")
        
        # Ambil semua sekolah dari website
        all_schools = self.get_all_schools_from_website()
        print(f"[INFO] Total sekolah dari website: {len(all_schools)}")
        
        # Cari yang hilang
        missing_schools = []
        for sekolah in all_schools:
            if sekolah['npsn'] not in existing_npsn:
                missing_schools.append(sekolah)
        
        print(f"[INFO] SMK yang hilang: {len(missing_schools)}")
        
        if missing_schools:
            print("[INFO] Daftar NPSN yang hilang:")
            for sekolah in missing_schools:
                print(f"  - {sekolah['npsn']} ({sekolah['kecamatan']}, {sekolah['kabupaten']})")
        
        return missing_schools
    
    def scrape_missing_schools(self, missing_schools):
        """Scrape detail sekolah yang hilang"""
        if not missing_schools:
            print("[INFO] Tidak ada sekolah yang hilang")
            return []
        
        print(f"[INFO] Mulai scraping {len(missing_schools)} SMK yang hilang...")
        
        scraped_schools = []
        
        for idx, sekolah in enumerate(missing_schools, 1):
            print(f"  [{idx}/{len(missing_schools)}] Scraping NPSN: {sekolah['npsn']}")
            
            try:
                school_data = self.scrape_sekolah_detail(sekolah)
                if school_data:
                    # Hanya simpan jika SMK
                    if 'SMK' in school_data.get('bentuk_pendidikan', ''):
                        scraped_schools.append(school_data)
                        print(f"    [SUCCESS] SMK: {school_data['nama_sekolah']}")
                    else:
                        print(f"    [SKIP] Bukan SMK: {school_data.get('bentuk_pendidikan', 'Unknown')}")
                time.sleep(random.uniform(0.5, 1.5))
            
            except Exception as e:
                print(f"    [ERROR] Gagal scrape NPSN {sekolah['npsn']}: {e}")
        
        return scraped_schools
    
    def scrape_sekolah_detail(self, sekolah):
        """Scrape detail sekolah dari halaman detail sekolah"""
        try:
            response = self.session.get(sekolah['url'], timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data dari tabel identitas satuan
            data = {
                'npsn': sekolah['npsn'],
                'nama_sekolah': self.extract_detail_data(soup, 'Nama'),
                'alamat': self.extract_detail_data(soup, 'Alamat'),
                'kelurahan': self.extract_detail_data(soup, 'Desa/Kelurahan'),
                'kecamatan': sekolah['kecamatan'],
                'kabupaten': sekolah['kabupaten'],
                'provinsi': sekolah['provinsi'],
                'status': self.extract_detail_data(soup, 'Status Sekolah'),
                'bentuk_pendidikan': self.extract_detail_data(soup, 'Bentuk Pendidikan'),
                'jenjang': self.extract_detail_data(soup, 'Jenjang Pendidikan'),
                'telepon': self.extract_contact_data(soup, 'Telepon'),
                'fax': self.extract_contact_data(soup, 'Fax'),
                'email': self.extract_contact_data(soup, 'Email'),
                'website': self.extract_contact_data(soup, 'Website'),
                'operator': self.extract_contact_data(soup, 'Operator')
            }
            
            return data
            
        except Exception as e:
            print(f"[ERROR] Gagal scrape detail sekolah NPSN {sekolah['npsn']}: {e}")
            return None
    
    def extract_detail_data(self, soup, field_name):
        """Extract data dari tabel identitas satuan"""
        try:
            for tr in soup.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 4:
                    if tds[1].get_text(strip=True) == field_name:
                        data = tds[3].get_text(strip=True)
                        link = tds[3].find('a')
                        if link and field_name == 'Website':
                            data = link.get('href', data)
                        return data if data else '-'
            return '-'
        except Exception as e:
            print(f"[ERROR] Gagal extract {field_name}: {e}")
            return '-'
    
    def extract_contact_data(self, soup, field_name):
        """Extract data dari tabel kontak"""
        try:
            for tr in soup.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 4:
                    field_text = tds[1].get_text(strip=True)
                    if field_text == field_name:
                        data = tds[3].get_text(strip=True)
                        
                        if field_name == 'Website':
                            link = tds[3].find('a')
                            if link:
                                data = link.get('href', data)
                        elif field_name == 'Email':
                            email_text = tds[3].get_text(strip=True)
                            if '@' in email_text:
                                data = email_text
                            else:
                                all_text = tds[3].get_text()
                                if '@' in all_text:
                                    import re
                                    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', all_text)
                                    if email_match:
                                        data = email_match.group()
                        
                        return data if data and data != '' else '-'
            return '-'
        except Exception as e:
            print(f"[ERROR] Gagal extract contact {field_name}: {e}")
            return '-'
    
    def save_missing_data(self, missing_schools):
        """Simpan data yang hilang ke CSV"""
        if not missing_schools:
            print("[WARNING] Tidak ada data untuk disimpan")
            return
        
        df = pd.DataFrame(missing_schools)
        
        # Reorder columns
        columns_order = [
            'npsn', 'nama_sekolah', 'alamat', 'kelurahan', 'kecamatan', 
            'kabupaten', 'provinsi', 'status', 'bentuk_pendidikan', 'jenjang',
            'telepon', 'fax', 'email', 'website', 'operator'
        ]
        
        # Filter columns yang ada
        existing_columns = [col for col in columns_order if col in df.columns]
        df = df[existing_columns]
        
        df.to_csv(self.missing_file, index=False, encoding='utf-8')
        print(f"[INFO] Data missing berhasil disimpan ke {self.missing_file}")
        print(f"[INFO] Total SMK missing: {len(missing_schools)}")
    
    def merge_data(self):
        """Gabungkan data existing dengan data missing"""
        try:
            existing_df = pd.read_csv(self.existing_file)
            missing_df = pd.read_csv(self.missing_file)
            
            # Gabungkan
            complete_df = pd.concat([existing_df, missing_df], ignore_index=True)
            
            # Simpan ke file lengkap
            complete_df.to_csv(self.complete_file, index=False, encoding='utf-8')
            
            print(f"[INFO] Data berhasil digabungkan!")
            print(f"[INFO] Data existing: {len(existing_df)} SMK")
            print(f"[INFO] Data missing: {len(missing_df)} SMK")
            print(f"[INFO] Total lengkap: {len(complete_df)} SMK")
            print(f"[INFO] File lengkap: {self.complete_file}")
            
        except Exception as e:
            print(f"[ERROR] Gagal menggabungkan data: {e}")

# Fungsi untuk menjalankan pencarian data missing
def run_find_missing():
    finder = MissingDataFinder()
    
    print("=" * 60)
    print("PENCARIAN DATA SMK BANTEN YANG HILANG")
    print("=" * 60)
    
    # Cari sekolah yang hilang
    missing_schools = finder.find_missing_schools()
    
    if missing_schools:
        print(f"\n[INFO] Ditemukan {len(missing_schools)} SMK yang hilang")
        
        # Scrape sekolah yang hilang
        scraped_schools = finder.scrape_missing_schools(missing_schools)
        
        if scraped_schools:
            # Simpan data missing
            finder.save_missing_data(scraped_schools)
            
            # Gabungkan data
            finder.merge_data()
            
            print("\n" + "=" * 60)
            print("HASIL PENCARIAN")
            print("=" * 60)
            print(f"Total SMK missing berhasil di-scrape: {len(scraped_schools)}")
            print(f"File missing: {finder.missing_file}")
            print(f"File lengkap: {finder.complete_file}")
            print("=" * 60)
        else:
            print("[WARNING] Tidak ada SMK missing yang berhasil di-scrape")
    else:
        print("[INFO] Tidak ada SMK yang hilang!")

if __name__ == "__main__":
    run_find_missing() 