.. |ruamel.yaml| replace:: ``ruamel.yaml``
.. _ruamel.yaml: http://yaml.readthedocs.io/en/latest/index.html

yamlize
=======

``yamlize`` is a package for serialization of Python objects to and from YAML. ``yamlize``:

* Retains round trip data (e.g. it retains comments, spacing, and other markup options).
* Checks types
* Sets defaults.
* Allows arbitrary logic checks by calling ``object.__init__``, with still retaining line numbers
  of the failed input.
* Does not require ``!!python/object:`` type annotations within the YAML.

Why not just serialze with PyYAML?
----------------------------------
PyYAML serialization requires (without custom implicit tag resolvers) that your YAML indicate the
Python object being represented. For example::

    >>> class A(object):
    >>>     def __init__(self, attr):
    >>>         self.attr = attr
    >>> a = A('attribute value')
    >>> import yaml
    >>> print(yaml.dump(a))
    !!python/object:__main__.A {attr: attribute value}

Unlike JSON and XML, one of the beauties of YAML is that it is mostly human readable and writable.
Using PyYAML out of the box requires that you either muddle the YAML with Python types, or define
custom resolvers/representers. The other deficiency of PyYAML out of the box is that it does not
support round trip data (spacing, block v. flow style, comments) retention, but |ruamel.yaml|_
does! |ruamel.yaml|_ similarly requires that specific resolvers/representers be created.

``yamlize`` makes the assumption that whatever you are loading / dumping is representative of the
type of the object expected. With this assumption, ``yamlize`` can create complex Python objects
without requiring specialized YAML customizations.

Getting started
---------------


