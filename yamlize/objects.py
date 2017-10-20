import inspect

import ruamel.yaml

from yamlize.yamlizable import Yamlizable, Dynamic
from yamlize import YamlizingError


MERGE_TAG = u'tag:yaml.org,2002:merge'


def _create_merge_node():
    return ruamel.yaml.ScalarNode(MERGE_TAG, '<<')


class _ParentLink(object):

    __slots__ = ('parent', 'attributes')

    def __init__(self, parent):
        self.parent = parent
        self.attributes = []

    def try_set_attr(self, obj, attribute, node):
        '''
        Attempts to set obj attribute from parent, returns True if successful,
        otherwise False.
        '''
        attr_name = attribute.name
        pp = self.parent

        get_method = None
        if hasattr(pp, attr_name):
            get_method = getattr

        elif hasattr(pp, '__contains__') and hasattr(pp, '__getitem__'):
            if attr_name in pp:
                get_method = getattr(pp.__class__, '__getitem__')

        if get_method is not None:
            self.attributes.append((attr_name, get_method))
            val = attribute.ensure_type(get_method(pp, attr_name), node)
            setattr(obj, attr_name, val)
            return True

        return False

    def is_parent(self, obj, representer, represented_attrs):
        '''Returns a list of possibly inherited attribute names.'''
        am_parent = False
        parent = self.parent
        if parent not in representer.represented_objects:
            return False

        for attr_name, get_method in self.attributes:
            try:
                if get_method(parent, attr_name) == getattr(obj, attr_name):
                    represented_attrs.add(attr_name)
                    am_parent = True
            except BaseException:
                pass

        return am_parent


