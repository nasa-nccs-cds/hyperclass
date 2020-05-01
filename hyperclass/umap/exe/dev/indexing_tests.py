import numpy as np


x = np.array( range(10) )

print( x )

ind = np.array( [3,5,9] )
vals = np.array( [-1,-2,-3] )

x[ind] = vals

print( x )