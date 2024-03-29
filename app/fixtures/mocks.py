# Mock the soap client
import os
import pprint
import re
from types import FunctionType, LambdaType
from typing import List, Tuple, Union
from unittest.mock import Mock
from lxml import etree

from app.config import BASE_PATH

pp = pprint.PrettyPrinter(indent=4)

FIXTURES_PATH = os.path.join(BASE_PATH, "fixtures")

# From https://github.com/CRiva/lxml_to_dict
# modified slightly
def lxml_to_dict(element):
    ret = {}
    if element.getchildren() == []:
        tag = re.sub("{.*}", "", element.tag)
        value = element.text

        if value == "false":
            value = False
        elif value == "true":
            value = True

        ret[tag] = value
    else:
        for elem in element.getchildren():
            subdict = lxml_to_dict(elem)
            tag = re.sub("{.*}", "", element.tag)
            subtag = re.sub("{.*}", "", elem.tag)

            if ret.get(tag, False) and subtag in ret[tag].keys():
                # Element tag.subtag is encoutered again, it must be an array
                if isinstance(ret[tag][subtag], dict):
                    ret[tag][subtag] = [ret[tag][subtag]]

                ret[tag][subtag].append(subdict[subtag])
            else:
                if ret.get(tag, False):
                    ret[tag].update(subdict)
                else:
                    ret[tag] = subdict
    return ret


def load_xml(xml):
    parser = etree.XMLParser(
        remove_blank_text=True, remove_comments=True, resolve_entities=False
    )
    return etree.fromstring(xml.strip(), parser=parser)


def load_response_file(service_name: str, method_name: str):
    file_name = os.path.join(FIXTURES_PATH, f"{service_name}.{method_name}.xml")
    with open(file_name) as fp:
        return bytes(fp.read(), encoding="utf8")


class MockService:
    def __init__(
        self,
        service_name: str,
        method_names: List[Union[str, Tuple[str, FunctionType]]],
    ):
        for method_name in method_names:
            response_handler = None

            if isinstance(method_name, tuple):
                (method_name_unpacked, response_handler_unpacked) = method_name
                response_handler = response_handler_unpacked
                method_name = method_name_unpacked
            else:
                response_handler = self.response_fixture(service_name, method_name)

            setattr(self, method_name, response_handler)

    def response_fixture(self, service_name: str, method_name: str, *args, **kwargs):
        def r(*args, **kwargs):
            response_dict = lxml_to_dict(
                load_xml(load_response_file(service_name, method_name))
            )
            response = {
                "body": response_dict["Envelope"]["Body"][
                    f"{service_name}___{method_name}Response"
                ]
            }

            return response

        return r


class MockElement:
    args = []

    def __init__(self, *args, **kwargs):
        self.args = args
        for a in kwargs:
            self.__setattr__(a, kwargs[a])


class MockClient:
    service = None
    args = []

    def __init__(
        self,
        service_name: str,
        method_names: List[Union[str, Tuple[str, FunctionType]]],
    ):
        self.service = MockService(service_name, method_names)

    def get_element(self, el_name: str, *args):
        return MockElement

    def get_type(self, el_name: str, *args):
        return MockElement


def mock_client(
    service_name: str, method_names: List[Union[str, Tuple[str, FunctionType]]]
):
    return {service_name: MockClient(service_name, method_names)}


def mock_clients(
    operations: List[Tuple[str, List[Union[str, Tuple[str, FunctionType]]]]]
):
    mocked_services = {}
    for (service_name, method_names) in operations:
        mocked_services.update(mock_client(service_name, method_names))
    return mocked_services


# def mock_soap_response(file_name: str):
#     def response(*args):
#         r = Response()
#         print("\n\n\n\n", "YEAS", "\n\n\n\n")
#         r.headers.setdefault("Content-type", "text/xml")
#         r.status_code = 200
#         response_content = load_fixture_as_bytes(file_name)
#         type(r).content = mock.PropertyMock(return_value=response_content)

#         return r

#     return response
