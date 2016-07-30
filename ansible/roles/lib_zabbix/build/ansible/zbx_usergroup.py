# pylint: skip-file

def main():
    ''' Ansible module for usergroup
    '''

    module = AnsibleModule(
        argument_spec=dict(
            zbx_server=dict(default='https://localhost/zabbix/api_jsonrpc.php', type='str'),
            zbx_user=dict(default=os.environ.get('ZABBIX_USER', None), type='str'),
            zbx_password=dict(default=os.environ.get('ZABBIX_PASSWORD', None), type='str'),
            zbx_debug=dict(default=False, type='bool'),
            debug_mode=dict(default='disabled', type='str'),
            gui_access=dict(default='default', type='str'),
            status=dict(default='enabled', type='str'),
            name=dict(default=None, type='str', required=True),
            rights=dict(default=None, type='list'),
            users=dict(default=None, type='list'),
            state=dict(default='present', type='str'),
        ),
        #supports_check_mode=True
    )

    zapi = ZabbixAPI(ZabbixConnection(module.params['zbx_server'],
                                      module.params['zbx_user'],
                                      module.params['zbx_password'],
                                      module.params['zbx_debug']))

    zbx_user = ZabbixUser(zapi)
    zbx_usergroup = ZabbixUserGroup(zapi)
    zbx_class_name = 'usergroup'
    idname = "usrgrpid"
    uname = module.params['name']
    state = module.params['state']

    content = zapi.get_content(zbx_class_name,
                               'get',
                               {'search': {'name': uname},
                                'selectUsers': 'userid',
                               })

    
    #******#
    # GET
    #******#
    if state == 'list':
        module.exit_json(changed=False, results=content['result'], state="list")

    #******#
    # DELETE
    #******#
    if state == 'absent':
        if not exists(content):
            module.exit_json(changed=False, state="absent")

        if not uname:
            module.exit_json(failed=True, changed=False, results='Need to pass in a user.', state="error")

        content = zapi.get_content(zbx_class_name, 'delete', [content['result'][0][idname]])
        module.exit_json(changed=True, results=content['result'], state="absent")

    # Create and Update
    if state == 'present':

        params = {'name': uname,
                  'rights': zbx_usergroup.get_rights(zapi, module.params['rights']),
                  'users_status': Utils.get_user_status(module.params['status']),
                  'gui_access': Utils.get_gui_access(module.params['gui_access']),
                  'debug_mode': Utils.get_debug_mode(module.params['debug_mode']),
                  'userids': zbx_users.get_userids(zapi, module.params['users']),
                 }

        # Remove any None valued params
        _ = [params.pop(key, None) for key in params.keys() if params[key] == None]

        #******#
        # CREATE
        #******#
        if not exists(content):
            # if we didn't find it, create it
            content = zapi.get_content(zbx_class_name, 'create', params)

            if content.has_key('error'):
                module.exit_json(failed=True, changed=True, results=content['error'], state="present")

            module.exit_json(changed=True, results=content['result'], state='present')


        ########
        # UPDATE
        ########
        differences = {}
        zab_results = content['result'][0]
        for key, value in params.items():
            if key == 'rights':
                differences['rights'] = value

            elif key == 'userids' and zab_results.has_key('users'):
                if zab_results['users'] != value:
                    differences['userids'] = value

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
