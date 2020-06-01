import googlemaps, responses
from datetime import datetime
from googlemaps.maps import StaticMapMarker
from googlemaps.maps import StaticMapPath

client = googlemaps.Client(key='zzzz')
url = "https://maps.googleapis.com/maps/api/staticmap"
responses.add(responses.GET, url, status=200)

path = StaticMapPath(
    points=[(62.107733, -145.541936), "Delta+Junction,AK"],
    weight=5,
    color="red",
)

m1 = StaticMapMarker(
    locations=[(62.107733, -145.541936)], color="blue", label="S"
)

m2 = StaticMapMarker(
    locations=["Delta+Junction,AK"], size="tiny", color="green"
)

m3 = StaticMapMarker(
    locations=["Tok,AK"], size="mid", color="0xFFFF00", label="C"
)

response = client.static_map(
            size=(400, 400),
            zoom=6,
            center=(63.259591, -144.667969),
            maptype="hybrid",
            format="png",
            scale=2,
            visible=["Tok,AK"],
            path=path,
            markers=[m1, m2, m3],
        )
print( ".")
