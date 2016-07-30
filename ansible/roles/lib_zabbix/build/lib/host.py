# pylint: skip-file

class ZabbixHost(object):
    '''class to manage the zabbix host '''

    def __init__(self, zbxapi):
        '''constructor for zabbix host'''
        self.zapi = zbxapi
        pass

    def get_host_id_by_name(self, host_name):
	'''Get host id by name'''
	content = self.zapi.get_content('host',
				        'get',
				        {'filter': {'name': host_name}})

	return content['result'][0]['hostid']

