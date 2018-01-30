.. |ruamel.yaml| replace:: ``ruamel.yaml``
.. _ruamel.yaml: http://yaml.readthedocs.io/en/latest/index.html

=======
yamlize
=======

``yamlize`` is a package for serialization of Python objects to and from YAML. ``yamlize``:

* Retains round trip data (e.g. it retains comments, spacing, and other markup options).
* Checks types
* Sets defaults.
* Does not require ``!!python/object:`` type annotations within the YAML.

.. image:: https://travis-ci.org/SimplyKnownAsG/yamlize.svg?branch=master
    :target: https://travis-ci.org/SimplyKnownAsG/yamlize


.. contents:: Table of Contents
    :backlinks: top

Package documentation
=====================

Yamlizable.load_ :
    A class method that exists on all ``yamlize`` subclasses to de-serialize YAML into an instance
    of that subclass.

Yamlizable.dump_ :
    A class method that exists on all ``yamlize`` subclasses to serialize an instance of that
    subclass to YAML.

Attributes_ : a YAML scalar kind of
    ``yamlize`` doesn't really have support for scalars, but it can do type checking on scalar
    types. An ``Attribute`` is used to define an instance attribute of something created by
    ``yamlize``.

Objects_ : a YAML map converted to a Python object
    ``yamlize`` class for serialization to and from a YAML map. Each key of the YAML map is an
    attribute of the class instance.

Maps_ : a YAML map
    Basically the same as an ``OrderedDict``, except that it can also have Attributes_.

`Keyed Lists`_ : a YAML map with special keys and values
    Similar to Maps_, the ``KeyedList`` takes the value of a Python object's attribute as a key.
    This is best explained with examples...

Sequences_ : a YAML sequence of objects
    This corresponds to a sequence of objects, and can be used to simply validate types (by using
    something like ``yamlize.StrList``), or to convert a list of other Python yamlizable objects.


.. _Yamlizeable.load:

Yamlizable.load
----------------
Before seeing much about ``yamlize``, this may be out of context, but it is important to know.

arguments : str, or file
    All subclasses implement a ``load`` class method. The class method is then used to create
    instances from YAML. The load method can accept either a YAML string, or a file-like object.

return type : instance of subclass
    This returns an instance of the subclass used. So, for example, ``Thing.load('...')`` returns
    an instance of a ``Thing``.


.. _Yamlizeable.dump:

Yamlizable.dump
----------------
arguments : object instance, and file (optional)
    All subclasses implement a ``dump`` class method. The class method is then used to write YAML
    from Python object instances.

    The dump method has a second optional argument of a file-like object.

return type : None if file was provided, otherwise string
    This returns an instance of the subclass used. So, for example, ``Thing.load('...')`` returns
    an instance of a ``Thing``.


.. _Objects:

Objects
-------

>>> from yamlize import Object, AttributeCollection, Attribute
>>>
>>> class Pet(Object):
...
...     attributes = AttributeCollection(Attribute(name='name'),
...                                      Attribute(name='age'))
>>>
>>> lucy = Pet.load(u'''
... name: Lucy  # yay it is some YAML!
... age: 8
... ''')
>>>
>>> lucy.name, lucy.age
('Lucy', 8)

Using |ruamel.yaml|_, the formatting can be retained allowing for hand-generated YAML files to
retain important information and legibility.

>>> print(Pet.dump(lucy))
name: Lucy  # yay it is some YAML!
age: 8
<BLANKLINE>

``yamlize`` also comes with a decorator to create yamlizable subclasses. The above can also be
written:

>>> from yamlize import yaml_object, Attribute
>>>
>>> @yaml_object(Attribute(name='name'),
...              Attribute(name='age'))
... class Pet(object):
...     # Note ^ lowercase object instead of yamlize.Object
...     pass
>>>
>>> lucy2 = Pet.load(u'''
... name: Lucy  # yay it is some YAML!
... age: 8
... ''')
...
>>> print(Pet.dump(lucy2))
name: Lucy  # yay it is some YAML!
age: 8
<BLANKLINE>


.. _Attributes:

Attributes
----------
Taking a step back from the introduction to ``yamlize`` Objects_, we should really look at
Attributes_. An Attribute is a way to map between YAML keys/values to a Python object's attributes.

