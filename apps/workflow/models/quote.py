from apps.accounting.models import Quote as _Quote


class Quote(_Quote):
    class Meta:
        proxy = True
