Snoopy Crime Copy (SCC)
=======================

|Build Status|

Introduction
------------

The scc command provides tools for simplifying the Git(Hub) workflow.

Dependencies
------------

Direct dependencies of scc are:

- `PyGithub`_
- `argparse`_

Installation
------------

To install ``scc``, run::

 $ python setup.py install

or using pip, run::

 $ pip install scc

To upgrade your pip installation, run::

 $ pip install -U scc

Usage
-----

The list of available commands can be listed with::

  $ scc -h

For each subcommand, additional help can be queried, e.g.::

  $ scc merge -h

Contributing
------------

PyGithub follows `PEP 8`_, the Style Guide for Python Code. Please check your
code with pep8_ or flake8_, the Python style guide checkers, by running
``flake8 -v scc/ test/`` or ``pep8 -v scc/ test``.

.. _PEP 8: http://www.python.org/dev/peps/pep-0008/


Running tests
-------------

The tests are located under the `test` directory. It is required to install
`mox`_ and `restview`_ as listed in `dev_requirements`.

Unit tests
^^^^^^^^^^

Unit tests are stored under the `test/unit` folder and can be run by calling::

  python test/unit

or using nose_::

  nosetests -v test/unit

Unit tests are also run by the Travis_ build on every Pull Request opened
against the main repository.

Integration tests
^^^^^^^^^^^^^^^^^

Integration tests are stored under `test/integration`. Many integration tests
use snoopys-sandbox_ and snoopys-sandbox2_ as sandbox repositories to test the
scc commands.

Running the integration test suite requires:

- a GitHub account
- a token-based GitHub connection, i.e. a global ``github.token`` stored under
  the global Git configuration file::

    $ git config --global github.token xxxx

- the user authenticated by the token defined above needs to own forks of
  snoopys-sandbox_ and snoopys-sandbox2_

Once this is set up, the integration tests can be run by calling::

  python test/integration

or using nose_::

  nosetests -v test/integration

Integration tests are run daily on the OME Continuous Integration
infrastructure under the SCC-self-merge_ job using the token-authenticated
`snoopycrimecop user <https://github.com/snoopycrimecop>`_

License
-------

snoopycrimecop is released under the GPL.

Copyright
---------

2012-2013, The Open Microscopy Environment

.. _SCC-self-merge: http://hudson.openmicroscopy.org.uk/view/Mgmt/job/SCC-self-merge/
.. _PyGithub: https://github.com/jacquev6/PyGithub
.. _argparse: http://pypi.python.org/pypi/argparse
.. _nose: https://nose.readthedocs.org/en/latest/
.. _pep8: https://pypi.python.org/pypi/pep8
.. _flake8: https://pypi.python.org/pypi/flake8
.. _mox: https://pypi.python.org/pypi/mox
.. _restview: https://pypi.python.org/pypi/restview
.. _snoopys-sandbox: https://github.com/openmicroscopy/snoopys-sandbox
.. _snoopys-sandbox2: https://github.com/openmicroscopy/snoopys-sandbox2
.. _Travis: http://travis-ci.org/openmicroscopy/snoopycrimecop

.. |Build Status| image:: https://travis-ci.org/openmicroscopy/snoopycrimecop.png
   :target: http://travis-ci.org/openmicroscopy/snoopycrimecop
