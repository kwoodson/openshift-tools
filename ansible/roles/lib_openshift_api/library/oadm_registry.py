#!/usr/bin/env python
#     ___ ___ _  _ ___ ___    _ _____ ___ ___
#    / __| __| \| | __| _ \  /_\_   _| __|   \
#   | (_ | _|| .` | _||   / / _ \| | | _|| |) |
#    \___|___|_|\_|___|_|_\/_/_\_\_|_|___|___/_ _____
#   |   \ / _ \  | \| |/ _ \_   _| | __|   \_ _|_   _|
#   | |) | (_) | | .` | (_) || |   | _|| |) | |  | |
#   |___/ \___/  |_|\_|\___/ |_|   |___|___/___| |_|
'''
   OpenShiftCLI class that wraps the oc commands in a subprocess
'''

import atexit
import json
import os
import shutil
import subprocess
import re

import yaml
# This is here because of a bug that causes yaml
# to incorrectly handle timezone info on timestamps
def timestamp_constructor(_, node):
    '''return timestamps as strings'''
    return str(node.value)
yaml.add_constructor(u'tag:yaml.org,2002:timestamp', timestamp_constructor)

# pylint: disable=too-few-public-methods
class OpenShiftCLI(object):
    ''' Class to wrap the command line tools '''
    def __init__(self,
                 namespace,
                 kubeconfig='/etc/origin/master/admin.kubeconfig',
                 verbose=False):
        ''' Constructor for OpenshiftCLI '''
        self.namespace = namespace
        self.verbose = verbose
        self.kubeconfig = kubeconfig

    # Pylint allows only 5 arguments to be passed.
    # pylint: disable=too-many-arguments
    def _replace_content(self, resource, rname, content, force=False):
        ''' replace the current object with the content '''
        res = self._get(resource, rname)
        if not res['results']:
            return res

        fname = '/tmp/%s' % rname
        yed = Yedit(fname, res['results'][0])
        changes = []
        for key, value in content.items():
            changes.append(yed.put(key, value))

        if any([change[0] for change in changes]):
            yed.write()

            atexit.register(Utils.cleanup, [fname])

            return self._replace(fname, force)

        return {'returncode': 0, 'updated': False}

    def _replace(self, fname, force=False):
        '''return all pods '''
        cmd = ['-n', self.namespace, 'replace', '-f', fname]
        if force:
            cmd.append('--force')
        return self.openshift_cmd(cmd)

    def _create(self, fname):
        '''return all pods '''
        return self.openshift_cmd(['create', '-f', fname, '-n', self.namespace])

    def _delete(self, resource, rname):
        '''return all pods '''
        return self.openshift_cmd(['delete', resource, rname, '-n', self.namespace])

    def _get(self, resource, rname=None):
        '''return a secret by name '''
        cmd = ['get', resource, '-o', 'json', '-n', self.namespace]
        if rname:
            cmd.append(rname)

        rval = self.openshift_cmd(cmd, output=True)
#
        # Ensure results are retuned in an array
        if rval.has_key('items'):
            rval['results'] = rval['items']
        elif not isinstance(rval['results'], list):
            rval['results'] = [rval['results']]

        return rval

    def openshift_cmd(self, cmd, oadm=False, output=False, output_type='json'):
        '''Base command for oc '''
        #cmds = ['/usr/bin/oc', '--config', self.kubeconfig]
        cmds = []
        if oadm:
            cmds = ['/usr/bin/oadm']
        else:
            cmds = ['/usr/bin/oc']

        cmds.extend(cmd)

        rval = {}
        results = ''
        err = None

        if self.verbose:
            print ' '.join(cmds)

        proc = subprocess.Popen(cmds,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env={'KUBECONFIG': self.kubeconfig})

        proc.wait()
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        rval = {"returncode": proc.returncode,
                "results": results,
                "cmd": ' '.join(cmds),
               }

        if proc.returncode == 0:
            if output:
                if output_type == 'json':
                    try:
                        rval['results'] = json.loads(stdout)
                    except ValueError as err:
                        if "No JSON object could be decoded" in err.message:
                            err = err.message
                elif output_type == 'raw':
                    rval['results'] = stdout

            if self.verbose:
                print stdout
                print stderr
                print

            if err:
                rval.update({"err": err,
                             "stderr": stderr,
                             "stdout": stdout,
                             "cmd": cmds
                            })

        else:
            rval.update({"stderr": stderr,
                         "stdout": stdout,
                         "results": {},
                        })

        return rval

