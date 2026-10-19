"""Mechanical external-session transport over current Core/C15 contracts."""
from __future__ import annotations
import base64
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import stat
import sys
import tempfile
import time
import uuid
import secrets

from aios_core.headless.core import HeadlessConfig,HeadlessCore
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.runtime.background_attempt import encode_model_directive
from aios_core.runtime.late_return import LateReturnVerifier,verify_late_return_proof
from tools.c15_persistence.backend import RunBackend,GenerationStore,require
from tools.c15_persistence.relay import RelayJournal
from tools.c15_persistence import remote_backend as remote_backend
from tools.c15_persistence.remote_backend import push_run_state,verify_local_remote_authority
from .atomic import atomic_write_bytes,fsync_dir
from .bridge import ExchangeBridge,ExchangeContractError
from .canonical import canonical_json_bytes
from .schema import serialize_runtime_snapshot,parse_model_directive
from .payload import parse
from .completion import finalize_local,operation_id,write_candidate
from .remote_completion import recover_remote_candidate,verify_completed_remote_record

# Run the child launcher from bytes that were independently authenticated by
# the current verified importer. ``exec`` targets the real __main__ namespace,
# so the bootstrap's normal startup checks see their actual launcher module.
_VERIFIED_LAUNCH_BOOTSTRAP = (
    "import hashlib,pathlib,sys\n"
    "path=pathlib.Path(sys.argv[1]);expected=sys.argv[2];args=sys.argv[3:]\n"
    "raw=path.read_bytes()\n"
    "if hashlib.sha256(raw).hexdigest()!=expected:raise SystemExit('BLOCKED / LAUNCH_BYTES_CHANGED')\n"
    "sys.argv=[str(path),*args];main=sys.modules['__main__'].__dict__;main['__file__']=str(path)\n"
    "exec(compile(raw,str(path),'exec',dont_inherit=True),main)\n"
)


def rpc(sockpath,command,expected_server_pid=None,expected_server_start_time=None):
    """Send one framed command and authenticate the Publisher process instance."""
    from .registration_ipc import rpc as socket_rpc
    return socket_rpc(sockpath,command,expected_server_pid=expected_server_pid,
        expected_server_start_time=expected_server_start_time,timeout=30.0)


def runner_start_time(pid):
    raw=Path(f'/proc/{pid}/stat').read_text(encoding='ascii')
    end=raw.rfind(')')
    require(end>=0,'cannot read current Runner process identity')
    fields=raw[end+1:].split()
    require(len(fields)>19,'Runner process identity is truncated')
    return fields[19]


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


@contextmanager
def _inject_at_git_push(fault_hook):
    if fault_hook is None:
        yield
        return
    original=remote_backend.subprocess.run
    fired=False
    def intercepted(command,*args,**kwargs):
        nonlocal fired
        values=list(command) if isinstance(command,(list,tuple)) else [str(command)]
        if not fired and len(values)>=2 and values[0]=='git' and values[1]=='push':
            fired=True
            fault_hook('during_remote_cas')
        return original(command,*args,**kwargs)
    remote_backend.subprocess.run=intercepted
    try:yield
    finally:remote_backend.subprocess.run=original


