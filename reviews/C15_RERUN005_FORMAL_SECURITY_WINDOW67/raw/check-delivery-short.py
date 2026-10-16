import os,pathlib,json,subprocess as sp,hashlib,sys
E=pathlib.Path(os.environ['W67']);S=E/'candidate';H=S/os.environ['H67'];B=H.parent;R=[]
def run(n,a):
 p=sp.run(a,cwd=S,capture_output=True,text=True,start_new_session=True);(E/(n+'.stdout')).write_text(p.stdout);(E/(n+'.stderr')).write_text(p.stderr);(E/(n+'.exit')).write_text(str(p.returncode));R.append({'name':n,'argv':a,'returncode':p.returncode});return p
inv=json.loads((B/'artifacts/MEMBERS.json').read_text());a=[sys.executable,'-I',str(S/'reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/materialize.py'),str(B/'artifacts/resident-harness.tar.gz'),str(E/'materialized'),'82aa3ff81d9492e0828934b5744adf4129fb6dc1361303a537379a603a319de3',json.dumps(inv)]
run('materialize-first',a);run('materialize-repeat',a)
run('materialized-verify',[sys.executable,'-I',str(E/'materialized/harness/launch.py'),'--source-repo',str(S),'--identity-sha256','364cc03617fcd782327b3307720baf5371839185b1b07b71476308af74c5a817','verify'])
m=json.loads((S/'reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/ORIGINAL38_SOURCE_SHA256.json').read_text());assert all(hashlib.sha256((S/'reviews/WINDOW67_ORIGINAL38_UNMODIFIED'/n).read_bytes()).hexdigest()==v for n,v in m.items());R.append({'name':'ORIGINAL38_ASSERTIONS_BYTE_IDENTICAL','status':'PASS','files':len(m)})
for n in ['enrollment.json','expired.json','tampered-enrollment.json','wrong_key_binding.json','wrong_scope.json']:
 code='import sys;sys.path.insert(0,'+repr(str(H))+');from r005.response_authorization import load_grant;load_grant('+repr('/var/lib/aios-window65/trust/'+n)+')'
 run('grant-reject-'+n,[sys.executable,'-B','-c',code])
(E/'delivery-grant-commands.json').write_text(json.dumps(R,indent=2));print(json.dumps([{k:v for k,v in r.items() if k!='argv'} for r in R],indent=2))
