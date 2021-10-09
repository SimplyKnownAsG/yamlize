import inspect

import ruamel.yaml

from .yamlizable import Yamlizable
from .yamlizing_error import YamlizingError
from .round_trip_data import RoundTripData


MERGE_TAG = u'tag:yaml.org,2002:merge'


def _create_merge_node():
    return ruamel.yaml.ScalarNode(MERGE_TAG, '<<')


class _AliasLink(object):

    __slots__ = ('parent', 'attributes')

    def __init__(self, parent):
        self.parent = parent
        self.attributes = []

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        self.__init__(state)

    def __repr__(self):
        return '<AliasLink to {}>'.format(self.parent)

    def try_set_attr(self, obj, attribute, node):
        '''
        Attempts to set obj attribute from parent, returns True if successful,
        otherwise False.
        '''
        get_method = attribute.get_value

        if get_method is not None:
            self.attributes.append((attribute, get_method))
            val = get_method(self.parent)
            attribute.set_value(obj, val)
            return True

        return False

    def is_parent(self, obj, representer, represented_attrs):
        '''Returns a list of possibly inherited attribute names.'''
        parent = self.parent

        if parent not in representer.represented_objects:
            return False

        am_parent = False

        for attr, get_method in self.attributes:
            try:
                if get_method(parent) == attr.get_value(obj):
                    represented_attrs.add(attr)
                    am_parent = True
            except BaseException:
                pass

        return am_parent


class ObjectType(type):

    def __init__(cls, name, bases, data):
        from yamlize.attribute_collection import AttributeCollection
        from yamlize.attributes import Attribute

        type.__init__(cls, name, bases, data)

        attributes = data.get('attributes')
        if attributes is None:
            attributes = AttributeCollection()

        elif not isinstance(attributes, AttributeCollection):
            attributes = AttributeCollection(*attributes)

        # not sure why I couldn't just overwrite data['attributes'], but it did not work
        cls.attributes = attributes

        for attr_name, attr_val in data.items():
            if isinstance(attr_val, Attribute) and attr_val.name is None:
                attr_val.name = attr_name
                attributes.add(attr_val)

        for attribute in attributes:
            if not hasattr(cls, attribute.name):
                setattr(cls, attribute.name, attribute)

        for parent_cls in cls.__mro__[1:]:
            if hasattr(parent_cls, 'attributes'):
                for attribute in parent_cls.attributes:
                    setattr(cls, attribute.name, attribute)

    def __setattr__(cls, attr_name, value):
        from yamlize.attributes import Attribute
        type.__setattr__(cls, attr_name, value)

        if isinstance(value, Attribute):
            cls.attributes.add(value)


