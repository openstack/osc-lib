#   Copyright 2012-2013 OpenStack Foundation
#
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

import copy
import json as jsonutils
from unittest import mock

from keystoneauth1.access import service_catalog
from keystoneauth1 import exceptions as ksa_exceptions
from keystoneauth1 import fixture as ksa_fixture
from keystoneauth1.identity import generic as generic_plugin
from keystoneauth1.identity.v3 import k2k
from keystoneauth1 import loading
from keystoneauth1 import noauth
from keystoneauth1 import token_endpoint
from openstack.config import cloud_config
from openstack.config import cloud_region
from openstack.config import defaults
from openstack import connection
from requests_mock.contrib import fixture as requests_mock_fixture

from osc_lib.api import auth
from osc_lib import clientmanager
from osc_lib import exceptions as exc
from osc_lib.test import base
from osc_lib.test import fakes

SERVICE_PROVIDER_ID = "bob"

TEST_RESPONSE_DICT = ksa_fixture.V2Token(
    token_id=fakes.TOKEN, user_name=fakes.USERNAME
)
_s = TEST_RESPONSE_DICT.add_service('identity', name='keystone')
_s.add_endpoint(fakes.AUTH_URL + ':5000/v2.0')
_s = TEST_RESPONSE_DICT.add_service('network', name='neutron')
_s.add_endpoint(fakes.AUTH_URL + ':9696')
_s = TEST_RESPONSE_DICT.add_service('compute', name='nova')
_s.add_endpoint(fakes.AUTH_URL + ':8774/v2')
_s = TEST_RESPONSE_DICT.add_service('image', name='glance')
_s.add_endpoint(fakes.AUTH_URL + ':9292')
_s = TEST_RESPONSE_DICT.add_service('object', name='swift')
_s.add_endpoint(fakes.AUTH_URL + ':8080/v1')

TEST_RESPONSE_DICT_V3 = ksa_fixture.V3Token(user_name=fakes.USERNAME)
TEST_RESPONSE_DICT_V3.set_project_scope()

TEST_VERSIONS = ksa_fixture.DiscoveryList(href=fakes.AUTH_URL)

AUTH_REF = {'version': 'v2.0'}
AUTH_REF.update(TEST_RESPONSE_DICT['access'])
SERVICE_CATALOG = service_catalog.ServiceCatalogV2(AUTH_REF)

AUTH_DICT = {
    'auth_url': fakes.AUTH_URL,
    'username': fakes.USERNAME,
    'password': fakes.PASSWORD,
    'project_name': fakes.PROJECT_NAME,
}


# This is deferred in api.auth but we need it here...
auth.get_options_list()


class Container:
    attr = clientmanager.ClientCache(lambda x: object())
    buggy_attr = clientmanager.ClientCache(lambda x: x.foo)

    def __init__(self):
        pass


class TestClientCache(base.TestCase):
    def test_singleton(self):
        # NOTE(dtroyer): Verify that the ClientCache descriptor only invokes
        # the factory one time and always returns the same value after that.
        c = Container()
        self.assertEqual(c.attr, c.attr)

    def test_attribute_error_propagates(self):
        c = Container()
        err = self.assertRaises(
            exc.PluginAttributeError, getattr, c, 'buggy_attr'
        )
        self.assertNotIsInstance(err, AttributeError)
        self.assertEqual("'Container' object has no attribute 'foo'", str(err))


