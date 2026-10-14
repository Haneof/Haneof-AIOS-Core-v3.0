"""Mechanical external-session transport over current Core/C15 contracts."""
from __future__ import annotations
import base64
from datetime import datetime,timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
import tempfile
import time
import uuid

from aios_core.headless.core import HeadlessConfig,HeadlessCore
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.late_return import LateReturnVerifier,verify_late_return_proof
from tools.c15_persistence.backend import RunBackend,GenerationStore,require
from tools.c15_persistence.relay import RelayJournal
from tools.c15_persistence.remote_backend import push_run_state,verify_local_remote_authority
from .atomic import atomic_write_bytes,fsync_dir
from .bridge import ExchangeBridge,ExchangeContractError
from .canonical import canonical_json_bytes
from .schema import serialize_runtime_snapshot,parse_model_directive
from .payload import parse


def rpc(sockpath,command):
    channel=Path(sockpath)
    require((channel/'ready.json').is_file(),'publisher channel unavailable')
    command_file=channel/(uuid.uuid4().hex+'.command.json')
    atomic_write_bytes(command_file,canonical_json_bytes({**command,'caller_pid':os.getpid()}))
    output=command_file.with_suffix('.result');deadline=time.monotonic()+30
    while not output.is_file():
        require(time.monotonic()<deadline,'publisher IPC acknowledgement timed out')
        time.sleep(.01)
    raw=output.read_bytes()
    result=json.loads(raw)
    require(result['ok'],str(result.get('error')))
    return result['result']


def artifacts(backend):
    # Never archive a live database while committed bytes remain only in WAL.
    # The accepted remote helper is still used for CAS; this wrapper requires
    # the SQLite checkpoint result before excluding WAL files from artifacts.
    for db in sorted(backend.root.rglob('*.sqlite')):
        if db.relative_to(backend.root).parts[0]=='generations':continue
        connection=sqlite3.connect(str(db),timeout=1)
        try:
            status=connection.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            require(status is not None and status[0]==0,'SQLite checkpoint busy or uncertain')
        finally:connection.close()
        wal=Path(str(db)+'-wal')
        require(not wal.exists() or wal.stat().st_size==0,'SQLite WAL not durably checkpointed')
        with db.open('rb') as handle:os.fsync(handle.fileno())
        fsync_dir(db.parent)
    result={}
    for p in backend.root.rglob('*'):
        rel=p.relative_to(backend.root)
        if rel.parts[0]=='generations' or p.name in {'.owner.lock','.remote-head','provider.pid'}:
            continue
        if p.is_file() and not p.is_symlink() and not p.name.endswith(('-wal','-shm','.tmp')):
            result[str(rel)]=p.read_bytes()
    return result


def barrier(backend,repo,label):
    generation=GenerationStore(backend).seal(artifacts(backend),label=label)
    RelayJournal(backend).ledger_set('generation',str(generation))
    return push_run_state(backend,repo_dir=repo,message='Resident mechanical durability: '+label)


def paths(backend):
    return backend.state_dir/'runtime/world.sqlite',backend.state_dir/'runtime/index.sqlite'


def init(root,run_id,session_id,subject_id,repo):
    backend=RunBackend.create(root,run_id=run_id,session_id=session_id,subject_id=subject_id,
        phase='A',remote_authority={'remote':'origin','remote_ref':'refs/heads/persistence/'+run_id})
    try:
        RelayJournal(backend,create=True)
        world,index=paths(backend)
        def unavailable(_snapshot):raise ExchangeContractError('no model call permitted in init')
        core=HeadlessCore(config=HeadlessConfig(world_path=world,index_path=index,subject_id=subject_id),
            model_handler=unavailable).start();core.stop()
        barrier(backend,repo,'fresh-init')
        return {'run_id':run_id,'session_id':session_id,'world':str(world),'index':str(index),
            'release_state':str(backend.state_dir/'runtime/release_state.json')}
    finally:backend.release()


