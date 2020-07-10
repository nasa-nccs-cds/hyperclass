import numpy as np
from time import time
npixels = 1000000
nbands = 420
image = np.random.rand(npixels,nbands)
weights = np.random.rand(nbands)

print( "Non Pythonic Weighted sum of bands at each pixel:" )
t0 = time()
result = []
for ix in range( npixels ):
    wsum = 0.0
    for ib in range( nbands ):
        wsum = wsum + image[ix,ib] * weights[ib]
    result.append( wsum )
dt0 = time()-t0
print( f"Non Pythonic result[100] = {result[100]:.4f}, time required = {dt0:.6f} secs.")

print( "Pythonic Weighted sum of bands at each pixel:" )
t0 = time()
result1 = image.dot( weights )
dt1 = time()-t0
print( f"Pythonic result[100] = {result1[100]:.4f}, time required = {dt1:.6f} secs.")

ddt = dt0/dt1
print( f"The pythonic method runs {ddt:.2f} times faster")