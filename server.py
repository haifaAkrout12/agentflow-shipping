"""
AgentFlow v0.3 — Shipping Service (MCP + REST)

Endpoints:
  GET  /health                          — health check
  GET  /shipment?orderNumber=ORD-1001   — REST endpoint (Salesforce Apex callout)
  POST /mcp                             — MCP Streamable HTTP (Agentforce Registry)
"""

from datetime import date, timedelta
import json

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount
import uvicorn
from mcp.server.mcpserver import MCPServer

# ---------------------------------------------------------------------------
# Mock shipment data
# ---------------------------------------------------------------------------
TODAY = date.today()

SHIPMENTS = {
    "ORD-1001": {
        "found": True, "orderNumber": "ORD-1001", "status": "In Transit",
        "carrier": "FedEx", "trackingNumber": "FX-987654321",
        "estimatedDelivery": str(TODAY + timedelta(days=3)),
    },
    "ORD-1002": {
        "found": True, "orderNumber": "ORD-1002", "status": "Processing",
        "carrier": "Not yet assigned", "trackingNumber": "Not yet assigned",
        "estimatedDelivery": "Not yet available",
    },
    "ORD-1003": {
        "found": True, "orderNumber": "ORD-1003", "status": "Delivered",
        "carrier": "UPS", "trackingNumber": "UPS-112233445",
        "estimatedDelivery": str(TODAY - timedelta(days=1)),
    },
}


def lookup_shipment(order_number: str) -> dict:
    return SHIPMENTS.get(order_number.upper(), SHIPMENTS.get(order_number)) or {
        "found": False,
        "orderNumber": order_number,
        "message": f"No shipment record found for order {order_number}.",
    }


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp_server = MCPServer(name="agentflow-shipping", version="0.3.0")


@mcp_server.tool(
    description=(
        "Returns shipment carrier, tracking number, status and estimated delivery "
        "for a given order number. Call this when the user asks about shipment or "
        "delivery details for a specific order."
    )
)
def get_shipment_status(orderNumber: str) -> str:
    """Look up shipment details by order number."""
    return json.dumps(lookup_shipment(orderNumber))


# ---------------------------------------------------------------------------
# REST route handlers
# ---------------------------------------------------------------------------
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "agentflow-shipping", "version": "0.3.0"})


async def shipment(request: Request) -> JSONResponse:
    order_number = request.query_params.get("orderNumber", "")
    if not order_number:
        return JSONResponse({"error": "orderNumber query parameter is required"}, status_code=400)
    return JSONResponse(lookup_shipment(order_number))


# ---------------------------------------------------------------------------
# Build the app: MCP app (with its lifespan) + REST routes mounted alongside
# ---------------------------------------------------------------------------
mcp_app = mcp_server.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
)

# Wrap the MCP app to also handle /health and /shipment
class CompositeApp:
    def __init__(self, mcp_asgi, rest_routes):
        self.mcp = mcp_asgi
        self.routes = {r.path: r.endpoint for r in rest_routes}

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path in self.routes:
                request = Request(scope, receive)
                response = await self.routes[path](request)
                await response(scope, receive, send)
                return
        await self.mcp(scope, receive, send)


rest_routes = [
    Route("/health", health),
    Route("/shipment", shipment),
]

app = CompositeApp(mcp_app, rest_routes)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=3000, log_level="info")
