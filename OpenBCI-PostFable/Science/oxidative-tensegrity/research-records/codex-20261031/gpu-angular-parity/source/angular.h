#pragma once
#ifndef __CUDACC_RTC__
#include <math.h>
#endif
#ifdef __CUDACC__
#define OXT_HD __host__ __device__
#else
#define OXT_HD
#endif
// Input per term: a[3], b[3], k, rest, sign_a, sign_b, mode, active.
// a,b are explicit image-resolved outward arms, NEVER reselect images here.
// Output: energy, forces(a,center,b)[9], full virial[9], status.
// Modes: 0 signed 2D; 1 wrapped 2D; 2 cosine 3D; 3 unsigned 3D.
// Invalid active terms return NaN and a nonzero status. Inactive terms are zero.
OXT_HD inline void oxt_angle(const double *p, double *o) {
  for(int j=0;j<20;++j)o[j]=0.;
  if(p[11]==0.)return;
  for(int j=0;j<12;++j)if(!isfinite(p[j])){o[19]=1.;o[0]=nan("");return;}
  int mode=(int)p[10];
  if(mode<0||mode>3||p[10]!=(double)mode||p[6]<0.||
     (p[8]!=1.&&p[8]!=-1.)||(p[9]!=1.&&p[9]!=-1.)||p[11]!=1.){
    o[19]=2.;o[0]=nan("");return;
  }
  double u[3],v[3],gu[3]={0.,0.,0.},gv[3]={0.,0.,0.};
  double aa=0.,bb=0.,dot=0.;
  for(int j=0;j<3;++j){u[j]=p[8]*p[j];v[j]=p[9]*p[3+j];aa+=u[j]*u[j];bb+=v[j]*v[j];dot+=u[j]*v[j];}
  if(aa<1e-16||bb<1e-16){o[19]=3.;o[0]=nan("");return;}
  double k=p[6],rest=p[7];
  if(mode<=1){
    if(u[2]!=0.||v[2]!=0.){o[19]=4.;o[0]=nan("");return;}
    double theta=atan2(u[0]*v[1]-u[1]*v[0],dot),d=theta-rest;
    if(mode==1)d=atan2(sin(d),cos(d));
    // Mode 0 can impose the commissioned positive lock sector with rest > 0.
    if(mode==0&&rest>0.&&theta<=0.){o[19]=5.;o[0]=nan("");return;}
    if(fabs(fabs(d)-3.14159265358979323846)<1e-12){o[19]=6.;o[0]=nan("");return;}
    o[0]=.5*k*d*d;
    gu[0]=k*d*u[1]/aa;gu[1]=-k*d*u[0]/aa;
    gv[0]=-k*d*v[1]/bb;gv[1]=k*d*v[0]/bb;
  }else if(mode==2){
    double denom=sqrt(aa)*sqrt(bb);
    // Match network3d's denominator clamp exactly; tiny arms are rejected above.
    double den=denom>1e-9?denom:1e-9;
    double c=dot/den,d=c-rest; o[0]=.5*k*d*d;
    for(int j=0;j<3;++j){
      gu[j]=k*d*(v[j]/den-(denom>1e-9?c*u[j]/aa:0.));
      gv[j]=k*d*(u[j]/den-(denom>1e-9?c*v[j]/bb:0.));
    }
  }else{
    // Stable unsigned atan2 bend: no artificial sin(theta) force floor.
    double cross[3]={u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]};
    double s=sqrt(cross[0]*cross[0]+cross[1]*cross[1]+cross[2]*cross[2]);
    double theta=atan2(s,dot),d=theta-rest;o[0]=.5*k*d*d;
    if(s==0.){
      if(dot>0.&&rest==0.)return; // differentiable straight minimum
      o[19]=7.;o[0]=nan("");return; // undefined cusp/antiparallel gradient
    }
    // n x u and v x n avoid cancellation at nearly straight hinges.
    double n[3]={cross[0]/s,cross[1]/s,cross[2]/s};
    double nxu[3]={n[1]*u[2]-n[2]*u[1],n[2]*u[0]-n[0]*u[2],n[0]*u[1]-n[1]*u[0]};
    double vxn[3]={v[1]*n[2]-v[2]*n[1],v[2]*n[0]-v[0]*n[2],v[0]*n[1]-v[1]*n[0]};
    for(int j=0;j<3;++j){gu[j]=-k*d*nxu[j]/aa;gv[j]=-k*d*vxn[j]/bb;}
  }
  double ga[3],gb[3];
  for(int j=0;j<3;++j){ga[j]=p[8]*gu[j];gb[j]=p[9]*gv[j];o[1+j]=-ga[j];o[4+j]=ga[j]+gb[j];o[7+j]=-gb[j];}
  for(int i=0;i<3;++i)for(int j=0;j<3;++j)o[10+3*i+j]=-p[i]*ga[j]-p[3+i]*gb[j];
  for(int j=0;j<19;++j)if(!isfinite(o[j])){o[19]=8.;o[0]=nan("");return;}
}
