from io import BytesIO
from PIL import Image
from urllib import request

url = "http://maps.googleapis.com/maps/api/staticmap?center=-30.027489,-51.229248&size=800x800&zoom=14&sensor=false&key=AIzaSyCnZ5le4NJhODIolA8SRv37NVN4f6q75Rw&maptype=satellite"
buffer = BytesIO(request.urlopen(url).read())
image = Image.open(buffer)

image.show()