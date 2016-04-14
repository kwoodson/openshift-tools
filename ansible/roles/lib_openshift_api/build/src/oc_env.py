# pylint: skip-file

# pylint: disable=too-many-instance-attributes
class OCEnv(OpenShiftCLI):
    ''' Class to wrap the oc command line tools '''

    container_env_path = {"pod": "spec#containers[0]#env",
                      "dc":  "spec#template#spec#containers[0]#env",
                      "rc":  "spec#template#spec#containers[0]#env",
                     }

    # pylint allows 5. we need 6
    # pylint: disable=too-many-arguments
    def __init__(self,
                 namespace,
                 kind,
                 env_vars,
                 resource_name=None,
                 list_all=False,
                 kubeconfig='/etc/origin/master/admin.kubeconfig',
                 verbose=False):
        ''' Constructor for OpenshiftOC '''
        super(OCEnv, self).__init__(namespace, kubeconfig)
        self.kind = kind
        self.name = resource_name
        self.namespace = namespace
        self.list_all = list_all
        self.env_vars = env_vars
        self.kubeconfig = kubeconfig
        self.verbose = verbose
        self.resource = None

    # pylint: disable=no-member
    def add_value(self, key, value):
        ''' add key, value pair to env array '''
        env = self.resource.get(OCEnv.container_env_path[self.kind])
        if env:
            env.append({'name': key, 'value': value})
        else:
            self.resource.put(OCEnv.container_env_path[self.kind], {'name': key, 'value': value})

    def value_exists(self, key, value):
        ''' return whether a key, value  pair exists '''
        results = self.resource.get(OCEnv.container_env_path[self.kind]) or []
        if not results:
            return False

        for result in results:
            if result['name'] == key and result['value'] == value:
                return True

        return False

    def key_exists(self, key):
        ''' return whether a key, value  pair exists '''
        results = self.resource.get(OCEnv.container_env_path[self.kind]) or []
        if not results:
            return False

        for result in results:
            if result['name'] == key:
                return True

        return False

    def get(self):
        '''return a environment variables '''
        env = self._get(self.kind, self.name)
        if env['returncode'] == 0:
            if self.kind == 'dc' or self.kind == 'deploymentconfig':
                self.resource = DeploymentConfig(env['results'][0])
            else:
                self.resource = Yedit(content=env['results'][0])

            env['results'] = self.resource.get(OCEnv.container_env_path[self.kind]) or []
        return env

    def delete(self):
        '''return all pods '''
        modified = self.resource.delete_env_var(self.env_vars.keys())
        if modified:
            return self._replace_content(self.kind, self.name, self.resource.yaml_dict)

        return {'returncode': 0, 'changed': False}

    def put(self):
        '''place env vars into dc '''
        results = []
        for update_key, update_value in self.env_vars.items():
            if self.resource.exists_env_value(update_key, update_value):
                results.append(self.resource.update_env_var(update_key, update_value))
            else:
                results.append(self.resource.add_env_value(update_key, update_value))

        return self._replace_content(self.kind, self.name, self.resource.yaml_dict)

