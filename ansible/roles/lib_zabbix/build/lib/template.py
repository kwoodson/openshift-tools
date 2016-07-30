# pylint: skip-file

class ZabbixTemplate(object):
    '''class to manage the zabbix template '''

    def __init__(self, zbxapi):
        '''constructor for zabbix host'''
        self.zapi = zbxapi


    @staticmethod
    def get_template_id_by_name(self, t_name):
	'''get the template id by name'''
	content = self.zapi.get_content('template',
				        'get',
				        {'filter': {'host': t_name}})

	return content['result'][0]['templateid']

