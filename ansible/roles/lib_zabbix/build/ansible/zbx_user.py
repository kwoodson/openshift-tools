# pylint: skip-file

def main():
    '''
    ansible zabbix module for users
    '''

    ##def user(self, name, state='present', params=None):

    module = AnsibleModule(
        argument_spec=dict(
            zbx_server=dict(default='https://localhost/zabbix/api_jsonrpc.php', type='str'),
            zbx_user=dict(default=os.environ.get('ZABBIX_USER', None), type='str'),
            zbx_password=dict(default=os.environ.get('ZABBIX_PASSWORD', None), type='str'),
            zbx_debug=dict(default=False, type='bool'),
            login=dict(default=None, type='str'),
            first_name=dict(default=None, type='str'),
            last_name=dict(default=None, type='str'),
            user_type=dict(default=None, type='str'),
            password=dict(default=None, type='str'),
            refresh=dict(default=None, type='int'),
            autologout=dict(default=None, type='int'),
            update_password=dict(default=False, type='bool'),
            user_groups=dict(default=[], type='list'),
            state=dict(default='present', type='str'),
        ),
        #supports_check_mode=True
    )

    zapi = ZabbixAPI(ZabbixConnection(module.params['zbx_server'],
                                      module.params['zbx_user'],
                                      module.params['zbx_password'],
                                      module.params['zbx_debug']))

    ## before we can create a user media and users with media types we need media
    zbx_class_name = 'user'
    idname = "userid"
    state = module.params['state']

    content = zapi.get_content(zbx_class_name,
                               'get',
                               {'output': 'extend',
                                'search': {'alias': module.params['login']},
                                "selectUsrgrps": 'usergrpid',
                               })
    if state == 'list':
        module.exit_json(changed=False, results=content['result'], state="list")

    if state == 'absent':
        if not ZabbixUtils.exists(content) or len(content['result']) == 0:
            module.exit_json(changed=False, state="absent")

        content = zapi.get_content(zbx_class_name, 'delete', [content['result'][0][idname]])
        module.exit_json(changed=True, results=content['result'], state="absent")

    if state == 'present':

        params = {'alias': module.params['login'],
                  'passwd': ZabbixUtils.get_passwd(module.params['password']),
                  'usrgrps': ZabbixUtils.get_usergroups(zapi, module.params['user_groups']),
                  'name': module.params['first_name'],
                  'surname': module.params['last_name'],
                  'refresh': module.params['refresh'],
                  'autologout': module.params['autologout'],
                  'type': ZabbixUtils.get_usertype(module.params['user_type']),
                 }

        # Remove any None valued params
        _ = [params.pop(key, None) for key in params.keys() if params[key] is None]

        if not ZabbixUtils.exists(content):
            # if we didn't find it, create it
            content = zapi.get_content(zbx_class_name, 'create', params)

            if content.has_key('Error'):
                module.exit_json(failed=True, changed=False, results=content, state='present')

            module.exit_json(changed=True, results=content['result'], state='present')
        # already exists, we need to update it
        # let's compare properties
        differences = {}

        # Update password
        if not module.params['update_password']:
            params.pop('passwd', None)

        zab_results = content['result'][0]
        for key, value in params.items():

            if key == 'usrgrps':
                # this must be done as a list of ordered dictionaries fails comparison
                # if the current zabbix group list is not all in the
                # provided group list
                # or the provided group list is not all in the current zabbix
                # group list
                if not all([_ in value for _ in zab_results[key]]) \
                   or not all([_ in zab_results[key] for _ in value]):
                    differences[key] = value

            elif zab_results[key] != value and zab_results[key] != str(value):
                differences[key] = value

        if not differences:
            module.exit_json(changed=False, results=zab_results, state="present")

        # We have differences and need to update
        differences[idname] = zab_results[idname]
        content = zapi.get_content(zbx_class_name, 'update', differences)
        module.exit_json(changed=True, results=content['result'], state="present")

    module.exit_json(failed=True,
                     changed=False,
                     results='Unknown state passed. %s' % state,
                     state="unknown")

# pylint: disable=redefined-builtin, unused-wildcard-import, wildcard-import, locally-disabled
# import module snippets.  This are required
from ansible.module_utils.basic import *

main()
