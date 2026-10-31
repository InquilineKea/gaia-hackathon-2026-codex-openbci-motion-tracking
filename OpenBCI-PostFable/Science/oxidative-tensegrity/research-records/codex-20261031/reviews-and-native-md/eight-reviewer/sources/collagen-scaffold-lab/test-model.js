'use strict';
const assert=require('node:assert/strict');const M=require('./model.js');
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-9*Math.max(1,Math.abs(b)),`${a} != ${b}`);
for(const type of M.types){
 const p={...M.defaults,type},g=M.geometry(p),v=M.evaluate(p,g);
 assert.equal(new Set(g.edges.map(e=>e.join(','))).size,g.edges.length);
 assert.ok(g.edges.every(([i,j])=>i!==j&&g.nodes[i]&&g.nodes[j]));
 // Every node is connected, checked independently by graph traversal.
 const visited=new Set([0]);for(let changed=true;changed;){changed=false;for(const [a,b] of g.edges)if(visited.has(a)!==visited.has(b)){visited.add(a);visited.add(b);changed=true;}}assert.equal(visited.size,g.nodes.length);
 near(v.moduli[0],v.moduli[1]);near(v.moduli[1],v.moduli[2]);
 near(M.evaluate({...p,modulus:p.modulus*2}).E,v.E*2);
 near(M.evaluate({...p,radius:p.radius*2}).E,v.E*4);
 near(M.evaluate({...p,pitch:p.pitch*2,radius:p.radius*2}).E,v.E);
 near(M.evaluate({...p,strain:0}).stress,0);
 assert.ok(v.porosity>0&&v.porosity<1);
 for(const r of M.sweep(p,true))near(r.metrics.density,v.density);
}
// Closed-form cubic network has n(n+1)^2 members in each direction.
const p={...M.defaults,type:'cubic'},g=M.geometry(p),n=p.cells;
assert.equal(g.nodes.length,(n+1)**3);assert.equal(g.edges.length,3*n*(n+1)**2);
near(M.evaluate(p).E,p.modulus*Math.PI*p.radius**2*(n+1)**2/(n*n*p.pitch**2));
const cell=M.geometry({...p,cells:1,type:'octet'});assert.equal(cell.nodes.length,14);assert.equal(cell.edges.length,36);
// Independent finite-difference energy curvature verifies the directional tensor sum.
for(const type of M.types){const q={...M.defaults,type},h=1e-5,geo=M.geometry(q),A=Math.PI*q.radius**2;let U=0;for(const [i,j] of geo.edges){const d=geo.nodes[j].map((v,k)=>v-geo.nodes[i][k]),L=Math.hypot(...d);d[q.axis]*=1-h;const dl=Math.hypot(...d)-L;U+=.5*q.modulus*A/L*dl*dl;}const finite=2*U/(h*h*geo.size**3);assert.ok(Math.abs(finite/M.evaluate(q).E-1)<2e-5);}
console.log('PASS: all four networks connected; cubic closed form; octet topology; symmetry; scaling; matched density; zero strain; independent energy curvature.');
