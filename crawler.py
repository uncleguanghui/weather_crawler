import re
import json
import configparser
from pathlib import Path
import warnings

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")


class WeatherCrawler(object):
    def __init__(self):
        # 城市名称及对应编码
        self.city_code_dict = self.read_configs('city_code.ini', "CityCode")
        # 所有用到的URL
        self.base_urls = self.read_configs('china_weather.ini', "AllUrl")
        # 风向对应的编码
        self.wind_direction_code = self.read_configs('china_weather.ini', "WindDirectionCode")
        # 风速对应的编码
        self.wind_speed_code = self.read_configs('china_weather.ini', "WindSpeedCode")
        # 天气对应的编码
        self.weather_code = self.read_configs('china_weather.ini', "WeatherCode")
        # 浏览器头
        self.__browser_header = self.read_configs('crawler.ini', "BrowserHeader")

    @staticmethod
    def read_configs(file_name, section) -> dict:
        """
        根据 配置文件名称 和 配置文件分段名称 读取配置文件，转化成dict
        :param file_name: 配置文件名称
        :param section: 配置文件分段的名称
        :return: 配置文件对应分段的数据字典
        """
        path_config = Path(__file__).parent / 'configs' / file_name
        if not path_config.exists():
            raise Exception(f"配置文件{path_config}不存在")
        config = configparser.ConfigParser()
        config.read(path_config, encoding='gbk')
        section_dict = dict(config[section].items())
        return section_dict

    def get_city_code(self, city_name: str) -> str:
        """
        根据城市中文名,查询字典,返回城市的代码
        :param city_name: 城市名称
        :return: 城市代码
        """
        for index in range(len(city_name)):
            cn = city_name[:(index + 1)]
            if cn in self.city_code_dict.keys():
                return self.city_code_dict[cn]
        raise ValueError('城市名称错误或不在已知编码清单内!')

    def __get_html(self, url: str) -> str:
        """
            请求天气信息页面
        :param url: 请求URL地址
        :return: 请求结果的字符串
        """
        response = requests.request('GET', url, headers=self.__browser_header, timeout=5)
        response.encoding = "utf-8"
        return response.text

    def get_real_time_weather(self, city_name: str) -> dict:
        """
        获取最近更新的天气数据
        :param city_name: 城市名称
        :return: 最新天气信息的字典
        """
        city_code = self.get_city_code(city_name)
        url = self.base_urls["实时天气"].format(city_code=city_code)
        html = self.__get_html(url)
        data = str(html).replace("var dataSK = ", "")
        data = json.loads(data)
        if 'time' not in data:
            return {"错误": "接口解析错误"}
        result = {
            "更新时间": data['time'],
            "日期": data['date'],
            "城市": data['cityname'],
            "城市编码": data['city'],
            "温度（摄氏）": data['temp'],
            "温度（华氏）": data['tempf'],
            "风向": data['WD'],
            "湿度": data['SD'],
            "天气": data['weather'],
            "风速": data['wse'].replace("&lt;", "<"),
            "24h降水": data['rain24h'],
            "aqi_pm25": data["aqi_pm25"],
        }
        return result

    def get_7d_weather(self, city_name: str) -> dict:
        """
        解析页面，获取近7天的天气预报
        :param city_name: 城市名称
        :return: 最近7天天气的数据字典
        """
        city_code = self.get_city_code(city_name)
        url = self.base_urls["近7天天气"].format(city_code=city_code)
        html = self.__get_html(url)
        soup = BeautifulSoup(html, 'lxml')
        date_ul = soup.find("ul", class_="date-container").findAll("li")
        blue_ul = soup.find("ul", class_="blue-container sky").findAll("li", class_='blue-item')
        temp_7d_H = eval(re.findall(r"var eventDay =(.*?);", html)[0])
        temp_7d_L = eval(re.findall(r"var eventNight =(.*?);", html)[0])
        update_time = str(re.findall(r"var uptime=(.*?);", html)[0]).replace("\"", "").replace("更新", "")
        data_list = []
        for _date, _temp_H, _temp_L, _wind in zip(date_ul, temp_7d_H, temp_7d_L, blue_ul):
            wind_list = _wind.find("div", class_='wind-container').findAll('i')
            wind_direction = ','.join(list(set([i.attrs['title'] for i in wind_list])))
            one_day_info = {
                '日期': _date.find("p", class_='date').get_text(),
                '日期标识': _date.find("p", class_='date-info').get_text(),
                '最高温度': _temp_H,
                '最低温度': _temp_L,
                '天气': _wind.find("p", class_='weather-info').get_text(),
                '风向': wind_direction,
                '风速': _wind.find("p", class_='wind-info').get_text().replace("\n", ""),
            }
            data_list.append(one_day_info)
        result = {
            '城市': city_name,
            '城市编码': city_code,
            '更新时间': update_time,
            '数据': data_list,
        }
        return result

    def get_15d_weather(self, city_name: str) -> dict:
        """
        解析页面，获取近15天的天气预报
        :param city_name: 城市名称
        :return: 最近15天天气的数据字典
        """
        city_code = self.get_city_code(city_name)
        url = self.base_urls["7至15天天气"].format(city_code=city_code)
        html = self.__get_html(url)
        soup = BeautifulSoup(html, 'lxml')
        date_ul = soup.find("ul", class_="date-container").findAll("li")
        blue_ul = soup.find("ul", class_="blue-container").findAll("li", class_='blue-item')
        temp_15d_H = eval(re.findall(r"var fifDay =(.*?);", html)[0])
        temp_15d_L = eval(re.findall(r"var fifNight =(.*?);", html)[0])
        update_time = soup.find('input', id='update_time').attrs['value']
        data_list = self.get_7d_weather(city_name)['数据']
        for _date, _temp_H, _temp_L, _wind in zip(date_ul, temp_15d_H, temp_15d_L, blue_ul):
            wind_list = _wind.find("div", class_='wind-container').findAll('i')
            wind_direction = ','.join(list(set([i.attrs['title'] for i in wind_list])))
            one_day_info = {
                '日期': _date.find("p", class_='date').get_text(),
                '日期标识': _date.find("p", class_='date-info').get_text(),
                '最高温度': _temp_H,
                '最低温度': _temp_L,
                '天气': _wind.find("p", class_='weather-info').get_text(),
                '风向': wind_direction,
                '风速': _wind.find("p", class_='wind-info').get_text().replace("\n", ""),
            }
            data_list.append(one_day_info)
        data = {
            '城市': city_name,
            '城市编码': city_code,
            '更新时间': update_time,
            '数据': data_list,
        }
        return data

    def get_hours_weather(self, city_name: str) -> dict:
        """
        获取逐小时的天气数据
        :param city_name: 城市名称
        :return: 最近24小时的天气数据字典
        """
        city_code = self.get_city_code(city_name)
        url = self.base_urls["逐小时天气"].format(city_code=city_code)
        html = self.__get_html(url)
        hours_data = eval(re.findall(r"var hour3data=(.*?);", html)[0])[0]
        update_time = eval(re.findall(r"var uptime=(.*?);", html)[0]).replace("更新", "")
        format_data = []
        for one_houe_data in hours_data:
            format_data.append({
                '天气': self.weather_code[one_houe_data.pop('ja')],
                '风向': self.wind_direction_code[one_houe_data.pop("jd")],
                '温度': one_houe_data.pop('jb'),
                '日期': one_houe_data.pop('jf'),
                '风速': self.wind_speed_code[one_houe_data.pop('jc')],
            })

        data = {
            '城市': city_name,
            '城市编码': city_code,
            "更新时间": update_time,
            '数据': format_data,
        }
        return data


if __name__ == '__main__':
    crawler = WeatherCrawler()
    city = "上海市"
    # 获取实时天气
    print(json.dumps(crawler.get_real_time_weather(city),
                     ensure_ascii=False, sort_keys=True, indent=4, separators=(', ', ': ')))
    # 获取近7天的天气预报
    print(json.dumps(crawler.get_7d_weather(city),
                     ensure_ascii=False, sort_keys=True, indent=4, separators=(', ', ': ')))
    # 获取近15天的天气预报
    print(json.dumps(crawler.get_15d_weather(city),
                     ensure_ascii=False, sort_keys=True, indent=4, separators=(', ', ': ')))
    # 获取逐小时的天气数据预报
    print(json.dumps(crawler.get_hours_weather(city),
                     ensure_ascii=False, sort_keys=True, indent=4, separators=(', ', ': ')))
