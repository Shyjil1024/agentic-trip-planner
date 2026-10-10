"""Small, best-effort road map adapter for the local prototype."""

import json
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MapUnavailable(Exception):
    pass


_geocode_cache: dict[str, dict] = {}
_geocode_lock = threading.Lock()
_last_geocode = 0.0
_headers = {"User-Agent": "WaypointTripPlanner/0.1 (local educational prototype)"}


def _json(url: str, data: bytes | None = None) -> dict | list:
    try:
        with urlopen(Request(url, data=data, headers=_headers), timeout=18) as response:
            return json.load(response)
    except Exception as error:
        raise MapUnavailable("The map data service is temporarily unavailable. Try again later.") from error


def _geocode(place: str) -> dict:
    global _last_geocode
    key = place.casefold().strip()
    with _geocode_lock:
        if key not in _geocode_cache:
            delay = 1.1 - (time.monotonic() - _last_geocode)
            if delay > 0:
                time.sleep(delay)
            _last_geocode = time.monotonic()
            query = urlencode({"q": place, "format": "jsonv2", "limit": 1})
            results = _json(f"https://nominatim.openstreetmap.org/search?{query}")
            if not results:
                raise MapUnavailable(f"Could not find '{place}' on the map. Try a more specific place name.")
            _geocode_cache[key] = {
                "name": results[0]["display_name"],
                "lat": float(results[0]["lat"]),
                "lon": float(results[0]["lon"]),
            }
        return _geocode_cache[key].copy()


def road_route(origin: str, destination: str) -> dict:
    start, end = _geocode(origin), _geocode(destination)
    coordinates = f'{start["lon"]},{start["lat"]};{end["lon"]},{end["lat"]}'
    query = urlencode({"overview": "full", "geometries": "geojson", "alternatives": "false"})
    result = _json(f"https://router.project-osrm.org/route/v1/driving/{coordinates}?{query}")
    if result.get("code") != "Ok" or not result.get("routes"):
        raise MapUnavailable("No drivable route was found between these places.")
    route = result["routes"][0]
    points = route["geometry"]["coordinates"]
    # Search several points along the road, keeping the public query small.
    samples = [points[round(i * (len(points) - 1) / 4)] for i in range(5)]
    hotels = []
    hotel_note = "OpenStreetMap listings near the route; availability and prices are not live."
    try:
        hotels = _hotel_list([(lon, lat, 5000) for lon, lat in samples[:-1]] +
                             [(end["lon"], end["lat"], 12000)])
    except MapUnavailable:
        hotel_note = "Hotel data is temporarily unavailable. The road route is still shown."
    return {
        "origin": start, "destination": end, "geometry": points,
        "distance_km": round(route["distance"] / 1000, 1),
        "duration_hours": round(route["duration"] / 3600, 1),
        "hotels": hotels, "rated_hotels": [], "hotel_note": hotel_note,
        "estimate_note": "Driving time is an estimate without live traffic, stops, or road closures.",
    }


def _hotel_list(samples: list[tuple[float, float, int]]) -> list[dict]:
    around = "".join(f'node(around:{radius},{lat},{lon})[tourism~"^(hotel|motel|guest_house|hostel)$"];'
                     f'way(around:{radius},{lat},{lon})[tourism~"^(hotel|motel|guest_house|hostel)$"];'
                     for lon, lat, radius in samples)
    data = _json("https://overpass-api.de/api/interpreter", urlencode({
        "data": f"[out:json][timeout:12];({around});out center 100;"
    }).encode())
    hotels, seen = [], set()
    for item in data.get("elements", []):
        tags = item.get("tags", {})
        position = item.get("center", item)
        if not tags.get("name") or "lat" not in position or "lon" not in position:
            continue
        if tags.get("amenity") in {"restaurant", "cafe", "bar", "pub", "fast_food"}:
            continue
        identity = (item["type"], item["id"])
        if identity in seen:
            continue
        seen.add(identity)
        address = ", ".join(str(tags[key]) for key in ("addr:street", "addr:city") if tags.get(key))
        website = tags.get("website") or tags.get("contact:website") or ""
        booking = next((tags[key] for key in ("contact:booking", "website:booking", "reservation:website", "website:reservation")
                        if isinstance(tags.get(key), str) and tags[key].startswith(("https://", "http://"))), "")
        hotels.append({"name": tags["name"], "lat": position["lat"], "lon": position["lon"],
                       "type": tags.get("tourism", "hotel"), "address": address,
                       "website": website if website.startswith(("https://", "http://")) else "",
                       "direct_booking_url": booking,
                       "map_url": f'https://www.openstreetmap.org/{item["type"]}/{item["id"]}',
                       "booking_url": "https://www.booking.com/searchresults.html?" +
                                      urlencode({"ss": tags["name"] + " " + (tags.get("addr:city") or "")})})
        if len(hotels) >= 40:
            break
    return hotels


def nearby_hotels(destination: str) -> dict:
    """Destination listings remain available even when a driving route cannot be found."""
    end = _geocode(destination)
    try:
        hotels = _hotel_list([(end["lon"], end["lat"], 12000)])
        note = "OpenStreetMap listings near the destination; ratings, prices and availability are not live."
    except MapUnavailable:
        hotels = []
        note = "Hotel listings could not load. Use the external search links to browse current options."
    return {"destination": end, "hotels": hotels, "rated_hotels": [], "hotel_note": note}


