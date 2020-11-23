import xml.etree.ElementTree as ET
from datetime import date

class Stock:
    def __init__(self, file_path, name):
        self.file_path = file_path
        self.file_tree = ET.parse(self.file_path)
        self.file_root = self.file_tree.getroot()
        self.name = name
        self.header_begin = ['ui']
        self.header_end = ['bin', 'anzahl', 'datum']
        self.chest_dict = {}

    def make_chest_dict(self, article_dict):
        for entry in self.file_root:
            articlenr = entry.get('article')
            if articlenr == '':
                self.add_chest(entry.get('ui'), None, xml_elem=entry)
            else:
                self.add_chest(
                    entry.get('ui'),
                    article_dict[articlenr],
                    xml_elem=entry
                    )

    def add_chest(self, ui, article, amount=0, xml_elem=None):
        if ui not in self.chest_dict.keys():
            chest = Chest(self, ui, article, str(amount), xml_elem)
            self.chest_dict[ui] = chest
            self.write_file()
        else:
            print('UI already taken.')

    def change_chest(self, ui, attrib_dict, article_dict):
        chest = self.chest_dict[ui]
        for attrib in attrib_dict:
            if attrib_dict[attrib] != '':
                if attrib == 'amount':
                    chest.set_amount(attrib_dict[attrib])
                elif attrib == 'article':
                    if attrib_dict[attrib] != chest.get_article_ui():
                        chest.change_article(article_dict[attrib_dict[attrib]])
                elif attrib == 'bin':
                    if attrib_dict[attrib] != chest.bin:
                        chest.set_bin(attrib_dict[attrib])

    def remove_chest(self, chest):
        self.file_root.remove(chest.xml_elem)
        self.chest_dict.pop(chest.ui)
        self.write_file()

    def remove(self, ui):
        self.remove_chest(self.chest_dict[ui])

    def write_file(self):
        self.file_tree.write(self.file_path)

    def search(self, attrib, search_values):
        chest_list = []
        if attrib == 'ui':
            for value in search_values:
                if value in self.chest_dict.keys():
                    chest_list.append(self.chest_dict[value])
        elif attrib == 'bin':
            for chest in self.chest_dict.values():
                for value in search_values:
                    if value in chest.bin:
                        chest_list.append(chest)
        elif attrib == 'anzahl':
            for chest in self.chest_dict.values():
                for value in search_values:
                    if value >= chest.amount and chest.article is not None:
                        chest_list.append(chest)
        else:
            for chest in self.chest_dict.values():
                article_attrib = chest.get_article_attrib(attrib)
                if article_attrib is not None:
                    for value in search_values:
                        if value in article_attrib:
                            chest_list.append(chest)
        return chest_list

    def get_filtered_list(self, attrib, search_value, d_attribs):
        chest_list = self.search(attrib, search_value)
        stock_list_header = [[self.header_begin + d_attribs + self.header_end]]
        return stock_list_header + sorted(self.get_article_attribs(d_attribs, list_=chest_list))

    def stock_list(self, d_attribs):
        stock_list_header = [self.header_begin + d_attribs + self.header_end]
        return stock_list_header + sorted(self.get_article_attribs(d_attribs))

    def get_article_attribs(self, d_attribs, list_=None):
        attribs = []

        if list_ is None:
            chest_list = list(self.chest_dict.values())
        else:
            chest_list = list_

        for chest in chest_list:
            c_list = [chest.ui]
            for attrib in d_attribs:
                c_list.append(chest.get_article_attrib(attrib))
            c_list.append(chest.bin)
            c_list.append(chest.amount)
            c_list.append(chest.date)
            attribs.append(c_list)

        return attribs

    def get_chest_uis(self, articlenr):
        ui_string = ''
        for chest in self.chest_dict.values():
            if chest.get_article_ui() == articlenr:
                ui_string += f'{chest.ui} '
        return ui_string




class Chest:
    def __init__(self, stock, ui, article, amount, xml_elem):
        self.stock = stock
        self.ui = ui
        self.article = article
        self.amount = amount
        if xml_elem is None:
            self.xml_elem = ET.SubElement(
                self.stock.file_root,
                'chest',
                attrib={'ui': self.ui}
                )
            if article is None:
                self.xml_elem.set('article', '')
            else:
                self.xml_elem.set('article', article.get(article.ui))
            self.xml_elem.set('amount', self.amount)
            self.bin = ''
        else:
            self.xml_elem = xml_elem
            self.amount = xml_elem.get('amount')
            if 'bin' in self.xml_elem.attrib:
                self.bin = self.xml_elem.get('bin')
            else:
                self.bin = ''
        self.date = self.xml_elem.get('date')

    def get_article_attrib(self, attrib):
        if self.article is None:
            return ''
        return self.article.get(attrib)

    def get_article_ui(self):
        if self.article is None:
            return ''
        return self.article.get(self.article.ui)

    def change_article(self, article):
        self.article = article
        self.xml_elem.set('article', article.get(article.ui))
        self.stock.write_file()

    def set_amount(self, value=0):
        self.amount = value
        self.date = date.today().strftime('%d.%m.%Y')
        self.xml_elem.set('amount', self.amount)
        self.xml_elem.set('date', self.date)
        self.stock.write_file()

    def set_bin(self, value):
        self.bin = value
        self.date = date.today().strftime('%d.%m.%Y')
        self.xml_elem.set('bin', self.bin)
        self.xml_elem.set('date', self.date)
        self.stock.write_file()
