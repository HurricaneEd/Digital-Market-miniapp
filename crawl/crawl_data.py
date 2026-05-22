import random
import time
import requests
from django.db import transaction
from lxml import etree
import re
from concurrent.futures import ThreadPoolExecutor
import os
import django

# 初始化 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DigRecSys.settings')
django.setup()

from Product.models import Product, Review, Category, Brand

CATEGORY_MAP = {
    'digital_camera': '数码相机',
    'cell_phone': '智能手机',
    'mice': '鼠标',
    'microphone': '耳机',
    'pocketpower':'移动电源',
    'tablepc':'平板电脑'
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    "Referer": "https://detail.zol.com.cn/",
    'cookie': 'ip_ck=58CA7vj0j7QuMDcxOTIzLjE3Njk2NTgwMDk%3D; m_area_city_new=quanzhou; m_area_cityId_new=202; m_area_provinceId_new=33; listSubcateId=1198; z_pro_city=s_provice%3Dfujian%26s_city%3Dquanzhou; userProvinceId=33; userCityId=202; userCountyId=1157; userLocationId=137405; realLocationId=137405; userFidLocationId=137405; lv=1770619348; vn=9; z_day=icnmo11564=1&rdetail=5; questionnaire_pv=1770595205'
}

session = requests.Session()
session.headers.update(HEADERS)

def clean_nested_specs(nested_dict):
    """清理详参中的噪音数据"""
    blacklist = ['仅供参考', '投诉', '资料有误', '加入对比', '纠错', '更多参数']
    cleaned = {}
    for group, params in nested_dict.items():
        sub_dict = {
            k: v for k, v in params.items()
            if not any(word in k for word in blacklist) and len(k) < 20
        }
        if sub_dict:
            cleaned[group] = sub_dict
    return cleaned


def get_best_brand(product_name, brand_map):
    """
    统一品牌识别逻辑：
    1. 优先匹配别名表 (解决 Redmi, iPhone 等问题)
    2. 其次匹配中文全名
    3. 最后匹配非数字的 Slug
    """
    brand_aliases = {
        '红米': ['redmi'],
        '华为': ['huawei']
    }
    name_lower = product_name.lower()

    # 第一步：根据映射表寻找中文名，看其别名是否在产品名中
    for b_id, b_name in brand_map.items():
        # 匹配中文全名 (如 "小米" in "小米11")
        if b_name in product_name:
            return b_name

        # 匹配英文别名 (如 "redmi" in "Redmi Note 9")
        aliases = brand_aliases.get(b_name, [])
        if any(alias in name_lower for alias in aliases):
            return b_name

        # 匹配 Slug (针对非数字的 data-link)
        if not b_id.isdigit() and b_id != "" and b_id in name_lower:
            return b_name

    return "其他"