def barrier(backend,repo,label,*,fault_hook=None):
    generation=GenerationStore(backend).seal(artifacts(backend),label=label)
    RelayJournal(backend).ledger_set('generation',str(generation))
    with _inject_at_git_push(fault_hook):
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
    def __init__(self,backend,journal,exchange,sockpath,service_pid,service_start_time,
                 runner_instance_id,operation_id,repo,verifier,spec):
        self.backend=backend;self.journal=journal;self.bridge=ExchangeBridge(exchange)
        self.sockpath=sockpath;self.service_pid=int(service_pid)
        self.service_start_time=str(service_start_time)
        self.runner_instance_id=runner_instance_id;self.operation_id=operation_id
        self.repo=repo;self.verifier=verifier;self.spec=spec
        self.contexts={};self.requests=[];self.runtime=None

    def accept_return_context(self,snapshot,context):
        from aios_core.runtime.late_return import LateReturnSigningContext
        require(isinstance(context,LateReturnSigningContext),'Core-owned LateReturnSigningContext required')
        require(snapshot.model_attempt_id==context.attempt_id,
            'Core context does not bind the actual RuntimeSnapshot attempt')
        require(context.subject_id==self.backend.owner['subject_id'],
            'Core context subject does not bind the active run')
        require(context.verifier_key_id==self.verifier.key_id,
            'Core context verifier does not bind the current Publisher instance')
        require(context.attempt_id not in self.contexts,'duplicate dispatch context')
        self.contexts[context.attempt_id]=context

    def summary(self,kind,payload):
        identity={k:self.backend.owner[k] for k in ('run_id','session_id','subject_id')}
        body=json.loads(canonical_json_bytes(payload))
        request=self.bridge.publish_request(kind=kind,body={'identity':identity,'summary_input':body})
        rid=request['request_id'];self.requests.append((rid,None))
        barrier(self.backend,self.repo,'summary-request-'+rid)
        rpc(self.sockpath,{'command':'register','request_id':rid,
            'request_sha256':request['request_sha256'],'context':None,'core_attempt_id':None,
            'runner_instance_id':self.runner_instance_id,'operation_id':self.operation_id},
            expected_server_pid=self.service_pid,
            expected_server_start_time=self.service_start_time)
        atomic_write_bytes(self.bridge.root/'ready'/f'{rid}.json',canonical_json_bytes(request))
        deadline=time.monotonic()+float(self.spec['timeout']);proofpath=self.bridge.root/'proofs'/f'{rid}.json'
        while not proofpath.is_file():
            require(time.monotonic()<deadline,'Summary response wait expired');time.sleep(.02)
        raw=self.bridge.await_response_bytes(rid,timeout_s=0);proof=json.loads(proofpath.read_bytes())
        require(proof['request_id']==rid and proof['request_sha256']==request['request_sha256'],
            'Summary proof request mismatch')
        require(proof.get('operation_id')==self.operation_id and
            proof.get('runner_instance_id')==self.runner_instance_id,
            'Summary proof belongs to another Runner operation')
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
        context=self.contexts.get(snapshot.model_attempt_id)
        if snapshot.model_attempt_id is not None:
            require(context is not None,'Core attempt context was not issued before dispatch')
        ctx=context.scope_fields() if context is not None else None
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
            'request_sha256':request['request_sha256'],
            'context':context.model_dump(mode='json') if context is not None else None,
            'core_attempt_id':snapshot.model_attempt_id,
            'runner_instance_id':self.runner_instance_id,'operation_id':self.operation_id},
            expected_server_pid=self.service_pid,
            expected_server_start_time=self.service_start_time)
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
        require(proof.get('operation_id')==self.operation_id and
            proof.get('runner_instance_id')==self.runner_instance_id,
            'publisher proof belongs to another Runner operation')
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


