class OutOfStock(Exception):
    """A product has fewer units in stock than the order asks for."""


class UnknownProduct(Exception):
    """An order line names a product id that does not exist."""
