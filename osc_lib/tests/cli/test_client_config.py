#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

from osc_lib.cli import client_config
from osc_lib.tests import utils


class TestOSCConfig(utils.TestCase):

    def setUp(self):
        super(TestOSCConfig, self).setUp()

        self.cloud = client_config.OSC_Config()

    def test_auth_select_default_plugin(self):
        config = {
            'auth_type': 'admin_token',
        }
        ret_config = self.cloud._auth_select_default_plugin(config)
        self.assertEqual('admin_token', ret_config['auth_type'])

    def test_auth_select_default_plugin_password(self):
        config = {
            'username': 'fred',
        }
        ret_config = self.cloud._auth_select_default_plugin(config)
        self.assertEqual('password', ret_config['auth_type'])
        self.assertEqual('fred', ret_config['username'])

    def test_auth_select_default_plugin_password_v2(self):
        config = {
            'identity_api_version': '2',
            'username': 'fred',
        }
        ret_config = self.cloud._auth_select_default_plugin(config)
        self.assertEqual('v2password', ret_config['auth_type'])
        self.assertEqual('fred', ret_config['username'])

    def test_auth_select_default_plugin_password_v3(self):
        config = {
            'identity_api_version': '3',
            'username': 'fred',
        }
        ret_config = self.cloud._auth_select_default_plugin(config)
        self.assertEqual('v3password', ret_config['auth_type'])
        self.assertEqual('fred', ret_config['username'])

    def test_auth_select_default_plugin_token(self):
        config = {
            'token': 'subway',
        }
        ret_config = self.cloud._auth_select_default_plugin(config)
        self.assertEqual('token', ret_config['auth_type'])
        self.assertEqual('subway', ret_config['token'])

    def test_auth_select_default_plugin_token_v2(self):
        config = {
            'identity_api_version': '2.2',
            'token': 'subway',
        }
        ret_config = self.cloud._auth_select_default_plugin(config)
        self.assertEqual('v2token', ret_config['auth_type'])
        self.assertEqual('subway', ret_config['token'])

    def test_auth_select_default_plugin_token_v3(self):
        config = {
            'identity_api_version': '3',
            'token': 'subway',
        }
        ret_config = self.cloud._auth_select_default_plugin(config)
        self.assertEqual('v3token', ret_config['auth_type'])
        self.assertEqual('subway', ret_config['token'])

    def test_auth_v2_arguments(self):
        config = {
            'identity_api_version': '2',
            'auth_type': 'v2password',
            'username': 'fred',
        }
        ret_config = self.cloud._auth_v2_arguments(config)
        self.assertEqual('fred', ret_config['username'])
        self.assertFalse('tenant_id' in ret_config)
        self.assertFalse('tenant_name' in ret_config)

        config = {
            'identity_api_version': '3',
            'auth_type': 'v3password',
            'username': 'fred',
            'project_id': 'id',
        }
        ret_config = self.cloud._auth_v2_arguments(config)
        self.assertEqual('fred', ret_config['username'])
        self.assertFalse('tenant_id' in ret_config)
        self.assertFalse('tenant_name' in ret_config)

        config = {
            'identity_api_version': '2',
            'auth_type': 'v2password',
            'username': 'fred',
            'project_id': 'id',
        }
        ret_config = self.cloud._auth_v2_arguments(config)
        self.assertEqual('id', ret_config['tenant_id'])
        self.assertFalse('tenant_name' in ret_config)

        config = {
            'identity_api_version': '2',
            'auth_type': 'v2password',
            'username': 'fred',
            'project_name': 'name',
        }
        ret_config = self.cloud._auth_v2_arguments(config)
        self.assertFalse('tenant_id' in ret_config)
        self.assertEqual('name', ret_config['tenant_name'])

    def test_auth_v2_ignore_v3(self):
        config = {
            'identity_api_version': '2',
            'auth_type': 'v2password',
            'username': 'fred',
            'project_id': 'id',
            'project_domain_id': 'bad',
        }
        ret_config = self.cloud._auth_v2_ignore_v3(config)
        self.assertEqual('fred', ret_config['username'])
        self.assertFalse('project_domain_id' in ret_config)

    def test_auth_config_hook_default_domain(self):
        config = {
            'identity_api_version': '3',
            'auth_type': 'admin_token',
            'default_domain': 'default',
            'username': 'fred',
            'project_id': 'id',
            'project_domain_id': None,
        }
        ret_config = self.cloud.auth_config_hook(config)
        self.assertEqual('admin_token', ret_config['auth_type'])
        self.assertEqual('default', ret_config['default_domain'])
        self.assertEqual('fred', ret_config['username'])
        self.assertEqual('default', ret_config['project_domain_id'])

    def test_auth_config_hook_default(self):
        config = {}
        ret_config = self.cloud.auth_config_hook(config)
        self.assertEqual('password', ret_config['auth_type'])
