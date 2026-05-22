"""
数据清洗任务
- 清洗 products: 原始产品表 -> clean_products
- 清洗 reviews: 原始评论表 -> clean_reviews
"""
import os
import re
import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, to_timestamp, udf, coalesce, lit

# 环境配置 
os.environ['PYSPARK_PYTHON'] = r'D:\Python\Python311\python.exe'
os.environ['PYSPARK_DRIVER_PYTHON'] = r'D:\Python\Python311\python.exe'

spark = SparkSession.builder \
    .appName('DataCleanJob') \
    .config("spark.driver.extraClassPath", "./mysql-connector-j-8.0.33.jar") \
    .config("spark.executor.extraClassPath", "./mysql-connector-j-8.0.33.jar") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .getOrCreate()

db_props = {
    "user": "root",
    "password": "root",
    "driver": "com.mysql.cj.jdbc.Driver"
}
jdbc_url = "jdbc:mysql://localhost:3306/digrecsys1?useSSL=false"


def truncate_mysql_table(table_name: str):
    import pymysql
    conn = pymysql.connect(host="localhost", user="root", password="root", database="digrecsys1")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
    finally:
        conn.close()

def parse_review_date(date_str: str) -> str:
    """
    解析评论日期
    输入: "发表于：2015年07月18日 10:40" 或 "2015年07月18日 10:40"
    输出: "2015-07-18 10:40:00"
    """
    if not date_str:
        return None
    # 提取日期部分
    patterns = [
        r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{1,2})',  # 完整日期
        r'(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{1,2})',        # 无年份
        r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})',   # 已格式化
    ]
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) == 5:
                # 有年份: 2015年07月18日 10:40
                year, month, day, hour, minute = groups
                year = int(year)
            elif len(groups) == 4:
                # 无年份: 07月18日 10:40
                month, day, hour, minute = groups
                year = datetime.datetime.now().year
            else:
                continue
            return f"{year}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{int(minute):02d}:00"
    return None

# 注册UDF算子
from pyspark.sql.types import StringType
date_parse_udf = udf(parse_review_date, StringType())

# 产品清洗
def clean_products_task():
    """清洗 products 表"""
    print("=" * 50)
    print("开始清洗 products 数据")
    print("=" * 50)
    # 读取原始产品表
    df = spark.read.jdbc(jdbc_url, table='products', properties=db_props)
    print(f"原始产品数: {df.count()}")
    # 清洗逻辑
    cleaned = (
        df.filter(
            col("prod_id").isNotNull() & (trim(col("prod_id")) != "") &
            col("name").isNotNull() & (trim(col("name")) != "") &
            col("price").isNotNull() & (col("price") > 0) &
            col("is_active") == 1
        )
        .withColumn("created_at", coalesce(to_timestamp(col("created_at")), to_timestamp(lit("2024-01-01 00:00:00"))))
        .withColumn("updated_at", coalesce(to_timestamp(col("updated_at")), to_timestamp(lit("2024-01-01 00:00:00"))))
    )
    # 选择输出字段
    output = cleaned.select(
        col("prod_id"), col("name"), col("price"), col("rate"), col("comment_count"),
        col("img_url"), col("sub_images"), col("all_params"), col("stock"),
        col("created_at"), col("updated_at"), col("is_active").cast("int"),
        col("brand_id").cast("int"), col("category_id").cast("int")
    )
    print(f"清洗后产品数: {output.count()}")
    # 清空目标表
    truncate_mysql_table("clean_products")
    # 写入 clean_products
    output.write.jdbc(jdbc_url, "clean_products", mode="append", properties=db_props)
    print("products 清洗完成!")
    # 返回 DataFrame 供后续 reviews 任务使用，避免二次读取
    return output.select("prod_id")


# 评论清洗任务
def clean_reviews_task(valid_products_df):
    """
    清洗 reviews 表
    参数: valid_products_df - 从 products 清洗任务传入的有效产品ID列表
    """
    print("=" * 50)
    print("开始清洗 reviews 数据")
    print("=" * 50)
    # 读取原始评论表
    df = spark.read.jdbc(jdbc_url, table='raw_reviews', properties=db_props)
    print(f"原始评论数: {df.count()}")
    # 链式处理: 过滤空内容 -> 解析日期 -> 过滤无效日期 -> 去重
    cleaned = (
        df.filter(col("content").isNotNull() & (trim(col("content")) != ""))
        .withColumn("date_parsed", date_parse_udf(col("date")))
        .filter(col("date_parsed").isNotNull())
        .dropDuplicates(subset=['username', 'product_id', 'content'])
    )
    output = (
        cleaned.join(
            valid_products_df,
            cleaned.product_id == valid_products_df.prod_id,
            "inner"
        )
        .select(
            col("id"), col("product_id"), col("username"), col("content"),
            col("rating"), to_timestamp(col("date_parsed"), "yyyy-MM-dd HH:mm:ss").alias("date"),
            lit("").alias("clean_content"),
            lit("").alias("sentiment_label")
        )
    )
    print(f"清洗后评论数: {output.count()}")
    truncate_mysql_table("clean_reviews")
    output.write.jdbc(jdbc_url, "clean_reviews", mode="append", properties=db_props)
    print("reviews 清洗完成!")


if __name__ == '__main__':
    valid_products_df = clean_products_task()
    clean_reviews_task(valid_products_df)
    print("\n" + "=" * 50)
    print("所有清洗任务完成!")
    print("=" * 50)