class Utils(object):
    ''' utilities for openshiftcli modules '''
    @staticmethod
    def create_file(rname, data, ftype='yaml'):
        ''' create a file in tmp with name and contents'''
        path = os.path.join('/tmp', rname)
        with open(path, 'w') as fds:
            if ftype == 'yaml':
                fds.write(yaml.safe_dump(data, default_flow_style=False))

            elif ftype == 'json':
                fds.write(json.dumps(data))
            else:
                fds.write(data)

        # Register cleanup when module is done
        atexit.register(Utils.cleanup, [path])
        return path

    @staticmethod
    def create_files_from_contents(content, content_type=None):
        '''Turn an array of dict: filename, content into a files array'''
        if isinstance(content, list):
            files = []
            for item in content:
                files.append(Utils.create_file(item['path'], item['data'], ftype=content_type))
            return files

        return Utils.create_file(content['path'], content['data'])


    @staticmethod
    def cleanup(files):
        '''Clean up on exit '''
        for sfile in files:
            if os.path.exists(sfile):
                if os.path.isdir(sfile):
                    shutil.rmtree(sfile)
                elif os.path.isfile(sfile):
                    os.remove(sfile)


    @staticmethod
    def exists(results, _name):
        ''' Check to see if the results include the name '''
        if not results:
            return False


        if Utils.find_result(results, _name):
            return True

        return False

    @staticmethod
    def find_result(results, _name):
        ''' Find the specified result by name'''
        rval = None
        for result in results:
            if result.has_key('metadata') and result['metadata']['name'] == _name:
                rval = result
                break

        return rval

    @staticmethod
    def get_resource_file(sfile, sfile_type='yaml'):
        ''' return the service file  '''
        contents = None
        with open(sfile) as sfd:
            contents = sfd.read()

        if sfile_type == 'yaml':
            contents = yaml.safe_load(contents)
        elif sfile_type == 'json':
            contents = json.loads(contents)

        return contents

    # Disabling too-many-branches.  This is a yaml dictionary comparison function
    # pylint: disable=too-many-branches,too-many-return-statements
    @staticmethod
    def check_def_equal(user_def, result_def, skip_keys=None, debug=False):
        ''' Given a user defined definition, compare it with the results given back by our query.  '''

        # Currently these values are autogenerated and we do not need to check them
        skip = ['metadata', 'status']
        if skip_keys:
            skip.extend(skip_keys)

        for key, value in result_def.items():
            if key in skip:
                continue

            # Both are lists
            if isinstance(value, list):
                if not isinstance(user_def[key], list):
                    if debug:
                        print 'user_def[key] is not a list'
                    return False

                for values in zip(user_def[key], value):
                    if isinstance(values[0], dict) and isinstance(values[1], dict):
                        if debug:
                            print 'sending list - list'
                            print type(values[0])
                            print type(values[1])
                        result = Utils.check_def_equal(values[0], values[1], skip_keys=skip_keys, debug=debug)
                        if not result:
                            print 'list compare returned false'
                            return False

                    elif value != user_def[key]:
                        if debug:
                            print 'value should be identical'
                            print value
                            print user_def[key]
                        return False

            # recurse on a dictionary
            elif isinstance(value, dict):
                if not isinstance(user_def[key], dict):
                    if debug:
                        print "dict returned false not instance of dict"
                    return False

                # before passing ensure keys match
                api_values = set(value.keys()) - set(skip)
                user_values = set(user_def[key].keys()) - set(skip)
                if api_values != user_values:
                    if debug:
                        print api_values
                        print user_values
                        print "keys are not equal in dict"
                    return False

                result = Utils.check_def_equal(user_def[key], value, skip_keys=skip_keys, debug=debug)
                if not result:
                    if debug:
                        print "dict returned false"
                        print result
                    return False

            # Verify each key, value pair is the same
            else:
                if not user_def.has_key(key) or value != user_def[key]:
                    if debug:
                        print "value not equal; user_def does not have key"
                        print value
                        print user_def[key]
                    return False

        return True

class YeditException(Exception):
    ''' Exception class for Yedit '''
    pass

