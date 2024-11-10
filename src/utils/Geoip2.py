import geoip2.database

LOCAL_PATH = '././database/geoip2/GeoLite2-ASN.mmdb'

class Geoip2:


    def getIpBlock(self, ip) -> None|str:

        # Consulte o IP
        try:
            response = self.reader.asn(ip)
            # Obtenha o bloco de IP
            network = response.network
            return str(network)
        
        except geoip2.errors.AddressNotFoundError as err:
            print(err)
            return None

    def close(self):
        # Feche o banco de dados
        self.reader.close()

    def open(self):
        self.reader = geoip2.database.Reader(LOCAL_PATH)
