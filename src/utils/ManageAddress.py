import ipaddress

class ManageAddress:
    def __init__(self):
        self.block_addresses = []

    def check_addres(self, address):
        address = ipaddress.IPv4Address(address)

        for block in self.block_addresses:
            