class Yedit(object):
    ''' Class to modify yaml files '''
    re_valid_key = r"(((\[-?\d+\])|([a-zA-Z-./]+)).?)+$"
    re_key = r"(?:\[(-?\d+)\])|([a-zA-Z-./]+)"

    def __init__(self, filename=None, content=None, content_type='yaml'):
        self.content = content
        self.filename = filename
        self.__yaml_dict = content
        self.content_type = content_type
        if self.filename and not self.content:
            self.load(content_type=self.content_type)

    @property
    def yaml_dict(self):
        ''' getter method for yaml_dict '''
        return self.__yaml_dict

    @yaml_dict.setter
    def yaml_dict(self, value):
        ''' setter method for yaml_dict '''
        self.__yaml_dict = value

    @staticmethod
    def remove_entry(data, key):
        ''' remove data at location key '''
        if not (key and re.match(Yedit.re_valid_key, key) and isinstance(data, (list, dict))):
            return None

        key_indexes = re.findall(Yedit.re_key, key)
        for arr_ind, dict_key in key_indexes[:-1]:
            if dict_key and isinstance(data, dict):
                data = data.get(dict_key, None)
            elif arr_ind and isinstance(data, list) and int(arr_ind) <= len(data) - 1:
                data = data[int(arr_ind)]
            else:
                return None

        # process last index for remove
        # expected list entry
        if key_indexes[-1][0]:
            if isinstance(data, list) and int(key_indexes[-1][0]) <= len(data) - 1:
                del data[int(key_indexes[-1][0])]
                return True

        # expected dict entry
        elif key_indexes[-1][1]:
            if isinstance(data, dict):
                del data[key_indexes[-1][1]]
                return True

    @staticmethod
    def add_entry(data, key, item=None):
        ''' Get an item from a dictionary with key notation a.b.c
            d = {'a': {'b': 'c'}}}
            key = a.b
            return c
        '''
        if not (key and re.match(Yedit.re_valid_key, key) and isinstance(data, (list, dict))):
            return None

        curr_data = data

        key_indexes = re.findall(Yedit.re_key, key)
        for arr_ind, dict_key in key_indexes[:-1]:
            if dict_key:
                if isinstance(data, dict) and data.has_key(dict_key):
                    data = data[dict_key]
                    continue

                data[dict_key] = {}
                data = data[dict_key]

            elif arr_ind and isinstance(data, list) and int(arr_ind) <= len(data) - 1:
                data = data[int(arr_ind)]
            else:
                return None

        # process last index for add
        # expected list entry
        if key_indexes[-1][0] and isinstance(data, list) and int(key_indexes[-1][0]) <= len(data) - 1:
            data[int(key_indexes[-1][0])] = item

        # expected dict entry
        elif key_indexes[-1][1] and isinstance(data, dict):
            data[key_indexes[-1][1]] = item

        return curr_data

    @staticmethod
    def get_entry(data, key):
        ''' Get an item from a dictionary with key notation a.b.c
            d = {'a': {'b': 'c'}}}
            key = a.b
            return c
        '''
        if not (key and re.match(Yedit.re_valid_key, key) and isinstance(data, (list, dict))):
            return None

        key_indexes = re.findall(Yedit.re_key, key)
        for arr_ind, dict_key in key_indexes:
            if dict_key and isinstance(data, dict):
                data = data.get(dict_key, None)
            elif arr_ind and isinstance(data, list) and int(arr_ind) <= len(data) - 1:
                data = data[int(arr_ind)]
            else:
                return None

        return data

    def write(self):
        ''' write to file '''
        if not self.filename:
            raise YeditException('Please specify a filename.')

        with open(self.filename, 'w') as yfd:
            yfd.write(yaml.safe_dump(self.yaml_dict, default_flow_style=False))

    def read(self):
        ''' write to file '''
        # check if it exists
        if not self.exists():
            return None

        contents = None
        with open(self.filename) as yfd:
            contents = yfd.read()

        return contents

    def exists(self):
        ''' return whether file exists '''
        if os.path.exists(self.filename):
            return True

        return False

    def load(self, content_type='yaml'):
        ''' return yaml file '''
        contents = self.read()

        if not contents:
            return None

        # check if it is yaml
        try:
            if content_type == 'yaml':
                self.yaml_dict = yaml.load(contents)
            elif content_type == 'json':
                self.yaml_dict = json.loads(contents)
        except yaml.YAMLError as _:
            # Error loading yaml or json
            return None

        return self.yaml_dict

    def get(self, key):
        ''' get a specified key'''
        try:
            entry = Yedit.get_entry(self.yaml_dict, key)
        except KeyError as _:
            entry = None

        return entry

    def delete(self, key):
        ''' remove key from a dict'''
        try:
            entry = Yedit.get_entry(self.yaml_dict, key)
        except KeyError as _:
            entry = None
        if not entry:
            return  (False, self.yaml_dict)

        result = Yedit.remove_entry(self.yaml_dict, key)
        if not result:
            return (False, self.yaml_dict)

        return (True, self.yaml_dict)

    def put(self, key, value):
        ''' put key, value into a dict '''
        try:
            entry = Yedit.get_entry(self.yaml_dict, key)
        except KeyError as _:
            entry = None

        if entry == value:
            return (False, self.yaml_dict)

        result = Yedit.add_entry(self.yaml_dict, key, value)
        if not result:
            return (False, self.yaml_dict)

        return (True, self.yaml_dict)

    def create(self, key, value):
        ''' create a yaml file '''
        if not self.exists():
            self.yaml_dict = {key: value}
            return (True, self.yaml_dict)

        return (False, self.yaml_dict)

# pylint: disable=too-many-instance-attributes
class Volume(object):
    ''' Class to wrap the oc command line tools '''
    volume_mounts_path = {"pod": "spec#containers[0]#volumeMounts",
                          "dc":  "spec#template#spec#containers[0]#volumeMounts",
                          "rc":  "spec#template#spec#containers[0]#volumeMounts",
                         }
    volumes_path = {"pod": "spec#volumes",
                    "dc":  "spec#template#spec#volumes",
                    "rc":  "spec#template#spec#volumes",
                   }

    # pylint allows 5
    # pylint: disable=too-many-arguments
