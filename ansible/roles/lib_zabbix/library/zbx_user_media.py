#!/usr/bin/env python
#     ___ ___ _  _ ___ ___    _ _____ ___ ___
#    / __| __| \| | __| _ \  /_\_   _| __|   \
#   | (_ | _|| .` | _||   / / _ \| | | _|| |) |
#    \___|___|_|\_|___|_|_\/_/_\_\_|_|___|___/_ _____
#   |   \ / _ \  | \| |/ _ \_   _| | __|   \_ _|_   _|
#   | |) | (_) | | .` | (_) || |   | _|| |) | |  | |
#   |___/ \___/  |_|\_|\___/ |_|   |___|___/___| |_|

import os


class ZabbixUtils(object):
    '''Utility class for help functions'''

    @staticmethod
    def exists(content, key='result'):
        ''' Check if key exists in content or the size of content[key] > 0
        '''
        if not content.has_key(key):
            return False

        if not content[key]:
            return False

        return True

    @staticmethod
    def get_passwd(passwd):
        '''Determine if password is set, if not, return 'zabbix'
        '''
        if passwd:
            return passwd

        return 'zabbix'

    @staticmethod
    def get_severity(severity):
        ''' determine severity
        '''
        if isinstance(severity, int) or \
           isinstance(severity, str):
            return severity

        val = 0
        sev_map = {
            'not': 2**0,
            'inf': 2**1,
            'war': 2**2,
            'ave':  2**3,
            'avg':  2**3,
            'hig': 2**4,
            'dis': 2**5,
        }
        for level in severity:
            val |= sev_map[level[:3].lower()]
        return val

    @staticmethod
    def get_active(is_active):
        '''Determine active value
           0 - enabled
           1 - disabled
        '''
        active = 1
        if is_active:
            active = 0

        return active
#!/usr/bin/env python
'''
  ZabbixAPI library

if __name__ == '__main__':
    server = 'http://localhost/zabbix/api_jsonrpc.php'
    username = ''
    password = ''
    zbc = ZabbixConnection(server, username, password)
    zbx = ZabbixAPI(data)
    print zbx.get_content('user', 'get', {})

'''
# vim: expandtab:tabstop=4:shiftwidth=4

#   Copyright 2015 Red Hat Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#  Purpose: An ansible module to communicate with zabbix.
#  Requires Packages on python < 2.7.9:
#      python-pyasn1 python-ndg_httpsclient pyOpenSSL
#

# pylint: disable=line-too-long
# Disabling line length for readability

import json
import requests
import httplib
import copy

class ZabbixAPIError(Exception):
    '''
        ZabbixAPIError
        Exists to propagate errors up from the api
    '''
    pass

# Disabling to have DTO
# pylint: disable=too-few-public-methods

# DTO needs an extra arg
# pylint: disable=too-many-arguments

class ZabbixConnection(object):
    '''
    Placeholder for connection options
    '''
    def __init__(self, server, username, password, ssl_verify=False, verbose=False):
        self.server = server
        self.username = username
        self.password = password
        self.verbose = verbose
        self.ssl_verify = ssl_verify

