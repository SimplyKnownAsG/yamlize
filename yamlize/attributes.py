import inspect

from yamlize.yamlizable import Dynamic
from yamlize.yamlizable import Yamlizable
from yamlize.yamlizingerror import YamlizingError


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

    def from_yaml(self, loader, node):
        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            return self.type.from_yaml(loader, node)

        # this will happen for something that is not subclass-able, such as
        # bool
        value = loader.construct_object(node, deep=True)

        return self.ensure_type(value, node)

    def to_yaml(self, dumper, data):
        if data == self.default and data is not NODEFAULT:
            # short circuit, don't write out default data
            return

        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            return self.type.to_yaml(dumper, data)

        # this will happen for something that is not subclass-able, such as
        # bool
        if not isinstance(data, self.type):
            try:
                data = self.type(data)
            except BaseException:
                raise YamlizingError('Failed to coerce value `{}` to type `{}`'
                                     .format(data, self.type))

        return dumper.represent_data(data)


