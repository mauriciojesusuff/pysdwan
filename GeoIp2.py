import requests
import tarfile
import os
import shutil
import hashlib

from dotenv import load_dotenv
import os

# Configurações
license_key = os.getenv('GEOIP2_KEY')
base_url = "https://download.maxmind.com/app/geoip_download"
edition_id = "GeoLite2-ASN"
download_url = f"{base_url}?edition_id={edition_id}&license_key={license_key}&suffix=tar.gz"
md5_url = f"{base_url}?edition_id={edition_id}&license_key={license_key}&suffix=tar.gz.md5"
download_path = 'GeoLite2-ASN.tar.gz'
mmdb_filename = 'GeoLite2-ASN.mmdb'
destination_path = 'database/geoip2/GeoLite2-ASN.mmdb'

def download_database(url, output_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"Download concluído: {output_path}")
    else:
        print(f"Falha no download. Código de status: {response.status_code}")

def extract_mmdb(tar_path, output_filename):
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            member = None
            for tarinfo in tar.getmembers():
                if tarinfo.name.endswith('.mmdb'):
                    member = tarinfo
                    break
            if member is not None:
                # Extraia o arquivo .mmdb para o diretório atual
                tar.extract(member, path='.')
                # Obtenha o caminho completo do arquivo extraído
                extracted_path = os.path.join('.', member.name)
                print(f"Arquivo extraído em: {extracted_path}")
                # Mova o arquivo extraído para o nome de saída desejado
                shutil.move(extracted_path, output_filename)
                print(f"Arquivo .mmdb movido para: {output_filename}")
                # Remover diretório vazio se necessário
                extracted_dir = os.path.dirname(extracted_path)
                if os.path.isdir(extracted_dir) and not os.listdir(extracted_dir):
                    os.rmdir(extracted_dir)
            else:
                print("Arquivo .mmdb não encontrado no arquivo tar.")
    except Exception as e:
        print(f"Erro durante a extração: {e}")

def replace_old_database(new_db_path, destination_path):
    try:
        if os.path.exists(destination_path):
            os.remove(destination_path)

        # Certifique-se de que o diretório de destino existe
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.move(new_db_path, destination_path)
        print(f"Banco de dados atualizado em: {destination_path}")
    except Exception as e:
        print(f"Erro ao substituir o banco de dados: {e}")

def get_remote_md5(url):
    response = requests.get(url)
    if response.status_code == 200:
        remote_md5 = response.text.strip()
        return remote_md5
    else:
        print(f"Falha ao obter o checksum remoto. Código de status: {response.status_code}")
        return None

def calculate_local_md5(file_path):
    if not os.path.exists(file_path):
        return None
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Obter o checksum remoto
remote_md5 = get_remote_md5(md5_url)

# Calcular o checksum local
local_md5 = calculate_local_md5(destination_path)

if remote_md5 == local_md5:
    print("O banco de dados local já está atualizado. Nenhum download necessário.")
else:
    print("O banco de dados foi atualizado. Iniciando o download...")
    # Executa as funções de download e atualização
    download_database(download_url, download_path)
    extract_mmdb(download_path, mmdb_filename)
    replace_old_database(mmdb_filename, destination_path)
    # Limpa o arquivo tar.gz (descomente após testar)
    os.remove(download_path)
