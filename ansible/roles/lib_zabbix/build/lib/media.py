# pylint: skip-file

class ZabbixMedia(object):
    '''class to manage the zabbix user '''

    def __init__(self, zbxapi):
        '''constructor for zabbix media'''
        self.zapi = zbxapi
        pass

    def get_mtype(self, mtype):
	'''Get mediatype

	   If passed an int, return it as the mediatypeid
	   if its a string, then try to fetch through a description
	'''
	if isinstance(mtype, int):
	    return mtype
	try:
	    return int(mtype)
	except ValueError:
	    pass

	content = self.zapi.get_content('mediatype', 'get', {'filter': {'description': mtype}})
	if content.has_key('result') and content['result']:
	    return content['result'][0]['mediatypeid']

	return None


    def get_media_type(self, mediatype=None, mediatype_desc=None):
	''' Determine mediatypeid
	'''
	mtypeid = None
	if mediatype:
	    mtypeid = self.get_mtype(mediatype)
	elif mediatype_desc:
	    mtypeid = self.get_mtype(mediatype_desc)

	return mtypeid

    def preprocess_medias(self, medias):
	''' Insert the correct information when processing medias '''
	for media in medias:
	    # Fetch the mediatypeid from the media desc (name)
	    if media.has_key('mediatype'):
		media['mediatypeid'] = self.get_media_type(mediatype=None, mediatype_desc=media.pop('mediatype'))

	    media['active'] = get_active(media.get('active'))
	    media['severity'] = int(get_severity(media['severity']))

	return medias

    @staticmethod
    def find_media(medias, user_media):
	''' Find the user media in the list of medias
	'''
	for media in medias:
	    if all([media[key] == str(user_media[key]) for key in user_media.keys()]):
		return media

	return None

    def get_mediatype_id_by_name(self, m_name):
	'''get the mediatype id from the mediatype name'''
	content = self.zapi.get_content('mediatype',
				   'get',
				   {'filter': {'description': m_name}})

	return content['result'][0]['mediatypeid']



    @staticmethod
    def get_event_source(from_src):
	'''Translate even str into value'''
	choices = ['trigger', 'discovery', 'auto', 'internal']
	rval = 0
	try:
	    rval = choices.index(from_src)
	except ValueError as _:
	    ZabbixAPIError('Value not found for event source [%s]' % from_src)

	return rval

    @staticmethod
    def get_status(inc_status):
	'''determine status for action'''
	rval = 1
	if inc_status == 'enabled':
	    rval = 0

	return rval

    @staticmethod
    def get_condition_operator(inc_operator):
	''' determine the condition operator'''
	vals = {'=': 0,
		'<>': 1,
		'like': 2,
		'not like': 3,
		'in': 4,
		'>=': 5,
		'<=': 6,
		'not in': 7,
	       }

	return vals[inc_operator]

