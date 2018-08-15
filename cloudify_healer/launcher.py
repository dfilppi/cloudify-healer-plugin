import os
import time
import tempfile
from cloudify import ctx
import json

def launch(**kwargs):
  
  depid = ctx.deployment.id
  targetip = ( ctx.target.instance.runtime_properties['ip']
               if 'ip' in ctx.target.instance.runtime_properties else '127.0.0.1' )
  targetid = ctx.target.instance.id
  user, password, tenant = ctx.source.node.properties['cfy_creds'].split(',')
  pingcnt = ctx.source.node.properties['config']['count']
  pingfreq = ctx.source.node.properties['config']['frequency']

  # Start ping process, put PID in attributes
  pid = os.fork()
  if pid > 0:
    ctx.source.instance.runtime_properties["pid"]= str(pid)
    return

  nodeprops = json.dumps(ctx.source.node.properties)

  customscript = ( ctx.source.node.properties['config']['script']
                   if ctx.source.node.properties['type'] == 'custom' else "" )
  
  
  with open("/tmp/log","a+") as f:
    f.write("launching\n")

  try:
    curdir = os.path.dirname(__file__)
    os.execlp("python", "python", curdir+"/healer.py", user, password,
             tenant, targetip, depid, targetid, nodeprops, customscript)
  except Exception as e:
    with open("/tmp/log","a+") as f:
      f.write("EXCEPTION {}\n".format(e.message))
  finally:
    with open("/tmp/log","a+") as f:
      f.write("FINALLY\n")
