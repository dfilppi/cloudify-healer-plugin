import os
import json
from cloudify import ctx

def launch(**kwargs):
  """ Launches the healer process
  """
  
  depid = ctx.deployment.id
  targetip = ( ctx.target.instance.runtime_properties['ip']
               if 'ip' in ctx.target.instance.runtime_properties else '127.0.0.1' )
  targetid = ctx.target.instance.id
  user, password, tenant = ctx.source.node.properties['cfy_creds'].split(',')
  pingcnt = ctx.source.node.properties['config']['count']
  pingfreq = ctx.source.node.properties['config']['frequency']

  # Start healer process, put PID in attributes
  pid = os.fork()
  if pid > 0:
    ctx.source.instance.runtime_properties["pid"]= str(pid)
    return

  nodeprops = json.dumps(ctx.source.node.properties)

  # If user has configured custom healer, pass it along
  customscript = ( ctx.source.node.properties['config']['script']
                   if ctx.source.node.properties['type'] == 'custom' else "" )
  path = ctx.download_resource(customscript) if customscript != "" else ""
                   
  close_fds(leave_open=[])
  try:
    curdir = os.path.dirname(__file__)
    os.execlp("python", "python", curdir+"/healer.py", user, password,
             tenant, targetip, depid, targetid, nodeprops, path)
  except Exception as e:
    pass
 
def close_fds(leave_open=[0, 1, 2]):
  fds = os.listdir(b'/proc/self/fd')
  for fdn in fds:
    fd = int(fdn)
    if fd not in leave_open:
      try:
        os.close(fd)
      except:
        pass

