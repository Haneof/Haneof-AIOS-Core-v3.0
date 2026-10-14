import argparse
import json
import sys
from pathlib import Path
from .safe_runner import init,run,publish
from .checks import loaded_modules


def main():
    p=argparse.ArgumentParser();subs=p.add_subparsers(dest='command',required=True)
    i=subs.add_parser('init');i.add_argument('--root',type=Path,required=True)
    i.add_argument('--run-id',required=True);i.add_argument('--session-id',required=True)
    i.add_argument('--subject-id',required=True);i.add_argument('--persistence-repo',type=Path,required=True)
    r=subs.add_parser('run');r.add_argument('--root',type=Path,required=True)
    r.add_argument('--run-id',required=True);r.add_argument('--session-id',required=True)
    r.add_argument('--operation',type=Path,required=True);r.add_argument('--persistence-repo',type=Path,required=True)
    s=subs.add_parser('publish');s.add_argument('--exchange',type=Path,required=True)
    s.add_argument('--request-id',required=True);s.add_argument('--response',type=Path,required=True)
    s.add_argument('--timeout',type=float,default=60)
    s.add_argument('--persistence-repo',type=Path,required=True)
    t=subs.add_parser('reattach');t.add_argument('--root',type=Path,required=True)
    t.add_argument('--run-id',required=True);t.add_argument('--session-id',required=True)
    t.add_argument('--commit-sha',required=True);t.add_argument('--persistence-repo',type=Path,required=True)
    subs.add_parser('verify')
    q=subs.add_parser('read-request');q.add_argument('--exchange',type=Path,required=True)
    q.add_argument('--request-id',required=True)
    c=subs.add_parser('checkpoint');c.add_argument('--root',type=Path,required=True)
    c.add_argument('--run-id',required=True);c.add_argument('--session-id',required=True)
    c.add_argument('--persistence-repo',type=Path,required=True)
    a=p.parse_args()
    if a.command=='init':value=init(a.root,a.run_id,a.session_id,a.subject_id,a.persistence_repo)
    elif a.command=='run':value=run(a.root,a.run_id,a.session_id,a.persistence_repo,json.loads(a.operation.read_bytes()))
    elif a.command=='reattach':
        from tools.c15_persistence.remote_backend import materialize_run_state
        b=materialize_run_state(run_id=a.run_id,session_id=a.session_id,target_dir=a.root,
            commit_sha=a.commit_sha,repo_dir=a.persistence_repo)
        try:value={'root':str(b.root),'run_id':a.run_id,'session_id':a.session_id,'commit_sha':a.commit_sha}
        finally:b.release()
    elif a.command=='publish':
        authorization=sys.stdin.readline().rstrip('\n')
        value=publish(a.exchange,a.request_id,a.response.read_bytes(),authorization,a.persistence_repo,a.timeout)
    elif a.command=='verify':
        import os
        value=loaded_modules(Path(os.environ['AIOS53_SOURCE_REPO']),Path(os.environ['AIOS53_LAUNCH']).parent)
        value['marker']='HARNESS_IDENTITY_AND_ROUTER_PASS'
    elif a.command=='read-request':
        from .bridge import ExchangeBridge
        b=ExchangeBridge(a.exchange)
        if not (a.exchange/'ready'/f'{a.request_id}.json').is_file():raise ValueError('request is not durably ready')
        value={'request_sha256':b.request_sha256(a.request_id),'request':b.requests.payload(a.request_id)}
    else:
        from .safe_runner import barrier
        from tools.c15_persistence.backend import RunBackend
        from tools.c15_persistence.remote_backend import verify_local_remote_authority
        b=RunBackend.open(a.root,run_id=a.run_id,session_id=a.session_id,adopt_stale_owner=True)
        try:
            verify_local_remote_authority(b,remote_ref='refs/heads/persistence/'+a.run_id,repo_dir=a.persistence_repo)
            ref,commit=barrier(b,a.persistence_repo,'external-mechanical-checkpoint')
            value={'remote_ref':ref,'remote_commit':commit}
        finally:b.release()
    print(json.dumps(value,ensure_ascii=False))


if __name__=='__main__':main()
