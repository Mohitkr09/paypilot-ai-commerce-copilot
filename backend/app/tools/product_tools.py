def search_products(
    query: str,
    max_price: float | None = None,
    category: str | None = None,
):
    """
    Search merchant catalog using semantic + structured filters.
    """