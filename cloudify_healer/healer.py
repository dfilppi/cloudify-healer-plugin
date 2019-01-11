########
# Copyright (c) 2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############


from cloudify_rest_client import CloudifyClient
import logging
import socket
import requests
import json
import time
import os
import sys

sys.path.append("/opt/mgmtworker/env/lib/python2.7/site-packages/")


DONE_STATES = ["failed", "completed", "cancelled", "terminated"]
logger = None


def main():
    global logger

    # Collect parms

    username, password, tenant, target_ip, deployment_id, instance_id = \
        sys.argv[1:7]
    nodeconfig = json.loads(sys.argv[7])
    script = sys.argv[8] if len(sys.argv) == 9 else None
    testtype = nodeconfig['type']
    freq = nodeconfig['config']['frequency']
    count = nodeconfig['config']['count']
    debug = bool(nodeconfig['debug'])
    loglevel = logging.DEBUG if debug else logging.INFO

    # Open logger
    logfile = "/tmp/healer_" + deployment_id + "_" + str(os.getpid()) + ".log"
    logging.basicConfig(
        filename=logfile, format='%(asctime)s %(levelname)8s %(message)s',
        level=loglevel)
    logger = logging.getLogger("healer")

    logger.info("\n---Starting {}---".format(time.asctime()))

    # Wait for install workflow to complete, if it doesn't, exit
    #    Find install
    client = CloudifyClient("127.0.0.1", username=username,
                            password=password, tenant=tenant)

    status = None
    for i in range(120):
        installid, status = get_last_install(client, deployment_id)
        if not status:
            logger.error("Failure: no install found. Exiting")
            os._exit(1)
        elif status != "started":
            logger.debug("breaking on status {}".format(status))
            break
        logger.info("waiting for install {} to complete".format(installid))
        time.sleep(5)
    if status == "started":
        logger.error("Timed out waiting for install to complete. Exiting.")
        os._exit(1)
    elif status != "terminated":
        logger.error(
            "Install execution stopped. Reason={}. Exiting..".format(status))
        os._exit(1)

    logger.info("install complete. continuing...")

    failcnt = 0

    while True:
        logger.debug("{}: {}".format(nodeconfig['type'], target_ip))

        failed = False

        if testtype == 'ping':
            failed = doPing(target_ip)

        elif testtype == 'port':
            failed = doSocket(target_ip, nodeconfig)

        elif testtype == 'http':
            failed = doHttp(target_ip, freq, nodeconfig)

        elif testtype == 'custom':
            os.execlp("python", "python", script, sys.argv[7])
        else:
            logger.error("ERROR: unknown test type: {}".format(testtype))
            os._exit(1)

        if failed:
            failed = False
            failcnt += 1
            logger.error(
                "Target test failure. Fail count = {}".format(failcnt))
            if failcnt >= count:
                # HEAL
                failcnt = 0
                logger.info("STARTING HEAL of {}".format(instance_id))
                execution = None
                try:
                    execution = client.executions.start(
                        deployment_id, "heal",
                        {"node_instance_id": instance_id})
                except Exception as e:
                    logger.error("CAUGHT EXCEPTION {}".format(e))

                logger.info("STARTED HEAL of {}".format(instance_id))
                while True:
                    status = execution.status
                    logger.debug(
                        "polling execution status = {}".format(status))
                    if status == "failed":
                        logger.error("execution failed")
                        os._exit(0)
                    if status in DONE_STATES:
                        os._exit(0)
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
    port = (nodeconfig['config']['port']
            if 'port' in nodeconfig['config'] else port)
    path = (nodeconfig['config']['path']
            if 'path' in nodeconfig['config'] else "/")
    prot = "http"
    prot = ("https" if 'secure' in nodeconfig['config'] and
            nodeconfig['config']['secure'] else prot)
    url = prot + "://" + target_ip + ":" + str(port) + path
    try:
        ret = requests.get(url, timeout=int(freq))
        if ret.status_code < 200 or ret.status_code > 299:
            logger.error("unexpected response code from {}:{}".format(
                url, ret.status_code))
            failed = True
    except requests.exceptions.ConnectTimeout:
        logger.error("timeout GET {}:{}".format(url, freq))
        failed = True
    except Exception as e:
        logger.error("caught exception in GET {}:{}".format(url, e.message))
        failed = True
    return failed


def doSocket(target_ip, nodeconfig):
    """ Open a TCP socket constructed from the ip and port from
        properties
    """
    failed = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((target_ip, nodeconfig['config']['port']))
    except Exception as e:
        logger.error("exception: {}".format(str(e)))
        failed = True
    return failed


def get_last_install(client, deployment_id):
    """ Gets the execution and status of the last install
        for the supplied deployment
    """

    executions = client.executions.list(deployment_id="p")

    execution = None
    for e in executions:
        if e.workflow_id == "install":
            execution = e

    if not execution:
        return None, None  # no install found

    if execution.status in ["started", "pending"]:
        return execution.id, "started"
    else:
        return execution.id, execution.status


if __name__ == "__main__":
    main()