class Object(Yamlizable):

    __merge_parents = None

    __complete_inheritance = False

    __attribute_order = None

    attributes = ()

    @classmethod
    def from_yaml(cls, loader, node):
        if not isinstance(node, ruamel.yaml.MappingNode):
            raise YamlizingError('Expected a mapping node', node)

        if node in loader.constructed_objects:
            return loader.constructed_objects[node]

        self = cls.__new__(cls)
        self._set_round_trip_data(node)
        self.__attribute_order = []
        loader.constructed_objects[node] = self

        self.__from_node(loader, node)

        return self

    @classmethod
    def from_yaml_key_val(cls, loader, key_node, val_node, key_name):
        complete_inheritance = False

        if val_node in loader.constructed_objects:
            if key_node in loader.constructed_objects:
                # we've constructed this object
                return loader.constructed_objects[val_node]
            else:
                # only a single merge parent!
                # something like
                #     parent: &parent
                #        ...
                #     child: *parent
                complete_inheritance = True

        attrs = cls.attributes.by_key
        self = cls.__new__(cls)
        self.__attribute_order = []

        if not complete_inheritance:
            # val_node should point to original object
            self._set_round_trip_data(val_node)
            loader.constructed_objects[val_node] = self
        else:
            self.__complete_inheritance = True
            self.__add_parent(loader, val_node)

        key_attribute = cls.attributes.by_name.get(key_name, None)

        if key_attribute is None:
            raise YamlizingError('Error parsing {}, there is no attribute '
                                 'named `{}`'
                                 .format(type(self), key_name), key_node)

        setattr(self, key_name, key_attribute.from_yaml(loader, key_node))
        self.__attribute_order.append(key_name)

        if not complete_inheritance:
            self.__from_node(loader, val_node)
        else:
            self.__apply_defaults(key_node)

        # need to do this last for some reason
        loader.constructed_objects[key_node] = self

        return self

    def __from_node(self, loader, node):
        attrs = self.attributes.by_key
        # node.value is a ordered list of keys and values
        previous_names = set(self.__attribute_order)
        for key_node, val_node in node.value:
            if key_node.tag == MERGE_TAG:
                self.__add_parent(loader, val_node)
                continue

            key = loader.construct_object(key_node)
            attribute = attrs.get(key, None)

            if attribute is None:
                raise YamlizingError('Error parsing {}, found key `{}` but '
                                     'expected any of {}'
                                     .format(type(self), key, attrs.keys()),
                                     node)

            if key in previous_names:
                raise YamlizingError('Error parsing {}, found duplicate entry '
                                     'for key `{}`'
                                     .format(type(self), key),
                                     key_node)

            value = attribute.from_yaml(loader, val_node)
            self.__attribute_order.append(attribute.name)
            setattr(self, attribute.name, value)

        self.__apply_defaults(node)

    def __add_parent(self, loader, parent_node):
        if self.__merge_parents is None:
            self.__merge_parents = list()

        self.__merge_parents.append(_ParentLink(
            loader.constructed_objects[parent_node]))

    def __apply_defaults(self, node):
        applied_attrs = set(self.__attribute_order)
        missing_required_attrs = []
        parents = self.__merge_parents or []

        for attr in self.attributes:
            if attr.name in applied_attrs:
                continue

            # DO NOT make this into a generator!!!!
            from_parent = any([parent.try_set_attr(self, attr, node)
                               for parent in parents])

            if not from_parent:
                if attr.default is not NODEFAULT:
                    setattr(self, attr.name, attr.default)
                else:
                    # hold on to a running list so user doesn't need to rerun
                    # to find //each// error, but can find all of then at once
                    missing_required_attrs.append(attr.name)

        if any(missing_required_attrs):
            raise YamlizingError('Missing {} attributes without default: {}'
                                 .format(type(self), missing_required_attrs),
                                 node)

    @classmethod
    def to_yaml(cls, dumper, self):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'
                                 .format(cls, self))

        if self in dumper.represented_objects:
            return dumper.represented_objects[self]

        node = self.__to_yaml(dumper)

        return node

    @classmethod
    def to_yaml_key_val(cls, dumper, self, key_name):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'
                                 .format(cls, self))

        if self in dumper.represented_objects:
            return dumper.represented_objects[self]

        key_attribute = cls.attributes.by_name[key_name]
        list_key_node = key_attribute.to_yaml(
            dumper, getattr(self, key_name, key_attribute.default))

        node = self.__to_yaml(dumper, key_name)

        return list_key_node, node

    def __to_yaml(self, dumper, skip_attr=None):
        represented_attrs = set([skip_attr] * (skip_attr is not None))
        parents = []

        node_items = []
        node = ruamel.yaml.MappingNode(
            ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, node_items)
        self._apply_round_trip_data(node)
        dumper.represented_objects[self] = node

        if self.__merge_parents is not None:
            remove_links = []

            if self.__complete_inheritance:
                merge_parent = self.__merge_parents[0]
                if merge_parent.is_parent(self, dumper, represented_attrs):
                    if not any(self.attributes.required - represented_attrs):
                        del dumper.represented_objects[self]
                        return dumper.represented_objects[merge_parent.parent]
                    else:
                        kn = _create_merge_node()
                        vn = dumper.represented_objects[merge_parent.parent]
                        node_items.append((kn, vn))
            else:
                for index, merge_parent in enumerate(self.__merge_parents):
                    if merge_parent.is_parent(self, dumper, represented_attrs):
                        kn = _create_merge_node()
                        vn = dumper.represented_objects[merge_parent.parent]
                        node_items.append((kn, vn))
                    else:
                        remove_links.append(index)

                for index in reversed(remove_links):
                    self.__merge_parents.pop(index)

        attrs_by_name = self.attributes.by_name
        attr_order = self.__attribute_order or []
        attr_order += sorted(set(attrs_by_name.keys()) - set(attr_order))
        list_key_node = None

        for attr_name in attr_order:
            if attr_name in represented_attrs:
                continue

            attribute = attrs_by_name[attr_name]
            attr_value = getattr(self, attr_name, attribute.default)
            val_node = attribute.to_yaml(dumper, attr_value)

            # short circuit when the value is the default
            if val_node is None:
                continue

            key_node = dumper.represent_data(attribute.key)

            node_items.append((key_node, val_node))

        return node


class NODEFAULT:

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
        self.type = Yamlizable.get_yamlizable_type(
            type) if type != NODEFAULT else Dynamic
        self.default = default

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
    def required(self):
        return {attr.name for attr in self if attr.default is NODEFAULT}

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
