"""Isolated byte publisher; private signing authority is never importable.

Only an already registered request may receive one external response. There is
no generic signing endpoint and no model, router, or response generator.
"""
if __name__ != '__main__':
    raise ImportError('publisher authority is subprocess-only')

import base64
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import stat
import select
import time
import sys

from r005.atomic import atomic_write_bytes
from r005.canonical import canonical_json_bytes
from r005.bridge import ExchangeBridge
from r005.schema import parse_model_directive
from r005.payload import parse
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.late_return import late_return_message


def prime(bits):
    while True:
        n=secrets.randbits(bits)|(1<<(bits-1))|1
        if any(n%p==0 for p in (3,5,7,11,13,17,19,23,29,31,37,41)):
            continue
        d=n-1;s=0
        while d%2==0:d//=2;s+=1
        valid=True
        for _ in range(32):
            a=secrets.randbelow(n-3)+2;x=pow(a,d,n)
            if x in (1,n-1):continue
            for _ in range(s-1):
                x=pow(x,2,n)
                if x==n-1:break
            else:valid=False;break
        if valid:return n


root=Path(sys.argv[1]);sockpath=sys.argv[2];runner_pid=int(sys.argv[3])
parent_fd=int(sys.argv[4])
parent_lifetime=select.poll()
parent_lifetime.register(parent_fd,select.POLLHUP|select.POLLERR)
p=q=0;n=0;e=65537
while n.bit_length()!=2048 or p==q or math.gcd(e,(p-1)*(q-1))!=1:
    p=prime(1024);q=prime(1024);n=p*q
d=pow(e,-1,(p-1)*(q-1));del p,q
key_id='resident-publisher-'+secrets.token_hex(12)
public={'key_id':key_id,'algorithm':'rsa-pkcs1v15-sha256',
    'modulus_hex':format(n,'x'),'public_exponent':e}
atomic_write_bytes(root/'publisher-public.json',canonical_json_bytes(public))
registered={}
# This capability is emitted only to the external session's inherited stdout.
# It is never returned over IPC, stored in run state, passed to Core, or logged
# by Runner. A recovery caller with the public descriptor cannot authorize bytes.
if stat.S_ISREG(os.fstat(1).st_mode):
    raise RuntimeError('Resident authorization must go to session pipe/terminal, never a disk log')
authorization=secrets.token_urlsafe(48)
print('RESIDENT_PUBLISH_AUTHORIZATION='+authorization,flush=True)


def sign(message):
    info=bytes.fromhex('3031300d060960864801650304020105000420')+hashlib.sha256(message).digest()
    em=b'\x00\x01'+b'\xff'*(256-len(info)-3)+b'\x00'+info
    sig=pow(int.from_bytes(em,'big'),d,n).to_bytes(256,'big').hex()
    return 'bglate_rsa_v1:'+key_id+':'+sig


channel=Path(sockpath);channel.mkdir(mode=0o700)
atomic_write_bytes(channel/'ready.json',canonical_json_bytes({'publisher_pid':os.getpid()}))
try:
    while True:
        if parent_lifetime.poll(0):break
        commands=sorted(channel.glob('*.command.json'))
        if not commands:
            time.sleep(.01);continue
        for command_file in commands:
            output=command_file.with_suffix('.result')
            if output.exists():continue
            try:
                command=json.loads(command_file.read_bytes());peer=int(command['caller_pid'])
                os.kill(peer,0)
                if peer==os.getpid():raise ValueError('publisher cannot call itself')
                rid=command['request_id'];b=ExchangeBridge(root)
                if command['command']=='register':
                    if peer!=runner_pid:raise ValueError('only live runner may register requests')
                    if rid in registered:raise ValueError('request already registered')
                    req=b.requests.payload(rid)
                    if command['request_sha256']!=b.request_sha256(rid):raise ValueError('request digest mismatch')
                    registered[rid]={'sha256':command['request_sha256'],'context':command['context']}
                    result={'registered':rid,'publisher_pid':os.getpid()}
                elif command['command']=='publish':
                    if parent_lifetime.poll(0):
                        raise ValueError('runner process is no longer live')
                    authorization_message=canonical_json_bytes({k:command[k] for k in ('request_id','request_sha256','raw')})
                    expected_authorization=hmac.new(authorization.encode(),authorization_message,hashlib.sha256).hexdigest()
                    if not secrets.compare_digest(str(command.get('authorization_proof','')),expected_authorization):
                        raise ValueError('external Resident authorization required')
                    if peer==runner_pid:raise ValueError('runner cannot publish a semantic response')
                    if rid not in registered:raise ValueError('unregistered/stale request')
                    registration=registered[rid]
                    if command['request_sha256']!=registration['sha256']:raise ValueError('request digest mismatch')
                    raw=base64.b64decode(command['raw'],validate=True)
                    req=b.requests.payload(rid)
                    directive=parse(req['kind'],raw)
                    if req['kind']=='model_directive':
                        binding=req['body']['provenance_binding']
                        if directive.provenance is None or {k:getattr(directive.provenance,k) for k in binding}!=binding:
                            raise ValueError('external response provenance mismatch')
                    # Validation does not alter any external response bytes.
                    b.requests.payload(rid)
                    result=b.responses.publish_bytes(request_id=rid,response_bytes=raw)
                    proof_path=root/'proofs'/f'{rid}.json'
                    if proof_path.exists():
                        proof=json.loads(proof_path.read_bytes())
                        if proof['response_sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('conflicting proof replay')
                    else:
                        proof={'request_id':rid,'request_sha256':registration['sha256'],
                            'response_sha256':hashlib.sha256(raw).hexdigest(),
                            'publisher_pid':os.getpid(),'runner_pid':runner_pid,'core_proof':None}
                        if registration['context'] is not None:
                            if directive.provenance is None:raise ValueError('background return requires external provenance')
                            payload=encode_model_directive(directive)
                            fp=hashlib.sha256(payload.encode()).hexdigest()
                            fields={**registration['context'],
                                'provider':directive.provenance.provider,'model':directive.provenance.model,
                                'provider_request_id':directive.provenance.request_id,
                                'response_fingerprint':fp,'payload_sha256':fp}
                            proof['core_proof']=sign(late_return_message(**fields))
                        message=canonical_json_bytes({k:proof[k] for k in ('request_id','request_sha256','response_sha256')})
                        proof['exchange_proof']=sign(message)
                        atomic_write_bytes(proof_path,canonical_json_bytes(proof))
                    result.update({'proof':str(proof_path),'publisher_pid':os.getpid()})
                else:raise ValueError('unsupported publisher command')
                atomic_write_bytes(output,canonical_json_bytes({'ok':True,'result':result}))
            except Exception as exc:
                atomic_write_bytes(output,canonical_json_bytes({'ok':False,'error':str(exc)}))
finally:
    (channel/'ready.json').unlink(missing_ok=True)