class ExternalHandler:
    def __init__(self,backend,journal,exchange,sockpath,repo,verifier,spec):
        self.backend=backend;self.journal=journal;self.bridge=ExchangeBridge(exchange)
        self.sockpath=sockpath;self.repo=repo;self.verifier=verifier;self.spec=spec
        self.contexts={};self.requests=[];self.runtime=None

    def accept_return_context(self,snapshot,context):
        require(context.attempt_id not in self.contexts,'duplicate dispatch context')
        self.contexts[context.attempt_id]=context.scope_fields()

    def summary(self,kind,payload):
        identity={k:self.backend.owner[k] for k in ('run_id','session_id','subject_id')}
        body=json.loads(canonical_json_bytes(payload))
        request=self.bridge.publish_request(kind=kind,body={'identity':identity,'summary_input':body})
        rid=request['request_id'];self.requests.append((rid,None))
        barrier(self.backend,self.repo,'summary-request-'+rid)
        rpc(self.sockpath,{'command':'register','request_id':rid,
            'request_sha256':request['request_sha256'],'context':None})
        atomic_write_bytes(self.bridge.root/'ready'/f'{rid}.json',canonical_json_bytes(request))
        deadline=time.monotonic()+float(self.spec['timeout']);proofpath=self.bridge.root/'proofs'/f'{rid}.json'
        while not proofpath.is_file():
            require(time.monotonic()<deadline,'Summary response wait expired');time.sleep(.02)
        raw=self.bridge.await_response_bytes(rid,timeout_s=0);proof=json.loads(proofpath.read_bytes())
        require(proof['request_id']==rid and proof['request_sha256']==request['request_sha256'],
            'Summary proof request mismatch')
        require(proof['response_sha256']==hashlib.sha256(raw).hexdigest(),'Summary proof bytes mismatch')
        message=canonical_json_bytes({k:proof[k] for k in ('request_id','request_sha256','response_sha256')})
        require(verify_late_return_proof(self.verifier,message=message,proof=proof['exchange_proof']),
            'Summary external signature invalid')
        text=parse(kind,raw)
        _,commit=barrier(self.backend,self.repo,'summary-return-'+rid)
        atomic_write_bytes(self.bridge.root/'committed'/f'{rid}.json',canonical_json_bytes({
            'request_id':rid,'response_sha256':hashlib.sha256(raw).hexdigest(),'remote_commit':commit}))
        self.bridge.consume_response(rid)
        return text

    def __call__(self,snapshot):
        from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
        require(isinstance(snapshot,RuntimeSnapshot),'genuine RuntimeSnapshot required')
        ctx=self.contexts.get(snapshot.model_attempt_id)
        identity={k:self.backend.owner[k] for k in ('run_id','session_id','subject_id')}
        binding={'provider':'external-resident','model':identity['session_id'],
            'request_id':ctx['relay_id'] if ctx else 'resident-'+uuid.uuid4().hex}
        request=self.bridge.publish_request(kind='model_directive',body={
            'identity':identity,'snapshot':serialize_runtime_snapshot(snapshot),'provenance_binding':binding})
        rid=request['request_id'];self.requests.append((rid,snapshot.model_attempt_id))
        if ctx:
            metadata={'run_id':identity['run_id'],'session_id':identity['session_id'],
                'cursor':self.spec['cursor'],'event_id':self.spec['event_id'],'round':snapshot.round_index,
                'model_request_id':rid,'attempt_id':ctx['attempt_id'],'nonce':rid,
                'request_fingerprint':ctx['outbound_request_fingerprint'],
                'binding_digest':hashlib.sha256(canonical_json_bytes(self.spec)).hexdigest(),
                'provider':binding['provider'],'model':binding['model']}
            self.journal.stage(metadata,self.bridge.requests.path_for(rid).read_bytes(),
                generation=GenerationStore(self.backend).latest() or 0)
            self.journal.expose(rid)
        # The approved reader/publisher sees a request only after remote durability.
        barrier(self.backend,self.repo,'request-published-'+rid)
        rpc(self.sockpath,{'command':'register','request_id':rid,
            'request_sha256':request['request_sha256'],'context':ctx})
        atomic_write_bytes(self.bridge.root/'ready'/f'{rid}.json',canonical_json_bytes(request))
        deadline=time.monotonic()+float(self.spec['timeout'])
        proofpath=self.bridge.root/'proofs'/f'{rid}.json'
        while not proofpath.is_file():
            if time.monotonic()>deadline:raise ExchangeContractError('response wait expired; preserve exact state and stop')
            time.sleep(.02)
        raw=self.bridge.await_response_bytes(rid,timeout_s=0)
        proof=json.loads(proofpath.read_bytes())
        require(proof['publisher_pid']!=os.getpid(),'publisher must be a separate process')
        require(proof['request_id']==rid and proof['request_sha256']==request['request_sha256'],
            'publisher proof request mismatch')
        require(proof['response_sha256']==hashlib.sha256(raw).hexdigest(),'publisher proof response mismatch')
        message=canonical_json_bytes({k:proof[k] for k in ('request_id','request_sha256','response_sha256')})
        require(verify_late_return_proof(self.verifier,message=message,proof=proof['exchange_proof']),
            'external publisher signature invalid')
        directive=parse_model_directive(json.loads(raw))
        require(directive.provenance is not None,'external response must supply provenance')
        require({k:getattr(directive.provenance,k) for k in binding}==binding,'external provenance binding mismatch')
        if ctx:
            payload=encode_model_directive(directive)
            self.journal.stage_reply(rid,payload.encode())
            self.runtime.background_model_attempts.attach_late_trusted_return(ctx['attempt_id'],
                attached_at=datetime.now(timezone.utc),directive_payload=payload,
                late_return_proof=proof['core_proof'],evidence='external-resident-publisher')
            receipt=self.runtime.background_model_attempts.response_authenticity_receipt(ctx['attempt_id'])
            self.journal.mark_authenticated(rid,receipt.model_dump(mode='json'))
            self.journal.verify_with_core(rid,self.runtime.background_model_attempts)
            self.journal.begin_applying(rid)
        _,commit=barrier(self.backend,self.repo,'response-authenticated-'+rid)
        # Publisher success is conditional on this remote durability acknowledgement.
        atomic_write_bytes(self.bridge.root/'committed'/f'{rid}.json',canonical_json_bytes({
            'request_id':rid,'response_sha256':hashlib.sha256(raw).hexdigest(),'remote_commit':commit}))
        self.bridge.consume_response(rid)
        return directive


