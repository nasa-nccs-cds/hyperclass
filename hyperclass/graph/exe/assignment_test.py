import numpy as np


x = np.zeros( (10,5), np.int32 )
ic0 = 2


index = np.array( ( 9, 8, 7, 6, 5, 4, 3, 2, 1, 0 ) )
labels = np.array( (1, 0, 2, 0, 5, 0, 7, 0, 9, 0 ) )

x[index,1] = labels

INic0 = index[ic0]
tCN = x[INic0]

print( x )