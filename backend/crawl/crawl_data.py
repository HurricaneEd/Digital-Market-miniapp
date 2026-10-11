import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.styles import Alignment, Font, PatternFill

import requests
from lxml import etree


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RAW_OUTPUT_ROOT = REPOSITORY_ROOT / 'data' / 'raw'

CATEGORY_MAP = {
    'digital_camera': '数码相机',
}

HEADERS = {
    'User-Agent': '替换为自己的',
    'Referer': 'https://detail.zol.com.cn/',
    'cookie': '替换为自己的'
}

session = requests.Session()
session.headers.update(HEADERS)


def get_best_brand(product_name, brand_map):
    """根据中文名、英文别名和来源 slug 推断品牌。"""
    brand_aliases = {
        '红米': ['redmi'],
        '华为': ['huawei'],
    }
    name_lower = product_name.lower()

    for brand_id, brand_name in brand_map.items():
        if brand_name in product_name:
            return brand_name

        aliases = brand_aliases.get(brand_name, [])
        if any(alias in name_lower for alias in aliases):
            return brand_name

        if not brand_id.isdigit() and brand_id and brand_id in name_lower:
            return brand_name

    return '其他'


def fetch_list_page(page, category_slug='cell_phone'):
    """抓取商品列表页；本函数不请求评论接口。"""
    url = "https://detail.zol.com.cn/cell_phone_index/subcate57_list_1.html"
    try:
        response = session.get(url, timeout=20)
        response.encoding = 'gbk'
        tree = etree.HTML(response.text)

        brand_map = {}
        for node in tree.xpath('//div[@id="J_BrandAll"]/a'):
            link_key = (node.xpath('./@data-link') or [''])[0].lower()
            brand_text = ''.join(node.xpath('.//text()')).strip()
            if brand_text:
                brand_map[link_key] = brand_text

        valid_items = []
        for item_node in tree.xpath('//ul[@id="J_PicMode"]/li'):
            name = (item_node.xpath('./a/img/@alt') or [''])[0].strip()

            # 仅从列表中的已有链接解析商品 ID，用于拼装参数页地址；不请求评论接口。
            href_nodes = item_node.xpath('.//a[@class="comment-num"]/@href')
            if not href_nodes:
                continue
            path_parts = [part for part in href_nodes[0].split('/') if part]
            if len(path_parts) < 2:
                continue
            category_id, product_id = path_parts[:2]
            image_url = (item_node.xpath('./a/img/@*[name()=".src"] | ./a/img/@src') or [''])[0]
            valid_items.append({
                'prod_id': product_id,
                'category_code': category_slug,
                'category_name': CATEGORY_MAP.get(category_slug, category_slug),
                'brand': get_best_brand(name, brand_map),
                'name': name,
                'price': (item_node.xpath('.//b[@class="price-type"]/text()') or [''])[0].strip(),
                'img_url': image_url,
                '_source_category_id': category_id,
            })
        return valid_items
    except Exception as exc:
        print(f'列表页第 {page} 页解析失败: {exc}')
        return []


def fetch_params(item):
    """抓取商品参数；参数页地址只在内存中使用，不进入导出结果。"""
    result = {
        'prod_id': item['prod_id'],
        'all_params': {},
    }
    try:
        if item.get('_source_category_id'):
            response = session.get(
                f"https://detail.zol.com.cn/{item['_source_category_id']}/{item['prod_id']}/param.shtml",
                timeout=10,
            )
            response.encoding = 'gbk'
            tree = etree.HTML(response.text)
            nested_specs = {}
            for table in tree.xpath('//div[@class="detailed-parameters"]//table'):
                group_name = ''.join(table.xpath('.//tr[1]/td/text()')).strip() or '其他参数'
                nested_specs[group_name] = {}
                for row in table.xpath('.//tr[position()>1]'):
                    key = ''.join(row.xpath('./th/span/text()')).strip()
                    value = ''.join(row.xpath('./td/span/a/text() | ./td/span/text()')).strip()
                    if key and value:
                        nested_specs[group_name][key] = value
            result['all_params'] = nested_specs
        return result
    except Exception as exc:
        print(f"商品 {item['prod_id']} 详情抓取失败: {exc}")
        return None


def _build_snapshot(items, params_list, batch_id, collected_at):
    params_map = {
        item['prod_id']: item
        for item in params_list
        if item and item.get('prod_id')
    }
    products = []
    for item in items:
        details = params_map.get(item['prod_id'], {})
        products.append({
            'batch_id': batch_id,
            'collected_at': collected_at,
            'prod_id': item['prod_id'],
            'category_code': item['category_code'],
            'category_name': item['category_name'],
            'brand': item['brand'],
            'name': item['name'],
            'price': item['price'],
            'img_url': item['img_url'],
            'all_params': details.get('all_params', {}),
        })
    return products


