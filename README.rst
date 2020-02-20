.. |ruamel.yaml| replace:: ``ruamel.yaml``
.. _ruamel.yaml: http://yaml.readthedocs.io/en/latest/index.html

=======
yamlize
=======

``yamlize`` is a package for serialization of Python objects to and from YAML. ``yamlize``:

* Retains round trip data

  * comments
  * spacing
  * alias/anchor names
  * YAML merge tags,
  * and other markup options

* Checks types
* Sets defaults.
* Allows for arbirtrary data validation.
* Does not require ``!!python/object:`` type annotations within the YAML.

.. image:: https://travis-ci.org/SimplyKnownAsG/yamlize.svg?branch=master
    :target: https://travis-ci.org/SimplyKnownAsG/yamlize


.. contents:: Table of Contents
    :backlinks: top

A couple important notes:

* ``yamlize`` and ``Yamlizable.load`` do not call ``__init__``. Instead they use ``__new__`` to
  create an instance and ``setattr(obj, name, value)`` to set attributes read from YAML. If you
  would like to customize some sort of initialization you can create your own ``__new__`` method,
  or override Yamlizable.from_yaml_
* The actual storage name of an attribute is different than the name of the attribute. Specifically,
  the storage name is ``'_yamlized_' + name``.
* ``yamlize`` can be used for data validation, search "data validation" within the page for various
  topics of interest.
* Within the examples, you may notice ``<BLANKLINE>`` simply indicating that there is a newline at
  the end of a string. This is an artifact of using `doctest
  <https://docs.python.org/3/library/doctest.html>`_.


Package documentation
=====================

Yamlizable.load_ :
    A class method that exists on all ``Yamlizable`` subclasses to de-serialize YAML into an
    instance of that subclass.

Yamlizable.dump_ :
    A class method that exists on all ``Yamlizable`` subclasses to serialize an instance of that
    subclass to YAML.

Attributes_ : a YAML scalar, kind of
    ``yamlize`` doesn't really have support for scalars, but it can do type checking on scalar
    types and data validation. An ``Attribute`` is used to define an instance attribute of something
    created by ``yamlize``.

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

``Yamlizable.load``
-------------------
Before seeing much about ``yamlize``, this may be out of context, but it is important to know.
All subclasses implement a ``load`` class method. The class method is then used to create class
instances from YAML (again, ``yamlize`` does not call ``__init__``, only ``__new__``).

arguments :
    ``stream`` : str or file
        The load method can accept either a YAML string, or a file-like object.
    ``Loader`` : ``ruamel.yaml.Loader``, optional
        A YAML loader; it has only been tested with the ``ruamel.yaml.RoundTripLoader``.

return type : instance of subclass
    This returns an instance of the subclass used. So, for example, ``Thing.load('...')`` returns
    an instance of a ``Thing``.


.. _Yamlizeable.dump:

``Yamlizable.dump``
-------------------
All subclasses implement a ``dump`` class method. The class method is used to write YAML from Python
object instances.

arguments :
    ``data`` : instance of subclass
        This is the object to be written, it should be of the same class as the type being used;
        e.g. ``Thing.dump(data=thing_instance)``
    ``stream`` : file-like object, optional
        If provided, ``dump`` writes to the stream, otherwise it returns a string.

return type : None if ``stream`` was provided, otherwise string
    If ``stream`` was provided, the output is written to the stream, otherwise returns an instance
    of a string.


.. _Objects:

Objects
-------

>>> from yamlize import Object, Attribute
>>>
>>> class Pet(Object):
...
...     name = Attribute()  # declare a yamlize.Attribute
...
...     age = Attribute()
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


.. _Attributes:

Attributes
----------
Taking a step back from the introduction to ``yamlize`` Objects_, we should really look at
Attributes_. An Attribute is a way to map between YAML keys/values to a Python object's attributes.

The Attribute constructor has the following arguments:

