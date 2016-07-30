# pylint: skip-file

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

    @staticmethod
    def get_gui_access(access):
        ''' Return the gui_access for a usergroup
        '''
        access = access.lower()
        if access == 'internal':
            return 1
        elif access == 'disabled':
            return 2

        return 0

    @staticmethod
    def get_debug_mode(mode):
        ''' Return the debug_mode for a usergroup
        '''
        mode = mode.lower()
        if mode == 'enabled':
            return 1

        return 0

    @staticmethod
    def get_user_status(status):
        ''' Return the user_status for a usergroup
        '''
        status = status.lower()
        if status == 'enabled':
            return 0

        return 1

    @staticmethod
    def get_priority(priority):
        ''' determine priority
        '''
        prior = 0
        if 'info' in priority:
            prior = 1
        elif 'warn' in priority:
            prior = 2
        elif 'avg' == priority or 'ave' in priority:
            prior = 3
        elif 'high' in priority:
            prior = 4
        elif 'dis' in priority:
            prior = 5

        return prior
