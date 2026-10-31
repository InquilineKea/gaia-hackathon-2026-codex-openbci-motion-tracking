"""Original static-source audit and analytic counterexample; no project code imported."""
import ast,json,pathlib,hashlib,math,sys
p=pathlib.Path(sys.argv[1])
source=p.read_text();tree=ast.parse(source);func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='scale_stiffness')
call=next(n for n in ast.walk(func) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='replace')
fields=[k.arg for k in call.keywords];s=2.3;mu=1.;mu_el=.1
# Homogeneous intact FCC axial stiffness is proportional to mu+mu_el.
wrong=(s*mu+mu_el)/(mu+mu_el);correct=(s*mu+s*mu_el)/(mu+mu_el)
report=dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),scaled_fields=fields,mu_el_scaled='mu_el' in fields,default_elastin=0.,counterexample=dict(mu=mu,mu_el=mu_el,s=s,observed_modulus_ratio=wrong,required_ratio=s,relative_shortfall=1-wrong/s,corrected_ratio=correct),conclusion='Exact global rescaling holds for zero background, but not general nonzero mu_el with the inspected helper. This is an analytic/static audit, not a full FCC solver rerun.')
out=pathlib.Path(sys.argv[2]);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