def run(root,run_id,session_id,repo,spec):
    require(set(spec)=={'mode','at','cursor','event_id','turn_index','user_input','timeout'},'operation schema mismatch')
    require(spec['mode'] in {'user','due'},'unsupported runner entry')
    require(type(spec['cursor']) is int and 1<=spec['cursor']<=13,'cursor must be 1..13')
    moment=datetime.fromisoformat(spec['at']);require(moment.tzinfo is not None,'timezone required')
    require(isinstance(spec['event_id'],str) and bool(spec['event_id']),'event identity required')
    require(float(spec['timeout'])>0,'positive response wait required')
    backend=RunBackend.open(root,run_id=run_id,session_id=session_id,adopt_stale_owner=True)
    proc=None;core=None;parent_read=None;parent_write=None
    try:
        verify_local_remote_authority(backend,remote_ref='refs/heads/persistence/'+run_id,repo_dir=repo)
        journal=RelayJournal(backend)
        opid=hashlib.sha256(canonical_json_bytes(spec)).hexdigest()
        exchange=backend.mailbox_dir/'operations'/opid
        marker=exchange/'operation.json'
        for other in (backend.mailbox_dir/'operations').glob('*/operation.json'):
            if other!=marker and json.loads(other.read_bytes())['state']!='completed':
                raise ExchangeContractError('older operation is unresolved; preserve and stop')
        if marker.exists():
            previous=json.loads(marker.read_bytes())
            require(previous['spec']==spec,'operation binding changed')
            require(previous['state']=='completed','interrupted operation: no redispatch or invented recovery')
            return previous['result']
        exchange.mkdir(parents=True)
        atomic_write_bytes(marker,canonical_json_bytes({'state':'started','spec':spec}))
        sockpath=str(Path(tempfile.gettempdir())/('aios53-'+uuid.uuid4().hex+'.ipc'))
        env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
        parent_read,parent_write=os.pipe()
        if 'AIOS53_LAUNCH' in env:
            service_command=[sys.executable,'-I',env['AIOS53_LAUNCH'],
                '--source-repo',env['AIOS53_SOURCE_REPO'],'--identity-sha256',env['AIOS53_IDENTITY_SHA'],
                'service','--exchange',str(exchange),'--channel',sockpath,'--runner-pid',str(os.getpid()),'--parent-fd',str(parent_read)]
        else:
            raise ExchangeContractError('pinned isolated launch is required for new execution')
        proc=subprocess.Popen(service_command,env=env,pass_fds=(parent_read,))
        os.close(parent_read);parent_read=None
        deadline=time.monotonic()+30
        while not (Path(sockpath)/'ready.json').exists():
            require(proc.poll() is None,'external publisher service exited')
            require(time.monotonic()<deadline,'publisher startup timeout');time.sleep(.02)
        public=json.loads((exchange/'publisher-public.json').read_bytes())
        verifier=LateReturnVerifier(**public)
        atomic_write_bytes(exchange/'service.json',canonical_json_bytes({'socket':sockpath,'pid':proc.pid}))
        handler=ExternalHandler(backend,journal,exchange,sockpath,repo,verifier,spec)
        world,index=paths(backend)
        def round_summary(request):return handler.summary('round_summary',request)
        def dimension_summary(request):return handler.summary('dimension_summary',request)
        core=HeadlessCore(config=HeadlessConfig(world_path=world,index_path=index,subject_id=backend.owner['subject_id']),
            model_handler=handler,round_summary_handler=round_summary,
            dimension_summary_handler=dimension_summary).start()
        # Use the accepted constructor; no Core source or attempt implementation is patched.
        core.runtime=FusedTurnRuntime(store=core.store,index=core.index,subject_id=backend.owner['subject_id'],
            model_handler=handler,round_summary_handler=round_summary,dimension_summary_handler=dimension_summary,
            late_return_verifier=verifier,external_return_observer=handler)
        handler.runtime=core.runtime
        recorder=core.runtime.cognitive_runtime.model_response_recorder
        def record(snapshot,directive):
            if snapshot.model_attempt_id is not None:
                require(core.runtime.background_model_attempts.response_authenticity_receipt(snapshot.model_attempt_id) is not None,
                    'background return lacks Core authenticity receipt')
                return
            return recorder(snapshot,directive)
        core.runtime.cognitive_runtime.model_response_recorder=record
        require(core.runtime.cognitive_runtime.model_handler is handler,'runtime handler substitution')
        if 'AIOS53_LAUNCH' in os.environ:
            from .checks import loaded_modules
            status=loaded_modules(Path(os.environ['AIOS53_SOURCE_REPO']),Path(os.environ['AIOS53_LAUNCH']).parent)
            atomic_write_bytes(exchange/'runtime-handler-identity.json',canonical_json_bytes(status))
        barrier(backend,repo,'operation-started')
        if spec['mode']=='user':
            result=core.submit_user_turn(session_id=session_id,turn_index=spec['turn_index'],
                user_input=spec['user_input'],occurred_at=moment)
        else:result=core.process_due_work(now=moment)
        require(getattr(result,'continuity_summary_error',None) is None,
            'Core reported Summary failure: '+str(getattr(result,'continuity_summary_error',None)))
        for rid,attempt in handler.requests:
            if attempt is not None:journal.mark_applied(rid)
        result=json.loads(canonical_json_bytes(result))
        atomic_write_bytes(marker,canonical_json_bytes({'state':'completed','spec':spec,'result':result}))
        barrier(backend,repo,'operation-completed')
        return result
    except Exception as original:
        if 'marker' in locals() and marker.exists():
            state=json.loads(marker.read_bytes())
            if state['state']=='completed' and 'result' in locals():
                atomic_write_bytes(marker,canonical_json_bytes({'state':'failed','spec':spec,
                    'reason':'completion durability was not established'}))
        backend.audit('harness_fail_closed',{'error':type(original).__name__+': '+str(original)})
        try:
            barrier(backend,repo,'harness-fail-closed')
        except Exception as durability_error:
            raise ExchangeContractError('failure durability barrier unavailable: '+str(durability_error)) from original
        raise
    finally:
        if core is not None:core.stop()
        if proc is not None:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        if parent_read is not None:os.close(parent_read)
        if parent_write is not None:os.close(parent_write)
        backend.release()