def fetch_list_page(page,category_slug="mice"):
    """抓取列表页并过滤高热度商品"""
    url = f'https://detail.zol.com.cn/{category_slug}/' if page == 1 else f'https://detail.zol.com.cn/{category_slug}/{page}.html'
    # url = f'https://detail.zol.com.cn/{category_slug}/pic.html' if page == 1 else f'https://detail.zol.com.cn/{category_slug}/pic_{page}.html'
    # url = f'https://detail.zol.com.cn/{category_slug}_index/subcate15_list_1.html' if page == 1 else f'https://detail.zol.com.cn/{category_slug}_index/subcate15_0_list_1_0_1_2_0_{page}.html'
    try:
        resp = session.get(url, timeout=10)
        resp.encoding = 'gbk'
        tree = etree.HTML(resp.text)

        # 构建品牌映射
        brand_map = {}
        for node in tree.xpath('//div[@id="J_BrandAll"]/a'):
            link_key = (node.xpath('./@data-link') or [""])[0].lower()
            brand_text = "".join(node.xpath('.//text()')).strip()
            if brand_text:
                brand_map[link_key] = brand_text

        li_list = tree.xpath('//ul[@id="J_PicMode"]/li')
        valid_items = []

        for li in li_list:
            # 提取商品详情页url
            index_path = (li.xpath('.//a[@class="pic"]/@href') or [""])[0]
            index_url = f"https://detail.zol.com.cn{index_path}" if index_path else ""
            # 提取评论人数
            comment_str = (li.xpath('.//a[@class="comment-num"]/text()') or ["0"])[0]
            comment_count = int(re.search(r'\d+', comment_str).group()) if re.search(r'\d+', comment_str) else 0
            # 提取商品名
            name = (li.xpath('./a/img/@alt') or ["null"])[0]
            # 构造参数页url，爬取详参
            href_nodes = li.xpath('.//a[@class="comment-num"]/@href')
            if not href_nodes: continue
            if href_nodes:
                hrefNodes_parse = [p for p in href_nodes[0].split('/') if p]
                cat_id = hrefNodes_parse[0]
                p_id = hrefNodes_parse[1]
                param_url = f"https://detail.zol.com.cn/{cat_id}/{p_id}/param.shtml"
            else:
                param_url = ""
            # 爬取网站主页商品图片
            img_url = (li.xpath('./a/img/@*[name()=".src"] | ./a/img/@src') or ["null"])[0]
            # 实现品牌模糊匹配,品牌与商品一一对应
            best_brand = get_best_brand(name, brand_map)

            valid_items.append({
                'pid': p_id,
                'category': category_slug,
                'brand': best_brand,
                'name': name,
                'price': (li.xpath('.//b[@class="price-type"]/text()') or ["暂无报价"])[0],
                'rate': (li.xpath('.//span[@class="score"]/text()') or ["0"])[0],
                'comment_count': comment_count,
                'img_url': img_url,
                'index_url': index_url,
                'url': param_url
            })
        return valid_items
    except Exception as e:
        print(f"列表页第 {page} 页解析失败: {e}")
        return []


def fetch_params(item):
    """抓取嵌套 JSON 参数"""
    res = { 'pid': item['pid'],'product_name': item['name'], 'sub_images': [],'all_params': {}}
    try:
        # --- 步骤 1：访问详情主页获取轮播图 ---
        if item['index_url']:
            resp_idx = session.get(item['index_url'], timeout=10)
            resp_idx.encoding = 'gbk'
            tree_idx = etree.HTML(resp_idx.text)
            img_srcs = tree_idx.xpath('//ul[@class="clearfix"]//img/@src')
            # 补全协议头并去重
            res['sub_images'] = list(set([f"https:{s}" if s.startswith('//') else s for s in img_srcs]))
        # --- 步骤 2：访问参数页获取详参 ---
        if item['url']:
            resp_param = session.get(item['url'], timeout=10)
            resp_param.encoding = 'gbk'
            tree_param = etree.HTML(resp_param.text)
            nested_specs = {}
            tables = tree_param.xpath('//div[@class="detailed-parameters"]//table')
            for table in tables:
                group_name = "".join(table.xpath('.//tr[1]/td/text()')).strip() or "其他参数"
                nested_specs[group_name] = {}
                for row in table.xpath('.//tr[position()>1]'):
                    k = "".join(row.xpath('./th/span/text()')).strip()
                    v = "".join(row.xpath('./td/span/a/text() | ./td/span/text()')).strip()
                    if k and v:
                        nested_specs[group_name][k] = v
            res['all_params'] = clean_nested_specs(nested_specs)
        return res

    except Exception as e:
        print(f"商品 {item['pid']} 详情抓取失败: {e}")
        return None