``name`` : str, optional
    Name of the Python object's attribute. By default this will be the name provided in the
    declaration (i.e. in the ``Pet`` example above, we could have written ``age =
    Attribute(name='age')``, but that is a bit redundant.

``key`` : str, optional (See `renaming keys`_)
    Key in a YAML file. For example, if you had an attribute with an underscore (_) in it, and
    would instead like to use spaces in the YAML file. Or if your Python object's attributes are
    camelCase, or PascalCase, but you'd like the YAML to be sane.

``type`` : type, optional (See `attribute types`_)
    This can be used to force an object to be cast to a specific type, or to ensure that the YAML
    input is valid.

``default`` : optional (See `attribute defaults`_)
    Provides a default value if the attribute is not defined within the YAML.

``validator``: callable, optional (See `attribute validators`_)
    Callable used to confirm a value is valid the signature is ``validator(value) -> False`` to
    indicate an invalid value, or a custom exception can be raised. Note: ``False is False`` and
    nothing else is, so don't return ``0``, ``[]``, ``{}``, etc. when you meant ``False``.


.. _renaming keys:

Using ``key`` to rename YAML inputs
+++++++++++++++++++++++++++++++++++
The Attributes_ ``key`` argument can be used to "map" from a YAML input name to the Python object's
attribute name.

>>> from yamlize import Object, Attribute
>>>
>>> class ThingWithAttribute(Object):
...
...     python_name = Attribute(key='YAML key')
>>>
>>> twa = ThingWithAttribute.load('YAML key: this is the value from YAML')
>>> twa.python_name
'this is the value from YAML'

.. note::

    ``yamlize`` doesn't prevent you from doing silly things like using names that shouldn't be
    valid python attributes, or keys that shouldn't be valid YAML.

    ``getattr(obj, 'why did I do this?')``


.. _attribute types:

Using ``type`` to for type data validation
++++++++++++++++++++++++++++++++++++++++++
The Attributes_ ``type`` argument can be used to perform type data validation on the input YAML.
(Sorry for using "type data validation" instead of "data type validation", but this way one can
search "data validation" within the documentation and find all relevant topics.)

>>> from yamlize import Object, Attribute
>>>
>>> class StronglyTypedThing(Object):
...
...     my_int = Attribute(type=int)
...     my_float = Attribute(type=float)
...     my_str = Attribute(type=str)
...
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
... my_str: 1.234
... ''') # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
YamlizingError: Coerced `<class 'ruamel.yaml.scalarfloat.ScalarFloat'>` to `<type 'str'>`, but the new value `1.234` is not equal to old `1.234`.
start:   in "<unicode string>", line 4, column 9:
    my_str: 1.234
            ^ (line: 4)
end:   in "<unicode string>", line 4, column 14:
    my_str: 1.234
                 ^ (line: 4)

The type data validation also works for attribute assignment.

>>> from yamlize import Object, Attribute
>>>
>>> class StronglyTypedThing(Object):
...
...     my_int = Attribute(type=int)
...     my_float = Attribute(type=float)
...     my_str = Attribute(type=str)
...
>>>
>>> stt = StronglyTypedThing()
>>> stt.my_int = 12
>>> stt.my_float = 1.01
>>> stt.my_str = 'abc'
>>> # now... lets try a badly typed operand
>>> stt.my_int = 12.34  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
yamlize.yamlizing_error.YamlizingError: Coerced `<class 'float'>` to `<class 'int'>`, but the new value `12` is not equal to old `12.34`.

.. _attribute defaults:

Using ``default`` to specify default Python object attribute values
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
The Attributes_ ``default`` argument can be used to simplify YAML input when an attribute can have a
default value.

>>> from yamlize import Object, Attribute
>>>
>>> class Point(Object):
...     x = Attribute()
...     y = Attribute()
...     z = Attribute(default=0.0)
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
    callable object. This will likely be changed in future versions. The issue with this is that we
    need to known when a value should and should not be written out.


.. _attribute validators:

Data validation with Attribute validators
+++++++++++++++++++++++++++++++++++++++++
Attribute data validation is available through validators. Your validator method will be called
whenever assigning a value to the attribute. You should get very accurate line numbers for the
failing YAML node.

>>> from yamlize import Object, AttributeCollection
>>>
>>> class PositivePoint(Object):
...
...     x = Attribute(type=float)
...
...     # raise a custom exception
...     @x.validator
...     def x(self, x):
...         if x < 0.0:
...             raise ValueError('Cannot set PositivePoint.x to {}'.format(x))
...
...     # or, return False when the value is not valid
...     y = Attribute(type=float, validator=lambda self, y: y >= 0)
>>>
>>> PositivePoint.load(u'{ x: -0.0000001, y: 1.0}')  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
YamlizingError: Failed to assign attribute `x` to `-1e-07`, got: Cannot set PositivePoint.x to -1e-07
start:   in "<unicode string>", line 1, column 6:
    { x: -0.0000001, y: 1.0}
         ^ (line: 1)
end:   in "<unicode string>", line 1, column 16:
    { x: -0.0000001, y: 1.0}
                   ^ (line: 1)

As noted, the validator is called every time the ``Attribute`` is assigned, so the attribute can
never be invalid.

>>> pp = PositivePoint()
>>> pp.x = 101.1
>>> pp.y = -101.1  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
ValueError: Cannot set `PositivePoint.y` to invalid value `-101.1`

When I say it can never be invalid, the value will not be assigned...

>>> pp.y  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
YamlizingError: Attribute `y` was not defined on `<__main__.PositivePoint object at 0x10da75a08>`

As noted this is rather cumbersome, so you may wish to use `Yamlizable.from_yaml for data
validation`_ instead.


.. _Maps:

Maps
----
``yamlize.Map`` is a subclass of the ``yamlize.Object`` that can be used to define a Python class
that has both attributes and keys/values. Attribute names are exclusive, and cannot also be
provided as a key name.

>>> from yamlize import Map, Typed, Attribute
>>>
>>> class Student(Map):
...     key_type = Typed(str)
...     value_type = Typed(float)
...     first = Attribute()
...     last = Attribute()
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

>>> from yamlize import Map, Typed
...
>>> class GradeBook(Map):
...     key_type = Typed(str)
...     value_type = Student  # no need to use Typed, as Student is already Yamlizable
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

>>> from yamlize import KeyedList, Attribute
>>>
>>> class GradeBook(KeyedList):
...     key_attr = Student.first  # attribute of the value that is the key
...     item_type = Student
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
A ``yamlize.Sequence`` should be used effectively as a Python strong-typed list. Unlike the other
``yamlize`` decorators / classes, a ``Sequence`` cannot have attributes. The lack of attributes is a
functionality of YAML itself; a YAML sequence cannot have attributes.

>>> from yamlize import Object, Sequence
>>>
>>> class Person(Object):
...     first = Attribute(type=str)
...     last = Attribute(type=str)
>>>
>>> class People(Sequence):
...     item_type = Person
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

>>> from yamlize import Object, Sequence
>>>
>>> class Person(Object):
...     first = Attribute(type=str)
...     last = Attribute(type=str)
>>>
>>> class People(Sequence):
...     item_type = Person
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

>>> from yamlize import Object, KeyedList
>>>
>>> class Thing(Object):
...     name = Attribute(type=str)
...     int_attr = Attribute(type=int)
...     str_attr = Attribute(type=str)
...     float_attr = Attribute(type=float)
>>>
>>> class Things(KeyedList):
...     key_attr = Thing.name
...     item_type = Thing
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


Customization
=============
We have already discussed the Yamlizable.load_ and Yamlizable.dump_ class methods. These two
methods only get called to open / create the "root" of the document tree and begin the parsing. The
actual bulk of the work is done using Yamlizable.from_yaml_ and Yamlizable.to_yaml_.


.. _Yamlizable.from_yaml:

``Yamizable.from_yaml``
-----------------------
The ``from_yaml`` method is also a class method that is used to create a new instance for a
``Yamlizable`` object.

arguments :
    ``loader`` : Loader (See |ruamel.yaml|_)
        A loader class, this should generally be used to parse the node, and register the created
        object.
    ``node`` : Node (See |ruamel.yaml|_)
        A YAML node.
    ``round_trip_data`` : ``yamlize.round_trip_data.RoundTripData``
        An object for retaining round trip data. This is passed from the parent object (which may
        or may not be ``Yamlizable``. ``Yamlizable`` objects have their own ``RoundTripData``
        instances, but non-``Yamlizable`` objects do not (i.e. int, float, str). In order to retain
        non-``Yamlizable`` round trip data, a ``RoundTripData`` instance can store additional data
        from other nodes.

return type : ``Yamlizable`` subclass instance
    The return type should be an instance of the subclass.

This method can be used effectively in place of a custom resolver.


.. _Yamlizable.from_yaml for data validation:

Data validation with ``Yamlizable.from_yaml``
+++++++++++++++++++++++++++++++++++++++++++++
Alternative to using `attribute validators`_, you can override the Yamlizable.from_yaml_
classmethod to supply custom data validation.

>>> from yamlize import Object, Attribute, YamlizingError
>>>
>>> class PositivePoint2(Object):
...     x = Attribute(type=float)
...     y = Attribute(type=float)
...
...     @classmethod
...     def from_yaml(cls, loader, node, round_trip_data=None):
...         # from_yaml.__func__ is the unbound class method
...         self = Object.from_yaml.__func__(PositivePoint2, loader, node, round_trip_data)
...
...         if self.x < 0.0 or self.y < 0.0:
...             raise YamlizingError('Point x and y values must be positive', node)
...
...         return self
>>>
>>> PositivePoint2.load(u'{ x: -0.0000001, y: 1.0}')  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
YamlizingError: Point x and y values must be positive
start:   in "<unicode string>", line 1, column 1:
    { x: -0.0000001, y: 1.0}
    ^ (line: 1)
end:   in "<unicode string>", line 1, column 25:
    { x: -0.0000001, y: 1.0}
                            ^ (line: 1)

Subclassing
+++++++++++
You can also use ``Yamlizable.from_yaml`` for handling subclassing.

>>> from yamlize import Object, Sequence
>>>
>>> class Shape(Object):
...
...     shape = Attribute(type=str)
...
...     @classmethod
...     def from_yaml(cls, loader, node, round_trip_data):
...         # the node is a map, let's find the "shape" key
...         for key_node, val_node in node.value:
...             key = loader.construct_object(key_node)
...             if key == 'shape':
...                 subclass_name = loader.construct_object(val_node)
...                 break
...         else:
...             raise YamlizingError('Missing "shape" key', node)
...
...         subclass = {
...             'Circle' : Circle,
...             'Square' : Square,
...             'Rectangle' : Rectangle
...             }[subclass_name]
...
...         # from_yaml.__func__ is the unbound class method
...         return Object.from_yaml.__func__(subclass, loader, node, round_trip_data)
>>>
>>> class Circle(Shape):
...
...     radius = Attribute(type=float)
>>>
>>> class Square(Shape):
...
...     side = Attribute(type=float)
>>>
>>> class Rectangle(Shape):
...
...     length = Attribute(type=float)
...     width = Attribute(type=float)
>>>
>>> class Shapes(Sequence):
...
...     item_type = Shape
>>>
>>> shapes = Shapes.load(u'''
... - {shape: Circle, radius: 1.0}
... - {shape: Square, side: 2.0}
... - {shape: Rectangle, length: 3.0, width: 4.0}
... ''')
>>>
>>> print(Shapes.dump(shapes))
- {shape: Circle, radius: 1.0}
- {shape: Square, side: 2.0}
- {shape: Rectangle, length: 3.0, width: 4.0}
<BLANKLINE>


Subclassing 2 -- when you can't subclass
++++++++++++++++++++++++++++++++++++++++
Under most conditions ``yamlize`` needs attributes and items to be subclasses of
``yamlize.Yamlizable``. This can cause problems when you have some data that otherwise just doesn't
need to be subclassed. ``yamlize`` allows you to specify specific conversion methods to and from
YAML in these instances.

>>> from yamlize import Object
>>> import aenum
>>> 
>>> class Sex(aenum.Enum):
...     FEMALE = aenum.auto()
...     MALE = aenum.auto()
>>>
>>> TypedSex = Typed(Sex,
...         from_yaml=lambda loader, node, rtd: Sex[loader.construct_object(node)],
...         to_yaml=lambda dumper, data, rtd: dumper.represent_data(str(data).replace('Sex.', '')))
>>>

With the above, you can now use ``TypedSex`` to ensure proper typing of the enumeration. For
example:

>>> class Person(Object):
...     name = Attribute(type=str)      # as an FYI, under the hood 'str' becomes Typed(str)
...     sex = Attribute(type=TypedSex)
>>>
>>> me = Person.load('{name: me, sex: MALE}')
>>> me.name
'me'
>>> str(me.sex)
'Sex.MALE'


Why not just serialze with PyYAML?
==================================
PyYAML serialization requires (without custom implicit tag resolvers) that your YAML indicate the
Python object being represented. It may also not be possible to have a specific map represent
specific types, and I don't think the root of a document can represent a single object. It may not
be possible for multiple implicit resolvers to distinguish between a variety of Python objects.
Also, using ``yamlize`` the YAML definition and class definition are one and the same; whereas with
custom resolvers for different object types you would need to also clarify the YAML tree of where a
certain type of object may exist. For example:

>>> class A(object):
...     def __init__(self, attr):
...         self.attr = attr
>>> a = A('attribute value')
>>> import yaml
>>> print(yaml.dump(a))
!!python/object:__main__.A
attr: attribute value
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

