from artikel import Article
from stock import Stock
from datetime import date, datetime
import os
import xml.etree.ElementTree as ET
import PySimpleGUI as sg
import cv2 as cv
import pyzbar.pyzbar as pz
import pdfkit
import json
import requests
from requests.auth import HTTPDigestAuth


def make_articles(file_path, file_tree):
    file_root = file_tree.getroot()
    article_dict = {}
    for entry in file_root:
        article = Article(file_path, file_tree, 'artikelnr', entry.attrib, xml_elem=entry)
        article_dict[article.get(article.ui)] = article
    return article_dict


def make_stocks(dir_path):
    stocks = {}
    for file_name in os.listdir(dir_path):
        stock_name = file_name.split('.')[0]
        stocks[stock_name] = Stock(dir_path + file_name, stock_name)
    return stocks


def make_history_file():
    file_name = 'history_' + date.today().strftime('%d.%m.%y') + '.xml'
    file_path = 'data/xml/histories/' + file_name

    if not os.path.exists(file_path):
        root = ET.Element('root')
        tree = ET.ElementTree(root)
        tree.write(file_path)

    file_tree = ET.parse(file_path)

    return file_path, file_tree


def make_history_list():
    dir_path = 'data/xml/histories/'
    output = [['datum', 'zeit', 'aktion', 'ui', 'attrib', 'alt', 'neu', 'info']]
    for file_name in os.listdir(dir_path):
        root = ET.parse(dir_path + file_name).getroot()
        for entry in root:
            tmp_list = list(entry.attrib.values())
            print(tmp_list)
            output.append(tmp_list)
    return [output.pop(0)] + sorted(output, key=lambda date: datetime.strptime(date[0], '%d.%m.%y'), reverse=True)


def export_stocks_to_pdf(def_dattribs):

    for stock in stocks.values():
        html_string = '<table style="border:1px solid black">'
        stock_list = stock.stock_list(def_dattribs)
        html_string += '<tr>'

        for header in stock_list[0]:
            html_string += f'<th style="border:1px solid black; border-collapse: collapse">{header}</th>'

        html_string += '</tr>'
        stock_list.pop(0)

        for data in stock_list:
            html_string += '<tr>'
            for entry in data:
                html_string += f'<td style="border:1px solid black; border-collapse: collapse">{entry}</td>'
            html_string += '</tr>'

        html_string += '</table>'

        pdfkit.from_string(html_string, f'data/PDF Export/{stock.name}.pdf')



def find_article_ean(ean_code):
    for article in article_dict.values():
        if article.get('ean') == ean_code:
            return article
    return None

def find_chestqr(qr_code):
    for stock in stocks.values():
        for chest in stock.chest_dict.values():
            if chest.ui == qr_code:
                return chest
    return None


def barcode_scanner(ret_type='all'):
    vidFile = cv.VideoCapture(0)
    ean_code = 0
    for _ in range(100):
        ret, frame = vidFile.read()
        #cv.imshow('t', frame)
        ean_codes = pz.decode(frame)

        if len(ean_codes) > 0:
            ean_code = ean_codes[0].data.decode('UTF-8')

        if ret_type == 'all':
            article = find_article_ean(ean_code)
            chest = find_chestqr(ean_code)

            if article is not None:
                return 'article', article
            elif chest is not None:
                return 'chest', chest
        elif ret_type == 'article':
            article = find_article_ean(ean_code)
            if article is not None:
                return 'article', article
        elif ret_type == 'chest':
            chest = find_chestqr(ean_code)
            if chest is not None:
                return 'chest', chest
    return None, None


