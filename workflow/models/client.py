from client.models import Client as BaseClient, Supplier as BaseSupplier


class Client(BaseClient):
    class Meta:
        proxy = True

class Supplier(BaseSupplier):

    class Meta:
        proxy = True