The Attribute constructor has the following arguments:

``name`` : str
    Name of the Python object's attribute

``key`` : str, optional (See `renaming keys`_)
    Key in a YAML file. For example, if you had an attribute with an underscore (_) in it, and
    would instead like to use spaces in the YAML file. Or if your Python object's attributes are
    camelCase, or PascalCase, but you'd like the YAML to be sane.

``type`` : type, optional (See `attribute types`_)
    This can be used to force an object to be cast to a specific type, or to ensure that the YAML
    input is valid.

``default`` : optional (See `attribute defaults`_)
    Provides a default value if the attribute is not defined within the YAML.

.. _renaming keys:

Using ``key`` to rename YAML inputs
+++++++++++++++++++++++++++++++++++
The Attributes_ ``key`` argument can be used to "map" from a YAML input name to the Python object's
attribute name.

>>> from yamlize import yaml_object, Attribute
>>>
>>> @yaml_object(Attribute(name='python_name', key='YAML key'))
... class ThingWithAttribute(object):
...     pass
>>>
>>> twa = ThingWithAttribute.load('YAML key: this is the value from YAML')
>>> twa.python_name
'this is the value from YAML'

.. note::

    ``yamlize`` doesn't prevent you from doing silly things like using names that shouldn't be
    valid python attributes, or keys that shouldn't be valid YAML.

    ``getattr(obj, 'why did I do this?')``


.. _attribute types:

Using ``type`` force specified type
+++++++++++++++++++++++++++++++++++
The Attributes_ ``type`` argument can be used to perform type validation on the input YAML.

>>> from yamlize import yaml_object, Attribute
>>>
>>> @yaml_object(Attribute(name='my_int', type=int),
...              Attribute(name='my_float', type=float),
...              Attribute(name='my_str', type=str))
... class StronglyTypedThing(object):
...     pass
>>>
>>> stt = StronglyTypedThing.load(u'''
... my_int: 42
... my_float: 9.9
... my_str: this is a string.   still
... ''')

The above worked just fine because all the types correspond. Giving incorrect types will result in
``YamlizingErrors`` indicating the line of input that is erroneous.

>>> StronglyTypedThing.load(u'''
... my_int: 12.1
... my_float: 9.9
... my_str: this is a string.   still
... ''') # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
YamlizingError: Coerced `<class 'ruamel.yaml.scalarfloat.ScalarFloat'>` to `<type 'int'>`, but the new value `12` is not equal to old `12.1`.
start:   in "<unicode string>", line 2, column 9:
    my_int: 12.1
            ^ (line: 2)
end:   in "<unicode string>", line 2, column 13:
    my_int: 12.1
                ^ (line: 2)

Note that we tried to coerce one type to another, so it is possible to trick the logic.

>>> stt2 = StronglyTypedThing.load(u'''
... my_int: 81.0      # this will be cast to an integer
... my_float: 92.1
... my_str: another boring message
... ''')
>>> stt2.my_int
81

Not all types can be tricked, and pull requests are welcome to fix unintended side effects.

>>> StronglyTypedThing.load(u'''
... my_int: 1001
... my_float: 1e99
... my_str: 1.234    # YAML parsers generate a float, but this should be '12.0' (with quotes)
... ''') # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
YamlizingError: Coerced `<class 'ruamel.yaml.scalarfloat.ScalarFloat'>` to `<type 'str'>`, but the new value `1.234` is not equal to old `1.234`.
start:   in "<unicode string>", line 4, column 9:
    my_str: 1.234    # YAML parsers generate ...
            ^ (line: 4)
end:   in "<unicode string>", line 4, column 14:
    my_str: 1.234    # YAML parsers generate a fl ...
                 ^ (line: 4)

.. _attribute defaults:

Using ``default`` to specify default Python object attribute values
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
The Attributes_ ``default`` argument can be used to simplify YAML input when an attribute can have a
default value.

>>> from yamlize import yaml_object, Attribute
>>>
>>> @yaml_object(Attribute(name='x'),
...              Attribute(name='y'),
...              Attribute(name='z', default=0.0))
... class Point(object):
...     pass
>>>
>>> p0 = Point.load(u'''
... x: 1.0
... y: 2.2
... ''')
>>> p0.x, p0.y, p0.z
(1.0, 2.2, 0.0)