class BaseTestClientManager(base.TestCase):
    """ClientManager class test framework"""

    default_password_auth = {
        'auth_url': fakes.AUTH_URL,
        'username': fakes.USERNAME,
        'password': fakes.PASSWORD,
        'project_name': fakes.PROJECT_NAME,
    }
    default_token_auth = {
        'auth_url': fakes.AUTH_URL,
        'token': fakes.TOKEN,
    }

    def setUp(self):
        super().setUp()
        self.mock = mock.Mock()
        self.requests = self.useFixture(requests_mock_fixture.Fixture())
        # fake v2password token retrieval
        self.stub_auth(json=TEST_RESPONSE_DICT)
        # fake token and token_endpoint retrieval
        self.stub_auth(
            json=TEST_RESPONSE_DICT,
            url='/'.join([fakes.AUTH_URL, 'v2.0/tokens']),
        )
        # fake v3password token retrieval
        self.stub_auth(
            json=TEST_RESPONSE_DICT_V3,
            url='/'.join([fakes.AUTH_URL, 'v3/auth/tokens']),
        )
        # fake password token retrieval
        self.stub_auth(
            json=TEST_RESPONSE_DICT_V3,
            url='/'.join([fakes.AUTH_URL, 'auth/tokens']),
        )
        # fake password version endpoint discovery
        self.stub_auth(json=TEST_VERSIONS, url=fakes.AUTH_URL, verb='GET')

        # Mock the auth plugin
        self.auth_mock = mock.Mock()

    def stub_auth(self, json=None, url=None, verb=None, **kwargs):
        subject_token = fakes.TOKEN
        base_url = fakes.AUTH_URL
        if json:
            text = jsonutils.dumps(json)
            headers = {
                'X-Subject-Token': subject_token,
                'Content-Type': 'application/json',
            }
        if not url:
            url = '/'.join([base_url, 'tokens'])
        url = url.replace("/?", "?")
        if not verb:
            verb = 'POST'
        self.requests.register_uri(
            verb,
            url,
            headers=headers,
            text=text,
        )

    def _clientmanager_class(self):
        """Allow subclasses to override the ClientManager class"""
        return clientmanager.ClientManager

    def _make_clientmanager(
        self,
        auth_args=None,
        config_args=None,
        identity_api_version=None,
        auth_plugin_name=None,
        auth_required=None,
    ):
        if identity_api_version is None:
            identity_api_version = '2.0'
        if auth_plugin_name is None:
            auth_plugin_name = 'password'

        if auth_plugin_name.endswith('password'):
            auth_dict = copy.deepcopy(self.default_password_auth)
        elif auth_plugin_name.endswith('token'):
            auth_dict = copy.deepcopy(self.default_token_auth)
        else:
            auth_dict = {}

        if auth_args is not None:
            auth_dict = auth_args

        cli_options = defaults.get_defaults()
        cli_options.update(
            {
                'auth_type': auth_plugin_name,
                'auth': auth_dict,
                'interface': fakes.INTERFACE,
                'region_name': fakes.REGION_NAME,
            }
        )
        if config_args is not None:
            cli_options.update(config_args)

        loader = loading.get_plugin_loader(auth_plugin_name)
        auth_plugin = loader.load_from_options(**auth_dict)
        client_manager = self._clientmanager_class()(
            cli_options=cloud_region.CloudRegion(
                name='t1',
                region_name='1',
                config=cli_options,
                auth_plugin=auth_plugin,
            ),
            api_version={
                'identity': identity_api_version,
            },
        )
        client_manager._auth_required = auth_required is True
        client_manager.setup_auth()
        client_manager.auth_ref

        self.assertEqual(
            auth_plugin_name,
            client_manager.auth_plugin_name,
        )
        return client_manager