def run(root,run_id,session_id,repo,spec,*,fault_hook=None):
    require(set(spec)=={'mode','at','cursor','event_id','turn_index','user_input','timeout'},'operation schema mismatch')
    require(spec['mode'] in {'user','due'},'unsupported runner entry')
    require(type(spec['cursor']) is int and 1<=spec['cursor']<=13,'cursor must be 1..13')
    moment=datetime.fromisoformat(spec['at']);require(moment.tzinfo is not None,'timezone required')
    require(isinstance(spec['event_id'],str) and bool(spec['event_id']),'event identity required')
    require(float(spec['timeout'])>0,'positive response wait required')
    backend=RunBackend.open(root,run_id=run_id,session_id=session_id,adopt_stale_owner=True)
    proc=None;core=None;parent_read=None;parent_write=None;socket_dir=None;socket_dir_identity=None
    try:
        journal=RelayJournal(backend)
        opid=operation_id(spec)
        remote_ref='refs/heads/persistence/'+run_id
        exchange=backend.mailbox_dir/'operations'/opid
        marker=exchange/'operation.json'
        if marker.exists():
            previous=json.loads(marker.read_bytes())
            if previous.get('state')=='remote_committing':
                recovery=recover_remote_candidate(backend=backend,marker=marker,spec=spec,
                    remote_ref=remote_ref,repo=repo,remote_backend=remote_backend,
                    verify_local_remote_authority=verify_local_remote_authority,fault_hook=fault_hook)
                return recovery['result']
            if previous.get('state')=='completed':
                replay=verify_completed_remote_record(backend=backend,marker=marker,record=previous,
                    spec=spec,remote_ref=remote_ref,repo=repo,remote_backend=remote_backend,
                    verify_local_remote_authority=verify_local_remote_authority)
                return replay['result']
            raise ExchangeContractError('interrupted operation has no remote completion candidate; no redispatch')
        for other in (backend.mailbox_dir/'operations').glob('*/operation.json'):
            if other==marker:continue
            previous=json.loads(other.read_bytes())
            if previous.get('state')=='remote_committing':
                other_spec=previous.get('spec')
                require(isinstance(other_spec,dict),'unresolved operation spec is invalid')
                recover_remote_candidate(backend=backend,marker=other,spec=other_spec,
                    remote_ref=remote_ref,repo=repo,remote_backend=remote_backend,
                    verify_local_remote_authority=verify_local_remote_authority)
            elif previous.get('state')=='completed':
                verify_completed_remote_record(backend=backend,marker=other,record=previous,
                    spec=previous.get('spec'),remote_ref=remote_ref,repo=repo,
                    remote_backend=remote_backend,verify_local_remote_authority=verify_local_remote_authority)
            else:
                raise ExchangeContractError('older operation is unresolved; preserve and stop')
        verify_local_remote_authority(backend,remote_ref=remote_ref,repo_dir=repo)
        exchange.mkdir(parents=True)
        atomic_write_bytes(marker,canonical_json_bytes({
            'state':'started','operation_id':opid,'spec':spec}))
        socket_dir=Path(tempfile.gettempdir())/('aios53-'+uuid.uuid4().hex)
        socket_dir.mkdir(mode=0o700)
        os.chmod(socket_dir,0o700)
        socket_dir_stat=os.lstat(socket_dir)
        socket_dir_identity=(socket_dir_stat.st_dev,socket_dir_stat.st_ino)
        sockpath=str(socket_dir/'publisher.sock')
        runner_instance_id=secrets.token_hex(32)
        if os.environ.get('AIOS66_TEST_ENROLLMENT'):
            from .response_authorization import configured_grant
            grant=configured_grant()
            require(grant['run_id']==run_id and grant['session_id']==session_id and
                opid in grant['operation_ids'], 'TEST_ONLY enrollment operation scope mismatch')
            runner_instance_id=grant['instance_id']
        runner_start=runner_start_time(os.getpid())
        env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
        parent_read,parent_write=os.pipe()
        if 'AIOS53_LAUNCH' in env:
            from .checks import bootstrap_sha256
            launch_sha=bootstrap_sha256()
            service_command=[sys.executable,'-I','-c',_VERIFIED_LAUNCH_BOOTSTRAP,
                env['AIOS53_LAUNCH'],launch_sha,
                '--source-repo',env['AIOS53_SOURCE_REPO'],'--identity-sha256',env['AIOS53_IDENTITY_SHA'],
                'service','--exchange',str(exchange),'--socket',sockpath,
                '--runner-pid',str(os.getpid()),'--runner-start-time',runner_start,
                '--runner-instance-id',runner_instance_id,'--operation-id',opid,
                '--parent-fd',str(parent_read)]
        else:
            raise ExchangeContractError('pinned isolated launch is required for new execution')
        proc=subprocess.Popen(service_command,env=env,pass_fds=(parent_read,))
        os.close(parent_read);parent_read=None
        deadline=time.monotonic()+30
        while not Path(sockpath).is_socket():
            require(proc.poll() is None,'external publisher service exited')
            require(time.monotonic()<deadline,'publisher startup timeout');time.sleep(.02)
        public=json.loads((exchange/'publisher-public.json').read_bytes())
        verifier=LateReturnVerifier(**public)
        atomic_write_bytes(exchange/'service.json',canonical_json_bytes({
            'socket':sockpath,'pid':proc.pid,'publisher_start_time':runner_start_time(proc.pid),
            'runner_instance_id':runner_instance_id,
            'operation_id':opid}))
        handler=ExternalHandler(backend,journal,exchange,sockpath,proc.pid,
            runner_start_time(proc.pid),runner_instance_id,opid,repo,verifier,spec)
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
        candidate=write_candidate(marker,spec,result,fault_hook=fault_hook)
        remote_ref_written,remote_commit=barrier(backend,repo,'operation-result-candidate',
            fault_hook=fault_hook)
        require(remote_ref_written==remote_ref,'remote completion ref changed unexpectedly')
        relative=marker.relative_to(backend.root).as_posix()
        committed=subprocess.run(['git','show',f'{remote_commit}:{relative}'],cwd=repo,capture_output=True)
        require(committed.returncode==0,'authoritative operation candidate is absent from remote commit')
        completed=finalize_local(marker,candidate,remote_ref=remote_ref,
            remote_commit=remote_commit,remote_candidate_bytes=committed.stdout,
            fault_hook=fault_hook)
        return completed['result']
    except Exception as original:
        if 'marker' in locals() and marker.exists():
            try:operation_state=json.loads(marker.read_bytes())
            except Exception:operation_state={}
            if operation_state.get('state') in {'remote_committing','completed'}:
                raise ExchangeContractError(
                    'remote completion candidate/receipt is preserved unchanged; stop and use exact restart recovery') from original
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
        if socket_dir is not None and socket_dir_identity is not None:
            try:
                current=os.lstat(socket_dir)
                if (current.st_dev,current.st_ino)==socket_dir_identity:
                    endpoint=socket_dir/'publisher.sock'
                    endpoint_stat=os.lstat(endpoint)
                    if stat.S_ISSOCK(endpoint_stat.st_mode):endpoint.unlink()
                    socket_dir.rmdir()
            except FileNotFoundError:pass
            except OSError:pass
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
    result=rpc(service['socket'],{'command':'publish',**content,'authorization_proof':authorization_proof},
        expected_server_pid=service['pid'],
        expected_server_start_time=service['publisher_start_time'])
    deadline=time.monotonic()+timeout
    while not path.is_file():
        require(time.monotonic()<deadline,'remote response durability acknowledgement unavailable')
        time.sleep(.02)
    receipt=json.loads(path.read_bytes())
    require(receipt['response_sha256']==hashlib.sha256(raw).hexdigest(),'remote acknowledgement mismatch')
    return {**result,**receipt}
