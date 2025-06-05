from apps.purchasing.models import Stock as _Stock


class Stock(_Stock):
    class Meta:
        proxy = True
