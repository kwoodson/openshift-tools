# pylint: skip-file

# pylint: disable=too-many-instance-attributes
class OCVolume(OpenShiftCLI):
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
    def __init__(self,
                 kind,
                 resource_name,
                 namespace,
                 vol_name,
                 mount_path,
                 mount_type,
                 secret_name,
                 claim_size,
                 claim_name,
                 kubeconfig='/etc/origin/master/admin.kubeconfig',
                 verbose=False):
        ''' Constructor for OCVolume '''
        super(OCVolume, self).__init__(namespace, kubeconfig)
        self.kind = kind
        self.name = resource_name
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.verbose = verbose
        self.resource = None

        self.volume_info = {'secret_name': secret_name,
                            'name': vol_name,
                            'type': mount_type,
                            'path': mount_path,
                            'claimName': claim_name,
                            'claimSize': claim_size,
                           }

        self.volume, self.volume_mount = Volume.create_volume_structure(self.volume_info)

    def get(self):
        '''return volume information '''
        vol = self._get(self.kind, self.name)
        if vol['returncode'] == 0:
            if self.kind == 'dc' or self.kind == 'deploymentconfig':
                self.resource = DeploymentConfig(content=vol['results'][0])
            else:
                self.resource = Yedit(content=vol['results'][0])

            vol['results'] = self.resource.get(OCVolume.volumes_path[self.kind]) or []

        return vol

    def exists(self):
        ''' return true/false whether the volume exists'''
        return self.resource.exists_volume(self.volume)

    def delete(self):
        '''delete a volume '''
        modified = self.resource.delete_volume_by_name(self.volume, self.volume_mount)
        if modified:
            return self._replace_content(self.kind, self.volume_info['name'], self.resource.yaml_dict)

        return {'returncode': 0, 'changed': False}

    def put(self):
        '''place volume into dc '''
        exist_volume = self.resource.find_volume_by_name(self.volume)
        # update the volume
        if not exist_volume:
            self.resource.add_volume(self.volume, self.volume_mount)
        else:
            self.resource.update_volume(self.volume)
            self.resource.update_volume_mount(self.volume_mount)

        return self._replace_content(self.kind, self.name, self.resource.yaml_dict)

    def needs_update(self):
        ''' verify an update is needed '''
        return self.resource.needs_update_volume(self.volume, self.volume_mount)
