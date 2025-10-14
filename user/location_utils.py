import requests


def get_location_from_ip(ip_address):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}")
        data = response.json()
        return {
            "city": data.get("city"),
            "region": data.get("regionName"),
            "district": data.get("district") or data.get("city"),
            "postal": data.get("zip"),
        }
    except Exception as e:
        return {
            "city": None,
            "region": None,
            "district": None,
            "postal": None,
        }
