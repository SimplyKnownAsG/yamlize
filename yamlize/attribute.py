import inspect

from yamlize import YamlizingError


class NODEFAULT:
    def __init__(self):
        raise NotImplementedError


class ANY:
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
        type of the attribute within the Python class. When ``ANY``, the type is
        a pass-through and whatever YAML determines it should be will be applied.
    default : value or NODEFAULT
        default value if not supplied in YAML. If ``default=NODEFAULT``, then
        the attribute must be supplied.
    """

    def __init__(self, name, key=None, type=ANY, default=NODEFAULT):
        self.name = name
        self.key = key or name
        self.type = type
        self.default = default

    def from_yaml(self, constructor, node):
        from yamlize.yamlizable import Yamlizable # prevent recursive import

        if inspect.isclass(self.type) and issubclass(self.type, Yamlizable):
            return self.type.from_yaml(constructor, node)

        value = constructor.construct_object(node, deep=True)

        if self.type is ANY or isinstance(value, self.type):
            return value
        else:
            try:
                return self.type(value)
            except:
                raise YamlizingError('Failed to coerce value `{}` to type `{}`'
                                     .format(value, self.type), node)


class AttributeCollection(object):

    __slots__ = ('by_key', 'by_name')

    def __init__(self, *args, **kwargs):
        self.by_key = dict()
        self.by_name = dict()
        for item in args:
            if not isinstance(item, Attribute):
                if isinstance(item, dict):
                    item = Attribute(**item)
                elif isinstance(item, (tuple, list)):
                    item = Attribute(*item)
                else:
                    raise TypeError('Incorrect type {} while initializing AttributeCollection with {}'
                                    .format(type(item), item))
            self.add(item)

    def add(self, attr):
        if attr.key in self.by_key:
            raise KeyError('AttributeCollection already contains an entry for {}, previously defined: {}'
                           .format(attr.key, self.by_key[attr.key]))

        if attr.name in self.by_name:
            raise KeyError('AttributeCollection already contains an entry for {}, previously defined: {}'
                           .format(attr.name, self.by_name[attr.name]))

        self.by_key[attr.key] = attr
        self.by_name[attr.name] = attr

