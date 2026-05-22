# utils/order_utils.py
import time
import random

def generate_order_sn():
    """生成唯一订单号：时间戳 + 随机数"""
    timestamp = time.strftime("%Y%m%d%H%M%S")
    random_str = "".join([str(random.randint(0, 9)) for _ in range(4)])
    return f"{timestamp}{random_str}"
