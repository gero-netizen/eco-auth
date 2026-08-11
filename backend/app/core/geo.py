import math

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim exige um User-Agent identificável - é uso gratuito de baixo volume,
# não uma chave de API.
_USER_AGENT = "eco-auth-ftth-viability/1.0"


class GeocodingError(Exception):
    pass


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta entre duas coordenadas, em metros. Não é a
    distância real do cabo (que depende da rota física), mas é a métrica
    padrão para triagem inicial de viabilidade."""
    radius_earth_m = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_earth_m * c


def geocode_address(address: str, timeout_seconds: float = 8.0) -> tuple[float, float]:
    """Converte um endereço em coordenadas usando o Nominatim (OpenStreetMap).
    Levanta GeocodingError se o endereço não for encontrado ou o serviço
    estiver indisponível."""
    if not address.strip():
        raise GeocodingError("empty_address")
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(
                NOMINATIM_URL,
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": _USER_AGENT},
            )
    except httpx.TimeoutException as error:
        raise GeocodingError("geocoding_timeout") from error
    except httpx.HTTPError as error:
        raise GeocodingError("geocoding_network_error") from error
    if response.status_code != 200:
        raise GeocodingError(f"geocoding_provider_error_{response.status_code}")
    results = response.json()
    if not results:
        raise GeocodingError("address_not_found")
    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, ValueError, TypeError) as error:
        raise GeocodingError("geocoding_malformed_response") from error