class ZabbixAPI(object):
    '''
        ZabbixAPI class
    '''
    classes = {
        'Action': ['create', 'delete', 'get', 'update'],
        'Alert': ['get'],
        'Application': ['create', 'delete', 'get', 'massadd', 'update'],
        'Configuration': ['export', 'import'],
        'Dhost': ['get'],
        'Dcheck': ['get'],
        'Discoveryrule': ['copy', 'create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Drule': ['copy', 'create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Dservice': ['get'],
        'Event': ['acknowledge', 'get'],
        'Graph': ['create', 'delete', 'get', 'update'],
        'Graphitem': ['get'],
        'Graphprototype': ['create', 'delete', 'get', 'update'],
        'History': ['get'],
        'Hostgroup': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'massadd', 'massremove', 'massupdate', 'update'],
        'Hostinterface': ['create', 'delete', 'get', 'massadd', 'massremove', 'replacehostinterfaces', 'update'],
        'Host': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'massadd', 'massremove', 'massupdate', 'update'],
        'Hostprototype': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Httptest': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Iconmap': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Image': ['create', 'delete', 'get', 'update'],
        'Item': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Itemprototype': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Maintenance': ['create', 'delete', 'get', 'update'],
        'Map': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Mediatype': ['create', 'delete', 'get', 'update'],
        'Proxy': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Screen': ['create', 'delete', 'get', 'update'],
        'Screenitem': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'update', 'updatebyposition'],
        'Script': ['create', 'delete', 'execute', 'get', 'getscriptsbyhosts', 'update'],
        'Service': ['adddependencies', 'addtimes', 'create', 'delete', 'deletedependencies', 'deletetimes', 'get', 'getsla', 'isreadable', 'iswritable', 'update'],
        'Template': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'massadd', 'massremove', 'massupdate', 'update'],
        'Templatescreen': ['copy', 'create', 'delete', 'get', 'isreadable', 'iswritable', 'update'],
        'Templatescreenitem': ['get'],
        'Trigger': ['adddependencies', 'create', 'delete', 'deletedependencies', 'get', 'isreadable', 'iswritable', 'update'],
        'Triggerprototype': ['create', 'delete', 'get', 'update'],
        'User': ['addmedia', 'create', 'delete', 'deletemedia', 'get', 'isreadable', 'iswritable', 'login', 'logout', 'update', 'updatemedia', 'updateprofile'],
        'Usergroup': ['create', 'delete', 'get', 'isreadable', 'iswritable', 'massadd', 'massupdate', 'update'],
        'Usermacro': ['create', 'createglobal', 'delete', 'deleteglobal', 'get', 'update', 'updateglobal'],
        'Usermedia': ['get'],
    }

    def __init__(self, zabbix_connection=None):
        self.server = zabbix_connection.server
        self.username = zabbix_connection.username
        self.password = zabbix_connection.password
        if any([value == None for value in [self.server, self.username, self.password]]):
            raise ZabbixAPIError('Please specify zabbix server url, username, and password.')

        self.verbose = zabbix_connection.verbose
        self.ssl_verify = zabbix_connection.ssl_verify
        if self.verbose:
            httplib.HTTPSConnection.debuglevel = 1
            httplib.HTTPConnection.debuglevel = 1
        self.auth = None

        for cname, _ in self.classes.items():
            setattr(self, cname.lower(), getattr(self, cname)(self))

        # pylint: disable=no-member
        # This method does not exist until the metaprogramming executed
        resp, content = self.user.login(user=self.username, password=self.password)

        if resp.status_code == 200:
            if content.has_key('result'):
                self.auth = content['result']
            elif content.has_key('error'):
                raise ZabbixAPIError("Unable to authenticate with zabbix server. {0} ".format(content['error']))
        else:
            raise ZabbixAPIError("Error in call to zabbix. Http status: {0}.".format(resp.status_code))

    def perform(self, method, rpc_params):
        '''
        This method calls your zabbix server.

        It requires the following parameters in order for a proper request to be processed:
            jsonrpc - the version of the JSON-RPC protocol used by the API;
                      the Zabbix API implements JSON-RPC version 2.0;
            method - the API method being called;
            rpc_params - parameters that will be passed to the API method;
            id - an arbitrary identifier of the request;
            auth - a user authentication token; since we don't have one yet, it's set to null.
        '''
        jsonrpc = "2.0"
        rid = 1

        headers = {}
        headers["Content-type"] = "application/json"

        body = {
            "jsonrpc": jsonrpc,
            "method":  method,
            "params":  rpc_params.get('params', {}),
            "id":      rid,
            'auth':    self.auth,
        }

        if method in ['user.login', 'api.version']:
            del body['auth']

        body = json.dumps(body)

        if self.verbose:
            print "BODY:", body
            print "METHOD:", method
            print "HEADERS:", headers

        request = requests.Request("POST", self.server, data=body, headers=headers)
        session = requests.Session()
        req_prep = session.prepare_request(request)
        response = session.send(req_prep, verify=self.ssl_verify)

        if response.status_code not in [200, 201]:
            raise ZabbixAPIError('Error calling zabbix.  Zabbix returned %s' % response.status_code)

        if self.verbose:
            print "RESPONSE:", response.text

        try:
            content = response.json()
        except ValueError as err:
            content = {"error": err.message}

        return response, content

    @staticmethod
    def meta(cname, method_names):
        '''
        This bit of metaprogramming is where the ZabbixAPI subclasses are created.
        For each of ZabbixAPI.classes we create a class from the key and methods
        from the ZabbixAPI.classes values.  We pass a reference to ZabbixAPI class
        to each subclass in order for each to be able to call the perform method.
        '''
        def meta_method(_class, method_name):
            '''
            This meta method allows a class to add methods to it.
            '''
            # This template method is a stub method for each of the subclass
            # methods.
            def template_method(self, params=None, **rpc_params):
                '''
                This template method is a stub method for each of the subclass methods.
                '''
                if params:
                    rpc_params['params'] = params
                else:
                    rpc_params['params'] = copy.deepcopy(rpc_params)

                return self.parent.perform(cname.lower()+"."+method_name, rpc_params)

            template_method.__doc__ = \
              "https://www.zabbix.com/documentation/2.4/manual/api/reference/%s/%s" % \
              (cname.lower(), method_name)
            template_method.__name__ = method_name
            # this is where the template method is placed inside of the subclass
            # e.g. setattr(User, "create", stub_method)
            setattr(_class, template_method.__name__, template_method)

        # This class call instantiates a subclass. e.g. User
        _class = type(cname,
                      (object,),
                      {'__doc__': \
                      "https://www.zabbix.com/documentation/2.4/manual/api/reference/%s" % cname.lower()})
        def __init__(self, parent):
            '''
            This init method gets placed inside of the _class
            to allow it to be instantiated.  A reference to the parent class(ZabbixAPI)
            is passed in to allow each class access to the perform method.
            '''
            self.parent = parent

        # This attaches the init to the subclass. e.g. Create
        setattr(_class, __init__.__name__, __init__)
        # For each of our ZabbixAPI.classes dict values
        # Create a method and attach it to our subclass.
        # e.g.  'User': ['delete', 'get', 'updatemedia', 'updateprofile',
        #                'update', 'iswritable', 'logout', 'addmedia', 'create',
        #                'login', 'deletemedia', 'isreadable'],
        # User.delete
        # User.get
        for method_name in method_names:
            meta_method(_class, method_name)
        # Return our subclass with all methods attached
        return _class

    def get_content(self, zbx_class_name, method, params):
        '''
        This bit of metaprogramming takes a zabbix_class_name (e.g. 'user' )
        This gets the instantiated object of type user and calls method
        with params as the parameters.

        Returns the zabbix query results
        '''
        zbx_class_inst = self.__getattribute__(zbx_class_name.lower())
        zbx_class = self.__getattribute__(zbx_class_name.capitalize())
        return zbx_class.__dict__[method](zbx_class_inst, params)[1]


# Attach all ZabbixAPI.classes to ZabbixAPI class through metaprogramming
for _class_name, _method_names in ZabbixAPI.classes.items():
    setattr(ZabbixAPI, _class_name, ZabbixAPI.meta(_class_name, _method_names))


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
	    mtypeid = self.get_mtype(zapi, mediatype)
	elif mediatype_desc:
	    mtypeid = self.get_mtype(zapi, mediatype_desc)

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