#    def __init__(self,
#                 kind,
#                 vol_name,
#                 mount_path,
#                 mount_type,
#                 secret_name,
#                 claim_size,
#                 claim_name):
#        ''' Constructor for OCVolume '''
#        self.kind = kind
#        self.volume_info = {'secret_name': secret_name,
#                            'name': vol_name,
#                            'type': mount_type,
#                            'path': mount_path,
#                            'claimName': claim_name,
#                            'claimSize': claim_size,
#                           }
#
#        self.volume, self.volume_mount = Volume.create_volume_structure(self.volume_info)

    @staticmethod
    def create_volume_structure(volume_info):
        ''' return a properly structured volume '''
        volume_mount = None
        volume = {'name': volume_info['name']}
        if volume_info['type'] == 'secret':
            volume['secret'] = {}
            volume[volume_info['type']] = {'secretName': volume_info['secret_name']}
            volume_mount = {'mountPath': volume_info['path'],
                            'name': volume_info['name']}
        elif volume_info['type'] == 'emptydir':
            volume['emptyDir'] = {}
            volume_mount = {'mountPath': volume_info['path'],
                            'name': volume_info['name']}
        elif volume_info['type'] == 'pvc':
            volume['persistentVolumeClaim'] = {}
            volume['persistentVolumeClaim']['claimName'] = volume_info['claimName']
            volume['persistentVolumeClaim']['claimSize'] = volume_info['claimSize']
        elif volume_info['type'] == 'hostpath':
            volume['hostPath'] = {}
            volume['hostPath']['path'] = volume_info['path']

        return (volume, volume_mount)

