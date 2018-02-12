#import packages
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy 
import time 
import h5py
import ActivityPatterns as ap
import basis_mrf as bm
import pixel_mrf_model as pm
import region_mrf_model as rm
import ThermalImagingAnalysis as tai


# Data, parametric and non-parametric components 
f = h5py.File("626510_sep.mat", "r")
S = numpy.array(f["S1024"].value)
T = numpy.array(f["T1024"].value)
f_P = h5py.File("Penalty_Gaussian_1024fr_2.5Hz_TruncatedWaveletBasis.mat", "r")
P = f_P["BPdir2"].value        # learned penalty matrix
P = P.transpose()              # P appears to be stored as transposed version of itself
B = f_P["B"].value             # basis matrix 
S2 = S[0:1024,]
T2 = T[0:1024,]
del S;
del T;
noTimepoints, noPixels = S2.shape

#compute gaussian activity pattern
X = ap.computeGaussianActivityPattern(numpy.squeeze(T2)).transpose();

#compute basis matrix and penalty matrix for MRF Regularization
num_knots = 80
B2 = bm.basis_mrf(num_knots,noTimepoints);
D = numpy.identity(B2.shape[0])
D_k = numpy.diff(D,n=1,axis=-1)  
P2 = numpy.dot(D_k,D_k.T)

#semiparametric regression
Z = tai.semiparamRegression(S2, X, B, B2, P, P2, noPixels, num_knots)
plt.imshow(Z.reshape(640,480).transpose())
plt.show()

#accuracy after pixel_mrf model
groundtruthImg = numpy.array(f["groundtruthImg"].value)
groundtruth_foreground = numpy.where(groundtruthImg > 0)[0]
groundtruth_background = numpy.where(groundtruthImg == 0)[0]
true_positive =  len(numpy.where(abs(Z[groundtruth_foreground,]) >= 5.2)[0])                                  
false_positive = len(numpy.where(abs(Z[groundtruth_foreground,]) < 5.2)[0])
true_negative = len(numpy.where(abs(Z[groundtruth_background,]) < 5.2)[0])
false_negative = len(numpy.where(abs(Z[groundtruth_background,]) >= 5.2)[0])
true_positive_rate = true_positive / numpy.float32(true_positive + false_negative)
false_positive_rate = false_positive / numpy.float32(false_positive + true_negative)
accuracy  = (true_positive + true_negative) / numpy.float32(len(groundtruth_background) + len(groundtruth_foreground))
  
#post processing region_mrf_model
Z_region = rm.region_mrf_model(Z)
Z_region = numpy.reshape(Z,[noPixels,])
plt.imshow(Z_region.reshape(640,480).transpose())
plt.show()


with h5py.File("Z_Final.h5","w") as f:
    d1 = f.create_dataset('Z_region',data=Z_region)













































with h5py.File("result.h5","w") as f:
  d1 = f.create_dataset('Z',data=Z)