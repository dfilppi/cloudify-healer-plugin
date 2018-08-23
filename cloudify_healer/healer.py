import sys

sys.path.append("/opt/mgmtworker/env/lib/python2.7/site-packages/")

import os
import time
import json
import requests
from cloudify_rest_client import CloudifyClient

DONE_STATES=["failed","completed","cancelled","terminated"]

def main():

  log("\n---Starting {}---".format(time.asctime()))
  
  if len(sys.argv)< 8:
    log("invalid args:"+str(sys.argv))
    os._exit(1)
  
  # Collect parms
  
  username,password,tenant,target_ip,deployment_id,instance_id = sys.argv[1:7]
  nodeconfig = json.loads(sys.argv[7])
  script = sys.argv[8] if len(sys.argv) == 9 else None
  testtype = nodeconfig['type']
  freq = nodeconfig['config']['frequency']
  count = nodeconfig['config']['count']

  # Wait for install workflow to complete, if it doesn't, exit
  #    Find install
  client = CloudifyClient("127.0.0.1",username=username,password=password,tenant=tenant)
  
  status = None
  for i in range(120):
    installid, status = get_last_install(client, deployment_id ) 
    if not status:
      log("Failure: no install found. Exiting")
      os._exit(1)
    elif status != "started":
      log("breaking on status {}".format(status))
      break
    log("waiting for install {} to complete".format(installid))
    time.sleep(5)
  if status == "started":
    log("Timed out waiting for install to complete. Exiting.")
    os._exit(1)
  elif status != "terminated":
    log("Install execution stopped. Reason={}. Exiting..".format(status))
    os_exit(1)

  log("install complete. continuing...")
  
  failcnt = 0
  
  while True:
    log("{}: {}".format(nodeconfig['type'],target_ip))
  
    failed = False
  
    if testtype == 'ping':
      failed = doPing(target_ip)
  
    elif testtype == 'port':
      os._exit(1)
  
    elif testtype == 'http':
      failed = doHttp(target_ip, freq, nodeconfig)
  
    elif testtype == 'custom':
      os.execlp("python", "python", script, sys.argv[7])
    else:
      log("ERROR: unknown test type: {}".format(testtype))
      os._exit(1)
      
    if failed:
      failed = False
      failcnt+=1
      if failcnt >=  count:
        #HEAL
        failcnt = 0
        log("STARTING HEAL of {}".format(instance_id))
        execution = None
        try:
          execution = client.executions.start( deployment_id, "heal", {"node_instance_id": instance_id})
        except Exception as e: 
          log("CAUGHT EXCEPTION {}".format(e))
          
        log("STARTED HEAL of {}".format(instance_id))
        while True:
          status  = execution.status
          log("polling execution status = {}".format(status))
          if status == "failed":
            log("execution failed")
            os._exit(0)
          if status in DONE_STATES:
            os._exit(0);
          time.sleep(4)
  
    time.sleep(freq)
  

def doPing(target_ip):
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


def doHttp(target_ip, freq, nodeconfig):
  """ perform an HTTP GET vs URL constructed from the ip, port, path from 
      properties
  """
  failed = False
  port = "80"
  port = nodeconfig['config']['port'] if 'port' in nodeconfig['config'] else port
  path = nodeconfig['config']['path'] if 'path' in nodeconfig['config'] else "/"
  prot = "http"
  prot = ("https" if 'secure' in nodeconfig['config'] and
                nodeconfig['config']['secure'] else prot)
  url = prot + "://" + target_ip + ":" + str(port) + path
  try:
    ret = requests.get( url, timeout=int(freq))
    if ret.status_code < 200 or ret.status_code > 299:
      log("unexpected response code from {}:{}".format(url,ret.status_code))
      failed = True
  except requests.exceptions.ConnectTimeout:
    log("timeout GET {}:{}".format(url,freq))
    failed = True
  except Exception as e:
    log("caught exception in GET {}:{}".format(url,e.message))
    failed = True
  return failed


def get_last_install(client, deployment_id):
  """ Gets the execution and status of the last install for the supplied deployment
  """

  executions = client.executions.list( deployment_id = "p" )

  execution = None
  for e in executions:
    if e.workflow_id == "install":
      execution = e

  if not execution:
    return None, None   #no install found

  log("execution status={}".format(execution.status))

  if execution.status in ["started", "pending"]:
    return execution.id, "started"
  else: 
    return execution.id, execution.status


### REPLACE THIS WITH SOMETHING SANE
def log(msg):
  with open("/tmp/log","a+") as f:
    f.write(msg+"\n")


if __name__ == "__main__":
  main()
