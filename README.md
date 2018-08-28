## Cloudify Healer Plugin

The purpose of the healer plugin is to enable agentless autohealing capability to Cloudify deployments.  The functionality is intended to be conceptually similar to 'liveness probes' found elsewhere.  The healer runs a process on the manager, and will only function for target hosts that have routable IPs from the manager.

### Plugin types

The plugin defines a new node type and relationship type.  The node type holds the configuration of the healer, and the relationship actually runs it.

#### cloudify.nodes.Healer

The `Healer` type configures the healer based on 4 different modes.  The modes are selected by setting the `type` property to one of:
* _ping_ - Performs ICMP pings on a host
* _http_ - Performs an HTTP get on a URL
* _port_ - Performs an connection open on a TCP port
* _custom_ - TBD

##### Common Properties
* _cfy_creds_ - Cloudify manager login credentials of the form `username,password,tenant_name`.  This is needed by the healer to run the _heal_ workflow on the target node.  These are best stored using the secret store.
* _debug_ - The plugin starts a background process that logs to '/tmp/healer_<deployment_id>_pid.log'.  This logging occurs at `info` level unless the `debug` property is true.
* _config/count_ The number of failed attempts that will trigger a heal.
* _config/frequency_ The pause between retries in seconds

##### Ping 
The ping healer performs an ICMP ping on the target host.  Take care that the target host permits inbound ICMP traffic from the manager.  It only requires the common properties to operate.

##### HTTP
The HTTP healer performs an HTTP GET on the target host.  If a non-2xx response status code is received, it is regarded as a failure.  Lower level connection problems also will count as failures.  Besides the common properties, the HTTP healer needs:
* _port_ - The target port (int)
* _path_ - The URL path (string)
* _secure_ - Whether HTTPS will be used (boolean)

##### Port
The port healer tries to open a connection to the supplied port on the target host.  If it can't, it is considered a failure.  Besides the common properties, the port healer needs:
* _port_ - The target port (int)

#### Relationship: cloudify.relationships.healer_connected_to
This relationship source should be the cloudify.nodes.Healer node template, and the target should be a compute node.  The ip address of the compute node is used to supply the target IP address to the various healers.  It has no inputs.
