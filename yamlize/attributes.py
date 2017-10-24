import inspect

from yamlize.yamlizable import Dynamic
from yamlize.yamlizable import Yamlizable
from yamlize.yamlizing_error import YamlizingError


class NODEFAULT:
    def __new__(cls):
        raise NotImplementedError

    def __init__(self):
        raise NotImplementedError


class Attribute(object):
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
    """

    __slots__ = ('name', 'key', 'type', 'default')

    def __init__(self, name, key=None, type=NODEFAULT, default=NODEFAULT):
        self.name = name
        self.key = key or name
        self.default = default

        if type == NODEFAULT:
            self.type = Dynamic
        else:
            self.type = Yamlizable.get_yamlizable_type(type)

    @property
    def has_default(self):
        return self.default is not NODEFAULT

    @property
    def is_required(self):
        return self.default is NODEFAULT

    def ensure_type(self, data, node):
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

    def from_yaml(self, obj, loader, node):
        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            value = self.type.from_yaml(loader, node)

        else:
            # this will happen for something that is not subclass-able (bool)
            value = loader.construct_object(node, deep=True)
            value = self.ensure_type(value, node)

        self.set_value(obj, value)

    def to_yaml(self, obj, dumper, node_items):
        data = self.get_value(obj)

        if data == self.default and data is not NODEFAULT:
            # short circuit, don't write out default data
            return

        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            val_node = self.type.to_yaml(dumper, data)

        # this will happen for something that is not subclass-able (bool)
        elif not isinstance(data, self.type):
            try:
                data = self.type(data)
            except BaseException:
                raise YamlizingError('Failed to coerce value `{}` to type `{}`'
                                     .format(data, self.type))

            val_node = dumper.represent_data(data)

        key_node = self._represent_key(dumper)
        node_items.append((key_node, val_node))

    def _represent_key(self, dumper):
        return dumper.represent_data(self.key)

    def get_value(self, obj):
        result = getattr(obj, self.name, self.default)

        if result is NODEFAULT:
            raise YamlizingError('Attribute `{}` was not defined on `{}`'
                                 .format(self.name, obj))

        return result

    def set_value(self, obj, value):
        setattr(obj, self.name, value)


class AttributeItem(Attribute):
    """
    Represents a key of a dictionary, and a key/value pair in YAML.

    This should only be used temporarily.
    """

    __slots__ = ('key_type')

    def __init__(self, key, key_type, val_type):
        # below will store the key in the name
        Attribute.__init__(self, key, type=val_type)
        self.key_type = key_type

    def _represent_key(self, dumper):
        # we stored the actual key in the self.name on __init__
        return self.key_type.to_yaml(dumper, self.name)

    def get_value(self, obj):
        if self.name in obj:
            result = obj[self.name]
        else:
            result = default

        if result is NODEFAULT:
            raise YamlizingError('Attribute `{}` was not defined on `{}`'
                                 .format(self.name, obj))

        return result

    def set_value(self, obj, value):
        obj.__setitem__(self.name, value)