class Object(Yamlizable, metaclass=ObjectType):

    __slots__ = ('__round_trip_data',)

    attributes = ()

    def __new__(cls, *args, **kwargs):
        self = Yamlizable.__new__(cls)
        self.__round_trip_data = RoundTripData(None)
        return self

    @property
    def __attribute_order(self):
        if self.__round_trip_data is None:
            return ()
        if self.__round_trip_data._name_order is None:
            return ()
        else:
            return [self.attributes.by_name[n] for n in self.__round_trip_data._name_order]

    @classmethod
    def from_yaml(cls, loader, node, _rtd=None):
        if not isinstance(node, ruamel.yaml.MappingNode):
            raise YamlizingError('Expected a mapping node', node)

        if node in loader.constructed_objects:
            return loader.constructed_objects[node]

        self = cls.__new__(cls)
        self.__round_trip_data = RoundTripData(node)
        loader.constructed_objects[node] = self
        self.__from_node(loader, node)

        return self

    @classmethod
    def from_yaml_key_val(cls, loader, key_node, val_node, key_attribute, _rtd=None):
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

        self = cls.__new__(cls)

        if not complete_inheritance:
            # val_node should point to original object
            self.__round_trip_data = RoundTripData(val_node)
            loader.constructed_objects[val_node] = self
        else:
            self.__round_trip_data._complete_inheritance = True
            self.__add_parent(loader, val_node)

        key_attribute.from_yaml(self, loader, key_node, self.__round_trip_data)
        # loader.constructed_objects[key_node] = self
        self.__round_trip_data._name_order.append(key_attribute.name)

        if not complete_inheritance:
            self.__from_node(loader, val_node)
        else:
            self.__apply_defaults(key_node)

        return self

    def __from_node(self, loader, node):
        attrs = self.attributes
        # node.value is a ordered list of keys and values
        previous_attrs = set(self.__attribute_order)
        for key_node, val_node in node.value:
            if key_node.tag == MERGE_TAG:
                self.__add_parent(loader, val_node)
                continue

            attribute = attrs.from_yaml(self, loader, key_node, val_node, self.__round_trip_data)

            if attribute is None:
                continue

            if attribute in previous_attrs:
                raise YamlizingError('Error parsing {}, found duplicate entry '
                                     'for key `{}`'
                                     .format(type(self), attribute.key),
                                     key_node)

            previous_attrs.add(attribute)
            self.__round_trip_data._name_order.append(attribute.name)

        self.__apply_defaults(node)

    def __add_parent(self, loader, parent_node):
        self.__round_trip_data._merge_parents.append(
            _AliasLink(loader.constructed_objects[parent_node]))

    def __apply_defaults(self, node):
        applied_attrs = set(self.__attribute_order)
        missing_required_attrs = self.attributes.required - applied_attrs
        links = self.__round_trip_data._merge_parents or []

        # using a separate set allows us to inherit the last value from
        # multiple parents
        inherited_attrs = set()

        for link in links:
            # TODO: why does this happen? inherit from Dynamic?
            lp = link.parent
            if not hasattr(lp, 'attributes'):
                continue

            for attribute in link.parent.attributes.yaml_attribute_order(
                    link.parent, []):
                if attribute in applied_attrs:
                    continue

                if link.try_set_attr(self, attribute, node):
                    inherited_attrs.add(attribute)

        # now apply defaults, where available
        applied_attrs |= inherited_attrs
        missing_required_attrs = list()

        for attribute in self.attributes:
            if attribute in applied_attrs:
                continue

            if attribute.is_required:
                # hold on to a running list so user doesn't need to rerun
                # to find //each// error, but can find all of then at once
                missing_required_attrs.append(attribute.name)

        if any(missing_required_attrs):
            raise YamlizingError('Missing {} attributes without default: {}'
                                 .format(type(self), missing_required_attrs),
                                 node)

    @classmethod
    def to_yaml(cls, dumper, self, _rtd=None):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'
                                 .format(cls, self))

        if self in dumper.represented_objects:
            return dumper.represented_objects[self]

        node = self.__to_yaml(dumper)

        return node

    @classmethod
    def to_yaml_key_val(cls, dumper, self, key_attribute, _rtd=None):
        if not isinstance(self, cls):
            raise YamlizingError('Expected instance of {}, got: {}'
                                 .format(cls, self))

        items = []
        key_attribute.to_yaml(self, dumper, items, self.__round_trip_data)

        if self in dumper.represented_objects:
            return items[0][1], dumper.represented_objects[self]

        node = self.__to_yaml(dumper, key_attribute)

        return items[0][1], node

    def __to_yaml(self, dumper, skip_attr=None):
        represented_attrs = set([skip_attr] * (skip_attr is not None))
        parents = []

        node_items = []
        node = ruamel.yaml.MappingNode(
            ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, node_items)
        self.__round_trip_data.apply(node)
        dumper.represented_objects[self] = node

        attr_order = self.attributes.attr_dump_order(
            self,
            self.__attribute_order
        )

        if self.__round_trip_data._merge_parents is not None:
            actual_parents = []

            for merge_parent in self.__round_trip_data._merge_parents:
                if merge_parent.is_parent(self, dumper, represented_attrs):
                    actual_parents.append(merge_parent)

            # this is now *an_alias_to_another_node
            if len(actual_parents) == 1 and not any(
                    set(attr_order) - represented_attrs):
                del dumper.represented_objects[self]
                return dumper.represented_objects[merge_parent.parent]

            # add <<: *merge_parent0, <<: *merge_parent1, ...
            for merge_parent in actual_parents:
                kn = _create_merge_node()
                vn = dumper.represented_objects[merge_parent.parent]
                node_items.append((kn, vn))

        for attribute in attr_order:
            if attribute in represented_attrs:
                continue

            attribute.to_yaml(self, dumper, node_items, self.__round_trip_data)

        return node