def get_orders():
    shop_url = 'BASE_SHOP_URL'
    api_base_url = f'{shop_url}PATH_TO_API_ACCESS'
    orders_url = f'{api_base_url}PATH_TO_ORDER_ACCESS'

    username = 'USERNAME'
    api_key = 'API_KEY'

    api_login = requests.get(orders_url, auth=HTTPDigestAuth(username, api_key))
    print(api_login.json())
    dict_data = api_login.json()['data']
    order_list_header = ['Datum', 'Kundenemail', 'Artikelnr', 'Anzahl', 'UI']
    order_list = [order_list_header]

    for order in dict_data:
        if order["orderStatusId"] == 0:
            r_order = requests.get(orders_url + str(order["id"]), auth=HTTPDigestAuth(username, api_key)).json()[
                'data']
            for i in range(len(r_order['details'])):
                temp_list = []
                temp_list.append(r_order['orderTime'].split('T')[0])
                temp_list.append(order["customer"]["email"])
                articlenr = r_order['details'][i]['articleNumber'].split('.')[0]
                temp_list.append(articlenr)
                temp_list.append(r_order['details'][i]['quantity'])

                chest_string = ''
                for stock in stocks.values():
                    chest_string += stock.get_chest_uis(articlenr)

                temp_list.append(chest_string)
                order_list.append(temp_list)

    if len(order_list) > 1:
        return order_list
    else:
        return order_list + ['Keine neuen Bestellungen']


def write_history(action, attrib, old_value, new_value, article=None, chest=None, add_info=''):
    history_attribs = {
        'datum': date.today().strftime('%d.%m.%y'),
        'zeit': datetime.now().strftime('%H:%M:%S'),
        'aktion': action,
        'ui': '',
        'attrib': attrib,
        'alt': old_value,
        'neu': new_value,
        'info': add_info
    }

    if article is None:
        history_attribs['ui'] = chest.ui
    else:
        history_attribs['ui'] = article.get(article.ui)

    ET.SubElement(h_file_root, 'action', history_attribs)
    h_file_tree.write(h_file_path)


def parse_input(input):
    values = input.split(':')
    attrib = values[0]
    values = values[1].split(',')
    return attrib, values


def find_article_list(dict, value):
    output = []
    for key in dict.keys():
        if value in key:
            tmp_list = dict[key].attrib_list()
            tmp_list.append(str(dict[key].amount))
            output.append(tmp_list)
    return sorted(output)


def make_displayable_list(dict):
    data = []
    header = [None]
    for elem in dict.values():
        if header[0] == None:
            header[0] = elem.attribs()
            header[0].append('anzahl')
        tmp_list = elem.attrib_list()
        tmp_list.append(str(elem.amount))
        data.append(tmp_list)
    return sorted(data), header[0]


def make_attrib_layout(attribs):
    print(attribs)
    label_layout = []
    input_layout = []
    for attrib in attribs:
        label_layout.append([sg.Text(attrib)])
        input_layout.append([sg.Input(key=attrib + '_input')])
    label_frame = sg.Frame('Label', label_layout)
    input_frame = sg.Frame('Input', input_layout)
    row = [label_frame, input_frame]
    return row