class DeploymentConfig(Yedit):
    ''' Class to wrap the oc command line tools '''

    env_path = "spec#template#spec#containers[0]#env"
    volumes_path = "spec#template#spec#volumes"
    container_path = "spec#template#spec#containers"
    volume_mounts_path = "spec#template#spec#containers[0]#volumeMounts"

    def __init__(self, content):
        ''' Constructor for OpenshiftOC '''
        super(DeploymentConfig, self).__init__(content=content) 

    # pylint: disable=no-member
    def add_env_value(self, key, value):
        ''' add key, value pair to env array '''
        rval = False
        env = self.get_env_vars()
        if env:
            env.append({'name': key, 'value': value})
            rval = True
        else:
            result = self.put(DeploymentConfig.env_path, {'name': key, 'value': value})
            rval = result[0]

        return rval

    def exists_env_value(self, key, value):
        ''' return whether a key, value  pair exists '''
        results = self.get_env_vars() or []
        if not results:
            return False

        for result in results:
            if result['name'] == key and result['value'] == value:
                return True

        return False

    def exists_env_key(self, key):
        ''' return whether a key, value  pair exists '''
        results = self.get_env_vars() or []
        if not results:
            return False

        for result in results:
            if result['name'] == key:
                return True

        return False

    def get_env_vars(self):
        '''return a environment variables '''
        return self.get(DeploymentConfig.env_path)

    def delete_env_var(self, keys):
        '''delete a list of keys '''
        if not isinstance(keys, list):
            keys = [keys]

        env_vars_array = self.get_env_vars() or []
        modified = False
        idx = None
        for key in keys:
            for env_idx, env_var in enumerate(env_vars_array):
                if env_var['name'] == key:
                    idx = env_idx
                    break

            if idx:
                modified = True
                del env_vars_array[idx]

        if modified:
            return True

        return False

    def update_env_var(self, key, value):
        '''place an env in the env var list'''

        env_vars_array = self.get_env_vars() or []
        idx = None
        for env_idx, env_var in enumerate(env_vars_array):
            if env_var['name'] == key:
                idx = env_idx
                break

        if idx:
            env_vars_array[idx][key] = value
        else:
            self.add_env_value(key, value)

        return True

    def exists_volume_mount(self, volume_mount):
        ''' return whether a volume mount exists '''
        exist_volume_mounts = self.get_volume_mounts() or []

        if not volume_mount:
            return volume_mount_found

        volume_mount_found = False
        for exist_volume_mount in exist_volume_mounts:
            if exist_volume_mount['name'] == volume_mount['name']:
                volume_mount_found = True
                break

        return volume_mount_found

    def exists_volume(self, volume):
        ''' return whether a volume exists '''
        exist_volumes = self.get_volumes() or []

        volume_found = False
        for exist_volume in exist_volumes:
            if exist_volume['name'] == volume['name']:
                volume_found = True
                break

        return volume_found

    def find_volume_by_name(self, volume, mounts=False):
        ''' return the index of a volume '''
        volumes = []
        if mounts:
            volumes = self.get_volume_mounts() or []
        else:
            volumes = self.get_volumes() or []
        for exist_volume in volumes:
            if exist_volume['name'] == volume['name']:
                return exist_volume

        return None

    def get_volume_mounts(self):
        '''return volume mount information '''
        return self.get_volumes(mounts=True)

    def get_volumes(self, mounts=False):
        '''return volume mount information '''
        if mounts:
            return self.get(DeploymentConfig.volume_mounts_path) or []

        return self.get(DeploymentConfig.volumes_path) or []

    def delete_volume_by_name(self, volume):
        '''delete a volume '''
        modified = False
        exist_volume_mounts = self.get_volume_mounts()
        exist_volumes = self.get_volumes()
        del_idx = None
        for idx, exist_volume in enumerate(exist_volumes):
            if exist_volume.has_key('name') and exist_volume['name'] == volume['name']:
                del_idx = idx
                break

        if del_idx != None:
            del exist_volumes[idx]
            modified = True

        del_idx = None
        for idx, exist_volume_mount in enumerate(exist_volume_mounts):
            if exist_volume_mount.has_key('name') and exist_volume_mount['name'] == volume['name']:
                del_idx = idx
                break

        if del_idx != None:
            del exist_volume_mounts[idx]
            modifed = True

        return modified

    def add_volume_mount(self, volume_mount):
        ''' add a volume or volume mount to the proper location '''
        rval = None
        exist_volume_mounts = self.get_volume_mounts()

        if not exist_volume_mounts and volume_mount:
            self.put(DeploymentConfig.volume_mounts_path, [volume_mount])
        else:
            exist_volume_mounts.append(volume_mount)

    def add_volume(self, volume):
        ''' add a volume or volume mount to the proper location '''
        rval = None
        exist_volumes = self.get_volumes()
        if not volume:
            return

        if not exist_volumes:
            self.put(DeploymentConfig.volumes_path, [volume])
        else:
            exist_volumes.append(volume)

    def update_volume(self, volume):
        '''place an env in the env var list'''
        exist_volumes = self.get_volumes() or []

        if not exist_volumes:
            return False

        if not volume:
            return False

        # update the volume
        update_idx = None
        for idx, exist_vol in enumerate(exist_volumes):
            if (exist_vol['name'] == volume['name']) and exist_vol != volume:
                update_idx = idx
                break

        if update_idx != None:
            volumes[idx] = volume
        else:
            self.add_volume(volume)

        return True

    def update_volume_mount(self, volume_mount):
        '''place an env in the env var list'''
        modified = False

        exist_volume_mounts = self.get_volume_mounts()

        if not exist_volume_mounts:
            return False

        if not volume_mount:
            return False

        # update the volume mount
        for idx, exist_vol_mount in enumerate(exist_volume_mounts):
            if exist_vol_mount['name'] == volume_mount['name']:
                if exist_vol_mount.has_key('mountPath') and \
                   str(exist_vol_mount['mountPath']) != str(volume_mount['mountPath']):
                    exist_vol_mount['mountPath'] = volume_mount['mountPath']
                    modified = True
                break

        if not modified:
            self.add_volume_mount(volume_mount)

        return True

    def needs_update_volume(self, volume, volume_mount):
        ''' verify a volume update is needed '''
        exist_volume = self.find_volume_by_name(volume)
        exist_volume_mount = self.find_volume_by_name(volume, mounts=True)
        results = []
        results.append(exist_volume['name'] == volume['name'])

        if volume.has_key('secret'):
            results.append(exist_volume.has_key('secret'))
            results.append(exist_volume['secret']['secretName'] == volume['secret']['secretName'])
            results.append(exist_volume_mount['name'] == volume_mount['name'])
            results.append(exist_volume_mount['mountPath'] == volume_mount['mountPath'])

        elif volume.has_key('emptydir'):
            results.append(exist_volume_mount['name'] == volume['name'])
            results.append(exist_volume_mount['mountPath'] == volume_mount['mountPath'])

        elif volume.has_key('persistentVolumeClaim'):
            pvc = 'persistentVolumeClaim'
            results.append(exist_volume.has_key(pvc))
            results.append(exist_volume[pvc]['claimName'] == volume[pvc]['claimName'])

            if volume[pvc].has_key('claimSize'):
                results.append(exist_volume[pvc]['claimSize'] == volume[pvc]['claimSize'])

        elif volume.has_key('hostpath'):
            results.append(exist_volume.has_key('hostPath'))
            results.append(exist_volume['hostPath']['path'] == volume_mount['mountPath'])

        return not all(results)

import time

class RegistryConfig(object):
    ''' RegistryConfig is a DTO for the registry.  '''
    def __init__(self, rname, kubeconfig, registry_options):
        self.name = rname
        self.kubeconfig = kubeconfig
        self._registry_options = registry_options

    @property
    def registry_options(self):
        ''' return registry options '''
        return self._registry_options

    def to_option_list(self):
        ''' return all options as a string'''
        return RegistryConfig.stringify(self.registry_options)

    @staticmethod
    def stringify(options):
        ''' return hash as list of key value pairs '''
        rval = []
        for key, data in options.items():
            if data['include'] and data['value']:
                rval.append('--%s=%s' % (key.replace('_', '-'), data['value']))

        return rval

