# pylint: skip-file

# pylint: disable=too-many-branches
def main():
    '''
    Ansible zabbix module for mediatype
    '''

    module = AnsibleModule(
        argument_spec=dict(
            zbx_server=dict(default='https://localhost/zabbix/api_jsonrpc.php', type='str'),
            zbx_user=dict(default=os.environ.get('ZABBIX_USER', None), type='str'),
            zbx_password=dict(default=os.environ.get('ZABBIX_PASSWORD', None), type='str'),
            zbx_debug=dict(default=False, type='bool'),
            login=dict(default=None, type='str'),
            active=dict(default=False, type='bool'),
            medias=dict(default=None, type='list'),
            mediaid=dict(default=None, type='int'),
            mediatype=dict(default=None, type='str'),
            mediatype_desc=dict(default=None, type='str'),
            #d-d,hh:mm-hh:mm;d-d,hh:mm-hh:mm...
            period=dict(default=None, type='str'),
            sendto=dict(default=None, type='str'),
            severity=dict(default=None, type='str'),
            state=dict(default='present', type='str'),
        ),
        #supports_check_mode=True
    )

    zapi = ZabbixAPI(ZabbixConnection(module.params['zbx_server'],
                                      module.params['zbx_user'],
                                      module.params['zbx_password'],
                                      module.params['zbx_debug']))

    #Set the instance and the template for the rest of the calls
    zbx_class_name = 'user'
    idname = "mediaid"
    state = module.params['state']

    # User media is fetched through the usermedia.get
    zbx_user_query = get_zbx_user_query_data(zapi, module.params['login'])
    content = zapi.get_content('usermedia', 'get',
                               {'userids': [uid for user, uid in zbx_user_query.items()]})
    #####
    # Get
    #####
    if state == 'list':
        module.exit_json(changed=False, results=content['result'], state="list")

    ########
    # Delete
    ########
    if state == 'absent':
        if not exists(content) or len(content['result']) == 0:
            module.exit_json(changed=False, state="absent")

        if not module.params['login']:
            module.exit_json(failed=True, changed=False, results='Must specifiy a user login.', state="absent")

        content = zapi.get_content(zbx_class_name, 'deletemedia', [res[idname] for res in content['result']])

        if content.has_key('error'):
            module.exit_json(changed=False, results=content['error'], state="absent")

        module.exit_json(changed=True, results=content['result'], state="absent")

    # Create and Update
    if state == 'present':
        active = get_active(module.params['active'])
        mtypeid = get_mediatype(zapi, module.params['mediatype'], module.params['mediatype_desc'])

        medias = module.params['medias']
        if medias == None:
            medias = [{'mediatypeid': mtypeid,
                       'sendto': module.params['sendto'],
                       'active': active,
                       'severity': int(get_severity(module.params['severity'])),
                       'period': module.params['period'],
                      }]
        else:
            medias = preprocess_medias(zapi, medias)

        params = {'users': [zbx_user_query],
                  'medias': medias,
                  'output': 'extend',
                 }

        ########
        # Create
        ########
        if not exists(content):
            if not params['medias']:
                module.exit_json(changed=False, results=content['result'], state='present')

            # if we didn't find it, create it
            content = zapi.get_content(zbx_class_name, 'addmedia', params)

            if content.has_key('error'):
                module.exit_json(failed=True, changed=False, results=content['error'], state="present")

            module.exit_json(changed=True, results=content['result'], state='present')

        # mediaid signifies an update
        # If user params exists, check to see if they already exist in zabbix
        # if they exist, then return as no update
        # elif they do not exist, then take user params only
        ########
        # Update
        ########
        diff = {'medias': [], 'users': {}}
        _ = [diff['medias'].append(media) for media in params['medias'] if not find_media(content['result'], media)]

        if not diff['medias']:
            module.exit_json(changed=False, results=content['result'], state="present")

        for user in params['users']:
            diff['users']['userid'] = user['userid']

        # Medias have no real unique key so therefore we need to make it like the incoming user's request
        diff['medias'] = medias

        # We have differences and need to update
        content = zapi.get_content(zbx_class_name, 'updatemedia', diff)

        if content.has_key('error'):
            module.exit_json(failed=True, changed=False, results=content['error'], state="present")

        module.exit_json(changed=True, results=content['result'], state="present")

    module.exit_json(failed=True,
                     changed=False,
                     results='Unknown state passed. %s' % state,
                     state="unknown")

# pylint: disable=redefined-builtin, unused-wildcard-import, wildcard-import, locally-disabled
# import module snippets.  This are required
from ansible.module_utils.basic import *

main()
