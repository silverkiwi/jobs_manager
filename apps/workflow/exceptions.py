class XeroValidationError(Exception):
    def __init__(self, missing_fields, entity, xero_id):
        self.missing_fields = missing_fields
        self.entity = entity
        self.xero_id = xero_id
        message = f"Missing fields {missing_fields} for {entity} {xero_id}"
        super().__init__(message)


class XeroProcessingError(Exception):
    pass
