"""
AgentFlow v0.3 — Shipping MCP + REST Server (FastAPI)

Endpoints:
  GET  /shipment?orderNumber=ORD-1001   — REST endpoint (used by Salesforce Named Credential)
  GET  /health                          — health check
  GET  /mcp                             — MCP SSE endpoint (for native MCP clients)
"""

from datetime import date, timedelta
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn

# ---------------------------------------------------------------------------
# Mock shipment data
# ---------------------------------------------------------------------------
TODAY = date.today()

SHIPMENTS = {
    "ORD-1001": {
        "found": True,
        "orderNumber": "ORD-1001",
        "status": "In Transit",
        "carrier": "FedEx",
        "trackingNumber": "FX-987654321",
        "estimatedDelivery": str(TODAY + timedelta(days=3)),
    },
    "ORD-1002": {
        "found": True,
        "orderNumber": "ORD-1002",
        "status": "Processing",
        "carrier": "Not yet assigned",
        "trackingNumber": "Not yet assigned",
        "estimatedDelivery": "Not yet available",
    },
    "ORD-1003": {
        "found": True,
        "orderNumber": "ORD-1003",
        "status": "Delivered",
        "carrier": "UPS",
        "trackingNumber": "UPS-112233445",
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
# FastAPI app (REST + health)
# ---------------------------------------------------------------------------
app = FastAPI(title="AgentFlow Shipping Service", version="0.3.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "agentflow-shipping", "version": "0.3.0"}


@app.get("/shipment")
def shipment_status(orderNumber: str = Query(..., description="Order number e.g. ORD-1001")):
    """
    REST endpoint for Salesforce Named Credential + Apex callout.
    Returns shipment details for the given order number.
    """
    return JSONResponse(lookup_shipment(orderNumber))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
