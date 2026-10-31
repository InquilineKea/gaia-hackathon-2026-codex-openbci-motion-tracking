#include "angular.h"
extern "C" void oxt_cpu(int n,const double *p,double *out){for(int i=0;i<n;++i)oxt_angle(p+12*i,out+20*i);}
