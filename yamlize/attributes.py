import inspect

from .yamlizing_error import YamlizingError


class NODEFAULT:

    def __new__(cls):
        raise NotImplementedError

    def __init__(self):
        raise NotImplementedError


class _Attribute(object):

    __slots__ = ()

    def __repr__(self):
        rep = '<{}'.format(self.__class__.__name__)

        for attr_name in self.__class__.__slots__:
            attr = getattr(self, attr_name)
            if inspect.isclass(attr):
                attr = attr.__name__
            rep += ' {}:{}'.format(attr_name, attr)

        return rep + '>'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        for attr_name in self.__class__.__slots__:
            if getattr(self, attr_name) != getattr(other, attr_name):
                return False

        return True

    def __hash__(self):
        return sum(hash(getattr(self, attr_name))
                   for attr_name in self.__class__.__slots__)

    @property
    def has_default(self):
        raise NotImplementedError

    @property
    def is_required(self):
        raise NotImplementedError

    def ensure_type(self, data, node):
        raise NotImplementedError

    def to_yaml(self, obj, dumper, node_items):
        raise NotImplementedError

    def get_value(self, obj):
        raise NotImplementedError

    def set_value(self, obj, value):
        raise NotImplementedError


class Attribute(_Attribute):
    """
    Represents an attribute of a Python class, and a key/value pair in YAML.

    Attributes
    ----------
    name : str
        name of the attribute within the Python class
    key : str
        name of the attribute within the YAML representation
    type : type or ANY
        type of the attribute within the Python class. When ``ANY``, the type
        is a pass-through and whatever YAML determines it should be will be
        applied.
    default : value or NODEFAULT
        default value if not supplied in YAML. If ``default=NODEFAULT``, then
        the attribute must be supplied.
    storage_name : str
        ``'_yamlized_' + name``, stored as a separate attribute for speed.
    """

    __slots__ = ('_name', 'storage_name', 'key', 'type', 'default', 'fvalidator', 'doc')

    def __init__(self, name=None, key=None, type=NODEFAULT, default=NODEFAULT, validator=None,
                 doc=None):
        from yamlize.yamlizable import Yamlizable, Dynamic

        # initialize _name for .name assignment
        self._name = None
        self.storage_name = None
        self.key = key
        self.name = name  # sets storage_name and key if applicable
        self.default = default
        self.fvalidator = validator
        self.doc = doc

        if type == NODEFAULT:
            self.type = Dynamic
        else:
            self.type = Yamlizable.get_yamlizable_type(type)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

        if name is not None:
            self.storage_name = '_yamlized_' + name

        if self.key is None:
            self.key = name

    @property
    def has_default(self):
        return self.default is not NODEFAULT

    @property
    def is_required(self):
        return self.default is NODEFAULT

    def ensure_type(self, data, node=None):
        if isinstance(data, self.type) or data == self.default:
            return data

        try:
            new_value = self.type(data)
        except BaseException:
            raise YamlizingError('Failed to coerce value `{}` to type `{}`'
                                 .format(data, self.type), node)

        if new_value != data:
            raise YamlizingError('Coerced `{}` to `{}`, but the new value `{}`'
                                 ' is not equal to old `{}`.'
                                 .format(type(data), type(new_value),
                                         new_value, data),
                                 node)

        return new_value

    def from_yaml(self, obj, loader, node, round_trip_data):
        from yamlize.yamlizable import Yamlizable
        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            value = self.type.from_yaml(loader, node, round_trip_data)

        else:
            # this will happen for something that is not subclass-able (bool)
            value = loader.construct_object(node, deep=True)
            value = self.ensure_type(value, node)

        try:
            self.set_value(obj, value)
        except Exception as ee:
            raise YamlizingError('Failed to assign attribute `{}` to `{}`, '
                                 'got: {}'
                                 .format(self.name, value, ee), node)

    def to_yaml(self, obj, dumper, node_items, round_trip_data):
        from yamlize.yamlizable import Yamlizable
        data = self.get_value(obj)

        if self.has_default and data == self.default:
            # short circuit, don't write out default data
            return

        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            val_node = self.type.to_yaml(dumper, data, round_trip_data)

        # this will happen for something that is not subclass-able (bool)
        else:
            if not isinstance(data, self.type):
                try:
                    data = self.type(data)
                except BaseException:
                    raise YamlizingError(
                        'Failed to coerce value `{}` to type `{}`'
                        .format(data, self.type))

            val_node = dumper.represent_data(data)

        key_node = dumper.represent_data(self.key)
        node_items.append((key_node, val_node))

    def get_value(self, obj):
        return self.__get__(obj)

    def set_value(self, obj, value):
        self.__set__(obj, value)

    def __get__(self, obj, owner=None):
        if obj is None:
            return self

        result = getattr(obj, self.storage_name, self.default)

        if result is NODEFAULT:
            raise YamlizingError('Attribute `{}` was not defined on `{}`'
                                 .format(self.name, obj))

        return result

    def __set__(self, obj, value):
        if self.fvalidator is not None:
            if self.fvalidator(value) is False:
                raise ValueError('Cannot set `{}.{}` to invalid value `{}`'
                                 .format(obj.__class__.__name__, self.name, value))
        setattr(obj, self.storage_name, value)

    def __delete__(self, obj):
        delattr(obj, self.storage_name)

    def validator(self, fvalidator):
        return type(self)(self.name, self.key, self.type, self.default, fvalidator, self.doc)


