import ipaddress
import re

import arrow
import arrow.parser
from schematics.exceptions import ConversionError, ValidationError
from schematics.types import BaseType, StringType


class KubeName(StringType):

    def __init__(self, **kwargs):
        super().__init__(max_length=63, **kwargs)
        self.k8s_reg = re.compile('[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*')

    def validate_kube(self, value, context=None):
        if self.k8s_reg.match(value) is None:
            raise ValidationError("must consist of lower case alphanumeric characters, '-' or '.', and must start and "
                                  "end with an alphanumeric character (e.g. 'example.com', regex used for validation "
                                  "is '[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*')")


class KubeString(StringType):
    def __init__(self, **kwargs):
        super().__init__(max_length=63, **kwargs)
        self.k8s_reg = re.compile('[a-z0-9A-Z.\-_]')

    def validate_kube(self, value, context=None):
        if self.k8s_reg.match(value) is None:
            raise ValidationError("must consist of alphanumeric characters, '_', '-' or '.' "
                                  "(regex used for validation is '[a-z0-9A-Z.\-_]')")


class ArrowType(BaseType):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_native(self, value, context=None):
        if not isinstance(value, arrow.Arrow):
            try:
                value = arrow.get(value)
            except arrow.parser.ParserError:
                raise ConversionError('Could not parse %s. Should be ISO 8601.' % value)
        return value

    def to_primitive(self, value, context=None):
        return value.isoformat()


class EnumType(BaseType):
    def __init__(self, enum_class, **kwargs):
        self.enum_class = enum_class
        super().__init__(**kwargs)

    def to_native(self, value, context=None):
        if not isinstance(value, self.enum_class):
            try:
                value = self.enum_class(value)
            except ValueError as e:
                raise ConversionError(e.__str__())

        return value

    def to_primitive(self, value, context=None):
        return value.value


class IPv4AddressType(BaseType):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_native(self, value, context=None):
        if not isinstance(value, ipaddress.IPv4Address):
            try:
                value = ipaddress.IPv4Address(value)
            except ValueError as e:
                raise ConversionError(e.__str__())

        if value.is_multicast:
            raise ConversionError("Cannot use a multicast (RFC 3171) IPv4 Address")

        if value.is_unspecified:
            raise ConversionError("Cannot use an unspecified (RFC 5735) IPv4 Address")

        if value.is_reserved:
            raise ConversionError("Cannot use a reserved (IETF reserved) IPv4 Address")

        if value.is_loopback:
            raise ConversionError("Cannot use a loopback (RFC 3330) IPv4 Address")

        if value.is_link_local:
            raise ConversionError("Cannot use a link local (RFC 3927) IPv4 Address")

        return value

    def to_primitive(self, value, context=None):
        return str(value)


class IPv4NetworkType(BaseType):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_native(self, value, context=None):
        if not isinstance(value, ipaddress.IPv4Network):
            try:
                value = ipaddress.IPv4Network(value)
            except ValueError as e:
                raise ConversionError(e.__str__())

        if value.is_multicast:
            raise ConversionError("Cannot use a multicast (RFC 3171) IPv4 Address")

        if value.is_unspecified:
            raise ConversionError("Cannot use an unspecified (RFC 5735) IPv4 Address")

        if value.is_reserved:
            raise ConversionError("Cannot use a reserved (IETF reserved) IPv4 Address")

        if value.is_loopback:
            raise ConversionError("Cannot use a loopback (RFC 3330) IPv4 Address")

        if value.is_link_local:
            raise ConversionError("Cannot use a link local (RFC 3927) IPv4 Address")

        return value

    def to_primitive(self, value, context=None):
        return str(value)
