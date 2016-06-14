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
#

import copy
import fixtures
import mock
import os
import testtools

from osc_lib import shell
from osc_lib.tests import utils


DEFAULT_AUTH_URL = "http://127.0.0.1:5000/v2.0/"
DEFAULT_PROJECT_ID = "xxxx-yyyy-zzzz"
DEFAULT_PROJECT_NAME = "project"
DEFAULT_DOMAIN_ID = "aaaa-bbbb-cccc"
DEFAULT_DOMAIN_NAME = "default"
DEFAULT_USER_DOMAIN_ID = "aaaa-bbbb-cccc"
DEFAULT_USER_DOMAIN_NAME = "domain"
DEFAULT_PROJECT_DOMAIN_ID = "aaaa-bbbb-cccc"
DEFAULT_PROJECT_DOMAIN_NAME = "domain"
DEFAULT_USERNAME = "username"
DEFAULT_PASSWORD = "password"

DEFAULT_CLOUD = "altocumulus"
DEFAULT_REGION_NAME = "ZZ9_Plural_Z_Alpha"
DEFAULT_TOKEN = "token"
DEFAULT_SERVICE_URL = "http://127.0.0.1:8771/v3.0/"
DEFAULT_AUTH_PLUGIN = "v2password"
DEFAULT_INTERFACE = "internal"

DEFAULT_COMPUTE_API_VERSION = ""
DEFAULT_IDENTITY_API_VERSION = ""
DEFAULT_IMAGE_API_VERSION = ""
DEFAULT_VOLUME_API_VERSION = ""
DEFAULT_NETWORK_API_VERSION = ""

LIB_COMPUTE_API_VERSION = ""
LIB_IDENTITY_API_VERSION = ""
LIB_IMAGE_API_VERSION = ""
LIB_VOLUME_API_VERSION = ""
LIB_NETWORK_API_VERSION = ""

CLOUD_1 = {
    'clouds': {
        'scc': {
            'auth': {
                'auth_url': DEFAULT_AUTH_URL,
                'project_name': DEFAULT_PROJECT_NAME,
                'username': 'zaphod',
            },
            'region_name': 'occ-cloud,krikkit',
            'donut': 'glazed',
            'interface': 'public',
        }
    }
}

CLOUD_2 = {
    'clouds': {
        'megacloud': {
            'cloud': 'megadodo',
            'auth': {
                'project_name': 'heart-o-gold',
                'username': 'zaphod',
            },
            'region_name': 'occ-cloud,krikkit,occ-env',
            'log_file': '/tmp/test_log_file',
            'log_level': 'debug',
            'cert': 'mycert',
            'key': 'mickey',
        }
    }
}

PUBLIC_1 = {
    'public-clouds': {
        'megadodo': {
            'auth': {
                'auth_url': DEFAULT_AUTH_URL,
                'project_name': DEFAULT_PROJECT_NAME,
            },
            'region_name': 'occ-public',
            'donut': 'cake',
        }
    }
}


# The option table values is a tuple of (<value>, <test-opt>, <test-env>)
# where <value> is the test value to use, <test-opt> is True if this option
# should be tested as a CLI option and <test-env> is True of this option
# should be tested as an environment variable.

# Global options that should be parsed before shell.initialize_app() is called
global_options = {
    '--os-cloud': (DEFAULT_CLOUD, True, True),
    '--os-region-name': (DEFAULT_REGION_NAME, True, True),
    '--os-default-domain': (DEFAULT_DOMAIN_NAME, True, True),
    '--os-cacert': ('/dev/null', True, True),
    '--timing': (True, True, False),
    '--os-profile': ('SECRET_KEY', True, False),
    '--os-interface': (DEFAULT_INTERFACE, True, True)
}


def opt2attr(opt):
    if opt.startswith('--os-'):
        attr = opt[5:]
    elif opt.startswith('--'):
        attr = opt[2:]
    else:
        attr = opt
    return attr.lower().replace('-', '_')


def opt2env(opt):
    return opt[2:].upper().replace('-', '_')


def make_shell():
    """Create a new command shell and mock out some bits."""
    _shell = shell.OpenStackShell()
    _shell.command_manager = mock.Mock()
    _shell.cloud = mock.Mock()

    return _shell


def fake_execute(shell, cmd):
    """Pretend to execute shell commands."""
    return shell.run(cmd.split())