def _write_sheet(workbook, title, headers, rows):

    sheet = workbook.create_sheet(title)
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, '') for header in headers])

    header_fill = PatternFill('solid', fgColor='1F4E78')
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(color='FFFFFF', bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    sheet.freeze_panes = 'A2'
    if rows:
        end_row = len(rows) + 1
        end_col = len(headers)
        end_letter = sheet.cell(1, end_col).column_letter
        table = Table(displayName=f'{title}Table', ref=f'A1:{end_letter}{end_row}')
        table.tableStyleInfo = TableStyleInfo(
            name='TableStyleMedium2',
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        sheet.add_table(table)

    for column_cells in sheet.columns:
        column_letter = column_cells[0].column_letter
        max_length = max(len(str(cell.value or '')) for cell in column_cells)
        sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 42)

    return sheet


def export_raw_data(items, params_list, category_slug, start_page, end_page, batch_id=None):
    """导出一个采集批次的 Excel、JSON 和元数据，不写入数据库。"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError as exc:
        raise RuntimeError('导出 Excel 需要安装 openpyxl：pip install openpyxl') from exc

    collected_at = datetime.now(timezone.utc).isoformat()
    batch_id = batch_id or datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = RAW_OUTPUT_ROOT / batch_id
    output_dir.mkdir(parents=True, exist_ok=True)
    products = _build_snapshot(items, params_list, batch_id, collected_at)

    product_rows = []
    cleaning_rows = []
    for row_number, product in enumerate(products, start=1):
        all_params_json = json.dumps(product['all_params'], ensure_ascii=False, separators=(',', ':'))
        product_rows.append({
            'batch_id': batch_id,
            'row_number': row_number,
            'collected_at': collected_at,
            'prod_id': product['prod_id'],
            'category_code': product['category_code'],
            'category_name': product['category_name'],
            'brand': product['brand'],
            'name': product['name'],
            'price': product['price'],
            'img_url': product['img_url'],
            'all_params': all_params_json,
        })
        cleaning_rows.append({
            'prod_id': product['prod_id'],
            'category_code': product['category_code'],
            'brand': product['brand'],
            'name': product['name'],
            'price': product['price'],
            'img_url': product['img_url'],
            'all_params': all_params_json,
            'stock': 0,
            'is_active': True,
            'status': 'pending',
            'cleaning_note': '',
        })

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)
    readme = workbook.create_sheet('README')
    readme.append(['采集批次', batch_id])
    readme.append(['采集时间（UTC）', collected_at])
    readme.append(['分类', category_slug])
    readme.append(['页码范围', f'{start_page}-{end_page}'])
    readme.append(['商品数量', len(products)])
    readme.append([])
    readme.append(['使用说明'])
    readme.append(['1', 'products_raw 是只读原始快照；all_params 单元格保存嵌套 JSON。'])
    readme.append(['2', '在 cleaning_result 中清洗固定字段与 all_params；status 使用 pending/approved/rejected。'])
    readme.append(['3', '只导入 status=approved 且通过校验的记录；完整原始 JSON 同步保存在 products_raw.json。'])
    for cell in readme['A']:
        cell.font = Font(bold=True if cell.row in (1, 7) else False)
    readme.column_dimensions['A'].width = 24
    readme.column_dimensions['B'].width = 100

    _write_sheet(workbook, 'products_raw', [
        'batch_id', 'row_number', 'collected_at', 'prod_id', 'category_code',
        'category_name', 'brand', 'name', 'price', 'img_url', 'all_params',
    ], product_rows)
    _write_sheet(workbook, 'cleaning_result', [
        'prod_id', 'category_code', 'brand', 'name', 'price', 'img_url',
        'all_params', 'stock', 'is_active', 'status', 'cleaning_note',
    ], cleaning_rows)

    workbook.save(output_dir / 'products_raw.xlsx')
    with (output_dir / 'products_raw.json').open('w', encoding='utf-8') as file:
        json.dump(products, file, ensure_ascii=False, indent=2)

    metadata = {
        'batch_id': batch_id,
        'collected_at': collected_at,
        'category_slug': category_slug,
        'start_page': start_page,
        'end_page': end_page,
        'product_count': len(products),
        'parameter_success_count': sum(1 for item in params_list if item),
        'database_write': False,
    }
    with (output_dir / 'metadata.json').open('w', encoding='utf-8') as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    return output_dir


if __name__ == '__main__':
    category_slug = input('分类 slug（默认 mice）: ').strip() or 'mice'
    start_page = int(input('起始页数: '))
    end_page = int(input('结束页数: '))
    batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    all_items = []
    all_params = []

    for page in range(start_page, end_page + 1):
        print(f'正在扫描第 {page} 页商品...')
        page_items = fetch_list_page(page, category_slug)
        if not page_items:
            continue

        print(f'正在并发抓取该页 {len(page_items)} 个商品参数...')
        with ThreadPoolExecutor(max_workers=5) as executor:
            page_params = list(executor.map(fetch_params, page_items))
        all_items.extend(page_items)
        all_params.extend(page_params)

        output_dir = export_raw_data(
            all_items,
            all_params,
            category_slug,
            start_page,
            end_page,
            batch_id=batch_id,
        )
        print(f'当前批次快照已保存：{output_dir}')
        time.sleep(1)

    if all_items:
        print(f'\n[完成] 原始商品数据已导出，共 {len(all_items)} 条。')
    else:
        print('\n[完成] 未采集到商品，未生成有效数据。')
