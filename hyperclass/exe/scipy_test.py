import numpy as np
from scipy.linalg import inv

R = np.array( [[-0.13323812, -3.11743383], [ 1.79885044,  0.        ]] )
TR = np.transpose(R)
TD = np.dot(TR, R)
cov_x = inv(TD)

print( cov_x )