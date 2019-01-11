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


from cloudify.mocks import MockCloudifyContext, MockRelationshipSubjectContext
from cloudify.mocks import MockNodeInstanceContext
from cloudify.state import current_ctx
from time import sleep
import subprocess


def test_stop():
    from cloudify_healer.stopper import stop

    # start process then stop it
    p = subprocess.Popen(["exec sleep 120"], shell=True)
    ctx = MockCloudifyContext(source=MockRelationshipSubjectContext(None,
                              MockNodeInstanceContext(
                              runtime_properties={"pid": str(p.pid)})))

    current_ctx.set(ctx)
    stop()
    sleep(2)
    if p.poll() is None:
        p.terminate()
        p.wait()
        assert False
