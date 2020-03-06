from time import time
import argparse

import pandas as pd

import crawler
import tools


def main(pool_size=1):
    """
    爬虫主函数
    :param pool_size: 线程池大小
    :return:
    """
    start_time = time()
    weather = crawler.WeatherCrawler()  # 初始化爬虫实例
    params = [(city,) for city in weather.city_code_dict.keys()]
    if pool_size == 1:
        results = tools.run_single_thread(params, weather.get_real_time_weather)  # 单线程循环爬，预计用时30min ~ 1h
    else:
        results = tools.run_thread_pool(params, weather.get_real_time_weather, pool_size=pool_size)  # 多线程爬

    data = [result for result in results if result]
    success_num = len(data)  # 成功数
    failure_num = len(results) - success_num  # 失败数
    df = pd.DataFrame(data)
    end_time = time()
    return f'成功城市数{success_num}, 失败城市数{failure_num}， 耗时{end_time-start_time:.0f}s'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='解析线程池大小')
    parser.add_argument('--pool', type=int, default=1)
    args = parser.parse_args()

    main(pool_size=args.pool)
