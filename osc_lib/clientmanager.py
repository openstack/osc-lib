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

"""Manage access to the clients, including authenticating when needed."""

import copy
import logging
import sys

from openstack import connection
from oslo_utils import strutils
import six

from osc_lib.api import auth
from osc_lib import exceptions
from osc_lib import session as osc_session
from osc_lib import version

# NOTE(dtroyer): Attempt an import to detect if the SDK installed is new
#                enough to not use Profile.  If so, use that.
try:
    from openstack.config import loader as config   # noqa
    profile = None
except ImportError:
    from openstack import profile

LOG = logging.getLogger(__name__)

PLUGIN_MODULES = []


class ClientCache(object):
    """Descriptor class for caching created client handles."""

    def __init__(self, factory):
        self.factory = factory
        self._handle = None

    def __get__(self, instance, owner):
        # Tell the ClientManager to login to keystone
        if self._handle is None:
            try:
                self._handle = self.factory(instance)
            except AttributeError as err:
                # Make sure the failure propagates. Otherwise, the plugin just
                # quietly isn't there.
                new_err = exceptions.PluginAttributeError(err)
                six.reraise(new_err.__class__, new_err, sys.exc_info()[2])
        return self._handle


class ClientManager(object):
    """Manages access to API clients, including authentication."""

    # NOTE(dtroyer): Keep around the auth required state of the _current_
    #                command since ClientManager has no visibility to the
    #                command itself; assume auth is not required.
    _auth_required = False

    def __init__(
        self,
        cli_options=None,
        api_version=None,
        pw_func=None,
        app_name=None,
        app_version=None,
    ):
        """Set up a ClientManager

        :param cli_options:
            Options collected from the command-line, environment, or wherever
        :param api_version:
            Dict of API versions: key is API name, value is the version
        :param pw_func:
            Callback function for asking the user for a password.  The function
            takes an optional string for the prompt ('Password: ' on None) and
            returns a string containing the password
        :param app_name:
            The name of the application for passing through to the useragent
        :param app_version:
            The version of the application for passing through to the useragent
        """

        self._cli_options = cli_options
        self._api_version = api_version
        self._pw_callback = pw_func
        self._app_name = app_name
        self._app_version = app_version
        self.region_name = self._cli_options.region_name
        self.interface = self._cli_options.interface

        self.timing = self._cli_options.timing

        self._auth_ref = None
        self.session = None

        # self.verify is the Requests-compatible form
        # self.cacert is the form used by the legacy client libs
        # self.insecure is not needed, use 'not self.verify'

        # NOTE(dtroyer): Per bug https://bugs.launchpad.net/bugs/1447784
        #                --insecure overrides any --os-cacert setting

        # Set a hard default
        self.verify = True
        if self._cli_options.insecure:
            # Handle --insecure
            self.verify = False
            self.cacert = None
        else:
            if (self._cli_options.cacert is not None
                    and self._cli_options.cacert != ''):
                # --cacert implies --verify here
                self.verify = self._cli_options.cacert
                self.cacert = self._cli_options.cacert
            else:
                # Fall through also gets --verify
                if self._cli_options.verify is not None:
                    self.verify = self._cli_options.verify
                self.cacert = None

        # Set up client certificate and key
        # NOTE(cbrandily): This converts client certificate/key to requests
        #                  cert argument: None (no client certificate), a path
        #                  to client certificate or a tuple with client
        #                  certificate/key paths.
        self.cert = self._cli_options.cert
        if self.cert and self._cli_options.key:
            self.cert = self.cert, self._cli_options.key

        # TODO(mordred) The logic above to set all of these is duplicated in
        # os-client-config but needs more effort to tease apart and ensure that
        # values are being passed in. For now, let osc_lib do it and just set
        # the values in occ.config
        self._cli_options.config['verify'] = self.verify
        self._cli_options.config['cacert'] = self.cacert
        # Attack of the killer passthrough values
        self._cli_options.config['cert'] = self._cli_options.cert
        self._cli_options.config['key'] = self._cli_options.key

        # TODO(mordred) We also don't have any support for setting or passing
        # in api_timeout, which is set in occ defaults but we skip occ defaults
        # so set it here by hand and later we should potentially expose this
        # directly to osc
        self._cli_options.config['api_timeout'] = None

        # Get logging from root logger
        root_logger = logging.getLogger('')
        LOG.setLevel(root_logger.getEffectiveLevel())

        # NOTE(gyee): use this flag to indicate whether auth setup has already
        # been completed. If so, do not perform auth setup again. The reason
        # we need this flag is that we want to be able to perform auth setup
        # outside of auth_ref as auth_ref itself is a property. We can not
        # retrofit auth_ref to optionally skip scope check. Some operations
        # do not require a scoped token. In those cases, we call setup_auth
        # prior to dereferrencing auth_ref.
        self._auth_setup_completed = False

    def setup_auth(self):
        """Set up authentication

        This is deferred until authentication is actually attempted because
        it gets in the way of things that do not require auth.
        """

        if self._auth_setup_completed:
            return

        # Stash the selected auth type
        self.auth_plugin_name = self._cli_options.config['auth_type']

        # Basic option checking to avoid unhelpful error messages
        auth.check_valid_authentication_options(
            self._cli_options,
            self.auth_plugin_name,
        )

        # Horrible hack alert...must handle prompt for null password if
        # password auth is requested.
        if (self.auth_plugin_name.endswith('password') and
                not self._cli_options.auth.get('password')):
            self._cli_options.auth['password'] = self._pw_callback()

        LOG.info('Using auth plugin: %s', self.auth_plugin_name)
        LOG.debug('Using parameters %s',
                  strutils.mask_password(self._cli_options.auth))
        self.auth = self._cli_options.get_auth()

        if self._cli_options.service_provider:
            self.auth = auth.get_keystone2keystone_auth(
                self.auth,
                self._cli_options.service_provider,
                self._cli_options.remote_project_id,
                self._cli_options.remote_project_name,
                self._cli_options.remote_project_domain_id,
                self._cli_options.remote_project_domain_name
            )

        self.session = osc_session.TimingSession(
            auth=self.auth,
            verify=self.verify,
            cert=self.cert,
            app_name=self._app_name,
            app_version=self._app_version,
            additional_user_agent=[('osc-lib', version.version_string)],
        )

        # Create a common default SDK Connection object if it is the newer
        # non-Profile style.
        if profile is None:
            self.sdk_connection = connection.Connection(
                config=self._cli_options,
                session=self.session,
            )

        self._auth_setup_completed = True

    def validate_scope(self):
        if self._auth_ref.project_id is not None:
            # We already have a project scope.
            return
        if self._auth_ref.domain_id is not None:
            # We already have a domain scope.
            return

        # We do not have a scoped token (and the user's default project scope
        # was not implied), so the client needs to be explicitly configured
        # with a scope.
        auth.check_valid_authorization_options(
            self._cli_options,
            self.auth_plugin_name,
        )

    @property
    def auth_ref(self):
        """Dereference will trigger an auth if it hasn't already"""
        if (not self._auth_required or
                self._cli_options.config['auth_type'] == 'none'):
            # Forcibly skip auth if we know we do not need it
            return None
        if not self._auth_ref:
            self.setup_auth()
            LOG.debug("Get auth_ref")
            self._auth_ref = self.auth.get_auth_ref(self.session)
        return self._auth_ref

    def is_service_available(self, service_type):
        """Check if a service type is in the current Service Catalog"""

        # Trigger authentication necessary to discover endpoint
        if self.auth_ref:
            service_catalog = self.auth_ref.service_catalog
        else:
            service_catalog = None
        # Assume that the network endpoint is enabled.
        service_available = None
        if service_catalog:
            if service_type in service_catalog.get_endpoints():
                service_available = True
                LOG.debug("%s endpoint in service catalog", service_type)
            else:
                service_available = False
                LOG.debug("No %s endpoint in service catalog", service_type)
        else:
            LOG.debug("No service catalog")
        return service_available

    def get_endpoint_for_service_type(self, service_type, region_name=None,
                                      interface='public'):
        """Return the endpoint URL for the service type."""
        if not interface:
            interface = 'public'
        # See if we are using password flow auth, i.e. we have a
        # service catalog to select endpoints from
        if self.auth_ref:
            endpoint = self.auth_ref.service_catalog.url_for(
                service_type=service_type,
                region_name=region_name,
                interface=interface,
            )
        else:
            # Get the passed endpoint directly from the auth plugin
            endpoint = self.auth.get_endpoint(
                self.session,
                interface=interface,
            )
        return endpoint

    def get_configuration(self):
        return copy.deepcopy(self._cli_options.config)
