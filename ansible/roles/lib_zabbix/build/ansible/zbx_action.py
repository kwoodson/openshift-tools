# pylint: skip-file

# pylint: disable=import-error
CUSTOM_SCRIPT_ACTION = '0'
IPMI_ACTION = '1'
SSH_ACTION = '2'
TELNET_ACTION = '3'
GLOBAL_SCRIPT_ACTION = '4'

EXECUTE_ON_ZABBIX_AGENT = '0'
EXECUTE_ON_ZABBIX_SERVER = '1'

OPERATION_REMOTE_COMMAND = '1'

def get_operation_type(inc_operation):
    ''' determine the correct operation type'''
    o_types = {'send message': 0,
               'remote command': OPERATION_REMOTE_COMMAND,
               'add host': 2,
               'remove host': 3,
               'add to host group': 4,
               'remove from host group': 5,
               'link to template': 6,
               'unlink from template': 7,
               'enable host': 8,
               'disable host': 9,
              }

    return o_types[inc_operation]

def get_opcommand_type(opcommand_type):
    ''' determine the opcommand type '''
    oc_types = {'custom script': CUSTOM_SCRIPT_ACTION,
                'IPMI': IPMI_ACTION,
                'SSH': SSH_ACTION,
                'Telnet': TELNET_ACTION,
                'global script': GLOBAL_SCRIPT_ACTION,
               }

    return oc_types[opcommand_type]

def get_execute_on(execute_on):
    ''' determine the execution target '''
    e_types = {'zabbix agent': EXECUTE_ON_ZABBIX_AGENT,
               'zabbix server': EXECUTE_ON_ZABBIX_SERVER,
              }

    return e_types[execute_on]

def action_remote_command(ansible_module, zapi, operation):
    ''' Process remote command type of actions '''

    if 'type' not in operation['opcommand']:
        ansible_module.exit_json(failed=True, changed=False, state='unknown',
                                 results="No Operation Type provided")

    operation['opcommand']['type'] = get_opcommand_type(operation['opcommand']['type'])

    if operation['opcommand']['type'] == CUSTOM_SCRIPT_ACTION:

        if 'execute_on' in operation['opcommand']:
            operation['opcommand']['execute_on'] = get_execute_on(operation['opcommand']['execute_on'])

        # custom script still requires the target hosts/groups to be set
        operation['opcommand_hst'] = []
        operation['opcommand_grp'] = []
        for usr_host in operation['target_hosts']:
            if usr_host['target_type'] == 'zabbix server':
                # 0 = target host local/current host
                operation['opcommand_hst'].append({'hostid': 0})
            elif usr_host['target_type'] == 'group':
                group_name = usr_host['target']
                gid = get_host_group_id_by_name(zapi, group_name)
                operation['opcommand_grp'].append({'groupid': gid})
            elif usr_host['target_type'] == 'host':
                host_name = usr_host['target']
                hid = get_host_id_by_name(zapi, host_name)
                operation['opcommand_hst'].append({'hostid': hid})

        # 'target_hosts' is just to make it easier to build zbx_actions
        # not part of ZabbixAPI
        del operation['target_hosts']
    else:
        ansible_module.exit_json(failed=True, changed=False, state='unknown',
                                 results="Unsupported remote command type")


def get_action_operations(ansible_module, zapi, inc_operations):
    '''Convert the operations into syntax for api'''
    for operation in inc_operations:
        operation['operationtype'] = get_operation_type(operation['operationtype'])
        if operation['operationtype'] == 0: # send message.  Need to fix the
            operation['opmessage']['mediatypeid'] = \
             get_mediatype_id_by_name(zapi, operation['opmessage']['mediatypeid'])
            operation['opmessage_grp'] = get_user_groups(zapi, operation.get('opmessage_grp', []))
            operation['opmessage_usr'] = get_users(zapi, operation.get('opmessage_usr', []))
            if operation['opmessage']['default_msg']:
                operation['opmessage']['default_msg'] = 1
            else:
                operation['opmessage']['default_msg'] = 0

        elif operation['operationtype'] == OPERATION_REMOTE_COMMAND:
            action_remote_command(ansible_module, zapi, operation)

        # Handle Operation conditions:
        # Currently there is only 1 available which
        # is 'event acknowledged'.  In the future
        # if there are any added we will need to pass this
        # option to a function and return the correct conditiontype
        if operation.has_key('opconditions'):
            for condition in operation['opconditions']:
                if condition['conditiontype'] == 'event acknowledged':
                    condition['conditiontype'] = 14

                if condition['operator'] == '=':
                    condition['operator'] = 0

                if condition['value'] == 'acknowledged':
                    condition['value'] = 1
                else:
                    condition['value'] = 0


    return inc_operations

def get_operation_evaltype(inc_type):
    '''get the operation evaltype'''
    rval = 0
    if inc_type == 'and/or':
        rval = 0
    elif inc_type == 'and':
        rval = 1
    elif inc_type == 'or':
        rval = 2
    elif inc_type == 'custom':
        rval = 3

    return rval

def get_action_conditions(zapi, event_source, inc_conditions):
    '''Convert the conditions into syntax for api'''

    calc_type = inc_conditions.pop('calculation_type')
    inc_conditions['evaltype'] = get_operation_evaltype(calc_type)
    for cond in inc_conditions['conditions']:

        cond['operator'] = get_condition_operator(cond['operator'])
        # Based on conditiontype we need to set the proper value
        # e.g. conditiontype = hostgroup then the value needs to be a hostgroup id
        # e.g. conditiontype = host the value needs to be a host id
        cond['conditiontype'] = get_condition_type(event_source, cond['conditiontype'])
        if cond['conditiontype'] == 0:
            cond['value'] = get_host_group_id_by_name(zapi, cond['value'])
        elif cond['conditiontype'] == 1:
            cond['value'] = get_host_id_by_name(zapi, cond['value'])
        elif cond['conditiontype'] == 4:
            cond['value'] = get_priority(cond['value'])

        elif cond['conditiontype'] == 5:
            cond['value'] = get_trigger_value(cond['value'])
        elif cond['conditiontype'] == 13:
            cond['value'] = get_template_id_by_name(zapi, cond['value'])
        elif cond['conditiontype'] == 16:
            cond['value'] = ''

    return inc_conditions


