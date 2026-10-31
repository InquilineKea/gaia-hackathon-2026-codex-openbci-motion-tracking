// Original implementation for this study. No downloaded source or dependencies.
#include <cuda_runtime.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
#include <random>
#include <fstream>
#include <chrono>
#include <string>
#include <stdexcept>
#define HD __host__ __device__
constexpr int T=256, NCOL=17, MAXROW=4000;
struct V {double x,y; HD V(double X=0,double Y=0):x(X),y(Y){} HD V operator+(V b)const{return V(x+b.x,y+b.y);} HD V operator-(V b)const{return V(x-b.x,y-b.y);} HD V operator*(double a)const{return V(x*a,y*a);} };
HD double dot(V a,V b){return a.x*b.x+a.y*b.y;}
HD double norm(V a){return sqrt(dot(a,a));}
HD V perp(V a){return V(-a.y,a.x);}
HD V direction(int d){return d==0?V(1,0):(d==1?V(.5,sqrt(3.)/2):V(-.5,sqrt(3.)/2));}
HD int next(int i,int d,int L,int s=1){int x=i%L,y=i/L; if(d==0)x+=s; if(d==1)y+=s; if(d==2){x-=s;y+=s;}return ((y+L)%L)*L+(x+L)%L;}
struct Config {int seed,arch,L,kind; double kappa,r,beta,threshold,step,dt,tol;int maxiter;};
struct State {V *u,*v,*f;double *q;unsigned char *mask,*alive;V *histS,*histY,*back,*oldf;};
HD V displacement(State a,int e,int L,double gamma){int i=e/3,d=e%3,j=next(i,d,L);V b=direction(d);b.x+=gamma*b.y;return b+a.u[j]-a.u[i];}
HD double stretch(V d,double q,double r,V &g){double l=norm(d); double a=l-1,b=l-q;g=d*((r*a+(1-r)*b)/fmax(l,1e-12));return .5*(r*a*a+(1-r)*b*b);}
HD double bend(V a,V b,double k,V &ga,V &gb){double la=norm(a),lb=norm(b);double theta=atan2(a.x*b.y-a.y*b.x,dot(a,b));ga=perp(a)*(-k*theta/fmax(la*la,1e-24));gb=perp(b)*(k*theta/fmax(lb*lb,1e-24));return .5*k*theta*theta;}
__device__ void add(V *a,int i,V v){atomicAdd(&a[i].x,v.x);atomicAdd(&a[i].y,v.y);}
__device__ double sum(double x,double *s){int t=threadIdx.x;s[t]=x;__syncthreads();for(int n=T/2;n;n/=2){if(t<n)s[t]+=s[t+n];__syncthreads();}double r=s[0];__syncthreads();return r;}
__device__ double maximum(double x,double *s){int t=threadIdx.x;s[t]=x;__syncthreads();for(int n=T/2;n;n/=2){if(t<n)s[t]=fmax(s[t],s[t+n]);__syncthreads();}double r=s[0];__syncthreads();return r;}
__device__ void forces(State a,Config c,double gamma,double *energy,double *stress,double *scratch){int n=c.L*c.L;for(int i=threadIdx.x;i<n;i+=T)a.f[i]=V();__syncthreads();double en=0,st=0;
 for(int e=threadIdx.x;e<3*n;e+=T){if(!a.alive[e])continue;int i=e/3,d=e%3,j=next(i,d,c.L);V v=displacement(a,e,c.L,gamma),g;en+=stretch(v,a.q[e],c.r,g);add(a.f,i,g);add(a.f,j,g*(-1));st+=g.x*direction(d).y;
 int prev=next(i,d,c.L,-1),e0=3*prev+d;
 if(a.alive[e0]){V ga,gb;en+=bend(displacement(a,e0,c.L,gamma),v,c.kappa,ga,gb);add(a.f,prev,ga);add(a.f,i,gb-ga);add(a.f,j,gb*(-1));st+=(ga.x+gb.x)*direction(d).y;}}
 double E=sum(en,scratch);double S=sum(st,scratch);if(threadIdx.x==0){*energy=E;*stress=S/(n*sqrt(3.)/2);}__syncthreads();
}
__device__ int relax_fire(State a,Config c,double gamma,double *scratch,double *shared){int n=c.L*c.L;double &E=shared[0],&stress=shared[1],&dt=shared[2],&alpha=shared[3],&fmaxv=shared[4];
 if(threadIdx.x==0){dt=.05;alpha=.1;}for(int i=threadIdx.x;i<n;i+=T)a.v[i]=V();__syncthreads();int positive=0,it=0;
 for(;it<c.maxiter;it++){forces(a,c,gamma,&E,&stress,scratch);double fm=0;for(int i=threadIdx.x;i<n;i+=T)fm=fmax(fm,isfinite(norm(a.f[i]))?norm(a.f[i]):1e300);double fmaxr=maximum(fm,scratch);if(threadIdx.x==0)fmaxv=fmaxr;__syncthreads();if(!isfinite(E)||!isfinite(stress)||fmaxv>1e20){it=c.maxiter;break;}if(fmaxv<c.tol)break;
  double p=0,vv=0,ff=0;for(int i=threadIdx.x;i<n;i+=T){a.v[i]=a.v[i]+a.f[i]*dt;p+=dot(a.v[i],a.f[i]);vv+=dot(a.v[i],a.v[i]);ff+=dot(a.f[i],a.f[i]);}
  double P=sum(p,scratch),VV=sum(vv,scratch),FF=sum(ff,scratch);if(P>0){positive++;if(threadIdx.x==0&&positive>5){dt=fmin(dt*1.1,.5);alpha*=.99;}}else{positive=0;if(threadIdx.x==0){dt*=.5;alpha=.1;}}__syncthreads();
  double factor=sqrt(VV/fmax(FF,1e-300));for(int i=threadIdx.x;i<n;i+=T){if(P<=0)a.v[i]=V();else a.v[i]=a.v[i]*(1-alpha)+a.f[i]*(alpha*factor);a.u[i]=a.u[i]+a.v[i]*dt;}__syncthreads();
 }
 // Recompute at the actual saved position even when the iteration budget is exhausted.
 forces(a,c,gamma,&E,&stress,scratch);double fm=0;for(int i=threadIdx.x;i<n;i+=T)fm=fmax(fm,isfinite(norm(a.f[i]))?norm(a.f[i]):1e300);double F=maximum(fm,scratch);if(threadIdx.x==0)fmaxv=F;__syncthreads();return it;
}
// Five-pair L-BFGS with an Armijo energy-decrease line search. Original code.
// The force/energy law is identical to the commissioning FIRE implementation.
__device__ int relax(State a,Config c,double gamma,double *scratch,double *sh){
 int n=c.L*c.L,head=0,used=0,it=0;double *rho=sh+8,*alpha=sh+13;
 forces(a,c,gamma,sh,sh+1,scratch);
 for(;it<c.maxiter;it++){
  double fm=0;for(int i=threadIdx.x;i<n;i+=T)fm=fmax(fm,isfinite(norm(a.f[i]))?norm(a.f[i]):1e300);
  double F=maximum(fm,scratch);if(threadIdx.x==0)sh[4]=F;__syncthreads();if(F<c.tol)break;
  if(!isfinite(sh[0])||F>1e20){it=c.maxiter;break;}
  for(int i=threadIdx.x;i<n;i+=T){a.v[i]=a.f[i];a.back[i]=a.u[i];a.oldf[i]=a.f[i];}__syncthreads();
  for(int k=0;k<used;k++){int h=(head-1-k+5)%5;double d=0;for(int i=threadIdx.x;i<n;i+=T)d+=dot(a.histS[h*n+i],a.v[i]);double A=rho[h]*sum(d,scratch);if(threadIdx.x==0)alpha[h]=A;for(int i=threadIdx.x;i<n;i+=T)a.v[i]=a.v[i]-a.histY[h*n+i]*A;__syncthreads();}
  double scale=.25;if(used){int h=(head-1+5)%5;double yy=0;for(int i=threadIdx.x;i<n;i+=T)yy+=dot(a.histY[h*n+i],a.histY[h*n+i]);double YY=sum(yy,scratch);scale=fmin(1e6,fmax(1e-6,1/(rho[h]*YY)));}
  for(int i=threadIdx.x;i<n;i+=T)a.v[i]=a.v[i]*scale;__syncthreads();
  for(int k=used-1;k>=0;k--){int h=(head-1-k+5)%5;double d=0;for(int i=threadIdx.x;i<n;i+=T)d+=dot(a.histY[h*n+i],a.v[i]);double B=rho[h]*sum(d,scratch);for(int i=threadIdx.x;i<n;i+=T)a.v[i]=a.v[i]+a.histS[h*n+i]*(alpha[h]-B);__syncthreads();}
  double fd=0;for(int i=threadIdx.x;i<n;i+=T)fd+=dot(a.f[i],a.v[i]);double FD=sum(fd,scratch);
  if(!(FD>0)||!isfinite(FD)){used=0;head=0;fd=0;for(int i=threadIdx.x;i<n;i+=T){a.v[i]=a.f[i]*.25;fd+=dot(a.f[i],a.v[i]);}FD=sum(fd,scratch);}
  double oldE=sh[0],step=1;bool accepted=false;
  for(int line=0;line<40;line++){
   for(int i=threadIdx.x;i<n;i+=T)a.u[i]=a.back[i]+a.v[i]*step;__syncthreads();forces(a,c,gamma,sh,sh+1,scratch);
   if(isfinite(sh[0])&&sh[0]<=oldE-1e-4*step*FD+1e-20*fmax(1.,fabs(oldE))){accepted=true;break;}step*=.5;
  }
  if(!accepted){for(int i=threadIdx.x;i<n;i+=T)a.u[i]=a.back[i];__syncthreads();forces(a,c,gamma,sh,sh+1,scratch);it=c.maxiter;break;}
  double sy=0,ss=0,yy=0;for(int i=threadIdx.x;i<n;i+=T){V s=a.u[i]-a.back[i],y=a.oldf[i]-a.f[i];sy+=dot(s,y);ss+=dot(s,s);yy+=dot(y,y);}
  double SY=sum(sy,scratch),SS=sum(ss,scratch),YY=sum(yy,scratch);
  if(SY>1e-12*sqrt(SS*YY)&&SY>1e-30){for(int i=threadIdx.x;i<n;i+=T){a.histS[head*n+i]=a.u[i]-a.back[i];a.histY[head*n+i]=a.oldf[i]-a.f[i];}if(threadIdx.x==0)rho[head]=1/SY;head=(head+1)%5;used=min(used+1,5);__syncthreads();}
 }
 double fm=0;for(int i=threadIdx.x;i<n;i+=T)fm=fmax(fm,isfinite(norm(a.f[i]))?norm(a.f[i]):1e300);double F=maximum(fm,scratch);if(threadIdx.x==0)sh[4]=F;__syncthreads();if(it==c.maxiter&&F<c.tol)return c.maxiter-1;return it;
}
__device__ void reset(State a,Config c){int n=c.L*c.L;for(int i=threadIdx.x;i<n;i+=T){a.u[i]=V();a.v[i]=V();}for(int e=threadIdx.x;e<3*n;e+=T){a.q[e]=1;a.alive[e]=a.mask[e];}__syncthreads();}
__device__ void update_memory(State a,Config c,double gamma,double dt){int n=c.L*c.L;for(int e=threadIdx.x;e<3*n;e+=T)if(a.alive[e]){double l=norm(displacement(a,e,c.L,gamma));double rate=exp(fmin(30.,c.beta*fabs(l-a.q[e])));a.q[e]=l+(a.q[e]-l)*exp(-dt*rate);}__syncthreads();}
// Rows: stage,gamma,time,stress,energy,fmax,iters,alive,mean strain2,mean strain4,max strain,nonaffinity,G0,Gcheck,failed solves,broken this step,mean q.
__device__ void record(State a,Config c,double gamma,double time,int stage,int iterations,double G0,double Gcheck,int bad,int broken,double *out,int row,double *s,double *shared){int n=c.L*c.L;double s2=0,s4=0,mx=0,qm=0,count=0,ux=0,uy=0;
 for(int e=threadIdx.x;e<3*n;e+=T)if(a.alive[e]){double epsi=norm(displacement(a,e,c.L,gamma))-1;s2+=epsi*epsi;s4+=epsi*epsi*epsi*epsi;mx=fmax(mx,fabs(epsi));qm+=a.q[e];count++;}
 double S2=sum(s2,s),S4=sum(s4,s),MX=maximum(mx,s),Q=sum(qm,s),C=sum(count,s);
 for(int i=threadIdx.x;i<n;i+=T){ux+=a.u[i].x;uy+=a.u[i].y;}double UX=sum(ux,s)/n,UY=sum(uy,s)/n;double na=0;for(int i=threadIdx.x;i<n;i+=T){V v=a.u[i]-V(UX,UY);na+=dot(v,v);}double NA=sum(na,s)/n;
 if(threadIdx.x==0){double *r=out+row*NCOL;double v[NCOL]={double(stage),gamma,time,shared[1],shared[0]/(n*sqrt(3.)/2),shared[4],double(iterations),C,S2/fmax(C,1.),S4/fmax(C,1.),MX,NA,G0,Gcheck,double(bad),double(broken),Q/fmax(C,1.)};for(int i=0;i<NCOL;i++)r[i]=v[i];}__syncthreads();
}
__global__ void run(Config *cfg,State all,double *output,int *rows){int id=blockIdx.x;Config c=cfg[id];int n=c.L*c.L;State a={all.u+id*n,all.v+id*n,all.f+id*n,all.q+id*3*n,all.mask+id*3*n,all.alive+id*3*n};a.histS=all.histS+id*5*n;a.histY=all.histY+id*5*n;a.back=all.back+id*n;a.oldf=all.oldf+id*n;double *out=output+id*MAXROW*NCOL;__shared__ double scratch[T],sh[32];int row=0,bad=0;
 reset(a,c);int it=relax(a,c,.001,scratch,sh);double G0=sh[1]/.001;if(it==c.maxiter)bad++;record(a,c,.001,0,0,it,G0,0,bad,0,out,row++,scratch,sh);
 it=relax(a,c,.002,scratch,sh);double Gcheck=sh[1]/.002;if(it==c.maxiter)bad++;record(a,c,.002,0,0,it,G0,Gcheck,bad,0,out,row++,scratch,sh);
 if(bad){if(threadIdx.x==0)rows[id]=row;return;}
 reset(a,c);
 if(c.kind==0){ // Undamaged relaxation hold after a mechanically quasistatic but instantaneous ramp.
  double target=.1;for(int s=1;s<=20;s++){it=relax(a,c,target*s/20,scratch,sh);if(it==c.maxiter){bad++;record(a,c,target*s/20,0,1,it,G0,Gcheck,bad,0,out,row++,scratch,sh);if(threadIdx.x==0)rows[id]=row;return;}}
  record(a,c,target,0,1,it,G0,Gcheck,bad,0,out,row++,scratch,sh);
  int steps=int(5/c.dt+.5);for(int s=1;s<=steps;s++){update_memory(a,c,target,c.dt);it=relax(a,c,target,scratch,sh);if(it==c.maxiter)bad++;record(a,c,target,s*c.dt,1,it,G0,Gcheck,bad,0,out,row++,scratch,sh);if(bad){if(threadIdx.x==0)rows[id]=row;return;}}
 }else{ // Finite-rate shear and irreversible segment failure; separate fresh specimen.
  int steps=int(.8/c.step+.5);double time=0;
  for(int s=1;s<=steps;s++){double gamma=s*c.step;it=relax(a,c,gamma,scratch,sh);if(it==c.maxiter){bad++;record(a,c,gamma,time,3,it,G0,Gcheck,bad,0,out,row++,scratch,sh);if(threadIdx.x==0)rows[id]=row;return;}if(c.r<1){update_memory(a,c,gamma,c.dt);time+=c.dt;it=relax(a,c,gamma,scratch,sh);if(it==c.maxiter)bad++;}
   record(a,c,gamma,time,3,it,G0,Gcheck,bad,0,out,row++,scratch,sh);if(bad){if(threadIdx.x==0)rows[id]=row;return;}
   int broken=0;for(int avalanche=0;avalanche<3*n;avalanche++){double removed=0;for(int e=threadIdx.x;e<3*n;e+=T)if(a.alive[e]&&norm(displacement(a,e,c.L,gamma))-1>c.threshold){a.alive[e]=0;removed++;}int R=int(sum(removed,scratch));broken+=R;if(R==0)break;it=relax(a,c,gamma,scratch,sh);if(it==c.maxiter){bad++;break;}}
   record(a,c,gamma,time,2,it,G0,Gcheck,bad,broken,out,row++,scratch,sh);if(bad){if(threadIdx.x==0)rows[id]=row;return;}
  }
 }
 if(threadIdx.x==0)rows[id]=row;
}
void check(cudaError_t x){if(x!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(x));}
template<class A>A* alloc(size_t n){A*p;check(cudaMalloc(&p,n*sizeof(A)));return p;}
__global__ void validate_kernel(State a,Config c,double gamma,double *out){__shared__ double scratch[T],sh[2];forces(a,c,gamma,&sh[0],&sh[1],scratch);if(threadIdx.x==0){out[0]=sh[0];out[1]=sh[1];}}
double host_energy(State a,Config c,double gamma){double E=0;int n=c.L*c.L;for(int e=0;e<3*n;e++)if(a.alive[e]){V g,ga,gb;E+=stretch(displacement(a,e,c.L,gamma),a.q[e],c.r,g);int i=e/3,d=e%3,e0=3*next(i,d,c.L,-1)+d;if(a.alive[e0])E+=bend(displacement(a,e0,c.L,gamma),displacement(a,e,c.L,gamma),c.kappa,ga,gb);}return E;}
void gpucheck(const std::string &dir){int n=16,m=48;std::vector<V>u(n),v(n),f(n);std::vector<double>q(m);std::vector<unsigned char>mask(m,1);for(int i=0;i<n;i++)u[i]=V(.03*sin(i*2.),.04*cos(i*3.));for(int e=0;e<m;e++)q[e]=1+.01*sin(e);State h={u.data(),v.data(),f.data(),q.data(),mask.data(),mask.data()};Config c={0,0,4,0,.03,.5,0,.1,.005,.05,1e-9,1000};State a={alloc<V>(n),alloc<V>(n),alloc<V>(n),alloc<double>(m),alloc<unsigned char>(m),alloc<unsigned char>(m)};check(cudaMemcpy(a.u,u.data(),n*sizeof(V),cudaMemcpyHostToDevice));check(cudaMemcpy(a.q,q.data(),m*sizeof(double),cudaMemcpyHostToDevice));check(cudaMemcpy(a.alive,mask.data(),m,cudaMemcpyHostToDevice));double *out=alloc<double>(2),es[2];validate_kernel<<<1,T>>>(a,c,.13,out);check(cudaDeviceSynchronize());check(cudaMemcpy(es,out,2*sizeof(double),cudaMemcpyDeviceToHost));check(cudaMemcpy(f.data(),a.f,n*sizeof(V),cudaMemcpyDeviceToHost));double maxerr=0,dh=1e-6;for(int i=0;i<n;i++)for(int j=0;j<2;j++){double &x=j==0?u[i].x:u[i].y;x+=dh;double ep=host_energy(h,c,.13);x-=2*dh;double em=host_energy(h,c,.13);x+=dh;double force=j==0?f[i].x:f[i].y;maxerr=std::max(maxerr,fabs((ep-em)/(2*dh)+force));}double se=(host_energy(h,c,.13+dh)-host_energy(h,c,.13-dh))/(2*dh)/(n*sqrt(3.)/2);double serr=fabs(se-es[1]),eerr=fabs(host_energy(h,c,.13)-es[0]);double e0=host_energy(h,c,.13);for(auto &x:u)x=x+V(.7,-.8);double terr=fabs(host_energy(h,c,.13)-e0);std::ofstream o(dir+"/gpu-validation.json");o.precision(15);o<<"{\"full_network_force_fd_max_error\":"<<maxerr<<",\"shear_derivative_error\":"<<serr<<",\"cpu_gpu_energy_error\":"<<eerr<<",\"translation_energy_error\":"<<terr<<"}\n";if(maxerr>1e-7||serr>1e-7||eerr>1e-10||terr>1e-10)throw std::runtime_error("GPU validation failed");cudaFree(a.u);cudaFree(a.v);cudaFree(a.f);cudaFree(a.q);cudaFree(a.mask);cudaFree(a.alive);cudaFree(out);}
void selftest(const std::string &dir){std::mt19937_64 rng(67513);std::uniform_real_distribution<double>U(-.4,.4);double maxe=0,maxb=0,maxd=0;
 for(int k=0;k<100;k++){V a(1+U(rng),U(rng)),b(1+U(rng),U(rng)),ga,gb,g;double q=1+U(rng),r=.5,kap=.03,h=1e-6;stretch(a,q,r,g);bend(a,b,kap,ga,gb);
  for(int j=0;j<2;j++){V da(j==0?h:0,j==1?h:0),z,w;double fd=(stretch(a+da,q,r,z)-stretch(a-da,q,r,z))/(2*h);maxe=std::max(maxe,fabs(fd-(j==0?g.x:g.y)));fd=(bend(a+da,b,kap,z,w)-bend(a-da,b,kap,z,w))/(2*h);maxb=std::max(maxb,fabs(fd-(j==0?ga.x:ga.y)));fd=(bend(a,b+da,kap,z,w)-bend(a,b-da,kap,z,w))/(2*h);maxb=std::max(maxb,fabs(fd-(j==0?gb.x:gb.y)));}
  V z;double E=stretch(a,q,r,z),l=norm(a),q2=l+(q-l)*exp(-.05*exp(10*fabs(l-q)));maxd=std::max(maxd,stretch(a,q2,r,z)-E);
 }
 std::ofstream o(dir+"/selftest.json");o.precision(15);o<<"{\"stretch_gradient_max_error\":"<<maxe<<",\"bend_gradient_max_error\":"<<maxb<<",\"max_passivity_violation\":"<<maxd<<"}\n";if(maxe>1e-7||maxb>1e-7||maxd>1e-12)throw std::runtime_error("selftest failed");
}
int main(int argc,char **argv){try{if(argc<9){fprintf(stderr,"network L seeds kinds(0=hold,1=fracture,2=both) step dt maxiter tol outdir [seedstart]\n");return 1;}int L=atoi(argv[1]),seeds=atoi(argv[2]),kinds=atoi(argv[3]),maxiter=atoi(argv[6]),start=argc>9?atoi(argv[9]):0;double step=atof(argv[4]),dt=atof(argv[5]),tol=atof(argv[7]);std::string dir=argv[8];if(L<4||L>64||seeds<1||seeds>64||1.6/step+3>=MAXROW||5/dt+3>=MAXROW)throw std::runtime_error("invalid bounds");selftest(dir);gpucheck(dir);std::vector<Config> configs;std::vector<unsigned char> masks;int n=L*L,m=3*n;std::ofstream geom(dir+"/geometry.csv");geom<<"L,seed,architecture,edges,bends,largest_component_fraction,isolated_node_fraction,degree_variance\n";
 for(int seed=start;seed<start+seeds;seed++){std::mt19937_64 rng(71231+seed);std::uniform_real_distribution<double>U(0,1);std::vector<double> pri(m);for(auto &x:pri)x=U(rng);double phase=U(rng)*6.283185307179586;
  for(int arch=0;arch<2;arch++){std::vector<std::pair<double,int>>rank;for(int e=0;e<m;e++){int i=e/3;double x=(i%L)/double(L),y=(i/L)/double(L);double h=cos(6.283185307179586*x+phase)*cos(6.283185307179586*y-phase);rank.push_back({pri[e]+arch*.3*h,e});}std::sort(rank.begin(),rank.end());std::vector<unsigned char> mask(m,0);for(int e=0;e<int(1.8*n);e++)mask[rank[e].second]=1;
   std::vector<int> parent(n),sizes(n,1),degree(n,0);for(int i=0;i<n;i++)parent[i]=i;auto find=[&](int x){while(parent[x]!=x){parent[x]=parent[parent[x]];x=parent[x];}return x;};int bends=0;for(int e=0;e<m;e++)if(mask[e]){int i=e/3,d=e%3,j=next(i,d,L);degree[i]++;degree[j]++;int a=find(i),b=find(j);if(a!=b){parent[b]=a;sizes[a]+=sizes[b];}bends+=mask[3*next(i,d,L,-1)+d];}int largest=0,isolated=0;double var=0,mean=2.*int(1.8*n)/n;for(int i=0;i<n;i++){largest=std::max(largest,sizes[find(i)]);isolated+=degree[i]==0;var+=(degree[i]-mean)*(degree[i]-mean);}geom<<L<<','<<seed<<','<<arch<<','<<int(1.8*n)<<','<<bends<<','<<double(largest)/n<<','<<double(isolated)/n<<','<<var/n<<'\n';
   for(double kap:{.003,.03})for(int model=0;model<4;model++)for(int kind=0;kind<2;kind++){if(kinds!=2&&kind!=kinds)continue;for(double threshold:{.1,.2}){if(kind==0&&threshold==.2)continue;Config c={seed,arch,L,kind,kap,model==0?1.:(model==3?.8:.5),model>=2?10.:0.,threshold,step,dt,tol,maxiter};configs.push_back(c);masks.insert(masks.end(),mask.begin(),mask.end());}}
  }
 }
 int count=configs.size();fprintf(stderr,"cases=%d nodes/case=%d edges/case=%d\n",count,n,int(1.8*n));fflush(stderr);Config *cfg=alloc<Config>(count);check(cudaMemcpy(cfg,configs.data(),count*sizeof(Config),cudaMemcpyHostToDevice));State a={alloc<V>(count*n),alloc<V>(count*n),alloc<V>(count*n),alloc<double>(count*m),alloc<unsigned char>(count*m),alloc<unsigned char>(count*m)};a.histS=alloc<V>(count*5*n);a.histY=alloc<V>(count*5*n);a.back=alloc<V>(count*n);a.oldf=alloc<V>(count*n);check(cudaMemcpy(a.mask,masks.data(),count*m,cudaMemcpyHostToDevice));double *output=alloc<double>(size_t(count)*MAXROW*NCOL);int *rows=alloc<int>(count);auto t0=std::chrono::steady_clock::now();run<<<count,T>>>(cfg,a,output,rows);check(cudaGetLastError());check(cudaDeviceSynchronize());double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
 std::vector<int> nr(count);std::vector<double> out(size_t(count)*MAXROW*NCOL);check(cudaMemcpy(nr.data(),rows,count*sizeof(int),cudaMemcpyDeviceToHost));check(cudaMemcpy(out.data(),output,out.size()*sizeof(double),cudaMemcpyDeviceToHost));
 std::ofstream o(dir+"/trajectories.csv");o.precision(12);o<<"case,L,seed,architecture,kappa,r,beta,kind,threshold,step,dt,tolerance,maxiter,stage,gamma,time,stress,energy,fmax,iterations,alive,strain2,strain4,max_abs_strain,nonaffinity,G0,Gcheck,failed_solves,broken,mean_q\n";
 for(int id=0;id<count;id++){auto c=configs[id];for(int j=0;j<nr[id];j++){o<<id<<','<<L<<','<<c.seed<<','<<c.arch<<','<<c.kappa<<','<<c.r<<','<<c.beta<<','<<c.kind<<','<<c.threshold<<','<<c.step<<','<<c.dt<<','<<c.tol<<','<<c.maxiter;for(int k=0;k<NCOL;k++)o<<','<<out[(size_t(id)*MAXROW+j)*NCOL+k];o<<'\n';}}std::ofstream field(dir+"/example-fields.csv");field.precision(12);field<<"case,seed,architecture,kappa,r,beta,node,x,y,ux,uy,edge0,edge1,edge2\n";for(int id=0;id<count;id++){auto c=configs[id];if(c.seed!=start||c.kind!=0||c.kappa!=.003||c.r!=1)continue;std::vector<V> uv(n);check(cudaMemcpy(uv.data(),a.u+id*n,n*sizeof(V),cudaMemcpyDeviceToHost));for(int i=0;i<n;i++)field<<id<<','<<c.seed<<','<<c.arch<<','<<c.kappa<<','<<c.r<<','<<c.beta<<','<<i<<','<<(i%L)+.5*(i/L)<<','<<sqrt(3.)/2*(i/L)<<','<<uv[i].x<<','<<uv[i].y<<','<<int(masks[id*m+3*i])<<','<<int(masks[id*m+3*i+1])<<','<<int(masks[id*m+3*i+2])<<'\n';}std::ofstream meta(dir+"/execution.json");meta<<"{\"cases\":"<<count<<",\"gpu_seconds\":"<<seconds<<",\"nodes_per_case\":"<<n<<",\"retained_edges_per_case\":"<<int(1.8*n)<<"}\n";fprintf(stderr,"complete seconds=%.3f\n",seconds);
}catch(std::exception &e){fprintf(stderr,"ERROR: %s\n",e.what());return 2;}return 0;}