class Registry(OpenShiftCLI):
    ''' Class to wrap the oc command line tools '''

    volume_mount_path = 'spec#template#spec#containers[0]volumesMounts'
    volume_path = 'spec#template#spec#volumes'
    env_path = 'spec#template#spec#containers[0]#env'

    def __init__(self,
                 registry_config,
                 verbose=False):
        ''' Constructor for OpenshiftOC

           a registry consists of 3 or more parts
           - dc/docker-registry
           - svc/docker-registry
           - endpoint/docker-registry
        '''
        super(Registry, self).__init__('default', registry_config.kubeconfig, verbose)
        self.svc_ip = None
        self.rconfig = registry_config
        self.verbose = verbose
        self.registry_parts = [{'kind': 'dc', 'name': self.rconfig.name},
                             {'kind': 'svc', 'name': self.rconfig.name},
                             #{'kind': 'endpoints', 'name': self.rconfig.name},
                            ]

        self.volume_mounts = []
        self.volumes = []
        for volume in self.rconfig.registry_options['volume_mounts']['value']:
            volume_info = {'secret_name': volume.get('secret_name', None),
                           'name':        volume.get('name', None),
                           'type':        volume.get('type', None),
                           'path':        volume.get('path', None),
                           'claimName':   volume.get('claim_name', None),
                           'claimSize':   volume.get('claim_size', None),
                          }

            vol, vol_mount = Volume.create_volume_structure(volume_info)
            self.volumes.append(vol)
            self.volume_mounts.append(vol_mount)

        self.dconfig = None
        self.svc = None

    @property
    def deploymentconfig(self):
        return self.dconfig

    @deploymentconfig.setter
    def deploymentconfig(self, config):
        self.dconfig = config

    @property
    def service(self):
        return self.svc

    @service.setter
    def service(self, config):
        self.svc = config

    def get(self):
        ''' return the self.registry_parts '''
        self.deploymentconfig = None
        self.service = None

        for part in self.registry_parts:
            result = self._get(part['kind'], rname=part['name'])
            if result['returncode'] == 0 and part['kind'] == 'dc':
                self.deploymentconfig = DeploymentConfig(result['results'][0])
            elif result['returncode'] == 0 and part['kind'] == 'svc':
                self.service = Yedit(content=result['results'][0])

        return (self.deploymentconfig, self.service)

    def exists(self):
        '''does the object exist?'''
        self.get()
        if self.deploymentconfig or self.service:
            return True

        return False

    def delete(self):
        '''return all pods '''
        parts = []
        for part in self.registry_parts:
            parts.append(self._delete(part['kind'], part['name']))

        return parts

    def prep_registry(self):
        options = self.rconfig.to_option_list()

        cmd = ['registry']
        cmd.extend(options)
        cmd.extend(['--dry-run=True', '-o', 'json'])

        results = self.openshift_cmd(cmd, oadm=True, output=True, output_type='json')
        # probably need to parse this
        if results['returncode'] != 0 and results['results'].has_key('items'):
            return results

        service = None
        deploymentconfig = None
        for obj in results['results']['items']:
            if obj['kind'] == 'DeploymentConfig':
                deploymentconfig = DeploymentConfig(obj)
            elif obj['kind'] == 'Service':
                service = obj

        # Verify we got a service and a deploymentconfig
        if not service or not deploymentconfig:
            return results

        # results will need to get parsed here and modifications added
        deploymentconfig = self.add_modifications(deploymentconfig)

        # modify service ip
        if self.svc_ip:
            service.put('spec#clusterIP', self.svc_ip)

        # need to create the service and the deploymentconfig
        service_file = Utils.create_file('service', service)
        deployment_file = Utils.create_file('deploymentconfig', deploymentconfig)

        return [service_file, deployment_file]

    def create(self):
        '''Create a deploymentconfig

           This can take some time to ensure deployment.
           TODO: WAIT??

           returns an array of results:
           result
             returncode: [0|1|?]
             stderr: some error message
             stdout: created successfully
        '''
        results = []
        files = self.prep_registry()
        if not files:
            return {'returncode': '1', 'msg': 'An error occured during registry prep'}

        for config in files:
            results.append(self._create(config))

        return results

    def update(self):
        '''run update for the registry.  This performs a delete and then create '''
        # Store the current service IP
        self.get()
        if self.deploymentconfig:
            svcip = self.deploymentconfig.get('spec#clusterIP')
            if svcip:
               self.svc_ip = svcip

        parts = self.delete()
        for part in parts:
            if part['returncode'] != 0:
                if part.has_key('stderr') and 'not found' in part['stderr']:
                    # the object is not there, continue
                    continue

                # something went wrong
                return parts

        # Ugly built in sleep here.
        #time.sleep(10)

        files = self.prep_registry()

        results = []
        files = self.prep_registry()
        for config in files:
            results.append(self._create(config))

        return results

    def add_modifications(self, deploymentconfig):
        ''' update a deployment config with changes '''
        # Currently we know that our deployment of a registry requires a few extra modifications
        # Modification 1
        # we need specific environment variables to be set
        for key, value in self.rconfig.registry_options['env_vars']['value'].items():
            if not deploymentconfig.exists_env_value(key, value):
            #if self.env_value_exists(yed.get(Registry.env_path), key, value):
                deploymentconfig.add_env_value(key, value)
                #self.env_add_value(yed.get(Registry.env_path), key, value)
            else:
                deploymentconfig.update_env_var(key, value)

        # Modification 2
        # we need specific volume variables to be set
        for volume in self.volumes:
            deploymentconfig.update_volume(volume)

        for vol_mount in self.volume_mounts:
            deploymentconfig.update_volume_mount(vol_mount)

        # Modification 3
        # Edits
        edit_results = []
        for key, value in self.rconfig.registry_options['edits']['value'].items():
            edit_results.append(deploymentconfig.put(key, value))

        if not any([res[0] for res in edit_results]):
            return None

        # Modification 4
        # Remove the default mount if we specified mounts
        if self.volumes:
            deploymentconfig.delete_volume_by_name({'name': 'registry-storage'})

        return deploymentconfig.yaml_dict

    def needs_update(self, verbose=False):
        ''' check to see if we need to update '''
        prep_svc, prep_dc = self.prep_registry()

        if not self.svc or not self.deploymentconfig:
            return True

        if not Utils.check_def_equal(prep_svc, self.service.yaml_dict):
            return True

        if not Utils.check_def_equal(prep_dc, self.deploymentconfig.yaml_dict):
            return True

        return False
