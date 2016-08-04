=======
osc-lib
=======

.. image:: https://img.shields.io/pypi/v/osc-lib.svg
    :target: https://pypi.python.org/pypi/osc-lib/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/dm/osc-lib.svg
    :target: https://pypi.python.org/pypi/osc-lib/
    :alt: Downloads

OpenStackClient (aka OSC) is a command-line client for OpenStack. osc-lib
is a package of common support modules for writing OSC plugins.

* `PyPi`_ - package installation
* `Online Documentation`_
* `Launchpad project`_ - part of OpenStackClient
* `Bugs`_ - issue tracking
* `Source`_
* `Developer` - getting started as a developer
* `Contributing` - contributing code
* `Testing` - testing code
* IRC: #openstack-sdks on Freenode (irc.freenode.net)
* License: Apache 2.0

.. _PyPi: https://pypi.python.org/pypi/osc-lib
.. _Online Documentation: http://docs.openstack.org/developer/osc-lib/
.. _Launchpad project: https://launchpad.net/python-openstackclient
.. _Bugs: https://bugs.launchpad.net/python-openstackclient
.. _Source: https://git.openstack.org/cgit/openstack/osc-lib
.. _Developer: http://docs.openstack.org/project-team-guide/project-setup/python.html
.. _Contributing: http://docs.openstack.org/infra/manual/developers.html
.. _Testing: http://docs.openstack.org/developer/osc-lib/developing.html#testing

Getting Started
===============

osc-lib can be installed from PyPI using pip::

    pip install osc-lib

Transition From OpenStackclient
===============================

This library was extracted from the main OSC repo after the OSC 2.4.0 release.
The following are the changes to imports that will cover the majority of
transition to using osc-lib:

* openstackclient.api.api -> osc_lib.api.api
* openstackclient.api.auth -> osc_lib.api.auth
* openstackclient.api.utils -> osc_lib.api.utils
* openstackclient.common.command -> osc_lib.command.command
* openstackclient.common.commandmanager -> osc_lib.command.commandmanager
* openstackclient.common.exceptions -> osc_lib.exceptions
* openstackclient.common.logs -> osc_lib.logs
* openstackclient.common.parseractions -> osc_lib.cli.parseractions
* openstackclient.common.session -> osc_lib.session
* openstackclient.common.utils -> osc_lib.utils
* openstackclient.i18n -> osc_lib.i18n
* openstackclient.shell -> osc_lib.shell

Also, some of the test fixtures and modules may be used:

* openstackclient.tests.fakes -> osc_lib.tests.fakes
* openstackclient.tests.utils -> osc_lib.tests.utils