def get_send_recovery(send_recovery):
    '''Get the integer value'''
    rval = 0
    if send_recovery:
        rval = 1

    return rval

# The branches are needed for CRUD and error handling
# pylint: disable=too-many-branches
def main():
    '''
    ansible zabbix module for zbx_item
    '''


    module = AnsibleModule(
        argument_spec=dict(
            zbx_server=dict(default='https://localhost/zabbix/api_jsonrpc.php', type='str'),
            zbx_user=dict(default=os.environ.get('ZABBIX_USER', None), type='str'),
            zbx_password=dict(default=os.environ.get('ZABBIX_PASSWORD', None), type='str'),
            zbx_debug=dict(default=False, type='bool'),

            name=dict(default=None, type='str'),
            event_source=dict(default='trigger', choices=['trigger', 'discovery', 'auto', 'internal'], type='str'),
            action_subject=dict(default="{TRIGGER.NAME}: {TRIGGER.STATUS}", type='str'),
            action_message=dict(default="{TRIGGER.NAME}: {TRIGGER.STATUS}\r\n" +
                                "Last value: {ITEM.LASTVALUE}\r\n\r\n{TRIGGER.URL}", type='str'),
            reply_subject=dict(default="{TRIGGER.NAME}: {TRIGGER.STATUS}", type='str'),
            reply_message=dict(default="Trigger: {TRIGGER.NAME}\r\nTrigger status: {TRIGGER.STATUS}\r\n" +
                               "Trigger severity: {TRIGGER.SEVERITY}\r\nTrigger URL: {TRIGGER.URL}\r\n\r\n" +
                               "Item values:\r\n\r\n1. {ITEM.NAME1} ({HOST.NAME1}:{ITEM.KEY1}): " +
                               "{ITEM.VALUE1}\r\n2. {ITEM.NAME2} ({HOST.NAME2}:{ITEM.KEY2}): " +
                               "{ITEM.VALUE2}\r\n3. {ITEM.NAME3} ({HOST.NAME3}:{ITEM.KEY3}): " +
                               "{ITEM.VALUE3}", type='str'),
            send_recovery=dict(default=False, type='bool'),
            status=dict(default=None, type='str'),
            escalation_time=dict(default=60, type='int'),
            conditions_filter=dict(default=None, type='dict'),
            operations=dict(default=None, type='list'),
            state=dict(default='present', type='str'),
        ),
        #supports_check_mode=True
    )

    zapi = ZabbixAPI(ZabbixConnection(module.params['zbx_server'],
                                      module.params['zbx_user'],
                                      module.params['zbx_password'],
                                      module.params['zbx_debug']))

    #Set the instance and the template for the rest of the calls
    zbx_class_name = 'action'
    state = module.params['state']

    content = zapi.get_content(zbx_class_name,
                               'get',
                               {'search': {'name': module.params['name']},
                                'selectFilter': 'extend',
                                'selectOperations': 'extend',
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

        content = zapi.get_content(zbx_class_name, 'delete', [content['result'][0]['actionid']])
        module.exit_json(changed=True, results=content['result'], state="absent")

    # Create and Update
    if state == 'present':

        conditions = get_action_conditions(zapi, module.params['event_source'], module.params['conditions_filter'])
        operations = get_action_operations(module, zapi,
                                           module.params['operations'])
        params = {'name': module.params['name'],
                  'esc_period': module.params['escalation_time'],
                  'eventsource': get_event_source(module.params['event_source']),
                  'status': get_status(module.params['status']),
                  'def_shortdata': module.params['action_subject'],
                  'def_longdata': module.params['action_message'],
                  'r_shortdata': module.params['reply_subject'],
                  'r_longdata': module.params['reply_message'],
                  'recovery_msg': get_send_recovery(module.params['send_recovery']),
                  'filter': conditions,
                  'operations': operations,
                 }

        # Remove any None valued params
        _ = [params.pop(key, None) for key in params.keys() if params[key] is None]

        #******#
        # CREATE
        #******#
        if not exists(content):
            content = zapi.get_content(zbx_class_name, 'create', params)

            if content.has_key('error'):
                module.exit_json(failed=True, changed=True, results=content['error'], state="present")

            module.exit_json(changed=True, results=content['result'], state='present')


        ########
        # UPDATE
        ########
        _ = params.pop('hostid', None)
        differences = {}
        zab_results = content['result'][0]
        for key, value in params.items():

            if key == 'operations':
                ops = operation_differences(zab_results[key], value)
                if ops:
                    differences[key] = ops

            elif key == 'filter':
                filters = filter_differences(zab_results[key], value)
                if filters:
                    differences[key] = filters

            elif zab_results[key] != value and zab_results[key] != str(value):
                differences[key] = value

        if not differences:
            module.exit_json(changed=False, results=zab_results, state="present")

        # We have differences and need to update.
        # action update requires an id, filters, and operations
        differences['actionid'] = zab_results['actionid']
        differences['operations'] = params['operations']
        differences['filter'] = params['filter']
        content = zapi.get_content(zbx_class_name, 'update', differences)

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
