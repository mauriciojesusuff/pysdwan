import requests
import tarfile
import os
import shutil
import hashlib
from dotenv import load_dotenv
import logging

# Carregar as variáveis do arquivo .env para o ambiente
load_dotenv()

# Configurações
license_key = os.getenv('GEOIP2_KEY')
if not license_key:
    raise ValueError("Chave de licença 'GEOIP2_KEY' não encontrada nas variáveis de ambiente.")

base_url = "https://download.maxmind.com/app/geoip_download"
edition_id = "GeoLite2-ASN"
download_url = f"{base_url}?edition_id={edition_id}&license_key={license_key}&suffix=tar.gz"
md5_url = f"{base_url}?edition_id={edition_id}&license_key={license_key}&suffix=tar.gz.md5"
download_path = 'GeoLite2-ASN.tar.gz'
mmdb_filename = 'GeoLite2-ASN.mmdb'
destination_path = 'database/geoip2/GeoLite2-ASN.mmdb'

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_database(url, output_path):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        logging.info(f"Download concluído: {output_path}")
    except requests.RequestException as e:
        logging.error(f"Falha no download do banco de dados: {e}")
        raise

def extract_mmdb(tar_path, output_filename):
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            member = next((m for m in tar.getmembers() if m.name.endswith('.mmdb')), None)
            if member:
                tar.extract(member, path='.')
                extracted_path = os.path.join('.', member.name)
                shutil.move(extracted_path, output_filename)
                logging.info(f"Arquivo .mmdb movido para: {output_filename}")
                # Remover diretório vazio se necessário
                extracted_dir = os.path.dirname(extracted_path)
                if os.path.isdir(extracted_dir) and not os.listdir(extracted_dir):
                    os.rmdir(extracted_dir)
            else:
                logging.error("Arquivo .mmdb não encontrado no arquivo tar.")
                raise FileNotFoundError("Arquivo .mmdb não encontrado no arquivo tar.")
    except Exception as e:
        logging.error(f"Erro durante a extração: {e}")
        raise

def replace_old_database(new_db_path, destination_path):
    try:
        if os.path.exists(destination_path):
            os.remove(destination_path)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.move(new_db_path, destination_path)
        logging.info(f"Banco de dados atualizado em: {destination_path}")
    except Exception as e:
        logging.error(f"Erro ao substituir o banco de dados: {e}")
        raise

def get_remote_md5(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        remote_md5 = response.text.strip()
        return remote_md5
    except requests.RequestException as e:
        logging.error(f"Falha ao obter o checksum remoto: {e}")
        return None

def calculate_local_md5(file_path):
    if not os.path.exists(file_path):
        return None
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def main():
    # Obter o checksum remoto
    remote_md5 = get_remote_md5(md5_url)
    if remote_md5 is None:
        logging.error("Não foi possível obter o checksum remoto. Abortando atualização.")
        return

    # Calcular o checksum local
    local_md5 = calculate_local_md5(destination_path)

    if local_md5 == remote_md5:
        logging.info("O banco de dados local já está atualizado. Nenhum download necessário.")
    else:
        logging.info("O banco de dados será atualizado. Iniciando o download...")
        try:
            download_database(download_url, download_path)
            extract_mmdb(download_path, mmdb_filename)
            replace_old_database(mmdb_filename, destination_path)
            logging.info("Atualização concluída com sucesso.")
        except Exception as e:
            logging.error(f"Erro durante o processo de atualização: {e}")
        finally:
            # Limpa o arquivo tar.gz
            if os.path.exists(download_path):
                os.remove(download_path)

if __name__ == "__main__":
    main()
