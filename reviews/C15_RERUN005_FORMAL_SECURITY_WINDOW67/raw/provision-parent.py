import os,pathlib,json,stat,hashlib
E=pathlib.Path(os.environ['W67']);S=E/'candidate';H=S/os.environ['H67'];m=json.loads((H/'IDENTITY.json').read_text());r=[]
for group,root in [('harness',H),('core',S/'src/aios_core'),('c15',S/'tools/c15_persistence')]:
 for kind,entries in [('directory_modes',m['directory_modes'][group]),('file_modes',m['file_modes'][group])]:
  for rel,mode in entries.items():
   p=root/rel;before=stat.S_IMODE(p.stat().st_mode);digest=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None;p.chmod(mode);assert stat.S_IMODE(p.stat().st_mode)==mode
   if digest:assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
   r.append({'path':str(p.relative_to(S)),'before':before,'after':mode,'bytes_unchanged':True})
(E/'parent-mode-provisioning.json').write_text(json.dumps(r,indent=2));print('DECLARED_MODES_PROVISIONED',len(r),'NO_BYTE_CHANGES')
