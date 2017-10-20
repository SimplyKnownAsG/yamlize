
from yamlize.yamlizing_error import YamlizingError
from yamlize.attributes import Attribute


class AttributeCollection(object):

    __slots__ = ('order', 'by_key', 'by_name')

    def __init__(self, *args, **kwargs):
        # let's assume the order things were defined is the order we want to
        # display them, still public if someone wants to muck
        self.order = list()
        self.by_key = dict()
        self.by_name = dict()

        for item in args:
            if not isinstance(item, Attribute):
                raise TypeError('Incorrect type {} while initializing '
                                'AttributeCollection with {}'
                                .format(type(item), item))
            self.add(item)

    def __iter__(self):
        return iter(self.order)

    @property
    def required(self):
        return {attr for attr in self if attr.is_required}

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
        self.order.append(attr)

    def from_yaml(self, obj, loader, key_node, val_node):
        """
        returns: Attribute that was applied
        """
        key = loader.construct_object(key_node)
        attribute = self.by_key.get(key, None)

        if attribute is None:
            raise YamlizingError('Error parsing {}, found key `{}` but '
                                 'expected any of {}'
                                 .format(type(obj), key, self.by_key.keys()),
                                 key_node)

        attribute.from_yaml(obj, loader, val_node)

        return attribute