#
#        user_dc = self.create(dryrun=True, output=True, output_type='raw')
#        if user_dc['returncode'] != 0:
#            return user_dc
#
        # Since the output from oadm_registry is returned as raw
        # we need to parse it.  The first line is the stats_password
        #user_dc_results = user_dc['results'].split('\n')
        ## stats_password = user_dc_results[0]

        ## Load the string back into json and get the newly created dc
        #user_dc = json.loads('\n'.join(user_dc_results[1:]))['items'][0]

        ## registry needs some exceptions.
        ## We do not want to check the autogenerated password for stats admin
        #if not self.rconfig.registry_options['stats_password']['value']:
        #    for idx, env_var in enumerate(user_dc['spec']['template']['spec']['containers'][0]['env']):
        #        if env_var['name'] == 'STATS_PASSWORD':
        #            env_var['value'] = \
        #              dc_inmem['results'][0]['spec']['template']['spec']['containers'][0]['env'][idx]['value']

        ## dry-run doesn't add the protocol to the ports section.  We will manually do that.
        #for idx, port in enumerate(user_dc['spec']['template']['spec']['containers'][0]['ports']):
        #    if not port.has_key('protocol'):
        #        port['protocol'] = 'TCP'

        ## These are different when generating
        #skip = ['dnsPolicy',
        #        'terminationGracePeriodSeconds',
        #        'restartPolicy', 'timeoutSeconds',
        #        'livenessProbe', 'readinessProbe',
        #        'terminationMessagePath',
        #        'rollingParams',
        #       ]

        #return not Utils.check_def_equal(user_dc, dc_inmem['results'][0], skip_keys=skip, debug=verbose)
'''
      --credentials='': Path to a .kubeconfig file that will contain the credentials the registry should use to contact the master.
      --dry-run=false: Check if the registry exists instead of creating.
      --images='openshift3/ose-${component}:${version}': The image to base this registry on - ${component} will be replaced with --type
      --labels='docker-registry=default': A set of labels to uniquely identify the registry and its components.
      --latest-images=false: If true, attempt to use the latest image for the registry instead of the latest release.
      --mount-host='': If set, the registry volume will be created as a host-mount at this path.
      --no-headers=false: When using the default output, don't print headers.
  -o, --output='': Output format. One of: json|yaml|wide|name|go-template=...|go-template-file=...|jsonpath=...|jsonpath-file=... See golang template [http://golang.org/pkg/text/template/#pkg-overview] and jsonpath template [http://releases.k8s.io/HEAD/docs/user-guide/jsonpath.md].
      --output-version='': Output the formatted object with the given version (default api-version).
      --ports='5000': A comma delimited list of ports or port pairs to expose on the registry pod. The default is set for 5000.
      --replicas=1: The replication factor of the registry; commonly 2 when high availability is desired.
      --selector='': Selector used to filter nodes on deployment. Used to run registries on a specific set of nodes.
      --service-account='': Name of the service account to use to run the registry pod.
  -a, --show-all=false: When printing, show all resources (default hide terminated pods.)
      --sort-by='': If non-empty, sort list types using this field specification.  The field specification is expressed as a JSONPath expression (e.g. 'ObjectMeta.Name'). The field in the API resource specified by this JSONPath expression must be an integer or a string.
  -t, --template='': Template string or path to template file to use when -o=go-template, -o=go-template-file. The template format is golang templates [http://golang.org/pkg/text/template/#pkg-overview].
      --type='docker-registry': The registry image to use - if you specify --images this flag may be ignored.
      --volume='/registry': The volume path to use for registry storage; defaults to /registry which is the default for origin-docker-registry.

Use "oadm options" for a list of global command-line options (applies to all commands).


/usr/bin/oadm registry --credentials=/etc/origin/master/openshift-registry.kubeconfig --service-account=registry --images='registry.access.redhat.com/openshift3/ose-${component}:${version}' --selector='type=infra' --replicas=0 -o yaml > /root/registry.yml

'''

