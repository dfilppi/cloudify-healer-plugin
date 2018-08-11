import os
import time
from cloudify import ctx

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
    ctx.source.instance.runtime_properties["pid"]= str(res.pid)
    return

  os.chdir("/")
  os.umask(0)
  os.setsid()

  pid = os.fork()
  if pid > 0:
    os._exit(0)
  
  os.execlp("python", "python", curdir+"/ping_healer.py", user, password, tenant, targetip, depid, targetid, str(pingfreq), str(pingcnt))
