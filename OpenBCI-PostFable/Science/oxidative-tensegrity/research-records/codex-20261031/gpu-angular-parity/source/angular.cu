#include "angular.h"
extern "C" __global__ void oxt_terms(int n,const double *p,double *out){
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)oxt_angle(p+12*i,out+20*i);
}
// CSR entries encode 3*term+role (0=arm a,1=center,2=arm b).
// One thread per node: fixed accumulation order, no double atomicAdd.
extern "C" __global__ void oxt_gather(int nn,const int *offset,const int *entry,const double *terms,double *forces){
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=nn)return;
 double f[3]={0.,0.,0.};for(int q=offset[i];q<offset[i+1];++q){int e=entry[q];for(int d=0;d<3;++d)f[d]+=terms[20*(e/3)+1+3*(e%3)+d];}
 for(int d=0;d<3;++d)forces[3*i+d]=f[d];
}
// Each thread serially reduces a fixed 256-term tile; second launch reduces tiles.
// 11 outputs: E, 9 virial components, invalid-term count. No global atomics.
extern "C" __global__ void oxt_partial(int n,const double *terms,double *partial){
 int tile=blockIdx.x*blockDim.x+threadIdx.x;int first=tile*256;if(first>=n)return;
 double sums[11]={0.};for(int i=first;i<n&&i<first+256;++i){sums[0]+=terms[20*i];for(int j=0;j<9;++j)sums[1+j]+=terms[20*i+10+j];sums[10]+=(terms[20*i+19]!=0.);}
 for(int j=0;j<11;++j)partial[11*tile+j]=sums[j];
}
extern "C" __global__ void oxt_total(int tiles,const double *partial,double *out){
 int j=threadIdx.x;if(j>=11)return;double s=0.;for(int i=0;i<tiles;++i)s+=partial[11*i+j];out[j]=s;
}
// GPU-resident geometry for fixed image topology. params = k,rest,sa,sb,mode,active.
// a = x[arm_a]-x[center]+F*image_a, likewise b. No minimum-image switching.
extern "C" __global__ void oxt_build(int n,const double *x,const int *nodes,const double *image,const double *F,const double *params,double *inputs){
 int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=n)return;
 for(int d=0;d<3;++d){
   double a=x[3*nodes[3*t]+d]-x[3*nodes[3*t+1]+d];
   double b=x[3*nodes[3*t+2]+d]-x[3*nodes[3*t+1]+d];
   for(int j=0;j<3;++j){a+=F[3*d+j]*image[6*t+j];b+=F[3*d+j]*image[6*t+3+j];}
   inputs[12*t+d]=a;inputs[12*t+3+d]=b;
 }
 for(int j=0;j<6;++j)inputs[12*t+6+j]=params[6*t+j];
}
// dE/dF holding x fixed, NOT a substitution of Cauchy virial for first Piola.
// image derivatives may also represent reference arms if x is nonaffine displacement.
extern "C" __global__ void oxt_dEdF(int n,const double *terms,const double *image,double *deriv){
 int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=n)return;
 for(int i=0;i<3;++i)for(int j=0;j<3;++j)
   deriv[9*t+3*i+j]=-terms[20*t+1+i]*image[6*t+j]-terms[20*t+7+i]*image[6*t+3+j];
}