def order_menu():
    window_title = 'Bestellungen'
    order_table_data = get_orders()
    order_table_header = order_table_data.pop(0)
    table_layout_row = [sg.Table(
        values=order_table_data,
        headings=order_table_header,
        max_col_width=300,
        def_col_width=10,
        auto_size_columns=True,
        justification='left',
        num_rows=30,  # min(len(stock_table_data), 20),
        vertical_scroll_only=False,
        key='order_table'
    )]

    layout = [table_layout_row]
    window = sg.Window(window_title, layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
    window.close()


def history_menu():
    window_title = 'Ereignisse'
    history_table_data = make_history_list()
    history_table_header = history_table_data.pop(0)

    history_layout_row = [sg.Table(
        values=history_table_data,
        headings=history_table_header,
        max_col_width=300,
        def_col_width=10,
        auto_size_columns=False,
        justification='left',
        num_rows=30,  # min(len(stock_table_data), 20),
        vertical_scroll_only=False,
        key='order_table'
    )]

    layout = [history_layout_row]
    window = sg.Window(window_title, layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
    window.close()


def new_chest(parent_window, def_stock_attribs=['ui', 'artikelnr', 'anzahl', 'bin']):
    window_title = 'Neues Fach'
    stock_names = [name for name in [stock.name for stock in stocks.values()]]

    layout = [
        [sg.Combo(stock_names, default_value=stock_names[0], key='stock_select'),
         sg.Checkbox('Leer', key='check_empty')]
    ]
    row = make_attrib_layout(def_stock_attribs)
    layout.append(row)
    layout.append([sg.Button('OK', key='submit')])
    window = sg.Window(window_title, layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        if event == 'submit':
            if window.Element('check_empty').Get() == 1:
                stocks[values['stock_select']].add_chest(values['ui_input'], None)
            else:
                try:
                    stocks[values['stock_select']].add_chest(values['ui_input'],
                                                    article_dict[values['artikelnr_input']],
                                                    amount=values['anzahl_input'])
                except KeyError:
                    pass
            try:
                new_chest = stocks[values['stock_select']].chest_dict[values['ui_input']]
                write_history(window_title, 'ui', '', values['ui_input'], chest=new_chest)
                stock_table_data = stocks[values['stock_select']].stock_list(def_stock_attribs)
                stock_table_data.pop(0)
                parent_window.Element('stock_table').Update(values=stock_table_data)
            except KeyError:
                pass
    window.close()


def change_chest(def_stock_attribs=['rechnungsnr/info', 'ui', 'artikelnr', 'anzahl', 'bin']):
    stock_names = [name for name in [stock.name for stock in stocks.values()]]
    actions = ['Fach ändern', 'Onlineshop Verkauf', 'Laden Verkauf']
    layout = [
        [sg.Text('Lager:'),
        sg.Combo(stock_names, default_value=stock_names[0], key='stock_select'),
        sg.Text('Aktion:'),
        sg.Combo(actions, default_value=actions[0], key='action_select'),
        sg.Button(button_text='Scan Code', key='scan')]
    ]
    layout.append(make_attrib_layout(def_stock_attribs))
    layout.append([sg.Button('OK', key='submit')])
    window = sg.Window('Fach bearbeiten', layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'scan':
            type_str, object  = barcode_scanner()
            for attrib in def_stock_attribs:
                window[attrib + '_input']('')
            if type_str == 'article':
                window.Element('artikelnr_input').Update(value=object.get('artikelnr'))
            elif type_str == 'chest':
                window.Element('stock_select').Update(value=object.stock.name)
                window.Element('ui_input').Update(value=object.ui)
                window.Element('artikelnr_input').Update(value=object.get_article_ui())
                window.Element('bin_input').Update(value=object.bin)
        elif event == 'submit':
            if values['ui_input'] != '':
                stock = stocks[values['stock_select']]
                try:
                    chest = stock.chest_dict[values['ui_input']]
                    old_amount = chest.amount
                    old_article = chest.get_article_ui()
                    old_bin = chest.bin
                except KeyError:
                    window.Element('ui_input').Update(value='UI nicht gefunden!')

                if values['action_select'] == 'Fach ändern':
                    attrib_dict = {
                        'amount': values['anzahl_input'],
                        'article': values['artikelnr_input'],
                        'bin': values['bin_input']
                    }
                    try:
                        stock.change_chest(values['ui_input'], attrib_dict, article_dict)
                        if values['rechnungsnr/info_input'] != '':
                            write_history('Fach ändern', 'anzahl', old_amount, chest.amount, add_info=values["rechnungsnr/info_input"])
                        if values['anzahl_input'] != '':
                            write_history('Fach ändern', 'anzahl', old_amount, chest.amount, chest=chest)
                        if values['artikelnr_input'] != '':
                            write_history('Fach ändern', 'artikel', old_article, chest.get_article_ui(), chest=chest)
                        if values['bin_input'] != '':
                            write_history('Fach ändern', 'bin', old_bin, chest.bin, chest=chest)
                    except KeyError:
                        window.Element('artikelnr_input').Update(value='Artikelnr nicht gefunden!')
                elif values['action_select'] == 'Onlineshop Verkauf':
                    if values['rechnungsnr/info_input'] != '':
                        if values['anzahl_input'] != '':
                            attrib_dict = {
                                'amount': str(int(chest.amount) - int(values['anzahl_input']))
                            }
                            old_amount = chest.amount
                            stock.change_chest(values['ui_input'], attrib_dict, article_dict)
                            add_info = f'{chest.get_article_ui()} für Rechnungsnr.: {values["rechnungsnr/info_input"]}'
                            write_history('Onlineshop Verkauf', 'anzahl', old_amount, chest.amount, chest=chest, add_info=add_info)
                        else:
                            window.Element('anzahl_input').Update(value='Anzahl muss angegeben werden!')
                    else:
                        window.Element('rechnungsnr/info_input').Update(value='Rechnungsnr muss angegeben werden!')
                elif values['action_select'] == 'Laden Verkauf':
                    if values['anzahl_input'] != '':
                        attrib_dict = {
                            'amount': str(int(chest.amount) - int(values['anzahl_input']))
                        }
                        old_amount = chest.amount
                        stock.change_chest(values['ui_input'], attrib_dict, article_dict)
                        add_info = f'{chest.get_article_ui()} für Rechnungsnr.: {values["rechnungsnr/info_input"]}'
                        write_history('Laden Verkauf', 'anzahl', old_amount, chest.amount, chest=chest, add_info=add_info)
                    else:
                        window.Element('anzahl_input').Update(value='Anzahl muss angegeben werden!')
            else:
                window.Element('ui_input').Update(value='UI muss angegeben werden!')

    window.close()


def new_article(parent_window):
    window_title = 'Neuer Artikel'
    for article in article_dict.values():
        attribs = article.attribs()
        break

    layout = []
    row = make_attrib_layout(attribs)
    layout.append(row)
    layout.append([sg.Button('OK', key='submit')])
    window = sg.Window(window_title, layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'submit':
            attrib_dict = {}
            if values['artikelnr_input'] not in article_dict:
                for attrib in attribs:
                    attrib_dict[attrib] = values[attrib + '_input']
                new_article = Article(file_path, file_tree, 'artikelnr', attrib_dict)
                article_dict[new_article.get(new_article.ui)] = new_article
                write_history(window_title, 'ui', '', new_article.get(new_article.ui), article=new_article)
                pim_table_data, _ = make_displayable_list(article_dict)
                parent_window.Element('pim_table').Update(values=pim_table_data)

    window.close()


def change_article(parent_window):
    window_title = 'Artikel bearbeiten'
    for article in article_dict.values():
        attribs = article.attribs()
        break
    layout = [[sg.Button('Scan Code', key='scan')]]
    row = make_attrib_layout(attribs)
    layout.append(row)
    layout.append([sg.Button('OK', key='submit')])
    window = sg.Window(window_title, layout)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        elif event == 'scan':
            type_str, article = barcode_scanner('article')

            if type_str == 'article':
                for attrib in attribs:
                    input_name = attrib + '_input'
                    window.Element(input_name).Update(value=article.get(attrib))
        elif event == 'submit':
            if values['artikelnr_input'] in article_dict.keys():
                article = article_dict[values['artikelnr_input']]
                for attrib in attribs:
                    input_name = attrib + '_input'
                    if values[input_name] != article.get(attrib) and values[input_name] != '':
                        old_value = article.get(attrib)
                        article.change(attrib, values[input_name])
                        write_history(window_title, attrib, old_value, values[input_name], article=article)
                pim_table_data, _ = make_displayable_list(article_dict)
                parent_window.Element('pim_table').Update(values=pim_table_data)
    window.close()



def new_stock_file():
    first_layout_row = [
        sg.Text('Name:', key='name_label'), sg.Input(key='name_input')
    ]
    second_layout_row = [
        sg.Button('OK', key='submit')
    ]
    layout = [
        first_layout_row,
        second_layout_row
    ]
    window = sg.Window('Neues Lager', layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        elif event == 'submit':
            file_root = ET.Element('root')
            file_tree = ET.ElementTree(file_root)
            file_tree.write('data/xml/stocks/' + values['name_input'] + '.xml')

    window.close()


def main_loop():
    def_stock_attribs = ['artikelnr', 'kollektion', 'modell', 'typ']
    pim_table_data, pim_table_header = make_displayable_list(article_dict)
    stock_names = [name for name in [stock.name for stock in stocks.values()]]
    stock_table_data = stocks[stock_names[0]].stock_list(def_stock_attribs)
    print('data length:' + str(len(stock_table_data)))
    if len(stock_table_data) == 1:
        stock_table_data.append(['' for _ in stock_table_data[0]])
    stock_table_header = stock_table_data.pop(0)

    first_layout_row = [
        sg.Button(button_text='Neues Lager', key='new_stock'),
        sg.Button(button_text='Neues Fach', key='new_chest'),
        sg.Button(button_text='Fach bearbeiten', key='change_chest'),
        sg.Button(button_text='Neuer Artikel', key='new_article'),
        sg.Button(button_text='Artikel bearbeiten', key='change_article'),
        sg.Button(button_text='Bestellungen', key='orders'),
        sg.Button(button_text='Ereignisse', key='history'),
        sg.Button(button_text='PDF Export', key='pdf_export')
    ]

    second_layout_row = [
        sg.InputCombo(stock_names, default_value=stock_names[0], key='stock_select'),
        sg.Button('Aktualisiere', key='refresh')
    ]

    third_layout_row = [
        sg.Input(default_text='artikelnr:', key='search_input'),
        sg.Button('Suche', key='search_button')
    ]

    table_layout_row = [sg.Table(
        values=stock_table_data,
        headings=stock_table_header,
        max_col_width=20,
        def_col_width=15,
        auto_size_columns=True,
        justification='left',
        num_rows=30,#min(len(stock_table_data), 20),
        vertical_scroll_only=False,
        key='stock_table'
        ),
        sg.Table(
        values=pim_table_data,
        headings=pim_table_header,
        max_col_width=15,
        auto_size_columns=True,
        justification='left',
        num_rows=30,
        vertical_scroll_only=False,
        key='pim_table'
        )
        ]

    layout = [
        first_layout_row,
        second_layout_row,
        third_layout_row,
        table_layout_row
        ]

    window = sg.Window('Table', layout, grab_anywhere=False, resizable=True)

    while True:
        event, values = window.read()
        print('Event',event)
        if event == sg.WIN_CLOSED:
            break
        elif event == 'new_stock':
            new_stock_file()
        elif event == 'refresh':
            if values['stock_select'] != '':
                stock_table_data = stocks[values['stock_select']].stock_list(def_stock_attribs)
                stock_table_data.pop(0)
                window.Element('stock_table').Update(values=stock_table_data)
        elif event == 'search_button':
            if values['stock_select'] != '' and values['search_input'] != '':
                attrib, search_values = parse_input(values['search_input'])
                stock_table_data = stocks[values['stock_select']].get_filtered_list(attrib, search_values, d_attribs=def_stock_attribs)
                if attrib == 'artikelnr':
                    pim_table_data = []
                    for value in search_values:
                        print('search_value:',value)
                        pim_table_data.extend(find_article_list(article_dict, value))
                elif attrib == 'ui':
                    pim_table_data = []
                    for chest in stocks[values['stock_select']].search('ui', search_values):
                        pim_table_data.extend(find_article_list(article_dict, chest.get_article_attrib('artikelnr')))
                stock_table_data.pop(0)
                window.Element('stock_table').Update(values=stock_table_data)
                window.Element('pim_table').Update(values=pim_table_data)
        elif event == 'new_article':
            new_article(window)
        elif event == 'change_article':
            change_article(window)
        elif event == 'new_chest':
            new_chest(window)
        elif event == 'change_chest':
            change_chest()
        elif event == 'pdf_export':
            export_stocks_to_pdf(['artikelnr', 'kollektion', 'modell', 'typ'])
        elif event == 'orders':
            order_menu()
        elif event == 'history':
            history_menu()

    window.close()


# Some globals
file_path = 'data/xml/Artikel.xml'
file_tree = ET.parse(file_path)

st_file_path = 'data/xml/stocks/Fertig.xml'
st_file_tree = ET.parse(st_file_path)

h_file_path, h_file_tree = make_history_file()
h_file_root = h_file_tree.getroot()

stocks = make_stocks('data/xml/stocks/')

article_dict = make_articles(file_path, file_tree)




if __name__ == '__main__':
    for stock in stocks.values():
        stock.make_chest_dict(article_dict)
        for chest in stock.chest_dict.values():
            if chest.get_article_ui() != '':
                article_dict[chest.get_article_ui()].amount += int(chest.amount)
    main_loop()
