import pathlib,os,shutil,json,hashlib,re
E=pathlib.Path(os.environ['W67']);P=E/'publication';D=P/'reviews/C15_RERUN005_FORMAL_SECURITY_WINDOW67';D.mkdir(parents=True,exist_ok=False)
for p in (E/'deliverables').iterdir():shutil.copy2(p,D/p.name)
raw=D/'raw';raw.mkdir()
for p in E.iterdir():
 if p.is_file():shutil.copy2(p,raw/p.name)
for name in ['regression-attempt1','parent-attempt1']:
 if (E/name).exists():shutil.copytree(E/name,raw/name)
records={};bad=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 data=p.read_bytes();records[str(p.relative_to(D))]={'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}
 # Match actual multi-line key blocks, not the regex source itself.
 if re.search(b'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----'+bytes([10])+b'[A-Za-z0-9+/=]+',data):bad.append(str(p.relative_to(D)))
assert not bad,bad
(D/'PUBLICATION_SECRET_REVIEW.json').write_text(json.dumps({'private_key_blocks_found':bad,'scope':'all packaged files; actual PEM block detection plus manual provenance review; no Operator/Resident private bytes or issued grants were collected','production_or_hosted_acceptance_claimed':False},indent=2))
(D/'SHA256.json').write_text(json.dumps(records,sort_keys=True,indent=2))
(E/'publication-pr-body.md').write_text('Independent Window67 validation of frozen PR370 candidate 6fb725407569bc719c049587f67fe65e797eb734. Formal disposition: FAIL / DO NOT MERGE. Original38:31PASS/7FAIL; Window55:33PASS; Window57:29PASS. Frozen parent independently reproduces the same seven failures. Fresh signed lifecycle, replay/CAS/crash and cross-environment gates remain BLOCKED; no new Operator enrollment was issued by this Reviewer. Evidence only; no engineering/test assertion changes, no Resident startup, no independent acceptance, no merge authorization.')
print('PACKAGED',len(records),'files',D)
