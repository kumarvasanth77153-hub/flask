import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.

    :param lat1: Latitude of origin point (in degrees)
    :param lon1: Longitude of origin point (in degrees)
    :param lat2: Latitude of destination point (in degrees)
    :param lon2: Longitude of destination point (in degrees)
    :return: Distance in kilometers rounded to 2 decimal places, or None if coordinates invalid.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
    except (ValueError, TypeError):
        return None

    R = 6371.0  # Earth's mean radius in kilometers

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    r_lat1 = math.radians(lat1)
    r_lat2 = math.radians(lat2)

    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(r_lat1) * math.cos(r_lat2) * (math.sin(d_lon / 2.0) ** 2)
    )

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c

    return round(distance, 2)
