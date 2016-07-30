# pylint: skip-file

class ZabbixUser(object):
    '''class to manage the zabbix user '''

    def __init__(self, zapi):
        self.zapi = zapi

    def get_user(self, user):
	''' Get userids from user aliases
	'''
	content = self.zapi.get_content('user', 'get', {'filter': {'alias': user}})
	if content['result']:
	    return content['result'][0]

	return None

    def get_users(zapi, users):
	'''get the mediatype id from the mediatype name'''
	rval_users = []

	for user in users:
	    content = self.get_user(user)
	    rval_users.append({'userid': content['result'][0]['userid']})

	return rval_users

    def get_zbx_user_query_data(self, user_name):
	''' If name exists, retrieve it, and build query params.
	'''
	query = {}
	if user_name:
	    zbx_user = self.get_user(zapi, user_name)
	    query = {'userid': zbx_user['userid']}

	return query

    def get_userids(self, users):
	''' Get userids from user aliases
	'''
	if not users:
	    return None

	userids = []
	for alias in users:
	    content = self.zapi.get_content('user', 'get', {'search': {'alias': alias}})
	    if content['result']:
		userids.append(content['result'][0]['userid'])

	return userids

    @staticmethod
    def get_usertype(user_type):
        '''
        Determine zabbix user account type
        '''
        if not user_type:
            return None

        utype = 1
        if 'super' in user_type:
            utype = 3
        elif 'admin' in user_type or user_type == 'admin':
            utype = 2

        return utype


