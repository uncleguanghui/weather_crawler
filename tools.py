from multiprocessing import Manager
from multiprocessing.pool import ThreadPool
from collections import deque


def run_thread_pool(params, func, pool_size=30):
    """
    多线程处理任务
    :param params: 每个线程的所需参数的的列表
    :param func: 任务函数
    :param pool_size: 线程池大小，默认50
    :return: 结果列表
    """
    manager = Manager()
    return_dict = manager.dict()

    def get_params(p):
        for key, param in enumerate(p):
            yield (param, func, key, return_dict)

    def foo(p):
        param, job, key, return_d = p
        return_d[key] = job(*param)

    pool_size = min(pool_size, len(params))
    pool = ThreadPool(processes=pool_size)
    pool.map(foo, get_params(params))
    pool.close()

    return [return_dict.get(i) for i in range(len(params))]


def run_single_thread(params, func):
    """
    单线程处理任务
    :return:
    """
    results = deque([])
    for param in params:
        results.append(func(*param))

    return list(results)
