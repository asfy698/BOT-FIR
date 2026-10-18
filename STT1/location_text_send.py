try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

"""Send a Botfir text update, then this device's approximate location via WhatsApp.

Install once:
    pip install twilio requests
"""

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from twilio.rest import Client


# Twilio WhatsApp configuration, intentionally kept in this file as requested.
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
FROM_WHATSAPP = "whatsapp:+14155238886"

# The original files had different recipients, so both are preserved.
TEXT_UPDATE_TO = "whatsapp:+919488000327"
LOCATION_UPDATE_TO = "whatsapp:+919488000327"

TEXT_UPDATE = "the visually impaired people location update"
MALAYSIA_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def build_text_update() -> str:
    """Build the first WhatsApp message with Malaysia's local timestamp."""
    sent_at = datetime.now(MALAYSIA_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    return f"{TEXT_UPDATE}\n\nSent: {sent_at}"


def get_current_location() -> dict[str, str]:
    """Return approximate device location from its public IP address."""
    try:
        response = requests.get("https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not determine location: {exc}") from exc

    latitude, _, longitude = data.get("loc", ",").partition(",")
    return {
        "ip": data.get("ip", "unknown"),
        "city": data.get("city", "unknown"),
        "region": data.get("region", "unknown"),
        "country": data.get("country", "unknown"),
        "lat": latitude or "unknown",
        "lon": longitude or "unknown",
    }


def build_location_update(location: dict[str, str]) -> str:
    """Build the second WhatsApp message, including a Google Maps link."""
    latitude, longitude = location["lat"], location["lon"]
    maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
    return (
        "📍 *Current Device Location*\n\n"
        f"City: {location['city']}\n"
        f"Region: {location['region']}\n"
        f"Country: {location['country']}\n"
        f"Coordinates: {latitude}, {longitude}\n"
        f"IP: {location['ip']}\n\n"
        f"Open in Maps: {maps_link}"
    )


def send_whatsapp(client: Client, recipient: str, body: str) -> str:
    """Send one WhatsApp message and return its Twilio SID."""
    message = client.messages.create(
        from_=FROM_WHATSAPP,
        to=recipient,
        body=body,
    )
    return message.sid


def main() -> None:
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # 1. Send the text update first.
    print("Sending Botfir text update...")
    text_sid = send_whatsapp(client, TEXT_UPDATE_TO, build_text_update())
    print(f"Text update sent. Twilio SID: {text_sid}")

    # 2. Detect and send the current location.
    print("Detecting current location...")
    try:
        location = get_current_location()
    except RuntimeError as exc:
        print(f"Location update was not sent: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Sending current location update...")
    location_sid = send_whatsapp(
        client,
        LOCATION_UPDATE_TO,
        build_location_update(location),
    )
    print(f"Location update sent. Twilio SID: {location_sid}")


if __name__ == "__main__":
    main()
