import ros_api
from src.utils.utils import Tools

class Mikrotik():
    def __init__(self, ip, user, password, port = 8728):
        print('[LOGIN] - Efetuando login\n')
        try:
            self.connection = ros_api.Api(ip, user=user, password=password, port=port, timeout=100)

            print('[LOGIN] - Login efetuado com sucesso.\n')
        except Exception as ex:
            print('[ERRO] - Não foi possivel efetuar o login no equipamento.')
            print('[ERRO] - Mensagem de erro: ', ex)
            exit()

    #Pegar todos os ips em conexão no momento.
    def get_connection_address(self) -> []:
        return self.exeCom('/ip/firewall/connection/print')

    #Pegar todos os ips já registrados nas listas.
    def get_address_list(self, list_name : list)-> []:
        results = []
        for name in list_name:

            search = self.exeCom(f"/ip/firewall/address-list/print ?list={name}")
            results.extend(search)

        return results

    #Adicionar um ip em uma lista especifica.
    def add_ip_in_address_list(self, address : str, list_name: str) -> any:
        return self.exeCom('/ip/firewall/address-list/add =address=' + address + ' =list=' + list_name + '')

    #Remover um ip de uma lista especifica
    def remove_ip_in_address_list(self, id : str) -> any:
        return self.exeCom('/ip/firewall/address-list/remove =numbers=' + id)

    #Executar um ping com ip de destino e origem.
    def ping(self, address : str, src: str) -> []:
        return self.exeCom('/ping \n =address=' + address +' \n =src-address=' + str(src) +' =count=1')
    
    def get_address_list_by_address(self, address : str) -> []:
        return self.exeCom(f"/ip/firewall/address-list/print ?address={address}")
    

    #Função para executar os comandos do mikrotik.
    def exeCom(self, command: str) -> []:
        return self.connection.talk(command)