import asyncio
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Import from supermarkets package
from src.supermarkets import (
    coles_search_products,
    coles_extract_products,
    COLES_DEFAULT_STORE_ID,
    woolworths_search_products,
)

# ---- Transport Security (fixes 421 / Invalid Host header on Render) ----
# Allow your Render public hostname. This prevents DNS-rebinding protection
# from rejecting legitimate requests. See MCP Python SDK guidance. :contentReference[oaicite:1]{index=1}
RENDER_HOST = "coles-woolworths-mcp-server.onrender.com"

from mcp.server.transport_security import TransportSecuritySettings

RENDER_HOST = "coles-woolworths-mcp-server.onrender.com"

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        # allow both styles
        RENDER_HOST,
        f"{RENDER_HOST}:*",
        f"{RENDER_HOST}:443",

        # local dev
        "localhost",
        "localhost:*",
        "127.0.0.1",
        "127.0.0.1:*",
        "0.0.0.0",
        "0.0.0.0:*",
    ],
    allowed_origins=[
        f"https://{RENDER_HOST}",
        "http://localhost",
        "http://localhost:*",
        "http://127.0.0.1",
        "http://127.0.0.1:*",
    ],
)

# Initialize FastMCP server (do NOT hardcode host='localhost' for remote deployment)
mcp = FastMCP(
    "supermarket-mcp",
    transport_security=transport_security,
)


@mcp.tool()
async def get_coles_products(
    query: str,
    store_id: str = COLES_DEFAULT_STORE_ID,
    limit: int = 10,
) -> str:
    """Search for products at Coles.

    Args:
        query: The product search query.
        store_id: The Coles store ID to search in.
        limit: Maximum number of products to return.
    """
    try:
        search_results = await asyncio.to_thread(
            coles_search_products,
            query=query,
            store_id=store_id,
        )

        if search_results.get("status") == "error":
            return (
                f"Error fetching Coles products: {search_results.get('message', 'Unknown error')}\n"
                f"Response: {search_results.get('response_text', '')}"
            )

        products = await asyncio.to_thread(coles_extract_products, search_results)

        products = products[: min(limit, len(products))]

        if not products:
            return f"No products found at Coles for '{query}'."

        formatted_products = []
        for p in products:
            price_str = f"${p['price']:.2f}" if p.get("price") is not None else "N/A"
            unit_str = p.get("unit") or "N/A"
            formatted_products.append(
                f"Name: {p.get('name','')}\nPrice: {price_str}\nUnit: {unit_str}\nStore: {p.get('store','')}"
            )
        return "\n---\n".join(formatted_products)

    except Exception as e:
        return f"An unexpected error occurred in get_coles_products: {str(e)}"


@mcp.tool()
async def get_woolworths_products(query: str, limit: int = 10) -> str:
    """Search for products at Woolworths.

    Args:
        query: The product search query.
        limit: Maximum number of products to return.
    """
    try:
        search_results = await asyncio.to_thread(woolworths_search_products, query=query)

        if search_results.get("status") == "error":
            return (
                f"Error fetching Woolworths products: {search_results.get('message', 'Unknown error')}\n"
                f"Response: {search_results.get('response_text', '')}"
            )

        products = search_results.get("products", [])
        products = products[: min(limit, len(products))]

        if not products:
            return f"No products found at Woolworths for '{query}'."

        formatted_products = []
        for p in products:
            price_str = f"${p['price']:.2f}" if p.get("price") is not None else "N/A"
            unit_str = p.get("unit") or "N/A"
            formatted_products.append(
                f"Name: {p.get('name','')}\nPrice: {price_str}\nUnit: {unit_str}\nStore: {p.get('store','')}"
            )
        return "\n---\n".join(formatted_products)

    except Exception as e:
        return f"An unexpected error occurred in get_woolworths_products: {str(e)}"


if __name__ == "__main__":
    # Local dev convenience ONLY.
    # On Render you will start it via:
    #   fastmcp run main.py --transport http|sse --host 0.0.0.0 --port $PORT
    transport = os.getenv("FASTMCP_TRANSPORT", "http")
    host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    port = int(os.getenv("FASTMCP_PORT", "8000"))

    mcp.run(transport=transport, host=host, port=port)
