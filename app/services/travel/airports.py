"""Static airport table (IATA, city, aliases, lat/lon) and a haversine nearest-airport lookup. No network."""

from __future__ import annotations

import math
import re

# (iata, city, airport name, lat, lon, aliases)
AIRPORTS: list[tuple[str, str, str, float, float, tuple[str, ...]]] = [
    ("BOM", "Mumbai", "Chhatrapati Shivaji Maharaj International", 19.0896, 72.8656, ("bombay", "mumbai")),
    ("DEL", "Delhi", "Indira Gandhi International", 28.5562, 77.1000, ("new delhi", "delhi", "ncr", "gurgaon", "gurugram", "noida")),
    ("BLR", "Bengaluru", "Kempegowda International", 13.1986, 77.7066, ("bangalore", "bengaluru", "bengalooru")),
    ("MAA", "Chennai", "Chennai International", 12.9941, 80.1709, ("madras", "chennai")),
    ("HYD", "Hyderabad", "Rajiv Gandhi International", 17.2403, 78.4294, ("hyderabad", "secunderabad")),
    ("CCU", "Kolkata", "Netaji Subhas Chandra Bose International", 22.6547, 88.4467, ("calcutta", "kolkata")),
    ("PNQ", "Pune", "Pune Airport", 18.5822, 73.9197, ("pune", "poona")),
    ("AMD", "Ahmedabad", "Sardar Vallabhbhai Patel International", 23.0772, 72.6347, ("ahmedabad", "gandhinagar")),
    ("GOI", "Goa (Dabolim)", "Dabolim", 15.3808, 73.8314, ("goa", "dabolim", "panaji")),
    ("GOX", "Goa (Mopa)", "Manohar International", 15.7444, 73.8603, ("mopa", "north goa")),
    ("COK", "Kochi", "Cochin International", 10.1520, 76.4019, ("cochin", "kochi", "ernakulam")),
    ("TRV", "Thiruvananthapuram", "Trivandrum International", 8.4821, 76.9200, ("trivandrum", "thiruvananthapuram")),
    ("JAI", "Jaipur", "Jaipur International", 26.8242, 75.8122, ("jaipur",)),
    ("LKO", "Lucknow", "Chaudhary Charan Singh International", 26.7606, 80.8893, ("lucknow",)),
    ("CJB", "Coimbatore", "Coimbatore International", 11.0300, 77.0434, ("coimbatore", "kovai")),
    ("IXE", "Mangaluru", "Mangalore International", 12.9613, 74.8901, ("mangalore", "mangaluru")),
    ("GAU", "Guwahati", "Lokpriya Gopinath Bordoloi International", 26.1061, 91.5859, ("guwahati",)),
    ("PAT", "Patna", "Jay Prakash Narayan", 25.5913, 85.0880, ("patna",)),
    ("BBI", "Bhubaneswar", "Biju Patnaik International", 20.2444, 85.8178, ("bhubaneswar",)),
    ("NAG", "Nagpur", "Dr. Babasaheb Ambedkar International", 21.0922, 79.0472, ("nagpur",)),
    ("IXC", "Chandigarh", "Chandigarh International", 30.6735, 76.7885, ("chandigarh", "mohali")),
    ("ATQ", "Amritsar", "Sri Guru Ram Dass Jee International", 31.7096, 74.7973, ("amritsar",)),
    ("SXR", "Srinagar", "Srinagar International", 33.9871, 74.7742, ("srinagar", "kashmir")),
    ("VNS", "Varanasi", "Lal Bahadur Shastri International", 25.4524, 82.8593, ("varanasi", "banaras", "kashi")),
    ("IDR", "Indore", "Devi Ahilya Bai Holkar", 22.7218, 75.8011, ("indore",)),
    ("BHO", "Bhopal", "Raja Bhoj", 23.2875, 77.3374, ("bhopal",)),
    ("VTZ", "Visakhapatnam", "Visakhapatnam International", 17.7212, 83.2245, ("vizag", "visakhapatnam")),
    ("IXM", "Madurai", "Madurai Airport", 9.8345, 78.0934, ("madurai",)),
    ("TRZ", "Tiruchirappalli", "Tiruchirappalli International", 10.7654, 78.7097, ("trichy", "tiruchirappalli")),
    ("UDR", "Udaipur", "Maharana Pratap", 24.6177, 73.8961, ("udaipur",)),
    ("IXB", "Bagdogra", "Bagdogra Airport", 26.6812, 88.3286, ("bagdogra", "siliguri", "darjeeling")),
    ("RPR", "Raipur", "Swami Vivekananda", 21.1804, 81.7388, ("raipur",)),
    ("IXR", "Ranchi", "Birsa Munda", 23.3143, 85.3217, ("ranchi",)),
    ("STV", "Surat", "Surat Airport", 21.1141, 72.7418, ("surat",)),
    ("DXB", "Dubai", "Dubai International", 25.2532, 55.3657, ("dubai",)),
    ("SIN", "Singapore", "Changi", 1.3644, 103.9915, ("singapore",)),
    ("LHR", "London", "Heathrow", 51.4700, -0.4543, ("london", "heathrow")),
    ("JFK", "New York", "John F. Kennedy International", 40.6413, -73.7781, ("new york", "nyc")),
    ("SFO", "San Francisco", "San Francisco International", 37.6213, -122.3790, ("san francisco", "bay area")),
    ("BKK", "Bangkok", "Suvarnabhumi", 13.6900, 100.7501, ("bangkok",)),
    ("DOH", "Doha", "Hamad International", 25.2731, 51.6081, ("doha", "qatar")),
    ("KUL", "Kuala Lumpur", "Kuala Lumpur International", 2.7456, 101.7099, ("kuala lumpur",)),
    ("CMB", "Colombo", "Bandaranaike International", 7.1808, 79.8841, ("colombo", "sri lanka")),
    ("KTM", "Kathmandu", "Tribhuvan International", 27.6966, 85.3591, ("kathmandu", "nepal")),
]
BY_CODE = {a[0]: a for a in AIRPORTS}


def view(a: tuple) -> dict:
    return {"iata": a[0], "city": a[1], "airport": a[2]}


def _norm(t: str) -> str:
    return re.sub(r"[^a-z ]", "", t.lower()).strip()


def resolve(text: str) -> dict | None:
    """'Mumbai', 'bombay', 'BOM', 'Bangalore airport' -> airport. None when nothing matches."""
    t = text.strip()
    if t.upper() in BY_CODE:
        return view(BY_CODE[t.upper()])
    n = _norm(t).replace(" airport", "").replace(" international", "")
    for a in AIRPORTS:
        if n == _norm(a[1]) or n in a[5]:
            return view(a)
    words = f" {n} "
    for a in AIRPORTS:  # whole words only: "north goa", "new delhi airport" match; "goalpara" does not match goa
        if any(f" {alias} " in words for alias in a[5]) or f" {_norm(a[1])} " in words:
            return view(a)
    return None


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def nearest(lat: float, lon: float) -> dict:
    a = min(AIRPORTS, key=lambda x: _km(lat, lon, x[3], x[4]))
    return {**view(a), "distance_km": round(_km(lat, lon, a[3], a[4]))}
