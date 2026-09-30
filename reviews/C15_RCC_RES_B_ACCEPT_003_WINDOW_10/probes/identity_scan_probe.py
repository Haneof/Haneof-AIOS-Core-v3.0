#!/usr/bin/env python3
"""Read-only scan for competing/retired persistence identity strings in a run archive."""
import argparse,json,re
from pathlib import Path
PAT=re.compile(r'c15-rcc-res-b-(?:rerun|session)-[A-Za-z0-9-]+')
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--run-root',type=Path,required=True); ap.add_argument('--output',type=Path); a=ap.parse_args(); root=a.run_root.resolve(); counts={}; locations={}; unreadable=[]
 for p in root.rglob('*'):
  if not p.is_file(): continue
  try:
   text=p.read_text(encoding='utf-8')
  except (UnicodeDecodeError,OSError):
   unreadable.append(str(p.relative_to(root))); continue
  for match in PAT.finditer(text):
   key=match.group(0); counts[key]=counts.get(key,0)+1; locations.setdefault(key,[]).append(str(p.relative_to(root)))
 result={'root':str(root),'unique_persistence_identity_strings':sorted(counts),'occurrence_counts':counts,'locations_by_identity':locations,'retired_rerun002_occurrences':sum(v for k,v in counts.items() if 'rerun-002' in k or 'session-002' in k),'unreadable_nontext_files':len(unreadable),'unreadable_paths':unreadable}
 out=json.dumps(result,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(out,encoding='utf-8')
 else:print(out)
if __name__=='__main__':main()
