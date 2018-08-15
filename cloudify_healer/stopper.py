from cloudify import ctx
import subprocess

def stop(**kwargs):
  pid=ctx.source.instance.runtime_properties["pid"]
  subprocess.call(["kill","-9", pid ])

