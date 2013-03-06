Snoopy Crime Copy (SCC)
=======================

The scc command provides tools for simplifying the git(hub) workflow.

|Build Status|

Getting Started
---------------

Under Python 2.7, the only requirement is `PyGithub`_.

::

    $ pip install pygithub

For Python 2.6, you will also need to install `argparse`_

::

    $ pip install argparse

With that, it's possible to execute scc:

::

    $ python scc.py

Brew installation
-----------------

To install the latest release of scc under `Homebrew`_, use brew
install:

::

    $ brew install scc

Or for the latest development version:

::

    $ brew install --HEAD scc

License
-------

snoopycrimecop is released under the GPL.

Copyright
---------

2012, The Open Microscopy Environment

.. _PyGithub: https://github.com/jacquev6/PyGithub
.. _argparse: http://pypi.python.org/pypi/argparse
.. _Homebrew: http://mxcl.github.com/homebrew/

.. |Build Status| image:: https://travis-ci.org/openmicroscopy/snoopycrimecop.png
   :target: http://travis-ci.org/openmicroscopy/snoopycrimecop
