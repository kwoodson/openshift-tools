# pylint: skip-file

class ZabbixHostGroup(object):
    '''class to manage the zabbix host '''

    def __init__(self, zbxapi):
        '''constructor for zabbix host'''
        self.zapi = zbxapi


    @staticmethod
    def get_host_group_id_by_name(self, hg_name):
	'''Get hostgroup id by name'''
	content = self.zapi.get_content('hostgroup',
				   'get',
				   {'filter': {'name': hg_name}})

	return content['result'][0]['groupid']

