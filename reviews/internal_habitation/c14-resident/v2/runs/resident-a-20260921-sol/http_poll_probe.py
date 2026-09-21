import json, os, urllib.request

def read_control(url):
    req=urllib.request.Request(url, headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'], 'Accept':'application/vnd.github.raw+json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)