The default obviously, only applies to the specific attribute, so the following results in an error.

>>> Point.load(u'''
... x: 1000.0001    # missing non-default z value
... z: 2000.0002
... ''') # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
YamlizingError: Missing <class '__main__.Point'> attributes without default: ['y']
start:   in "<unicode string>", line 2, column 1:
    x: 1000.0001    # missing non-de ...
    ^ (line: 2)
end:   in "<unicode string>", line 4, column 1:
<BLANKLINE>
    ^ (line: 4)


.. warning::
    The default argument *should* work more similar to ``collections.defaultdict`` accepting a
    callable object. This will likely be changed in future versions.


.. _Maps:

Maps
----
``yamlize.Map`` is a subclass of the ``yamlize.Object`` that can be used to define a Python class
that has both attributes and keys/values. Attribute names are exclusive, and cannot also be
provided as a key name.

>>> from yamlize import yaml_map, Attribute
>>>
>>> @yaml_map(str,    # key_type
...           float,  # value_type
...           Attribute(name='first'),
...           Attribute(name='last'))
... class Student(object):
...     pass # ... or did they?
>>>
>>> f = Student.load(u'''
... first: Failing
... last: Student
... homework 1: 15.0  # turned in late
... homework 2: 45.0  # turned in late, again
... homework 3: 60.0  # turned in late, again again
... homework 4: 95.0
... exam 1: 65.0
... ''')
>>> f.first
'Failing'
>>> f['homework 1']
15.0

.. note:: Now for the neat stuff.

You can use ``yamlize`` types as arguments to other classes.

>>> from yamlize import yaml_map
...
>>> @yaml_map(str,      # key type
...           Student)  # value type
... class GradeBook(object):
...     pass
>>>
>>> gb = GradeBook()
>>> gb['Failing Student'] = f
>>> print(GradeBook.dump(gb))
Failing Student:
  first: Failing
  last: Student
  homework 1: 15.0 # turned in late
  homework 2: 45.0 # turned in late, again
  homework 3: 60.0 # turned in late, again again
  homework 4: 95.0
  exam 1: 65.0
<BLANKLINE>

.. _Keyed Lists:

Keyed Lists
-----------
``yamlize.KeyedList`` is a subclass of the ``yamlize.Object`` that can be used to define a Python
class that has both attributes and keys/values. Attribute names are exclusive, and cannot also be
provided as a key name.

The difference between a ``yamlize.Map`` and a ``yamlize.KeyedList`` is that the ``KeyedList`` key
points to an attribute on the value. This operates under the assumption that the value type is
another Yamlizable type. The purpose of pointing to an attribute on the value is to reduce
duplication of data. In the previous example of the ``GradeBook`` we specified "Failing Student"
twice.

>>> from yamlize import yaml_keyed_list, Attribute
>>>
>>> @yaml_keyed_list('first',      # attribute of the value that is the key
...                  Student,      # value_type
...                  )
... class GradeBook(object):
...     pass
>>>
>>> grade_book = GradeBook()
>>> grade_book.add(f)  # f is failing student from above
>>> print(GradeBook.dump(grade_book))
Failing:
  last: Student
  homework 1: 15.0 # turned in late
  homework 2: 45.0 # turned in late, again
  homework 3: 60.0 # turned in late, again again
  homework 4: 95.0
  exam 1: 65.0
<BLANKLINE>


.. _Sequences:

Sequences
---------
A ``yamlize.Sequence`` should be used effectively as a Python strong-typed list.

>>> from yamlize import yaml_object, yaml_list
>>>
>>> @yaml_object(Attribute(name='first', type=str),
...              Attribute(name='last', type=str))
... class Person(object):
...     pass
>>>
>>> @yaml_list(Person)
... class People(object):
...     pass
>>>
>>> peeps = People.load(u'''
... - {first: g, last: m}
... - {first: First, last: Last}
... - first: First2
...   last: Last2
... ''')
>>> peeps[0].first, peeps[2].last
('g', 'Last2')


Alias and Anchor Treatment
==========================
A ``yamlize`` correctly handles YAML anchors (&), aliases (*), and merge tags (<<).