# """Small, best-effort road map adapter for the local prototype."""

# import json
# import os
# import threading
# import time
# from urllib.parse import urlencode
# from urllib.request import Request, urlopen


# class MapUnavailable(Exception):
#     pass


# _geocode_cache: dict[str, dict] = {}
# _geocode_lock = threading.Lock()
# _last_geocode = 0.0
# _headers = {"User-Agent": "WaypointTripPlanner/0.1 (local educational prototype)"}


# def _json(url: str, data: bytes | None = None) -> dict | list:
#     try:
#         with urlopen(Request(url, data=data, headers=_headers), timeout=18) as response:
#             return json.load(response)
#     except Exception as error:
#         raise MapUnavailable("The map data service is temporarily unavailable. Try again later.") from error


# def _geocode(place: str) -> dict:
#     global _last_geocode
#     key = place.casefold().strip()
#     with _geocode_lock:
#         if key not in _geocode_cache:
#             delay = 1.1 - (time.monotonic() - _last_geocode)
#             if delay > 0:
#                 time.sleep(delay)
#             _last_geocode = time.monotonic()
#             query = urlencode({"q": place, "format": "jsonv2", "limit": 1})
#             results = _json(f"https://nominatim.openstreetmap.org/search?{query}")
#             if not results:
#                 raise MapUnavailable(f"Could not find '{place}' on the map. Try a more specific place name.")
#             _geocode_cache[key] = {
#                 "name": results[0]["display_name"],
#                 "lat": float(results[0]["lat"]),
#                 "lon": float(results[0]["lon"]),
#             }
#         return _geocode_cache[key].copy()


# def road_route(origin: str, destination: str) -> dict:
#     start, end = _geocode(origin), _geocode(destination)
#     coordinates = f'{start["lon"]},{start["lat"]};{end["lon"]},{end["lat"]}'
#     query = urlencode({"overview": "full", "geometries": "geojson", "alternatives": "false"})
#     result = _json(f"https://router.project-osrm.org/route/v1/driving/{coordinates}?{query}")
#     if result.get("code") != "Ok" or not result.get("routes"):
#         raise MapUnavailable("No drivable route was found between these places.")
#     route = result["routes"][0]
#     points = route["geometry"]["coordinates"]
#     # Search several points along the road, keeping the public query small.
#     samples = [points[round(i * (len(points) - 1) / 5)] for i in range(6)]
#     around = "".join(f'node(around:3000,{lat},{lon})[tourism~"^(hotel|motel|guest_house)$"];'
#                      f'way(around:3000,{lat},{lon})[tourism~"^(hotel|motel|guest_house)$"];'
#                      for lon, lat in samples)
#     hotels = []
#     hotel_note = "Hotels are sampled near six points on the road; this is not a complete list or live availability. OpenStreetMap listings have no guest ratings."
#     try:
#         data = _json("https://overpass-api.de/api/interpreter", urlencode({
#             "data": f"[out:json][timeout:15];({around});out center 80;"
#         }).encode())
#         seen = set()
#         for item in data.get("elements", []):
#             tags = item.get("tags", {})
#             position = item.get("center", item)
#             if not tags.get("name") or "lat" not in position or "lon" not in position:
#                 continue
#             identity = (item["type"], item["id"])
#             if identity in seen:
#                 continue
#             seen.add(identity)
#             hotels.append({"name": tags["name"], "lat": position["lat"], "lon": position["lon"],
#                            "type": tags.get("tourism", "hotel")})
#             if len(hotels) >= 40:
#                 break
#     except MapUnavailable:
#         hotel_note = "Hotel data is temporarily unavailable. The road route is still shown."
#     rated_hotels = []
#     if os.getenv("GOOGLE_PLACES_API_KEY"):
#         for lon, lat in (samples[2], samples[4]):
#             try:
#                 request = Request("https://places.googleapis.com/v1/places:searchNearby",
#                     data=json.dumps({"includedTypes": ["hotel"], "maxResultCount": 10,
#                         "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon},
#                                                            "radius": 5000.0}}}).encode(),
#                     headers={"Content-Type": "application/json", "X-Goog-Api-Key": os.environ["GOOGLE_PLACES_API_KEY"],
#                              "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.googleMapsUri"})
#                 with urlopen(request, timeout=15) as response:
#                     places = json.load(response).get("places", [])
#                 for place in places:
#                     if place.get("rating") is not None:
#                         rated_hotels.append({"name": place.get("displayName", {}).get("text", "Hotel"),
#                                              "rating": place["rating"],
#                                              "review_count": place.get("userRatingCount", 0),
#                                              "url": place.get("googleMapsUri", "")})
#             except Exception:
#                 hotel_note += " Rated hotel listings are temporarily unavailable."
#         rated_hotels = list({hotel["url"]: hotel for hotel in rated_hotels if hotel["url"]}.values())
#     return {
#         "origin": start, "destination": end, "geometry": points,
#         "distance_km": round(route["distance"] / 1000, 1),
#         "duration_hours": round(route["duration"] / 3600, 1),
#         "hotels": hotels, "rated_hotels": rated_hotels, "hotel_note": hotel_note,
#         "estimate_note": "Driving time is an estimate without live traffic, stops, or road closures.",
#     }
