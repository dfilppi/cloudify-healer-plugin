import sys

sys.path.append("/opt/mgmtworker/env/lib/python2.7/site-packages/")

import os
import time
import json
import requests
from cloudify_rest_client import CloudifyClient

with open("/tmp/log","a+") as f:
  f.write("\n---Starting {}---\n".format(time.asctime()))

DONE_STATES=["failed","completed","cancelled","terminated"]

if len(sys.argv)< 8:
  with open("/tmp/log","a+") as f:
    f.write("invalid args:"+str(sys.argv))
  sys.exit(1)


# Collect parms

username,password,tenant,target_ip,deployment_id,instance_id = sys.argv[1:7]
nodeconfig = json.loads(sys.argv[7])
script = sys.argv[8] if len(sys.argv) == 9 else None
testtype = nodeconfig['type']
freq = nodeconfig['config']['frequency']
count = nodeconfig['config']['count']

failcnt = 0

while True:
  with open("/tmp/log","a+") as f:
    f.write("{}: {}\n".format(nodeconfig['type'],target_ip))

  failed = False

  if testtype == 'ping':
    failed = doPing()

  elif testtype == 'port':
    os._exit(1)

  elif testtype == 'http':
    failed = doHttp()

  elif testtype == 'custom':
    os.execlp("python", "python", script, sys.argv[7])
  else:
    with open("/tmp/log","a+") as f:
      f.write("ERROR: unknown test type: {}\n".format(testtype))
    os._exit(1)
    
  if failed:
    failed = False
    failcnt+=1
    if failcnt >=  count:
      #HEAL
      failcnt = 0
      client = CloudifyClient("127.0.0.1",username=username,password=password,tenant=tenant)
      with open("/tmp/log","a+") as f:
        f.write("STARTING HEAL of {}\n".format(instance_id))
      execution = None
      try:
        execution = client.executions.start( deployment_id, "heal", {"node_instance_id": instance_id})
      except Exception as e: 
        with open("/tmp/log","a+") as f:
          f.write("CAUGHT EXCEPTION {}\n".format(e))
        
      with open("/tmp/log","a+") as f:
        f.write("STARTED HEAL of {}\n".format(instance_id))
      while True:
        status  = execution.status
        if status == "failed":
          with open("/tmp/log","a+") as f:
            f.write("execution failed")
            sys.exit(0)
        if status in DONE_STATES:
          sys.exit(0);

  time.sleep(freq)

def doPing():
  """ Does a ping against the ip address from the target relationship
  """
  failed = False
  pid = os.fork()
  if pid == 0:
    os.execlp("ping", "ping", "-q", "-c", "1", "-w", "1", target_ip)
  _, returncode = os.waitpid(pid, 0)
  if os.WIFEXITED(returncode) and os.WEXITSTATUS(returncode) != 0:
    failed = True
  return failed

def doHttp():
  """ perform an HTTP GET vs URL constructed from the ip, port, path from 
      properties
  """
  failed = False
  port = "80"
  port = nodeconfig['config']['port'] if 'port' in nodeconfig['config'] else port
  path = nodeconfig['config']['path']
  prot = "http"
  prot = ("https" if 'secure' in nodeconfig['config'] and
                nodeconfig['config']['secure'] else prot)
  url = prot + target_ip + ":" + port + path
  try:
    ret = requests.get( url, timeout=int(freq))
    if ret.status_code < 200 or ret.status_code > 299:
      with open("/tmp/log","a+") as f:
        f.write("unexpected response code from {}:{}\n".format(url,ret.status_code))
      failed = True
  except requests.exceptions.ConnectTimeout:
    with open("/tmp/log","a+") as f:
      f.write("timeout GET {}:{}\n".format(url,freq))
    failed = True
    pass
  except Exception as e:
    with open("/tmp/log","a+") as f:
      f.write("caught exception in GET {}:{}\n".format(url,e.message))
  return failed
