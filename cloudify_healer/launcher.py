import os
import time
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
import subprocess

def launch(creds, pingcnt, pingfreq, **kwargs):
  #run as new process
  curdir = os.path.dirname(__file__)
  
  depid = ctx.deployment.id
  targetip = ctx.target.instance.runtime_properties['ip'] if 'ip' in ctx.target.instance.runtime_properties else '127.0.0.1'
  targetid = ctx.target.instance.id
  user, password, tenant = creds.split(',')
  
  # Start ping process, put PID in attributes
  res = None
  pid = os.fork()
  if pid > 0:
    return
  try:
    res = subprocess.Popen(["python", curdir+"/ping_healer.py", user, password, tenant, targetip, depid, targetid, str(pingfreq), str(pingcnt)])
    time.sleep(3)
    ctx.source.instance.runtime_properties["pid"]= str(res.pid)
    ctx.logger.info("exiting")
  except Exception as e:
    raise NonRecoverableError("CAUGHT EXCEPTION: {}".format(e.message))
    
