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

To install :program:`scc`, run::

 $ python setup.py install

or using :program:`pip`, run::

 $ pip install scc

To upgrade your pip installation, run::

 $ pip install -U scc

Usage
-----

The list of available commands can be listed with::

  $ scc -h
  usage: scc [-h]

  {already-merged,check-milestone,clean-sandbox,deploy,label,merge,rebase,set-commit-status,tag-release,token,travis-merge,unrebased-prs,update-submodules,version}
           ...

  Snoopy Crime Cop Script

  optional arguments:
    -h, --help                            show this help message and exit

  Subcommands:
    {already-merged,check-milestone,clean-sandbox,deploy,label,merge,rebase,set-commit-status,tag-release,token,travis-merge,unrebased-prs,update-submodules,version}
      already-merged                      Detect branches local & remote which are already merged
      check-milestone                     Check all merged PRs for a set milestone
      clean-sandbox                       Cleans snoopys-sandbox repo after testing
      deploy                              Deploy an update to a website using the "symlink swapping" strategy.
      label                               Query/add/remove labels from Github issues.
      merge                               Merge Pull Requests opened against a specific base branch.
      rebase                              Rebase Pull Requests opened against a specific base branch.
      set-commit-status                   Set commit status on all pull requests with any of the given labels.
      tag-release                         Tag a release recursively across submodules.
      token                               Utility functions to manipulate local and remote Github tokens
      travis-merge                        Update submodules and merge Pull Requests in Travis CI jobs.
      unrebased-prs                       Check that PRs in one branch have been merged to another.
      update-submodules                   Similar to the 'merge' command, but only updates submodule pointers.
      version                             Find which version of scc is being used

For each subcommand, additional help can be queried::

  $ scc merge -h

Contributing
------------

PyGithub follows `PEP 8`_ the Style Guide for Python Code. Please check your
code with pep8 Python style guide checker, by running ``flake8 -v scc/ test/``
or ``pep8 -v scc/ test``.

.. _PEP 8: http://www.python.org/dev/peps/pep-0008/


Running tests
-------------

The tests are located under the `test` directory. It is required to install
the dependencies listed in dev_requirements.

Unit tests
^^^^^^^^^^

Unit tests are stored under the `test/unit` folder and can be run by calling::

  python test/unit

or using nose_::

  nosetests -v test/unit

Unit tests are also run by the Travis_ build on every Pull Request opened
against the main repository.

Integration tests
^^^^^^^^^^

Integration tests are stored under `test/integration`. Many integration tests
use https://github.com/openmicroscopy/snoopys-sandbox and
https://github.com/openmicroscopy/snoopys-sandbox2 as sandbox repositories
to test the scc commands.

Running the integration test suite requires:
- a GitHub account
- a token-based GitHub connection, i.e. a global ``github.token`` stored under
  the global Git configuration file::

    $ git config --global github.token xxxx

- the user authenticated by the token defined above needs to own forks of the
  `sandbox repository <snoopy-sandbox-fork>`_ and its
  `submodule <snoopy-sandbox2-fork>`_

Once this is set up, the integration tests can be run by calling::

  python test/integration

or using nose_::

  nosetests -v test/integration

Integration tests are run daily on the OME Continuous Integration
infrastructure under the SCC-self-merge_ job using the token-authenticated
`snoopycrimecop user <https://github.com/snoopycrimecop>`_

.. _snoopy-sandbox-fork: https://github.com/openmicroscopy/snoopys-sandbox/fork
.. _snoopy-sandbox2-fork: https://github.com/openmicroscopy/snoopys-sandbox2/fork

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
.. _Travis: http://travis-ci.org/openmicroscopy/snoopycrimecop

.. |Build Status| image:: https://travis-ci.org/openmicroscopy/snoopycrimecop.png
   :target: http://travis-ci.org/openmicroscopy/snoopycrimecop
