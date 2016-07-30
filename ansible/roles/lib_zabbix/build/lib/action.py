# pylint: skip-file

class ZabbixAction(object):
    '''class to manage the zabbix user '''

    def __init__(self, zapi):
        self.zapi = zapi

    @staticmethod
    def conditions_equal(zab_conditions, user_conditions):
	'''Compare two lists of conditions'''
	c_type = 'conditiontype'
	_op = 'operator'
	val = 'value'
	if len(user_conditions) != len(zab_conditions):
	    return False

	for zab_cond, user_cond in zip(zab_conditions, user_conditions):
	    if zab_cond[c_type] != str(user_cond[c_type]) or zab_cond[_op] != str(user_cond[_op]) or \
	       zab_cond[val] != str(user_cond[val]):
		return False

	return True

    @staticmethod
    def filter_differences(zabbix_filters, user_filters):
	'''Determine the differences from user and zabbix for operations'''
	rval = {}
	for key, val in user_filters.items():

	    if key == 'conditions':
		if not conditions_equal(zabbix_filters[key], val):
		    rval[key] = val

	    elif zabbix_filters[key] != str(val):
		rval[key] = val

	return rval

    @staticmethod
    def opconditions_diff(zab_val, user_val):
	''' Report whether there are differences between opconditions on
	    zabbix and opconditions supplied by user '''

	if len(zab_val) != len(user_val):
	    return True

	for z_cond, u_cond in zip(zab_val, user_val):
	    if not all([str(u_cond[op_key]) == z_cond[op_key] for op_key in \
			['conditiontype', 'operator', 'value']]):
		return True

	return False

    @staticmethod
    def opmessage_diff(zab_val, user_val):
	''' Report whether there are differences between opmessage on
	    zabbix and opmessage supplied by user '''

	for op_msg_key, op_msg_val in user_val.items():
	    if zab_val[op_msg_key] != str(op_msg_val):
		return True

	return False

    @staticmethod
    def opmessage_grp_diff(zab_val, user_val):
	''' Report whether there are differences between opmessage_grp
	    on zabbix and opmessage_grp supplied by user '''

	zab_grp_ids = set([ugrp['usrgrpid'] for ugrp in zab_val])
	usr_grp_ids = set([ugrp['usrgrpid'] for ugrp in user_val])
	if usr_grp_ids != zab_grp_ids:
	    return True

	return False

    @staticmethod
    def opmessage_usr_diff(zab_val, user_val):
	''' Report whether there are differences between opmessage_usr
	    on zabbix and opmessage_usr supplied by user '''

	zab_usr_ids = set([usr['userid'] for usr in zab_val])
	usr_ids = set([usr['userid'] for usr in user_val])
	if usr_ids != zab_usr_ids:
	    return True

	return False

    @staticmethod
    def opcommand_diff(zab_op_cmd, usr_op_cmd):
	''' Check whether user-provided opcommand matches what's already
	    stored in Zabbix '''

	for usr_op_cmd_key, usr_op_cmd_val in usr_op_cmd.items():
	    if zab_op_cmd[usr_op_cmd_key] != str(usr_op_cmd_val):
		return True
	return False

    @staticmethod
    def host_in_zabbix(zab_hosts, usr_host):
	''' Check whether a particular user host is already in the
	    Zabbix list of hosts '''

	for usr_hst_key, usr_hst_val in usr_host.items():
	    for zab_host in zab_hosts:
		if usr_hst_key in zab_host and \
		   zab_host[usr_hst_key] == str(usr_hst_val):
		    return True

	return False

    # We are comparing two lists of dictionaries (the one stored on zabbix and the
    # one the user is providing). For each type of operation, determine whether there
    # is a difference between what is stored on zabbix and what the user is providing.
    # If there is a difference, we take the user-provided data for what needs to
    # be stored/updated into zabbix.
    @staticmethod
    def operation_differences(zabbix_ops, user_ops):
	'''Determine the differences from user and zabbix for operations'''

	# if they don't match, take the user options
	if len(zabbix_ops) != len(user_ops):
	    return user_ops

	rval = {}
	for zab, user in zip(zabbix_ops, user_ops):
	    for oper in user.keys():
		if oper == 'opconditions' and opconditions_diff(zab[oper], \
								    user[oper]):
		    rval[oper] = user[oper]

		elif oper == 'opmessage' and opmessage_diff(zab[oper], \
							    user[oper]):
		    rval[oper] = user[oper]

		elif oper == 'opmessage_grp' and opmessage_grp_diff(zab[oper], \
								    user[oper]):
		    rval[oper] = user[oper]

		elif oper == 'opmessage_usr' and opmessage_usr_diff(zab[oper], \
								    user[oper]):
		    rval[oper] = user[oper]

		elif oper == 'opcommand' and opcommand_diff(zab[oper], \
							    user[oper]):
		    rval[oper] = user[oper]

		# opcommand_grp can be treated just like opcommand_hst
		# as opcommand_grp[] is just a list of groups
		elif oper == 'opcommand_hst' or oper == 'opcommand_grp':
		    if not hostlist_in_zabbix(zab[oper], user[oper]):
			rval[oper] = user[oper]

		# if it's any other type of operation than the ones tested above
		# just do a direct compare
		elif oper not in ['opconditions', 'opmessage', 'opmessage_grp',
				  'opmessage_usr', 'opcommand', 'opcommand_hst',
				  'opcommand_grp'] \
			    and str(zab[oper]) != str(user[oper]):
		    rval[oper] = user[oper]

	return rval

    @staticmethod
    def get_condition_type(event_source, inc_condition):
	'''determine the condition type'''
	c_types = {}
	if event_source == 'trigger':
	    c_types = {'host group': 0,
		       'host': 1,
		       'trigger': 2,
		       'trigger name': 3,
		       'trigger severity': 4,
		       'trigger value': 5,
		       'time period': 6,
		       'host template': 13,
		       'application': 15,
		       'maintenance status': 16,
		      }

	elif event_source == 'discovery':
	    c_types = {'host IP': 7,
		       'discovered service type': 8,
		       'discovered service port': 9,
		       'discovery status': 10,
		       'uptime or downtime duration': 11,
		       'received value': 12,
		       'discovery rule': 18,
		       'discovery check': 19,
		       'proxy': 20,
		       'discovery object': 21,
		      }

	elif event_source == 'auto':
	    c_types = {'proxy': 20,
		       'host name': 22,
		       'host metadata': 24,
		      }

	elif event_source == 'internal':
	    c_types = {'host group': 0,
		       'host': 1,
		       'host template': 13,
		       'application': 15,
		       'event type': 23,
		      }
	else:
	    raise ZabbixAPIError('Unkown event source %s' % event_source)

	return c_types[inc_condition]