>>> from yamlize import yaml_object, yaml_list
>>>
>>> @yaml_object(Attribute(name='first', type=str),
...              Attribute(name='last', type=str))
... class Person(object):
...     pass
>>>
>>> @yaml_list(Person)
... class People(object):
...     pass
>>>
>>> peeps = People.load(u'''
... - &g {first: g, last: m}
... - {first: First, last: Last}
... - {first: First, last: Last}
... - *g
... ''')

.. here is a comment* to help vim syntax highlighting recover from the asterisk

Since an anchor and alias were used to define ``g`` twice, there is one object reference for ``g``.

>>> g0 = peeps[0]
>>> g3 = peeps[3]
>>> g0 == g3, id(g0) == id(g3)
(True, True)

Conversely, despite having the same definition for ``{first: First, last: Last}`` twice, they are
different objects.

>>> peeps[1] == peeps[2], id(peeps[1]) == id(peeps[2])
(False, False)

When dumping back to YAML, anchor and alias names are retained:

>>> print(People.dump(peeps))
- &g {first: g, last: m}
- {first: First, last: Last}
- {first: First, last: Last}
- *g
<BLANKLINE>

.. here is a comment* to help vim syntax highlighting recover from the asterisk

Merge tags
==========
One neat aspect of YAML is the ability to use merge tags ``<<:`` to reduce user input. ``yamlize``
will retain these.

>>> from yamlize import yamlizable, yaml_keyed_list
>>> @yamlizable(Attribute(name='name', type=str),
...             Attribute(name='int_attr', type=int),
...             Attribute(name='str_attr', type=str),
...             Attribute(name='float_attr', type=float))
... class Thing(object):
...     pass
>>>
>>> @yaml_keyed_list(key_name='name', item_type=Thing)
... class Things(object):
...     pass
>>>
>>> things = Things.load(u'''
... thing1: &thing1
...   int_attr: 1
...   str_attr: '1'
...   float_attr: 99.2
... thing2: &thing2
...   <<: *thing1
...   str_attr: an actual string
... thing3:
...   <<: *thing1
...   <<: *thing2
...   float_attr: 42.42
... ''')

.. here is a comment* to help vim syntax highlighting recover from the asterisk

The last merged value is the one that is applied, so:

>>> thing1, thing2, thing3 = list(things.values())
>>> thing1.int_attr == thing2.int_attr
True
>>> thing2.str_attr == thing3.str_attr
True

And of course, merge tags are retained when dumping back to YAML.

>>> print(Things.dump(things))
thing1: &thing1
  int_attr: 1
  str_attr: '1'
  float_attr: 99.2
thing2: &thing2
  <<: *thing1
  str_attr: an actual string
thing3:
  <<: *thing1
  <<: *thing2
  float_attr: 42.42
<BLANKLINE>

.. here is a comment* to help vim syntax highlighting recover from the asterisk

Round trip information
======================
Note this will retain block or flow style and comments when dumping back to yaml.

>>> formatted_people = People.load(u'''
... - {first: f, last: l} # comment 1
... - first: First  # value-add comment 2
...   last: Last    #
... ''')
>>> print(People.dump(formatted_people))
- {first: f, last: l} # comment 1
- first: First  # value-add comment 2
  last: Last    #
<BLANKLINE>

Why not just serialze with PyYAML?
==================================
PyYAML serialization requires (without custom implicit tag resolvers) that your YAML indicate the
Python object being represented. For example:

>>> class A(object):
...     def __init__(self, attr):
...         self.attr = attr
>>> a = A('attribute value')
>>> import yaml
>>> print(yaml.dump(a))
!!python/object:__main__.A {attr: attribute value}
<BLANKLINE>


Unlike JSON and XML, one of the beauties of YAML is that it is mostly human readable and writable.
Using PyYAML out of the box requires that you either muddle the YAML with Python types, or define
custom resolvers/representers in addition to the types you already need. The other deficiency of
PyYAML out of the box is that it does not support round trip data (spacing, block v. flow style,
comments) retention, but |ruamel.yaml|_ does! |ruamel.yaml|_ similarly requires that specific
resolvers/representers be created.

``yamlize`` makes the assumption that whatever you are loading / dumping is representative of the
type of the object expected. With this assumption, ``yamlize`` can create complex Python objects
without requiring specialized YAML customizations.

