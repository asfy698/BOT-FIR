try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

"""Send a Botfir text update, then this device's approximate location via WhatsApp.

Modular module for sending current location.
"""

import sys
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from twilio.rest import Client


# Twilio WhatsApp configuration
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
FROM_WHATSAPP = "whatsapp:+14155238886"

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


def send_location(status_callback=None) -> bool:
    """Modular function to send WhatsApp text & location update synchronously."""
    def log(msg, tag="LOCATION"):
        print(f"[{tag}] {msg}")
        if status_callback:
            try:
                status_callback(msg, tag)
            except Exception:
                pass

    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)

        # 1. Send the text update first.
        log("Sending Botfir text update...", "LOCATION")
        text_sid = send_whatsapp(client, TEXT_UPDATE_TO, build_text_update())
        log(f"Text update sent. Twilio SID: {text_sid}", "LOCATION")

        # 2. Detect and send the current location.
        log("Detecting current location...", "LOCATION")
        location = get_current_location()

        log("Sending current location update...", "LOCATION")
        location_sid = send_whatsapp(
            client,
            LOCATION_UPDATE_TO,
            build_location_update(location),
        )
        log(f"Location update sent. Twilio SID: {location_sid}", "LOCATION")
        return True

    except Exception as exc:
        log(f"Location update failed: {exc}", "ERROR")
        return False


def send_location_async(status_callback=None):
    """Modular function to send location update asynchronously in a background thread."""
    thread = threading.Thread(
        target=send_location,
        args=(status_callback,),
        daemon=True,
        name="LocationSendThread"
    )
    thread.start()
    return thread


def main() -> None:
    success = send_location()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()