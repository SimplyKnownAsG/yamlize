import ruamel.yaml
import six
import inspect

from yamlize import YamlizingError


class _AnchorNode(object):

    __slots__ = ('value', )

    def __init__(self, value):
        self.value = value


class Yamlizable(object):

    __round_trip_data = None

    @classmethod
    def get_yamlizable_type(cls, type_):
        if issubclass(type_, Yamlizable):
            return type_
        else:
            return Strong(type_)  # returns a new Strong type

    @classmethod
    def load(cls, stream, Loader=ruamel.yaml.RoundTripLoader):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
        loader = Loader(stream)
        try:
            node = loader.get_single_node()
            return cls.from_yaml(loader, node)
        finally:
            loader.dispose()

    @classmethod
    def dump(cls, data, stream=None, Dumper=ruamel.yaml.RoundTripDumper):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
        convert_to_string = stream is None
        stream = stream or six.StringIO()
        dumper = Dumper(stream)

        try:
            dumper._serializer.open()
            root_node = cls.to_yaml(dumper, data)
            dumper.serialize(root_node)
            dumper._serializer.close()
        finally:
            try:
                dumper._emitter.dispose()
            except AttributeError:
                raise
                dumper.dispose()  # cyaml

        if convert_to_string:
            return stream.getvalue()

        return None

    def _set_round_trip_data(self, node):
        self.__round_trip_data = {}

        for key in dir(node):
            if key.startswith('__') or key in {'value', 'id'}:
                continue

            attr = getattr(node, key)

            if callable(attr):
                continue

            self.__round_trip_data[key] = attr

    def _apply_round_trip_data(self, node):
        if self.__round_trip_data is None:
            return

        for key, val in self.__round_trip_data.items():
            if key == 'anchor':
                val = _AnchorNode(val)
            setattr(node, key, val)

    @classmethod
    def from_yaml(cls, loader, node):
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, dumper, self):
        raise NotImplementedError


class Dynamic(Yamlizable):

    __type = None

    __types = dict()

    def __new__(cls, value):
        type_ = type(value)

        if type_ not in cls.__types:
            # attrs = {'load': Yamlizable.load, 'dump': Yamlizable.dump,
            cls.__types[type_] = type(
                'DynamicYamlizable' + type_.__name__, (type_, Dynamic), {})
            cls.__types[type_].__type = type_

        return cls.__types[type_](value)

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_object(node, deep=True)

        try:
            data = Dynamic(data)
            data._set_round_trip_data(node)
        except BaseException:
            # ok, we couldn't coerce the type, but whatev's, it's dynamic!
            pass

        return data

    @classmethod
    def to_yaml(cls, dumper, self):
        if isinstance(self, Dynamic):
            node = dumper.yaml_representers[self.__type](dumper, self)
            self._apply_round_trip_data(node)
        elif isinstance(self, Yamlizable):
            # infinite recursion if checked first
            node = Yamlizable.to_yaml(dumper, self)
        else:
            # we've lost round trip data, but that is OK
            node = dumper.represent_data(self)

        return node


class Strong(Yamlizable):

    __type = None

    __types = {bool: bool}

    def __new__(cls, type_):
        if type_ not in cls.__types:
            # attrs = {'load': Yamlizable.load, 'dump': Yamlizable.dump,
            cls.__types[type_] = type(
                'StrongYamlizable' + type_.__name__, (type_, Strong), {})
            cls.__types[type_].__type = type_

        # gets called to create a new
        return cls.__types[type_]

    @classmethod
    def from_yaml(cls, loader, node):
        data = loader.construct_object(node, deep=True)

        if not isinstance(data, cls):
            try:
                new_value = cls(data)  # to coerce to correct type
                new_value._set_round_trip_data(node)
                loader.constructed_objects[node] = new_value
            except BaseException:
                raise YamlizingError('Failed to coerce data `{}` to type `{}`'
                                     .format(data, cls))

            if new_value != data:
                raise YamlizingError(
                    'Coerced `{}` to `{}`, but the new value `{}`'
                    ' is not equal to old `{}`.'
                    .format(type(data), type(new_value), new_value, data),
                    node)

            data = new_value

        return data

    @classmethod
    def to_yaml(cls, dumper, self):
        if not isinstance(self, (cls, cls.__type)):
            try:
                self = cls.__type(self)  # to coerce to correct type
            except BaseException:
                raise YamlizingError('Failed to coerce data `{}` to type `{}`'
                                     .format(self, cls))

        node = dumper.yaml_representers[cls.__type](dumper, self)

        # it is possible that it is the base type (int, str, etc.) and not
        # Yamlizable
        if isinstance(self, Yamlizable):
            self._apply_round_trip_data(node)

        return node

