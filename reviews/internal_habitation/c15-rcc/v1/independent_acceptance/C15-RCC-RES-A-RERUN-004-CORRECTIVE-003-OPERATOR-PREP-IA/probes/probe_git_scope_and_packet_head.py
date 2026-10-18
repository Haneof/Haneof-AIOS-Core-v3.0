import subprocess, json, hashlib
C='10901d467679b70437ae112747eab81f889fd5cb'; P='abb8b435e5187c7c6c2f4332aea37cd805b4a53c'; expected='reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-004-CORRECTIVE-003-OPERATOR-PREP/'
paths=subprocess.check_output(['git','diff','--name-only',P,C],text=True).splitlines()
packet_path=expected+'RESIDENT_SAFE_LAUNCH_PACKET.json'
packet=json.loads(subprocess.check_output(['git','show',C+':'+packet_path],text=True))
checks={'head':subprocess.check_output(['git','show','-s','--format=%H',C],text=True).strip()==C,'parent':subprocess.check_output(['git','show','-s','--format=%P',C],text=True).strip()==P,'tree':subprocess.check_output(['git','show','-s','--format=%T',C],text=True).strip()=='db79761216529cf83f217ab00c937bc79806a510','scope':all(x.startswith(expected) for x in paths),'packet_parent':packet['operator_prep_exact_head']==P,'packet_absent_parent':subprocess.run(['git','cat-file','-e',P+':'+packet_path],capture_output=True).returncode!=0}
print(json.dumps({'paths':paths,'checks':checks},indent=2)); assert all(checks.values())
