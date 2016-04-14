# pylint: skip-file
'''
      --credentials='': Path to a .kubeconfig file that will contain the credentials the registry should use to contact the master.
      --dry-run=false: Check if the registry exists instead of creating.
      --images='openshift3/ose-${component}:${version}': The image to base this registry on - ${component} will be replaced with --type
      --labels='docker-registry=default': A set of labels to uniquely identify the registry and its components.
      --latest-images=false: If true, attempt to use the latest image for the registry instead of the latest release.
      --mount-host='': If set, the registry volume will be created as a host-mount at this path.
      --no-headers=false: When using the default output, don't print headers.
  -o, --output='': Output format. One of: json|yaml|wide|name|go-template=...|go-template-file=...|jsonpath=...|jsonpath-file=... See golang template [http://golang.org/pkg/text/template/#pkg-overview] and jsonpath template [http://releases.k8s.io/HEAD/docs/user-guide/jsonpath.md].
      --output-version='': Output the formatted object with the given version (default api-version).
      --ports='5000': A comma delimited list of ports or port pairs to expose on the registry pod. The default is set for 5000.
      --replicas=1: The replication factor of the registry; commonly 2 when high availability is desired.
      --selector='': Selector used to filter nodes on deployment. Used to run registries on a specific set of nodes.
      --service-account='': Name of the service account to use to run the registry pod.
  -a, --show-all=false: When printing, show all resources (default hide terminated pods.)
      --sort-by='': If non-empty, sort list types using this field specification.  The field specification is expressed as a JSONPath expression (e.g. 'ObjectMeta.Name'). The field in the API resource specified by this JSONPath expression must be an integer or a string.
  -t, --template='': Template string or path to template file to use when -o=go-template, -o=go-template-file. The template format is golang templates [http://golang.org/pkg/text/template/#pkg-overview].
      --type='docker-registry': The registry image to use - if you specify --images this flag may be ignored.
      --volume='/registry': The volume path to use for registry storage; defaults to /registry which is the default for origin-docker-registry.

Use "oadm options" for a list of global command-line options (applies to all commands).


/usr/bin/oadm registry --credentials=/etc/origin/master/openshift-registry.kubeconfig --service-account=registry --images='registry.access.redhat.com/openshift3/ose-${component}:${version}' --selector='type=infra' --replicas=0 -o yaml > /root/registry.yml

'''

def main():
    '''
    ansible oc module for registry
    '''

    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='present', type='str',
                       choices=['present', 'absent']),
            debug=dict(default=False, type='bool'),
            namespace=dict(default='default', type='str'),
            name=dict(default=None, required=True, type='str'),

            kubeconfig=dict(default='/etc/origin/master/admin.kubeconfig', type='str'),
            credentials=dict(default='/etc/origin/master/openshift-registry.kubeconfig', type='str'),
            images=dict(default=None, type='str'),
            latest_image=dict(default=False, type='bool'),
            labels=dict(default=None, type='list'),
            ports=dict(default=['5000'], type='list'),
            replicas=dict(default=1, type='int'),
            selector=dict(default=None, type='str'),
            service_account=dict(default='registry', type='str'),
            mount_host=dict(default=None, type='str'),
            registry_type=dict(default='docker-registry', type='str'),
            template=dict(default=None, type='str'),
            volume=dict(default='/registry', type='str'),
            env_vars=dict(default=None, type='dict'),
            volume_mounts=dict(default=None, type='list'),
            edits=dict(default=None, type='dict'),
        ),
        mutually_exclusive=[["registry_type", "images"]],

        supports_check_mode=True,
    )

    rconfig = RegistryConfig(module.params['name'],
                             module.params['kubeconfig'],
                             {'credentials': {'value': module.params['credentials'], 'include': True},
                              'default_cert': {'value': None, 'include': True},
                              'images': {'value': module.params['images'], 'include': True},
                              'latest_image': {'value': module.params['latest_image'], 'include': True},
                              'labels': {'value': module.params['labels'], 'include': True},
                              'ports': {'value': ','.join(module.params['ports']), 'include': True},
                              'replicas': {'value': module.params['replicas'], 'include': True},
                              'selector': {'value': module.params['selector'], 'include': True},
                              'service_account': {'value': module.params['service_account'], 'include': True},
                              'registry_type': {'value': module.params['registry_type'], 'include': False},
                              'mount_host': {'value': module.params['mount_host'], 'include': True},
                              'volume': {'value': module.params['mount_host'], 'include': True},
                              'template': {'value': module.params['template'], 'include': True},
                              'env_vars': {'value': module.params['env_vars'], 'include': False},
                              'volume_mounts': {'value': module.params['volume_mounts'], 'include': False},
                              'edits': {'value': module.params['edits'], 'include': False},
                           })


    ocregistry = Registry(rconfig)

    state = module.params['state']
    print "Exists"

    ########
    # Delete
    ########
    if state == 'absent':
        if not ocregistry.exists():
            module.exit_json(changed=False, state="absent")

        if module.check_mode:
            module.exit_json(change=False, msg='Would have performed a delete.')

        api_rval = ocregistry.delete()
        module.exit_json(changed=True, results=api_rval, state="absent")


    if state == 'present':
        ########
        # Create
        ########
        print "exists?"
        if not ocregistry.exists():

            if module.check_mode:
                module.exit_json(change=False, msg='Would have performed a create.')

            api_rval = ocregistry.create()

            if api_rval['returncode'] != 0:
                module.fail_json(msg=api_rval)

            module.exit_json(changed=True, results=api_rval, state="present")

        ########
        # Update
        ########
        if not ocregistry.needs_update():
            module.exit_json(changed=False, state="present")

        if module.check_mode:
            module.exit_json(change=False, msg='Would have performed an update.')

        print "UPDATE"
        api_rval = ocregistry.update()
        print api_rval

        if api_rval['returncode'] != 0:
            module.fail_json(msg=api_rval)

        module.exit_json(changed=True, results=api_rval, state="present")

    module.exit_json(failed=True,
                     changed=False,
                     results='Unknown state passed. %s' % state,
                     state="unknown")

# pylint: disable=redefined-builtin, unused-wildcard-import, wildcard-import, locally-disabled
# import module snippets.  This are required
from ansible.module_utils.basic import *
main()