def main():
    '''
    ansible oc module for registry
    '''

    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='present', type='str',
                       choices=['present', 'absent']),
            debug=dict(default=False, type='bool'),
            namespace=dict(default='default', type='str'),
            name=dict(default=None, required=True, type='str'),

            kubeconfig=dict(default='/etc/origin/master/admin.kubeconfig', type='str'),
            credentials=dict(default='/etc/origin/master/openshift-registry.kubeconfig', type='str'),
            images=dict(default=None, type='str'),
            latest_image=dict(default=False, type='bool'),
            labels=dict(default=None, type='list'),
            ports=dict(default=['5000'], type='list'),
            replicas=dict(default=1, type='int'),
            selector=dict(default=None, type='str'),
            service_account=dict(default='registry', type='str'),
            mount_host=dict(default=None, type='str'),
            registry_type=dict(default='docker-registry', type='str'),
            template=dict(default=None, type='str'),
            volume=dict(default='/registry', type='str'),
            env_vars=dict(default=None, type='dict'),
            volume_mounts=dict(default=None, type='list'),
            edits=dict(default=None, type='dict'),
        ),
        mutually_exclusive=[["registry_type", "images"]],

        supports_check_mode=True,
    )

    rconfig = RegistryConfig(module.params['name'],
                             module.params['kubeconfig'],
                             {'credentials': {'value': module.params['credentials'], 'include': True},
                              'default_cert': {'value': None, 'include': True},
                              'images': {'value': module.params['images'], 'include': True},
                              'latest_image': {'value': module.params['latest_image'], 'include': True},
                              'labels': {'value': module.params['labels'], 'include': True},
                              'ports': {'value': ','.join(module.params['ports']), 'include': True},
                              'replicas': {'value': module.params['replicas'], 'include': True},
                              'selector': {'value': module.params['selector'], 'include': True},
                              'service_account': {'value': module.params['service_account'], 'include': True},
                              'registry_type': {'value': module.params['registry_type'], 'include': False},
                              'mount_host': {'value': module.params['mount_host'], 'include': True},
                              'volume': {'value': module.params['mount_host'], 'include': True},
                              'template': {'value': module.params['template'], 'include': True},
                              'env_vars': {'value': module.params['env_vars'], 'include': False},
                              'volume_mounts': {'value': module.params['volume_mounts'], 'include': False},
                              'edits': {'value': module.params['edits'], 'include': False},
                           })


    ocregistry = Registry(rconfig)

    state = module.params['state']
    print "Exists"

    ########
    # Delete
    ########
    if state == 'absent':
        if not ocregistry.exists():
            module.exit_json(changed=False, state="absent")

        if module.check_mode:
            module.exit_json(change=False, msg='Would have performed a delete.')

        api_rval = ocregistry.delete()
        module.exit_json(changed=True, results=api_rval, state="absent")


    if state == 'present':
        ########
        # Create
        ########
        print "exists?"
        if not ocregistry.exists():

            if module.check_mode:
                module.exit_json(change=False, msg='Would have performed a create.')

            api_rval = ocregistry.create()

            if api_rval['returncode'] != 0:
                module.fail_json(msg=api_rval)

            module.exit_json(changed=True, results=api_rval, state="present")

        ########
        # Update
        ########
        if not ocregistry.needs_update():
            module.exit_json(changed=False, state="present")

        if module.check_mode:
            module.exit_json(change=False, msg='Would have performed an update.')

        print "UPDATE"
        api_rval = ocregistry.update()
        print api_rval

        if api_rval['returncode'] != 0:
            module.fail_json(msg=api_rval)

        module.exit_json(changed=True, results=api_rval, state="present")

    module.exit_json(failed=True,
                     changed=False,
                     results='Unknown state passed. %s' % state,
                     state="unknown")

# pylint: disable=redefined-builtin, unused-wildcard-import, wildcard-import, locally-disabled
# import module snippets.  This are required
from ansible.module_utils.basic import *
main()
