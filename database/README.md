# 商品入库

`import_products.py` 把已经确认的商品数据导入 `Product`、`Brand` 和 `Category`。

## 推荐流程

1. 在 `products_raw.xlsx` 的 `cleaning_result` 工作表中清洗字段。
2. 将确认可以入库的行标记为 `approved`。
3. 先执行预检：

   ```powershell
   python database/import_products.py data/raw/<批次号>/products_raw.xlsx --dry-run
   ```

4. 预检通过后执行正式导入：

   ```powershell
   python database/import_products.py data/raw/<批次号>/products_raw.xlsx
   ```

也可以导入 `products_raw.json`。JSON 是采集快照，默认需要显式允许未审核数据：

```powershell
python database/import_products.py data/raw/<批次号>/products_raw.json --allow-unapproved --dry-run
python database/import_products.py data/raw/<批次号>/products_raw.json --allow-unapproved
```

Excel 默认读取 `cleaning_result`。如果确实要读取原始工作表，需显式指定并允许未审核数据：

```powershell
python database/import_products.py data/raw/<批次号>/products_raw.xlsx --sheet products_raw --allow-unapproved --dry-run
```

## 入库规则

- 通过 `prod_id` 幂等更新商品，重复执行不会产生重复商品。
- 品牌按名称去重，分类按 `category_code` 去重。
- `price` 会去除货币符号和千分位，无法解析或超出数据库范围时整批失败。
- `all_params` 可以是 Excel 单元格中的 JSON 文本或 JSON 文件中的对象，必须是“分组对象”结构。
- `stock` 默认 0，`is_active` 默认 `True`；清洗表可以覆盖这两个默认值。
- 所有商品在同一个事务中写入；任意一行校验失败都不会写入数据库。
- `--dry-run` 会执行完整事务流程并回滚，适合在正式导入前确认数据。
