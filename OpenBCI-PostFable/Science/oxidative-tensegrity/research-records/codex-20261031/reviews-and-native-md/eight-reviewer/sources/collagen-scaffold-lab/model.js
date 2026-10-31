/* Original, dependency-free educational mechanics. Length: mm. Modulus: kPa. */
(function(root){
'use strict';
const types=['cubic','bcc','octet','reinforced'];
const defaults={type:'octet',cells:3,pitch:0.6,radius:0.025,modulus:100,strain:0.03,axis:2};
function geometry(p){
 const n=p.cells, a=p.pitch, nodes=[],edges=[],lookup=new Map(),seen=new Set();
 const add=(x,y,z)=>{const k=[x,y,z].join(',');if(!lookup.has(k)){lookup.set(k,nodes.length);nodes.push([x*a,y*a,z*a]);}return lookup.get(k);};
 const edge=(i,j)=>{const k=[Math.min(i,j),Math.max(i,j)].join(',');if(i!==j&&!seen.has(k)){seen.add(k);edges.push([i,j]);}};
 for(let x=0;x<=n;x++)for(let y=0;y<=n;y++)for(let z=0;z<=n;z++)add(x,y,z);
 if(p.type==='cubic'||p.type==='reinforced')for(let x=0;x<=n;x++)for(let y=0;y<=n;y++)for(let z=0;z<=n;z++){
  const i=add(x,y,z);if(x<n)edge(i,add(x+1,y,z));if(y<n)edge(i,add(x,y+1,z));if(z<n)edge(i,add(x,y,z+1));
 }
 if(p.type==='bcc'||p.type==='reinforced')for(let x=0;x<n;x++)for(let y=0;y<n;y++)for(let z=0;z<n;z++){
  const c=add(x+.5,y+.5,z+.5);for(let dx=0;dx<=1;dx++)for(let dy=0;dy<=1;dy++)for(let dz=0;dz<=1;dz++)edge(c,add(x+dx,y+dy,z+dz));
 }
 if(p.type==='octet'){
  for(let x=0;x<n;x++)for(let y=0;y<n;y++)for(let z=0;z<=n;z++)add(x+.5,y+.5,z);
  for(let x=0;x<n;x++)for(let z=0;z<n;z++)for(let y=0;y<=n;y++)add(x+.5,y,z+.5);
  for(let y=0;y<n;y++)for(let z=0;z<n;z++)for(let x=0;x<=n;x++)add(x,y+.5,z+.5);
  for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
   const d=nodes[i].reduce((s,v,k)=>s+(v-nodes[j][k])**2,0);if(Math.abs(d-a*a/2)<1e-8)edge(i,j);
  }
 }
 return {nodes,edges,size:n*a};
}
function evaluate(p,g=geometry(p)){
 const area=Math.PI*p.radius**2,V=g.size**3, direction=[0,0,0],lengths=[];
 let totalLength=0;
 for(const [i,j] of g.edges){const d=g.nodes[j].map((v,k)=>v-g.nodes[i][k]),L=Math.hypot(...d);lengths.push(L);totalLength+=L;for(let k=0;k<3;k++)direction[k]+=p.modulus*area*L/V*(d[k]/L)**4;}
 const density=area*totalLength/V,porosity=1-density,E=direction[p.axis];
 return {density,porosity,moduli:direction,E,stress:E*p.strain,energy:.5*E*p.strain**2,solidVolume:area*totalLength,totalLength,minLength:Math.min(...lengths),surface:2*Math.PI*p.radius*totalLength/V,valid:density<1};
}
function sweep(p,equalDensity=false){const target=evaluate(p).density;return types.map(type=>{
 const q={...p,type};if(equalDensity)q.radius*=Math.sqrt(target/evaluate(q).density);
 return {parameters:q,metrics:evaluate(q)};
});}
function graphml(p){const g=geometry(p);return '<?xml version="1.0" encoding="UTF-8"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'+['x','y','z'].map(k=>`<key id="${k}" for="node" attr.name="${k}_mm" attr.type="double"/>`).join('\n')+'\n<key id="radius" for="edge" attr.name="radius_mm" attr.type="double"/>\n<graph id="scaffold_geometry" edgedefault="undirected">\n'+g.nodes.map((v,i)=>`<node id="n${i}">${v.map((x,k)=>`<data key="${['x','y','z'][k]}">${x}</data>`).join('')}</node>`).join('\n')+'\n'+g.edges.map(([i,j],k)=>`<edge id="e${k}" source="n${i}" target="n${j}"><data key="radius">${p.radius}</data></edge>`).join('\n')+'\n</graph></graphml>';}
const api={types,defaults,geometry,evaluate,sweep,graphml};if(typeof module!=='undefined')module.exports=api;root.Scaffold=api;
})(typeof globalThis!=='undefined'?globalThis:this);
