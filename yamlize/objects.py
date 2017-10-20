import inspect

import ruamel.yaml

from yamlize.yamlizable import Yamlizable, Dynamic
from yamlize import YamlizingError


MERGE_TAG = u'tag:yaml.org,2002:merge'


def _create_merge_node():
    return ruamel.yaml.ScalarNode(MERGE_TAG, '<<')


class _AliasLink(object):

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
            self.attributes.append((attribute, get_method))
            val = attribute.ensure_type(get_method(pp, attr_name), node)
            setattr(obj, attr_name, val)
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
                if get_method(parent, attr.name) == attr.get_value(obj):
                    represented_attrs.add(attr)
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

        key_attribute.from_yaml(self, loader, key_node)
        self.__attribute_order.append(key_attribute)

        if not complete_inheritance:
            self.__from_node(loader, val_node)
        else:
            self.__apply_defaults(key_node)

        # need to do this last for some reason
        loader.constructed_objects[key_node] = self

        return self

    def __from_node(self, loader, node):
        attrs = self.attributes
        # node.value is a ordered list of keys and values
        previous_attrs = set(self.__attribute_order)
        for key_node, val_node in node.value:
            if key_node.tag == MERGE_TAG:
                self.__add_parent(loader, val_node)
                continue

            attribute = attrs.from_yaml(self, loader, key_node, val_node)

            if attribute in previous_attrs:
                raise YamlizingError('Error parsing {}, found duplicate entry '
                                     'for key `{}`'
                                     .format(type(self), attribute.key),
                                     key_node)

            previous_attrs.add(attribute)
            self.__attribute_order.append(attribute)

        self.__apply_defaults(node)

    def __add_parent(self, loader, parent_node):
        if self.__merge_parents is None:
            self.__merge_parents = list()

        self.__merge_parents.append(_AliasLink(
            loader.constructed_objects[parent_node]))

    def __apply_defaults(self, node):
        applied_attrs = set(self.__attribute_order)
        missing_required_attrs = []
        parents = self.__merge_parents or []

        for attribute in self.attributes:
            if attribute in applied_attrs:
                continue

            # DO NOT make this into a generator!!!!
            from_parent = any([parent.try_set_attr(self, attribute, node)
                               for parent in parents])

            if not from_parent:
                if attribute.has_default:
                    attribute.set_value(self, attribute.default)
                else:
                    # hold on to a running list so user doesn't need to rerun
                    # to find //each// error, but can find all of then at once
                    missing_required_attrs.append(attribute.name)

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
        list_key_node = key_attribute.to_yaml(self, dumper)

        node = self.__to_yaml(dumper, key_attribute)

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
            if self.__complete_inheritance:
                merge_parent = self.__merge_parents[0]
                if merge_parent.is_parent(self, dumper, represented_attrs):
                    if not any(set(self.attributes.required) - represented_attrs):
                        del dumper.represented_objects[self]
                        return dumper.represented_objects[merge_parent.parent]
                    else:
                        kn = _create_merge_node()
                        vn = dumper.represented_objects[merge_parent.parent]
                        node_items.append((kn, vn))
            else:
                remove_links = []

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
        # add the rest in order of definition
        attr_order += [attr for attr in self.attributes if attr not in attr_order]

        for attribute in attr_order:
            if attribute in represented_attrs:
                continue

            val_node = attribute.to_yaml(self, dumper)

            # short circuit when the value is the default
            if val_node is None:
                continue

            key_node = dumper.represent_data(attribute.key)

            node_items.append((key_node, val_node))

        return node


