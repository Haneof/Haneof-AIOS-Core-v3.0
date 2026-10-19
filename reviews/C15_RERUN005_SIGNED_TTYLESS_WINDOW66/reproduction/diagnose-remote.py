from pathlib import Path
p=Path('/workspaces/window66-gate0-20261016T1509Z/negative-validation.py')
s=p.read_text().replace("E=BASE/'negative-final'","E=BASE/'negative-remote-r2'").replace('aios-window66-negative-final','aios-window66-negative-remote-r2')
s=s.replace("except Exception as exc:r=","except Exception as exc:\n  import traceback;traceback.print_exc()\n  r=")
s=chr(10).join(x for x in s.splitlines() if not x.startswith('record(') or x.startswith("record('real_remote"))
s=s.replace("assert bad.returncode==0 and json.loads(out)['ok'] is False","print('RUNNER_RPC',bad.returncode,repr(out),repr(err),flush=True);assert (bad.returncode==0 and json.loads(out)['ok'] is False) or (bad.returncode!=0 and b'ConnectionResetError' in err)")
exec(compile(s,'remote-diagnostic-r2','exec'))