class MapItem(_Attribute):
    """
    Represents a key of a dictionary, and a key/value pair in YAML.

    This should only be used temporarily.
    """

    __slots__ = ('key', 'key_type', 'val_type')

    def __init__(self, key, key_type, val_type):
        self.key = key
        self.key_type = key_type
        self.val_type = val_type

    @property
    def has_default(self):
        return False

    @property
    def is_required(self):
        return False

    def to_yaml(self, obj, dumper, node_items, round_trip_data):
        from yamlize.yamlizable import Yamlizable
        data = self.get_value(obj)

        if inspect.isclass(self.val_type) and issubclass(self.val_type, Yamlizable):
            val_node = self.val_type.to_yaml(dumper, data, round_trip_data)

        # this will happen for something that is not subclass-able (bool)
        elif not isinstance(data, self.type):
            try:
                data = self.type(data)
            except BaseException:
                raise YamlizingError('Failed to coerce value `{}` to type `{}`'
                                     .format(data, self.type))

            val_node = dumper.represent_data(data)

        key_node = self.key_type.to_yaml(dumper, self.key, round_trip_data)
        node_items.append((key_node, val_node))

    def get_value(self, obj):
        return obj[self.key]

    def set_value(self, obj, value):
        obj[self.key] = value


class KeyedListItem(_Attribute):
    """
    Represents a key of a dictionary, and a key/value pair in YAML.

    This should only be used temporarily.
    """

    __slots__ = ('key_attr', 'item_type', 'item_key')

    def __init__(self, key_attr, item_type, item_key):
        # HACK: key_attr is a descriptor, make it a tuple to trick python
        self.key_attr = (key_attr,)
        self.item_type = item_type
        self.item_key = item_key

    @property
    def has_default(self):
        return False

    @property
    def is_required(self):
        return False

    def to_yaml(self, obj, dumper, node_items, round_trip_data):
        value = self.get_value(obj)
        # HACK: key_attr is a tuple of the Attribute descriptor
        key_node, val_node = self.item_type.to_yaml_key_val(
            dumper, value, self.key_attr[0], round_trip_data)
        node_items.append((key_node, val_node))

    def get_value(self, obj):
        return obj[self.item_key]

    def set_value(self, obj, value):
        obj[self.item_key] = value

