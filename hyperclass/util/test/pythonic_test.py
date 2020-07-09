import numpy as np
from time import time
npixels = 10000000
image = np.random.rand(npixels)
weights = np.random.rand(npixels)

# Non Pythonic Weighted sum of pixels:
t0 = time()
result = 0.0
for ix in range( npixels ):
    result = result + image[ix] * weights[ix]
dt0 = time()-t0
print( f"Non Pythonic result = {result:.4f}, time required = {dt0:.6f} secs.")

# Pythonic Weighted sum of pixels:
t0 = time()
result = image.dot( weights )
dt1 = time()-t0
print( f"Pythonic result = {result:.4f}, time required = {dt1:.6f} secs.")

ddt = dt0/dt1
print( f"The pythonic method runs {ddt:.2f} times faster")