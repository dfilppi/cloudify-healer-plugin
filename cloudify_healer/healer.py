import sys

sys.path.append("/opt/mgmtworker/env/lib/python2.7/site-packages/")

import os
import time
import json
from cloudify_rest_client import CloudifyClient

with open("/tmp/log","a+") as f:
  f.write("\n-------------------------\n")

DONE_STATES=["failed","completed","cancelled","terminated"]

if len(sys.argv)< 8:
  with open("/tmp/log","a+") as f:
    f.write("invalid args:"+str(sys.argv))
  sys.exit(1)


# Collect parms

username = sys.argv[1]
password = sys.argv[2]
tenant = sys.argv[3]
target_ip = sys.argv[4]
deployment_id = sys.argv[5]
instance_id = sys.argv[6]
nodeconfig = json.loads(sys.argv[7])
script = sys.argv[8] if len(sys.argv) == 9 else None
testtype = nodeconfig['type']
freq = nodeconfig['config']['frequency']
count = nodeconfig['config']['count']

failcnt = 0

while True:
  with open("/tmp/log","a+") as f:
    f.write("{}: {}\n".format(nodeconfig['type'],target_ip))

  pid = os.fork()
  if pid == 0:
    if testtype == 'ping':
      os.execlp("ping", "ping", "-q", "-c", "1", "-w", "1", target_ip)
    elif testtype == 'port':
      os._exit(1)
    elif testtype == 'http':
      os._exit(1)
    elif testtype == 'custom':
      os.execlp("python", "python", script, sys.argv[7])
    else:
      os._exit(1)
    
  _, returncode = os.waitpid(pid, 0)
  if os.WIFEXITED(returncode) and os.WEXITSTATUS(returncode) != 0:
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