class EnvFixture(fixtures.Fixture):
    """Environment Fixture.

    This fixture replaces os.environ with provided env or an empty env.
    """

    def __init__(self, env=None):
        self.new_env = env or {}

    def _setUp(self):
        self.orig_env, os.environ = os.environ, self.new_env
        self.addCleanup(self.revert)

    def revert(self):
        os.environ = self.orig_env


class TestShell(utils.TestCase):

    def setUp(self):
        super(TestShell, self).setUp()
        patch = "osc_lib.shell.OpenStackShell.run_subcommand"
        self.cmd_patch = mock.patch(patch)
        self.cmd_save = self.cmd_patch.start()
        self.addCleanup(self.cmd_patch.stop)
        self.app = mock.Mock("Test Shell")


class TestShellHelp(TestShell):
    """Test the deferred help flag"""

    def setUp(self):
        super(TestShellHelp, self).setUp()
        self.useFixture(EnvFixture())

    @testtools.skip("skip until bug 1444983 is resolved")
    def test_help_options(self):
        flag = "-h list server"
        kwargs = {
            "deferred_help": True,
        }
        with mock.patch(
                "osc_lib.shell.OpenStackShell.initialize_app",
                self.app,
        ):
            _shell, _cmd = make_shell(), flag
            fake_execute(_shell, _cmd)

            self.assertEqual(
                kwargs["deferred_help"],
                _shell.options.deferred_help,
            )


class TestShellOptions(TestShell):
    """Test the option handling by argparse and os_client_config

    This covers getting the CLI options through the initial processing
    and validates the arguments to initialize_app() and occ_get_one()
    """

    def setUp(self):
        super(TestShellOptions, self).setUp()
        self.useFixture(EnvFixture())

    def _assert_initialize_app_arg(self, cmd_options, default_args):
        """Check the args passed to initialize_app()

        The argv argument to initialize_app() is the remainder from parsing
        global options declared in both cliff.app and
        osc_lib.OpenStackShell build_option_parser().  Any global
        options passed on the command line should not be in argv but in
        _shell.options.
        """

        with mock.patch(
                "osc_lib.shell.OpenStackShell.initialize_app",
                self.app,
        ):
            _shell, _cmd = make_shell(), cmd_options + " module list"
            fake_execute(_shell, _cmd)

            self.app.assert_called_with(["module", "list"])
            for k in default_args.keys():
                self.assertEqual(
                    default_args[k],
                    vars(_shell.options)[k],
                    "%s does not match" % k,
                )

    def _assert_cloud_config_arg(self, cmd_options, default_args):
        """Check the args passed to cloud_config.get_one_cloud()

        The argparse argument to get_one_cloud() is an argparse.Namespace
        object that contains all of the options processed to this point in
        initialize_app().
        """

        cloud = mock.Mock(name="cloudy")
        cloud.config = {}
        self.occ_get_one = mock.Mock(return_value=cloud)
        with mock.patch(
                "os_client_config.config.OpenStackConfig.get_one_cloud",
                self.occ_get_one,
        ):
            _shell, _cmd = make_shell(), cmd_options + " module list"
            fake_execute(_shell, _cmd)

            self.app.assert_called_with(["module", "list"])
            opts = self.occ_get_one.call_args[1]['argparse']
            for k in default_args.keys():
                self.assertEqual(
                    default_args[k],
                    vars(opts)[k],
                    "%s does not match" % k,
                )

    def _test_options_init_app(self, test_opts):
        """Test options on the command line"""
        for opt in test_opts.keys():
            if not test_opts[opt][1]:
                continue
            key = opt2attr(opt)
            if isinstance(test_opts[opt][0], str):
                cmd = opt + " " + test_opts[opt][0]
            else:
                cmd = opt
            kwargs = {
                key: test_opts[opt][0],
            }
            self._assert_initialize_app_arg(cmd, kwargs)

    def _test_env_init_app(self, test_opts):
        """Test options in the environment"""
        for opt in test_opts.keys():
            if not test_opts[opt][2]:
                continue
            key = opt2attr(opt)
            kwargs = {
                key: test_opts[opt][0],
            }
            env = {
                opt2env(opt): test_opts[opt][0],
            }
            os.environ = env.copy()
            self._assert_initialize_app_arg("", kwargs)

    def _test_options_get_one_cloud(self, test_opts):
        """Test options sent "to os_client_config"""
        for opt in test_opts.keys():
            if not test_opts[opt][1]:
                continue
            key = opt2attr(opt)
            if isinstance(test_opts[opt][0], str):
                cmd = opt + " " + test_opts[opt][0]
            else:
                cmd = opt
            kwargs = {
                key: test_opts[opt][0],
            }
            self._assert_cloud_config_arg(cmd, kwargs)

    def _test_env_get_one_cloud(self, test_opts):
        """Test environment options sent "to os_client_config"""
        for opt in test_opts.keys():
            if not test_opts[opt][2]:
                continue
            key = opt2attr(opt)
            kwargs = {
                key: test_opts[opt][0],
            }
            env = {
                opt2env(opt): test_opts[opt][0],
            }
            os.environ = env.copy()
            self._assert_cloud_config_arg("", kwargs)

    def test_no_options(self):
        os.environ = {}
        self._assert_initialize_app_arg("", {})
        self._assert_cloud_config_arg("", {})

    def test_global_options(self):
        self._test_options_init_app(global_options)
        self._test_options_get_one_cloud(global_options)

    def test_global_env(self):
        self._test_env_init_app(global_options)
        self._test_env_get_one_cloud(global_options)


