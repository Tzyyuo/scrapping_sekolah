import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import csv
import re
import urllib3
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MissingSchoolDataAPI:
    def __init__(self):
        self.existing_data_file = 'data_smk_jawa_barat.csv'
        self.missing_data_file = 'data_smk_jabar_missing.csv'
        self.base_url = 'https://referensi.data.kemdikbud.go.id'
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        ]
        self.missing_schools_data = []
        
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
        """Load existing SMK data to get NPSN list"""
        if not os.path.exists(self.existing_data_file):
            print(f"[ERROR] File {self.existing_data_file} tidak ditemukan!")
            return set()
        
        try:
            df = pd.read_csv(self.existing_data_file)
            existing_npsn = set(df['npsn'].astype(str))
            print(f"[INFO] Loaded {len(existing_npsn)} existing NPSN from {self.existing_data_file}")
            return existing_npsn
        except Exception as e:
            print(f"[ERROR] Gagal load existing data: {e}")
            return set()
    
    def find_missing_schools(self):
        """Find missing SMK by comparing with expected total"""
        print("[INFO] Mencari SMK yang belum tersimpan...")
        
        existing_npsn = self.load_existing_data()
        print(f"[INFO] Total SMK yang sudah ada: {len(existing_npsn)}")
        print(f"[INFO] Target total SMK Jawa Barat: 2,927")
        print(f"[INFO] SMK yang masih missing: {2927 - len(existing_npsn)}")
        
        # Mulai dari halaman utama
        start_url = f"{self.base_url}/pendidikan/dikmen/000000/0/jf/15/all"
        
        print(f"[INFO] Mengakses halaman utama: {start_url}")
        
        try:
            # Gunakan session dengan SSL verification disabled
            response = self.session.get(start_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ambil daftar daerah
            daerah_links = soup.find_all('td', class_='link1')
            jabar_daerah = None
            
            for td in daerah_links:
                link = td.find('a')
                if link and 'dikmen' in link.get('href', ''):
                    daerah_name = link.get_text(strip=True)
                    daerah_url = link.get('href')
                    
                    # Cari Jawa Barat
                    if 'JAWA BARAT' in daerah_name.upper() or 'JABAR' in daerah_name.upper():
                        jabar_daerah = {
                            'nama': daerah_name,
                            'url': daerah_url
                        }
                        break
            
            if not jabar_daerah:
                print("[ERROR] Jawa Barat tidak ditemukan dalam daftar daerah!")
                return []
            
            print(f"[INFO] Ditemukan: {jabar_daerah['nama']}")
            
            # Scrape Jawa Barat untuk mencari yang missing
            missing_schools = self.scrape_daerah_missing(jabar_daerah, existing_npsn)
            self.missing_schools_data.extend(missing_schools)
            
            # Simpan data missing
            self.save_missing_to_csv()
            print(f"\n[INFO] SELESAI! Total SMK missing yang ditemukan: {len(self.missing_schools_data)}")
            return self.missing_schools_data
            
        except Exception as e:
            print(f"[ERROR] Gagal mengakses halaman utama: {e}")
            print("[INFO] Mencoba dengan Selenium...")
            
            try:
                driver = self.setup_selenium()
                driver.get(start_url)
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                driver.quit()
                
                # Ambil daftar daerah
                daerah_links = soup.find_all('td', class_='link1')
                jabar_daerah = None
                
                for td in daerah_links:
                    link = td.find('a')
                    if link and 'dikmen' in link.get('href', ''):
                        daerah_name = link.get_text(strip=True)
                        daerah_url = link.get('href')
                        
                        # Cari Jawa Barat
                        if 'JAWA BARAT' in daerah_name.upper() or 'JABAR' in daerah_name.upper():
                            jabar_daerah = {
                                'nama': daerah_name,
                                'url': daerah_url
                            }
                            break
                
                if not jabar_daerah:
                    print("[ERROR] Jawa Barat tidak ditemukan dalam daftar daerah!")
                    return []
                
                print(f"[INFO] Ditemukan: {jabar_daerah['nama']}")
                
                # Scrape Jawa Barat untuk mencari yang missing
                missing_schools = self.scrape_daerah_missing(jabar_daerah, existing_npsn)
                self.missing_schools_data.extend(missing_schools)
                
                # Simpan data missing
                self.save_missing_to_csv()
                print(f"\n[INFO] SELESAI! Total SMK missing yang ditemukan: {len(self.missing_schools_data)}")
                return self.missing_schools_data
                
            except Exception as e2:
                print(f"[ERROR] Selenium juga gagal: {e2}")
                return []
    
    def scrape_daerah_missing(self, daerah, existing_npsn):
        """Scrape semua kabupaten di satu daerah untuk mencari yang missing"""
        missing_schools = []
        
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
            
            print(f"  [INFO] Ditemukan {len(kabupaten_list)} kabupaten di {daerah['nama']}")
            
            for idx, kabupaten in enumerate(kabupaten_list, 1):
                print(f"    [{idx}/{len(kabupaten_list)}] Scraping kabupaten: {kabupaten['nama']}")
                missing_kabupaten = self.scrape_kabupaten_missing(kabupaten, daerah['nama'], existing_npsn)
                missing_schools.extend(missing_kabupaten)
                
                # Simpan progress setiap kabupaten
                self.save_missing_to_csv()
                print(f"      [PROGRESS] Total SMK missing: {len(self.missing_schools_data)}")
                
                time.sleep(random.uniform(1, 3))
        
        except Exception as e:
            print(f"[ERROR] Gagal scrape daerah {daerah['nama']}: {e}")
        
        return missing_schools
    
    def scrape_kabupaten_missing(self, kabupaten, nama_daerah, existing_npsn):
        """Scrape semua kecamatan di satu kabupaten untuk mencari yang missing"""
        missing_schools = []
        
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
            
            print(f"      [INFO] Ditemukan {len(kecamatan_list)} kecamatan di {kabupaten['nama']}")
            
            for idx, kecamatan in enumerate(kecamatan_list, 1):
                print(f"        [{idx}/{len(kecamatan_list)}] Scraping kecamatan: {kecamatan['nama']}")
                missing_kecamatan = self.scrape_kecamatan_missing(kecamatan, kabupaten['nama'], nama_daerah, existing_npsn)
                missing_schools.extend(missing_kecamatan)
                time.sleep(random.uniform(1, 2))
        
        except Exception as e:
            print(f"[ERROR] Gagal scrape kabupaten {kabupaten['nama']}: {e}")
        
        return missing_schools
    
    def scrape_kecamatan_missing(self, kecamatan, nama_kabupaten, nama_daerah, existing_npsn):
        """Scrape semua sekolah di satu kecamatan untuk mencari yang missing"""
        missing_schools = []
        
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
                        'url': sekolah_url
                    })
            
            print(f"          [INFO] Ditemukan {len(sekolah_list)} sekolah di {kecamatan['nama']}")
            
            for idx, sekolah in enumerate(sekolah_list, 1):
                # Cek apakah NPSN sudah ada di data existing
                if sekolah['npsn'] not in existing_npsn:
                    print(f"            [{idx}/{len(sekolah_list)}] Scraping sekolah NPSN: {sekolah['npsn']} (MISSING)")
                    school_data = self.scrape_sekolah_detail(sekolah, kecamatan['nama'], nama_kabupaten, nama_daerah)
                    if school_data:
                        # Hanya simpan jika SMK
                        if 'SMK' in school_data.get('bentuk_pendidikan', ''):
                            missing_schools.append(school_data)
                            print(f"              [SUCCESS] SMK MISSING: {school_data['nama_sekolah']}")
                        else:
                            print(f"              [SKIP] Bukan SMK: {school_data.get('bentuk_pendidikan', 'Unknown')}")
                else:
                    print(f"            [{idx}/{len(sekolah_list)}] Skip sekolah NPSN: {sekolah['npsn']} (SUDAH ADA)")
                time.sleep(random.uniform(0.5, 1.5))
        
        except Exception as e:
            print(f"[ERROR] Gagal scrape kecamatan {kecamatan['nama']}: {e}")
        
        return missing_schools
    
    def scrape_sekolah_detail(self, sekolah, nama_kecamatan, nama_kabupaten, nama_daerah):
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
                'kecamatan': nama_kecamatan,
                'kabupaten': nama_kabupaten,
                'provinsi': nama_daerah,
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
            # Cari semua tr dalam tabel
            for tr in soup.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 4:
                    # Cek apakah td kedua berisi nama field
                    if tds[1].get_text(strip=True) == field_name:
                        # Ambil data dari td keempat
                        data = tds[3].get_text(strip=True)
                        
                        # Jika ada link di dalamnya, ambil href
                        link = tds[3].find('a')
                        if link and field_name == 'Website':
                            data = link.get('href', data)
                        
                        return data if data else '-'
            
            return '-'
            
        except Exception as e:
            print(f"[ERROR] Gagal extract {field_name}: {e}")
            return '-'
    
    def extract_contact_data(self, soup, field_name):
        """Extract data dari tabel kontak berdasarkan struktur HTML yang spesifik"""
        try:
            # Cari semua tr dalam halaman
            for tr in soup.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 4:
                    # Cek apakah td kedua berisi nama field
                    field_text = tds[1].get_text(strip=True)
                    if field_text == field_name:
                        # Ambil data dari td keempat
                        data = tds[3].get_text(strip=True)
                        
                        # Khusus untuk Website, ambil href dari link
                        if field_name == 'Website':
                            link = tds[3].find('a')
                            if link:
                                data = link.get('href', data)
                        
                        # Khusus untuk Email, cari yang mengandung @
                        elif field_name == 'Email':
                            # Cari text yang mengandung @
                            email_text = tds[3].get_text(strip=True)
                            if '@' in email_text:
                                data = email_text
                            else:
                                # Coba cari di seluruh td
                                all_text = tds[3].get_text()
                                if '@' in all_text:
                                    # Extract email dari text
                                    import re
                                    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', all_text)
                                    if email_match:
                                        data = email_match.group()
                        
                        # Khusus untuk Telepon, cari yang mengandung angka
                        elif field_name == 'Telepon':
                            phone_text = tds[3].get_text(strip=True)
                            if phone_text and phone_text != '':
                                data = phone_text
                            else:
                                data = '-'
                        
                        # Khusus untuk Fax
                        elif field_name == 'Fax':
                            fax_text = tds[3].get_text(strip=True)
                            if fax_text and fax_text != '-':
                                data = fax_text
                            else:
                                data = '-'
                        
                        # Khusus untuk Operator
                        elif field_name == 'Operator':
                            operator_text = tds[3].get_text(strip=True)
                            if operator_text and operator_text.strip():
                                data = operator_text
                            else:
                                data = '-'
                        
                        print(f"              [DEBUG] Found {field_name}: '{data}'")
                        return data if data and data != '' else '-'
            
            print(f"              [DEBUG] Not found: {field_name}")
            return '-'
            
        except Exception as e:
            print(f"[ERROR] Gagal extract contact {field_name}: {e}")
            return '-'
    
    def save_missing_to_csv(self):
        """Simpan data missing ke CSV"""
        if not self.missing_schools_data:
            print("[WARNING] Tidak ada data missing untuk disimpan")
            return
        
        df = pd.DataFrame(self.missing_schools_data)
        
        # Reorder columns
        columns_order = [
            'npsn', 'nama_sekolah', 'alamat', 'kelurahan', 'kecamatan', 
            'kabupaten', 'provinsi', 'status', 'bentuk_pendidikan', 'jenjang',
            'telepon', 'fax', 'email', 'website', 'operator'
        ]
        
        # Filter columns yang ada
        existing_columns = [col for col in columns_order if col in df.columns]
        df = df[existing_columns]
        
        df.to_csv(self.missing_data_file, index=False, encoding='utf-8')
        print(f"[INFO] Data missing berhasil disimpan ke {self.missing_data_file}")
        print(f"[INFO] Total SMK missing: {len(self.missing_schools_data)}")
        
        # Tampilkan statistik
        print(f"[STATS] Kabupaten: {df['kabupaten'].nunique()}")
        print(f"[STATS] Kecamatan: {df['kecamatan'].nunique()}")
    
    def merge_with_existing_data(self):
        """Gabungkan data missing dengan data existing"""
        if not os.path.exists(self.missing_data_file):
            print(f"[ERROR] File {self.missing_data_file} tidak ditemukan!")
            return
        
        try:
            # Load existing data
            existing_df = pd.read_csv(self.existing_data_file)
            missing_df = pd.read_csv(self.missing_data_file)
            
            # Gabungkan data
            combined_df = pd.concat([existing_df, missing_df], ignore_index=True)
            
            # Simpan ke file baru
            output_file = 'data_smk_jawa_barat_complete.csv'
            combined_df.to_csv(output_file, index=False, encoding='utf-8')
            
            print(f"[INFO] Data berhasil digabungkan!")
            print(f"[INFO] Total SMK existing: {len(existing_df)}")
            print(f"[INFO] Total SMK missing: {len(missing_df)}")
            print(f"[INFO] Total SMK complete: {len(combined_df)}")
            print(f"[INFO] File output: {output_file}")
            
        except Exception as e:
            print(f"[ERROR] Gagal menggabungkan data: {e}")

# Fungsi untuk menjalankan scraping missing data
def run_missing_scraping():
    api = MissingSchoolDataAPI()
    
    print("=" * 60)
    print("SCRAPER DATA SMK MISSING JAWA BARAT")
    print("=" * 60)
    
    missing_schools = api.find_missing_schools()
    
    print("\n" + "=" * 60)
    print("HASIL SCRAPING MISSING DATA")
    print("=" * 60)
    print(f"Total SMK missing yang ditemukan: {len(missing_schools)}")
    print(f"File CSV missing: {api.missing_data_file}")
    
    # Gabungkan dengan data existing
    api.merge_with_existing_data()
    
    print("=" * 60)

if __name__ == "__main__":
    run_missing_scraping() 