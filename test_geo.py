import requests

# Test Chennai
r = requests.get(
    "https://nominatim.openstreetmap.org/reverse",
    params={"lat": "13.0827", "lon": "80.2707", "format": "json"},
    headers={"User-Agent": "ComplaintDashboard/1.0"},
    timeout=8,
)
print("Status:", r.status_code)
data = r.json()
addr = data.get("address", {})
print("Full address dict:")
for k, v in addr.items():
    print(f"  {k}: {v}")

print()
print("Parsed:")
state = addr.get("state", "")
district = addr.get("county") or addr.get("state_district") or addr.get("district") or ""
muni = addr.get("city") or addr.get("town") or addr.get("city_district") or addr.get("municipality") or addr.get("township") or addr.get("hamlet") or addr.get("village") or district or ""
area = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter") or addr.get("residential") or addr.get("road") or addr.get("amenity") or ""
print(f"  state={state!r}")
print(f"  district={district!r}")
print(f"  municipality={muni!r}")
print(f"  area={area!r}")
print(f"  display={data.get('display_name','')[:70]!r}")