def publish(exchange,rid,raw,authorization,repo,timeout=60):
    exchange=Path(exchange);b=ExchangeBridge(exchange)
    require((exchange/'ready'/f'{rid}.json').is_file(),'request not durably ready')
    b.requests.payload(rid)
    parse(b.requests.payload(rid)['kind'],raw)
    path=exchange/'committed'/f'{rid}.json'
    if path.is_file():
        receipt=json.loads(path.read_bytes())
        require(receipt['response_sha256']==hashlib.sha256(raw).hexdigest(),'conflicting response replay')
        require(b.responses.published_bytes(rid)==raw,'durable replay bytes mismatch')
        backend_root=exchange.parents[2]
        for item in [b.requests.path_for(rid),b.responses.path_for(rid),
            exchange/'proofs'/f'{rid}.json',exchange/'publisher-public.json']:
            relative=str(item.relative_to(backend_root))
            stored=subprocess.run(['git','show',receipt['remote_commit']+':'+relative],cwd=repo,capture_output=True)
            require(stored.returncode==0 and stored.stdout==item.read_bytes(),
                'replay bytes do not match the exact remote commit')
        public=LateReturnVerifier(**json.loads((exchange/'publisher-public.json').read_bytes()))
        proof=json.loads((exchange/'proofs'/f'{rid}.json').read_bytes())
        message=canonical_json_bytes({k:proof[k] for k in ('request_id','request_sha256','response_sha256')})
        require(verify_late_return_proof(public,message=message,proof=proof['exchange_proof']),
            'replay external signature invalid')
        return {**receipt,'idempotent_replay':True}
    require(bool(authorization),'Resident-held authorization required for a new response')
    service=json.loads((exchange/'service.json').read_bytes())
    content={'request_id':rid,'request_sha256':b.request_sha256(rid),'raw':base64.b64encode(raw).decode()}
    authorization_proof=hmac.new(authorization.encode(),canonical_json_bytes(content),hashlib.sha256).hexdigest()
    result=rpc(service['socket'],{'command':'publish',**content,'authorization_proof':authorization_proof})
    deadline=time.monotonic()+timeout
    while not path.is_file():
        require(time.monotonic()<deadline,'remote response durability acknowledgement unavailable')
        time.sleep(.02)
    receipt=json.loads(path.read_bytes())
    require(receipt['response_sha256']==hashlib.sha256(raw).hexdigest(),'remote acknowledgement mismatch')
    return {**result,**receipt}
