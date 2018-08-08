import sys

sys.path.append("/opt/manager/env/lib/python2.7/site-packages/")

import os
import time
import subprocess
from cloudify_rest_client import CloudifyClient
from cloudify.proxy.client import client_req


with open("/tmp/log","a+") as f:
  f.write("\n-------------------------\n")

DONE_STATES=["failed","completed","cancelled","terminated"]

if len(sys.argv)< 6:
  with open("/tmp/log","a+") as f:
    f.write("invalid args:"+str(sys.argv))
  sys.exit(1)
# Ping:  N consecutive failures causes heal
with open("/tmp/log","a+") as f:
  f.write("target_ip: {}\n".format(sys.argv[2]))

username = sys.argv[1]
password = sys.argv[2]
tenant = sys.argv[3]
target_ip = sys.argv[4]
deployment_id = sys.argv[5]
instance_id = sys.argv[6]
pingfreq = int(sys.argv[7])
pingcnt = int(sys.argv[8])
failcnt = 0

while True:
  with open("/tmp/log","a+") as f:
    f.write("PING: {}\n".format(target_ip))
  devnull = open("/dev/null","w")
  ret = subprocess.Popen(["ping","-q","-c","1","-w","1", target_ip], stdout = devnull)
  ret.wait()
  if ret.returncode != 0:
    failcnt+=1
    if failcnt >=  pingcnt:
      #HEAL
      failcnt = 0
      with open("/tmp/log","a+") as f:
        f.write("GETTING CLIENT\n")
      client = CloudifyClient("127.0.0.1",username=username,password=password,tenant=tenant)
      with open("/tmp/log","a+") as f:
        f.write("GOT CLIENT\n")
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

  time.sleep(pingfreq)

