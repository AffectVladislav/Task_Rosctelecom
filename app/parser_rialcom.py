import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dataclasses import dataclass

from fake_useragent import UserAgent

from .data_parser import DataParser


@dataclass
class ParserRialcom(DataParser):
    """
    Класс для парсинга интернет-тарифов с сайта Rialcom.

    Атрибуты:
        url (str): URL страницы с тарифами.
        ua (UserAgent): Объект для генерации случайного User-Agent.
        names (list): Список названий тарифов.
        channels (list): Список количества каналов.
        speeds (list): Список скоростей доступа.
        payments (list): Список абонентских плат.
        count_tariff_channel (dict): Словарь для хранения количества каналов по тарифам.

    Методы:
        load_data(url): Загружает данные с указанного URL.
        process_data(): Обрабатывает загруженные данные и возвращает списки с тарифами.
        save_data(name): Сохраняет обработанные данные в Excel файл с указанным именем.
    """
    url: str = "https://www.rialcom.ru/internet_tariffs/"
    ua: UserAgent = UserAgent()

    def __init__(self):
        """
         Инициализирует экземпляр ParserRialcom и его атрибуты.
        """
        super().__init__()
        self.names = []
        self.channels = []
        self.speeds = []
        self.payments = []
        self.count_tariff_channel = {}

    def load_data(self, url=url):
        """
        Загружает данные с указанного URL.

        Параметры:
            url (str): URL для загрузки данных. По умолчанию используется атрибут url.

        Возвращает:
            int: Код состояния HTTP (200 для успешного запроса).
        """
        headers = {'User-Agent': self.ua.random}

        response = requests.get(url=url, headers=headers)

        if response.status_code == 200:
            # Парсим HTML при помощи Beautiful Soup
            self.data = BeautifulSoup(response.text, 'html.parser')
            return 200
        else:
            return response.status_code

    def process_data(self):
        """
        Обрабатывает загруженные данные.

        Возвращает:
            list: Списки с названиями тарифов, количеством каналов, скоростями и абонентскими платами.
        """
        processRialcom = DataRialcom(self.data)
        return processRialcom.process_data()

    def save_data(self, name: str = "example"):
        """
        Сохраняет обработанные данные в Excel файл.

        Параметры:
            name (str): Имя файла для сохранения. По умолчанию "example".
        """
        _dict = {}
        headers = ['Название тарифа', 'Количество каналов', 'Скорость доступа', 'Абонентская плата']
        data = self.process_data()
        for i in range(len(headers)):
            _dict[headers[i]] = data[i]
        df = pd.DataFrame(_dict)
        df.to_excel(f"{name}.xlsx", index=False)


class DataRialcom(ParserRialcom):
    """
    Класс для обработки данных тарифов Rialcom.

    Атрибуты:
        data (BeautifulSoup): Загруженные данные в формате BeautifulSoup.

    Методы:
        process_data(): Обрабатывает данные и извлекает информацию о тарифах.
    """

    def __init__(self, data):
        """
        Инициализирует экземпляр DataRialcom с загруженными данными.

        Параметры:
            data (BeautifulSoup): Загруженные данные для обработки.
        """
        super().__init__()
        self.data = data

    def process_data(self):
        """
        Обрабатывает данные и извлекает информацию о тарифах.

        Возвращает:
            list: Списки с названиями тарифов, количеством каналов, скоростями и абонентскими платами.
        """

        # CSS-селектор
        tables = self.data.find_all('table')

        # Обходим строки в цикле
        for table in tables:
            rows = table.find_all('tr')
            heads = rows[0].find_all('th')
            united_heads = ' '.join(map(lambda x: x.get_text(), heads))

            # Сценарий для таблиц формата 1
            if re.search("тариф", united_heads) is not None:
                self.__process_tariff(rows)

            # Сценарий для таблиц формата 2
            elif re.search("Интернет", united_heads) is not None:
                self.__process_tariff_TV(rows, heads)

            # Сценарий для остальных таблиц
            else:
                continue

        return [self.names, self.channels, self.speeds, self.payments]

    def __process_tariff(self, rows):
        """
        Обрабатывает строки таблицы с тарифами.

        Параметры:
            rows (list): Список строк таблицы, содержащих информацию о тарифах.
        """
        for row in rows[1:]:
            columns = row.find_all('td')
            self.names.append(columns[0].text.strip())
            self.channels.append('null')
            self.speeds.append(int(int(re.search(r'\d+', columns[3].text.strip()).group()) / 1000))
            self.payments.append(int(columns[1].text.strip().split()[0]))

    def __process_tariff_TV(self, rows, heads):
        """
        Обрабатывает строки таблицы с тарифами, включающими телевидение.

        Параметры:
            rows (list): Список строк таблицы, содержащих информацию о тарифах с телевидением.
            heads (list): Список заголовков таблицы.
        """
        for row in rows[1:]:
            columns = row.find_all('td')
            tariff = columns[0].text.strip()
            is_tariff = False

            if tariff in self.count_tariff_channel.keys():
                channel = self.count_tariff_channel[tariff]
                is_tariff = True

            else:
                pattern = r"(?P<name>[\s\S]*?)\s*\((?P<num>\d+)[\s\S]*\)"
                groups = re.search(pattern, tariff)
                name, num = groups.groupdict()['name'], int(groups.groupdict()['num'])
                self.count_tariff_channel[name] = num
                channel = num

            self.__wrtite_tariff_TV(heads, columns, channel, is_tariff, tariff)

    def __wrtite_tariff_TV(self, heads, columns, channel: int, is_tariff: bool, tariff: str):
        """
        Записывает информацию о тарифах с телевидением в соответствующие списки.

        Параметры:
            heads (list): Список заголовков таблицы.
            columns (list): Список ячеек текущей строки таблицы.
            channel (int): Количество каналов для текущего тарифа.
            is_tariff (bool): Флаг, указывающий, является ли тариф уже известным.
            tariff (str): Название текущего тарифа.
        """
        for i in range(1, len(heads)):
            head = heads[i].text.strip()
            speed = int(re.search(r'\d+', head).group())
            if is_tariff:
                self.names.append(f"{tariff} + РиалКом Интернет {speed} + TB_ч")
            else:
                self.names.append(f"{tariff} + РиалКом Интернет {speed} + TB")
            self.channels.append(channel)
            self.speeds.append(speed)
            self.payments.append(int(columns[i].text.strip()))