def fetch_reviews(item):
    """通过 API 抓取评论数据"""
    pid = item['pid']
    all_comments = []
    # 每个商品抓取前 6页评论
    for page in range(1, 3):
        api_url = f'https://detail.zol.com.cn/xhr4_Review_GetList_%5EproId={pid}%5Epage={page}.html'
        try:
            time.sleep(random.uniform(0.5, 2.0))
            data = session.get(api_url, timeout=10).json()
            html = data.get('list', '')
            if not html: break

            tree = etree.HTML(html)
            for node in tree.xpath('//div[@class="comments-item"]'):
                all_comments.append({
                    'pid': pid,
                    'username': (node.xpath('.//a[@class="name"]/text()') or ["anonymous"])[0].strip(),
                    'content': node.xpath('string(.//div[@class="words-article"])').strip().replace('\n', ' '),
                    'rating': (int(re.search(r'width:\s*(\d+)%',
                                             node.xpath('.//div[@class="star"]/em/@style')[0]).group(
                        1)) / 20) if node.xpath('.//div[@class="star"]/em/@style') else 0,
                    'date': (node.xpath('.//span[@class="date"]/text()') or [""])[0]
                })
            if data.get('isEnd') == 1: break
        except:
            break
    return all_comments


def save_to_mysql(items, params_list, reviews_list):
    """使用 Django ORM 执行入库 """
    params_map = {p['pid']: (p['all_params'], p.get('sub_images', [])) for p in params_list if p}
    with transaction.atomic():
        processed_products = []
        for item in items:
            params, sub_imgs = params_map.get(item['pid'], ({}, []))
            category_obj, _ = Category.objects.get_or_create( code=item['category'],defaults={'name': CATEGORY_MAP.get(item['category'], item['category']) } )
            brand_name = item['brand']
            if brand_name and brand_name != "其他": brand_obj, _ = Brand.objects.get_or_create(name=brand_name)
            else:brand_obj = None  # 如果是"其他"或空，设为空
            from decimal import Decimal
            price_str = item['price'].replace('￥', '').replace(',', '').strip()
            try:price_val = Decimal(price_str) if price_str and price_str != '暂无报价' else Decimal('0.00')
            except: price_val = Decimal('0.00')
            p_obj, created = Product.objects.update_or_create(
                prod_id=item['pid'],
                defaults={'category': category_obj, 'brand': brand_obj,'name': item['name'],'price': price_val,'rate': float(item['rate']) if item['rate'] else 0.0,
                          'comment_count': item['comment_count'],'img_url': item['img_url'], 'all_params': params, 'sub_images': sub_imgs,'stock': random.randint(10, 100), })
            processed_products.append(p_obj)
            print(f"[{'NEW' if created else 'UPD'}] {p_obj.name} - {category_obj.name}")
        # 批量存入评论表
        product_map = {p.prod_id: p for p in processed_products}
        db_reviews = []
        for r in reviews_list:
            p_instance = product_map.get(r['pid'])
            if p_instance:
                db_reviews.append(Review(
                    product=p_instance,
                    username=r['username'],
                    content=r['content'],
                    rating=r['rating'],
                    date=r['date']
                ))
        if db_reviews:
            Review.objects.bulk_create(db_reviews, ignore_conflicts=True)
            print(f"--- 批量导入评论成功: {len(db_reviews)} 条 ---")



if __name__ == '__main__':
    start_p = int(input('起始页数: '))
    end_p = int(input('结束页数: '))

    for p in range(start_p, end_p + 1):
        print(f"正在扫描第 {p} 页列表...")
        items = fetch_list_page(p)
        if not items: continue

        # 使用线程池并发抓取详情和评论
        print(f"正在并发抓取该页 {len(items)} 个商品的详细数据...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 抓取参数
            params_res = list(executor.map(fetch_params, items))
            review_res = list(executor.map(fetch_reviews, items))
        # 需要将嵌套的评论列表摊平
        flat_reviews = [rev for sublist in review_res for rev in sublist]

        # 执行入库
        save_to_mysql(items, params_res, reviews_list=flat_reviews)
        time.sleep(1)

    print("\n[完成] 数据已同步至 MySQL 数据库。")