class TestShellCli(TestShell):
    """Test handling of specific global options

    _shell.options is the parsed command line from argparse
    _shell.client_manager.* are the values actually used

    """

    def setUp(self):
        super(TestShellCli, self).setUp()
        env = {}
        self.useFixture(EnvFixture(env.copy()))

    def test_shell_args_tls_options(self):
        """Test the TLS verify and CA cert file options"""
        _shell = make_shell()

        # Default
        fake_execute(_shell, "module list")
        self.assertIsNone(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertIsNone(_shell.options.cacert)
        self.assertTrue(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

        # --verify
        fake_execute(_shell, "--verify module list")
        self.assertTrue(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertIsNone(_shell.options.cacert)
        self.assertTrue(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

        # --insecure
        fake_execute(_shell, "--insecure module list")
        self.assertIsNone(_shell.options.verify)
        self.assertTrue(_shell.options.insecure)
        self.assertIsNone(_shell.options.cacert)
        self.assertFalse(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

        # --os-cacert
        fake_execute(_shell, "--os-cacert foo module list")
        self.assertIsNone(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertEqual('foo', _shell.options.cacert)
        self.assertEqual('foo', _shell.client_manager.verify)
        self.assertEqual('foo', _shell.client_manager.cacert)

        # --os-cacert and --verify
        fake_execute(_shell, "--os-cacert foo --verify module list")
        self.assertTrue(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertEqual('foo', _shell.options.cacert)
        self.assertEqual('foo', _shell.client_manager.verify)
        self.assertEqual('foo', _shell.client_manager.cacert)

        # --os-cacert and --insecure
        # NOTE(dtroyer): Per bug https://bugs.launchpad.net/bugs/1447784
        #                in this combination --insecure now overrides any
        #                --os-cacert setting, where before --insecure
        #                was ignored if --os-cacert was set.
        fake_execute(_shell, "--os-cacert foo --insecure module list")
        self.assertIsNone(_shell.options.verify)
        self.assertTrue(_shell.options.insecure)
        self.assertEqual('foo', _shell.options.cacert)
        self.assertFalse(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

    def test_shell_args_cert_options(self):
        """Test client cert options"""
        _shell = make_shell()

        # Default
        fake_execute(_shell, "module list")
        self.assertEqual('', _shell.options.cert)
        self.assertEqual('', _shell.options.key)
        self.assertIsNone(_shell.client_manager.cert)

        # --os-cert
        fake_execute(_shell, "--os-cert mycert module list")
        self.assertEqual('mycert', _shell.options.cert)
        self.assertEqual('', _shell.options.key)
        self.assertEqual('mycert', _shell.client_manager.cert)

        # --os-key
        fake_execute(_shell, "--os-key mickey module list")
        self.assertEqual('', _shell.options.cert)
        self.assertEqual('mickey', _shell.options.key)
        self.assertIsNone(_shell.client_manager.cert)

        # --os-cert and --os-key
        fake_execute(_shell, "--os-cert mycert --os-key mickey module list")
        self.assertEqual('mycert', _shell.options.cert)
        self.assertEqual('mickey', _shell.options.key)
        self.assertEqual(('mycert', 'mickey'), _shell.client_manager.cert)

    @mock.patch("os_client_config.config.OpenStackConfig._load_config_file")
    def test_shell_args_cloud_no_vendor(self, config_mock):
        """Test cloud config options without the vendor file"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_1))
        _shell = make_shell()

        fake_execute(
            _shell,
            "--os-cloud scc module list",
        )
        self.assertEqual(
            'scc',
            _shell.cloud.name,
        )

        # These come from clouds.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            DEFAULT_PROJECT_NAME,
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.client_manager.region_name,
        )
        self.assertEqual(
            'glazed',
            _shell.cloud.config['donut'],
        )
        self.assertEqual(
            'public',
            _shell.cloud.config['interface'],
        )

        self.assertIsNone(_shell.cloud.config['cert'])
        self.assertIsNone(_shell.cloud.config['key'])
        self.assertIsNone(_shell.client_manager.cert)

    @mock.patch("os_client_config.config.OpenStackConfig._load_vendor_file")
    @mock.patch("os_client_config.config.OpenStackConfig._load_config_file")
    def test_shell_args_cloud_public(self, config_mock, public_mock):
        """Test cloud config options with the vendor file"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        public_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = make_shell()

        fake_execute(
            _shell,
            "--os-cloud megacloud module list",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.client_manager.region_name,
        )

        self.assertEqual('mycert', _shell.cloud.config['cert'])
        self.assertEqual('mickey', _shell.cloud.config['key'])
        self.assertEqual(('mycert', 'mickey'), _shell.client_manager.cert)

    @mock.patch("os_client_config.config.OpenStackConfig._load_vendor_file")
    @mock.patch("os_client_config.config.OpenStackConfig._load_config_file")
    def test_shell_args_precedence(self, config_mock, vendor_mock):
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = make_shell()

        # Test command option overriding config file value
        fake_execute(
            _shell,
            "--os-cloud megacloud --os-region-name krikkit module list",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )
        self.assertEqual(
            'krikkit',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'krikkit',
            _shell.client_manager.region_name,
        )


class TestShellCliPrecedence(TestShell):
    """Test option precedencr order"""

    def setUp(self):
        super(TestShellCliPrecedence, self).setUp()
        env = {
            'OS_CLOUD': 'megacloud',
            'OS_REGION_NAME': 'occ-env',
        }
        self.useFixture(EnvFixture(env.copy()))

    @mock.patch("os_client_config.config.OpenStackConfig._load_vendor_file")
    @mock.patch("os_client_config.config.OpenStackConfig._load_config_file")
    def test_shell_args_precedence_1(self, config_mock, vendor_mock):
        """Test environment overriding occ"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = make_shell()

        # Test env var
        fake_execute(
            _shell,
            "module list",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )

        # These come from the environment
        self.assertEqual(
            'occ-env',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'occ-env',
            _shell.client_manager.region_name,
        )

    @mock.patch("os_client_config.config.OpenStackConfig._load_vendor_file")
    @mock.patch("os_client_config.config.OpenStackConfig._load_config_file")
    def test_shell_args_precedence_2(self, config_mock, vendor_mock):
        """Test command line overriding environment and occ"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = make_shell()

        # Test command option overriding config file value
        fake_execute(
            _shell,
            "--os-region-name krikkit list user",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )

        # These come from the command line
        self.assertEqual(
            'krikkit',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'krikkit',
            _shell.client_manager.region_name,
        )

    @mock.patch("os_client_config.config.OpenStackConfig._load_vendor_file")
    @mock.patch("os_client_config.config.OpenStackConfig._load_config_file")
    def test_shell_args_precedence_3(self, config_mock, vendor_mock):
        """Test command line overriding environment and occ"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_1))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = make_shell()

        # Test command option overriding config file value
        fake_execute(
            _shell,
            "--os-cloud scc --os-region-name krikkit list user",
        )
        self.assertEqual(
            'scc',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'glazed',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            DEFAULT_PROJECT_NAME,
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )

        # These come from the command line
        self.assertEqual(
            'krikkit',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'krikkit',
            _shell.client_manager.region_name,
        )
