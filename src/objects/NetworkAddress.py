class NetworkAddress:
    def __init__(self, network, address, addresses, operator = None, list_name = None):
        self.network = network
        self.address = address
        self.list_name = list_name
        self.operator = operator
        self.addresses = []
        