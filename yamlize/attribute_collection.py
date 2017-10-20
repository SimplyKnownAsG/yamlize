
from yamlize.attributes import Attribute


class AttributeCollection(object):

    __slots__ = ('by_key', 'by_name')

    def __init__(self, *args, **kwargs):
        self.by_key = dict()
        self.by_name = dict()
        for item in args:
            if not isinstance(item, Attribute):
                raise TypeError('Incorrect type {} while initializing '
                                'AttributeCollection with {}'
                                .format(type(item), item))
            self.add(item)

    def __iter__(self):
        return iter(self.by_key.values())

    @property
    def required_names(self):
        return {attr.name for attr in self if attr.is_required}

    def add(self, attr):
        if attr.key in self.by_key:
            raise KeyError('AttributeCollection already contains an entry for '
                           '{}, previously defined: {}'
                           .format(attr.key, self.by_key[attr.key]))

        if attr.name in self.by_name:
            raise KeyError('AttributeCollection already contains an entry for '
                           '{}, previously defined: {}'
                           .format(attr.name, self.by_name[attr.name]))

        self.by_key[attr.key] = attr
        self.by_name[attr.name] = attr

