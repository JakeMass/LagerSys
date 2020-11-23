import xml.etree.ElementTree as ET

# Some decorators
def is_attrib(func):
    def check(article, *args):
        if args[0] in article.attrib_dict:
            return func(article, *args)
        else:
            return None
    return check


class Article:
    def __init__(self, file_path, file_tree, ui, attrib_dict, xml_elem=None):
        self.ui = ui
        self.attrib_dict = attrib_dict
        self.file_path = file_path
        self.file_tree = file_tree
        self.amount = 0
        if xml_elem is None:
            self.xml_elem = self.make_xml_elem(file_path, file_tree)
        else:
            self.xml_elem = xml_elem

    def make_xml_elem(self, file_tree):
        xml_elem = ET.SubElement(file_tree.getroot(), 'article', self.attrib_dict)
        self.write_file()
        return xml_elem

    @is_attrib
    def get(self, attrib):
        return self.attrib_dict[attrib]

    @is_attrib
    def change(self, attrib, new_value):
        self.attrib_dict[attrib] = new_value
        self.xml_elem.set(attrib, new_value)
        self.write_file()

    def get_amount(self):
        return self.amount

    def attrib_list(self):
        return list(self.attrib_dict.values())

    def attribs(self):
        return list(self.attrib_dict.keys())

    def write_file(self):
        self.file_tree.write(self.file_path)
