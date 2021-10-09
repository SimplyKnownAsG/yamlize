import ruamel.yaml
import inspect
import io

from yamlize.round_trip_data import RoundTripData
from yamlize.yamlizing_error import YamlizingError


class Yamlizable(object):

    __slots__ = ()

    def __getstate__(self):
        state = {}

        if hasattr(self, "__dict__"):
            state.update(self.__dict__)

        applied_slots = set((None,))  # populated with None

        for cls in reversed(type(self).__mro__):
            cls_slots = getattr(cls, "__slots__", None)

            if cls_slots in applied_slots:
                continue

            applied_slots.add(cls_slots)

            for attr_name in cls_slots:
                if attr_name.startswith("__"):
                    attr_name = "_{}{}".format(cls.__name__, attr_name)
                    while attr_name.startswith("__"):
                        attr_name = attr_name[1:]

                if attr_name in state:
                    continue

                state[attr_name] = getattr(self, attr_name)

        return state

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)

    @classmethod
    def load(cls, stream, Loader=ruamel.yaml.RoundTripLoader):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
        loader = Loader(stream)
        try:
            node = loader.get_single_node()
            return cls.from_yaml(loader, node, None)
        finally:
            loader.dispose()

    @classmethod
    def dump(cls, data, stream=None, Dumper=ruamel.yaml.RoundTripDumper):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
        convert_to_yaml = stream is None
        stream = stream or io.StringIO()
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

        if convert_to_yaml:
            return stream.getvalue()

        return None

    @classmethod
    def from_yaml(cls, loader, node, round_trip_data):
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, dumper, self, round_trip_data):
        raise NotImplementedError


class Typed(type):

    __types = {}

    def __new__(mcls, type_, from_yaml=None, to_yaml=None, compare_after_cast=True):
        if issubclass(type_, Yamlizable):
            return type_

        if type_ not in mcls.__types:
            mcls.__types[type_] = type(
                "Yamlizable" + type_.__name__,
                (Strong,),
                {
                    "_Strong__type": type_,
                    "_Strong__from_yaml": staticmethod(from_yaml),
                    "_Strong__to_yaml": staticmethod(to_yaml),
                    "_Strong__compare_after_cast": compare_after_cast,
                },
            )
        return mcls.__types[type_]


class Strong(Yamlizable):
    """
    The Strongly typed Yamlizable subclass. Subclasses of Strong are dynamically created on demand
    when someone creates an Attribute with ``type=sometype``.

    Note that there may never be an instance of a Strongint. If there were, it would actually get
    more complicated because we currently rely upon ``ruamel.yaml`` to give us rational representers
    and composers. If an ``int`` was cast to a ``Strongint``, then we would need to add a
    representer into the ``ruamel.yaml.Dumper``.
    """

    __slots__ = ()

    __type = None

    __from_yaml = None

    __to_yaml = None

    __compare_after_cast = None

    def __new__(cls, obj):
        # this is really only ever called to cast an object that is not the correct type to the
        # correct type. We generally assume that the correct type is the Strong subclass, but as
        # stated above, it is easier to keep data as primitives.
        if isinstance(obj, (cls, cls.__type)):
            return obj

        return cls.__type(obj)

    @classmethod
    def from_yaml(cls, loader, node, round_trip_data):
        if cls.__from_yaml is not None:
            data = cls.__from_yaml.__call__(loader, node, round_trip_data)
        else:
            data = loader.construct_object(node, deep=True)

        if not isinstance(data, cls.__type):
            try:
                new_value = cls.__type(data)  # to coerce to correct type
            except Exception:
                raise YamlizingError(
                    "Failed to coerce data `{}` to type `{}`".format(data, cls.__type)
                )

            if cls.__compare_after_cast:
                if new_value != data:
                    # common case for Attribute(type=str, default=None) ... str(None) != 'None'
                    raise YamlizingError(
                        "Coerced `{}` to `{}`, but the new value `{}` is not equal to old `{}`."
                        .format(type(data), type(new_value), new_value, data),
                        node,
                    )

            data = new_value

        round_trip_data[data] = RoundTripData(node)
        return data

    @classmethod
    def to_yaml(cls, dumper, data, round_trip_data):
        if not isinstance(data, cls.__type) or (
            cls.__type in (int, float, bool) and cls.__type != type(data)
        ):
            try:
                new_value = cls.__type(data)  # to coerce to correct type
            except Exception:
                raise YamlizingError(
                    "Failed to coerce data `{}` to type `{}`".format(data, cls)
                )

            if cls.__compare_after_cast:
                try:
                    if new_value == data:
                        data = new_value
                except Exception:
                    pass

        if cls.__to_yaml is not None:
            node = cls.__to_yaml.__call__(dumper, data, round_trip_data)
        else:
            node = dumper.represent_data(
                data if cls.__to_yaml is None else cls.__to_yaml(data)
            )

        round_trip_data[data].apply(node)
        return node


Dynamic = Typed(object)
