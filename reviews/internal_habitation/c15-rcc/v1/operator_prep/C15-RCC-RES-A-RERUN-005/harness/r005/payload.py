import json
from .schema import parse_response_envelope,parse_model_directive


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key')
        result[key]=value
    return result


def reject_constant(value):raise ValueError('nonfinite JSON value: '+value)


def parse(kind,raw):
    envelope=parse_response_envelope(json.loads(raw,object_pairs_hook=unique_object,parse_constant=reject_constant))
    if kind=='model_directive':return parse_model_directive(envelope)
    if kind not in {'round_summary','dimension_summary'}:raise ValueError('unknown external decision kind')
    value=envelope['directive']
    if set(value)!={'text'} or not isinstance(value['text'],str) or not value['text'].strip():
        raise ValueError('explicit external Summary text required')
    return value['text']