class TestClientManager(BaseTestClientManager):
    def test_client_manager_none(self):
        none_auth = {
            'endpoint': fakes.AUTH_URL,
        }
        client_manager = self._make_clientmanager(
            auth_args=none_auth,
            auth_plugin_name='none',
        )

        self.assertEqual(
            fakes.AUTH_URL,
            client_manager._cli_options.config['auth']['endpoint'],
        )
        self.assertIsInstance(
            client_manager.auth,
            noauth.NoAuth,
        )
        # Check that the endpoint option works as the override
        self.assertEqual(
            fakes.AUTH_URL,
            client_manager.get_endpoint_for_service_type('baremetal'),
        )

    def test_client_manager_admin_token(self):
        token_auth = {
            'endpoint': fakes.AUTH_URL,
            'token': fakes.TOKEN,
        }
        client_manager = self._make_clientmanager(
            auth_args=token_auth,
            auth_plugin_name='admin_token',
        )

        self.assertEqual(
            fakes.AUTH_URL,
            client_manager._cli_options.config['auth']['endpoint'],
        )
        self.assertEqual(
            fakes.TOKEN,
            client_manager.auth.get_token(None),
        )
        self.assertIsInstance(
            client_manager.auth,
            token_endpoint.Token,
        )
        # NOTE(dtroyer): This is intentionally not assertFalse() as the return
        #                value from is_service_available() may be == None
        self.assertNotEqual(
            False,
            client_manager.is_service_available('network'),
        )

    def test_client_manager_password(self):
        client_manager = self._make_clientmanager(
            auth_required=True,
        )

        self.assertEqual(
            fakes.AUTH_URL,
            client_manager._cli_options.config['auth']['auth_url'],
        )
        self.assertEqual(
            fakes.USERNAME,
            client_manager._cli_options.config['auth']['username'],
        )
        self.assertEqual(
            fakes.PASSWORD,
            client_manager._cli_options.config['auth']['password'],
        )
        self.assertIsInstance(
            client_manager.auth,
            generic_plugin.Password,
        )
        self.assertTrue(client_manager.verify)
        self.assertIsNone(client_manager.cert)

        # These need to stick around until the old-style clients are gone
        self.assertEqual(
            AUTH_REF.pop('version'),
            client_manager.auth_ref.version,
        )
        self.assertEqual(
            AUTH_REF,
            client_manager.auth_ref._data['access'],
        )
        self.assertEqual(
            dir(SERVICE_CATALOG),
            dir(client_manager.auth_ref.service_catalog),
        )
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify(self):
        client_manager = self._make_clientmanager(
            auth_required=True,
        )

        self.assertTrue(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_ca(self):
        config_args = {
            'cacert': 'cafile',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        # Test that client_manager.verify is Requests-compatible,
        # i.e. it contains the value of cafile here
        self.assertTrue(client_manager.verify)
        self.assertEqual('cafile', client_manager.verify)
        self.assertEqual('cafile', client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_false(self):
        config_args = {
            'verify': False,
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        self.assertFalse(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_insecure(self):
        config_args = {
            'insecure': True,
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        self.assertFalse(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_insecure_ca(self):
        config_args = {
            'insecure': True,
            'cacert': 'cafile',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        # insecure overrides cacert
        self.assertFalse(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_client_cert(self):
        config_args = {
            'cert': 'cert',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
        )

        self.assertEqual('cert', client_manager.cert)

    def test_client_manager_password_client_key(self):
        config_args = {
            'cert': 'cert',
            'key': 'key',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
        )

        self.assertEqual(('cert', 'key'), client_manager.cert)

    def test_client_manager_select_auth_plugin_password(self):
        # test password auth
        auth_args = {
            'auth_url': fakes.AUTH_URL,
            'username': fakes.USERNAME,
            'password': fakes.PASSWORD,
            'tenant_name': fakes.PROJECT_NAME,
        }
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='2.0',
            auth_plugin_name='v2password',
        )

        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.update(
            {
                'user_domain_name': 'default',
                'project_domain_name': 'default',
            }
        )
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
            auth_plugin_name='v3password',
        )

        # Use v2.0 auth args
        auth_args = {
            'auth_url': fakes.AUTH_URL,
            'username': fakes.USERNAME,
            'password': fakes.PASSWORD,
            'tenant_name': fakes.PROJECT_NAME,
        }
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='2.0',
        )

        # Use v3 auth args
        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.update(
            {
                'user_domain_name': 'default',
                'project_domain_name': 'default',
            }
        )
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
        )

        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.pop('username')
        auth_args.update({'user_id': fakes.USER_ID})
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
        )

    def test_client_manager_select_auth_plugin_token(self):
        # test token auth
        self._make_clientmanager(
            # auth_args=auth_args,
            identity_api_version='2.0',
            auth_plugin_name='v2token',
        )
        self._make_clientmanager(
            # auth_args=auth_args,
            identity_api_version='3',
            auth_plugin_name='v3token',
        )
        self._make_clientmanager(
            # auth_args=auth_args,
            identity_api_version='x',
            auth_plugin_name='token',
        )

    def test_client_manager_select_auth_plugin_failure(self):
        self.assertRaises(
            ksa_exceptions.NoMatchingPlugin,
            self._make_clientmanager,
            identity_api_version='3',
            auth_plugin_name='bad_plugin',
        )

    @mock.patch('osc_lib.api.auth.check_valid_authentication_options')
    def test_client_manager_auth_setup_once(self, check_authn_options_func):
        loader = loading.get_plugin_loader('password')
        auth_plugin = loader.load_from_options(**AUTH_DICT)
        cli_options = defaults.get_defaults()
        cli_options.update(
            {
                'auth_type': 'password',
                'auth': AUTH_DICT,
                'interface': fakes.INTERFACE,
                'region_name': fakes.REGION_NAME,
            }
        )
        client_manager = self._clientmanager_class()(
            cli_options=cloud_config.CloudConfig(
                name='t1',
                region='1',
                config=cli_options,
                auth_plugin=auth_plugin,
            ),
            api_version={
                'identity': '2.0',
            },
        )
        self.assertFalse(client_manager._auth_setup_completed)
        client_manager.setup_auth()
        self.assertTrue(check_authn_options_func.called)
        self.assertTrue(client_manager._auth_setup_completed)

        # now make sure we don't do auth setup the second time around
        # by checking whether check_valid_auth_options() gets called again
        check_authn_options_func.reset_mock()
        client_manager.auth_ref
        check_authn_options_func.assert_not_called()

    def test_client_manager_endpoint_disabled(self):
        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.update(
            {
                'user_domain_name': 'default',
                'project_domain_name': 'default',
            }
        )
        # v3 fake doesn't have network endpoint
        client_manager = self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
            auth_plugin_name='v3password',
        )

        self.assertFalse(client_manager.is_service_available('network'))

    def test_client_manager_k2k_auth_setup(self):
        loader = loading.get_plugin_loader('password')
        auth_plugin = loader.load_from_options(**AUTH_DICT)
        cli_options = defaults.get_defaults()
        cli_options.update(
            {
                'auth_type': 'password',
                'auth': AUTH_DICT,
                'interface': fakes.INTERFACE,
                'region_name': fakes.REGION_NAME,
                'service_provider': SERVICE_PROVIDER_ID,
                'remote_project_id': fakes.PROJECT_ID,
            }
        )
        client_manager = self._clientmanager_class()(
            cli_options=cloud_config.CloudConfig(
                name='t1',
                region='1',
                config=cli_options,
                auth_plugin=auth_plugin,
            ),
            api_version={
                'identity': '3',
            },
        )

        self.assertFalse(client_manager._auth_setup_completed)
        client_manager.setup_auth()
        # Note(knikolla): Make sure that the auth object is of the correct
        # type and that the service_provider is correctly set.
        self.assertIsInstance(client_manager.auth, k2k.Keystone2Keystone)
        self.assertEqual(client_manager.auth._sp_id, SERVICE_PROVIDER_ID)
        self.assertEqual(client_manager.auth.project_id, fakes.PROJECT_ID)
        self.assertTrue(client_manager._auth_setup_completed)

    def test_client_manager_none_auth(self):
        # test token auth
        client_manager = self._make_clientmanager(
            auth_args={},
            auth_plugin_name='none',
        )
        self.assertIsNone(
            client_manager.get_endpoint_for_service_type('compute')
        )

    def test_client_manager_endpoint_override(self):
        # test token auth
        client_manager = self._make_clientmanager(
            auth_args={},
            config_args={
                'compute_endpoint_override': 'http://example.com',
                'foo_bar_endpoint_override': 'http://example2.com',
            },
            auth_plugin_name='none',
        )
        self.assertEqual(
            'http://example.com',
            client_manager.get_endpoint_for_service_type('compute'),
        )
        self.assertEqual(
            'http://example2.com',
            client_manager.get_endpoint_for_service_type('foo-bar'),
        )
        self.assertTrue(client_manager.is_service_available('compute'))

    def test_client_manager_connection(self):
        client_manager = self._make_clientmanager(
            auth_required=True,
        )

        self.assertIsInstance(
            client_manager.sdk_connection,
            connection.Connection,
        )
