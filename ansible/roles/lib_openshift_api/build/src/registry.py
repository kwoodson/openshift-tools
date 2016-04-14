# pylint: skip-file

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
