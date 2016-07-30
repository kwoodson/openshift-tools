# pylint: skip-file

class ZabbixUserGroup(object):
    '''class to manage the zabbix user '''

    def __init__(self, zapi):
        self.zapi = zapi

    def get_rights(self, rights):
	'''Get rights 
	'''
	if rights == None:
	    return None

	perms = []
	for right in rights:
	    hstgrp = right.keys()[0]
	    perm = right.values()[0]
	    content = self.zapi.get_content('hostgroup', 'get', {'search': {'name': hstgrp}})
	    if content['result']:
		permission = 0
		if perm == 'ro':
		    permission = 2
		elif perm == 'rw':
		    permission = 3
		perms.append({'id': content['result'][0]['groupid'],
			      'permission': permission})
	return perms

    def get_user_groups(self, groups):
	'''get the mediatype id from the mediatype name'''
	user_groups = []

	for group in groups:
	    content = self.zapi.get_content('usergroup',
					    'get',
					    {'search': {'name': group}})
	    for result in content['result']:
		user_groups.append({'usrgrpid': result['usrgrpid']})

	return user_groups

