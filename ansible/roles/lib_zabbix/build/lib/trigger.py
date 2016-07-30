# pylint: skip-file

class ZabbixTrigger(object):
    '''class to manage the zabbix host '''

    def __init__(self, zbxapi):
        '''constructor for zabbix host'''
        self.zapi = zbxapi

    @staticmethod
    def get_trigger_value(inc_trigger):
	'''determine the proper trigger value'''
	rval = 1
	if inc_trigger == 'PROBLEM':
	    rval = 1
	else:
	    rval = 0

	return rval

