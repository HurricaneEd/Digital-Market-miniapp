# AGENTS.md

## 项目定位

DigRecSys 是一个数码商品交易项目。后端使用 Python 3.11、Django 5.2、Django REST Framework 3.16 和 MySQL；仓库还包含商品采集/入库工具及微信原生小程序客户端。

所有工作必须以当前代码、迁移和实际测试结果为准。不要根据规划文档虚构功能、接口、测试结果或运行状态。

## 开始工作前

1. 阅读与任务范围相关的模型、序列化器、视图、路由、迁移和测试。

2. 执行 `git status --short`，保留用户已有修改，不覆盖或清理无关文件。

3. 优先使用 `rg`、`rg --files` 定位实现和调用方。

4. 设计UI设计时参考`/docs/design.md`

   

## 仓库地图

- `DigRecSys/`：Django 全局设置、根路由、ASGI/WSGI 入口。
- `Users/`：用户模型、认证、个人资料和后台用户接口。
- `Product/`：品牌、分类、商品、评论及相关 API。
- `Orders/`：地址、购物车、订单、订单明细及交易流程。
- `crawl/`：商品采集脚本；输出原始 Excel/JSON，不直接写业务数据库。
- `database/`：经过校验的商品入库工具和使用说明。
- `data/raw/`：按批次保存的原始采集快照，不属于线上业务表。
- `miniapp/`：微信原生小程序；`miniprogram_npm/` 是构建生成的第三方代码。
- `docs/`：架构、验收、变更和测试等项目事实记录，项目UI样式设计规则。

## 架构约束

- 根路由 `DigRecSys/urls.py` 只负责 `include` 应用路由、管理后台和 API 文档。
- DRF Router 和 ViewSet 路由由 `Users/urls.py`、`Product/urls.py`、`Orders/urls.py` 分别维护。
- 线上商品统一使用 `Product`；不要重新引入 `CleanProduct` 或第二套商品事实来源。
- 商品采用固定核心字段加 `all_params` JSON。品牌、分类、价格、库存、上下架状态不得重复塞入 JSON。
- 不恢复 EAV 参数表、多图模型、`source_url`、`params_url` 或 `sub_images`，除非用户提出新的明确需求。
- 爬虫只采集商品信息，不请求评论接口。评论模型与 API 保留给线上用户和未来独立导入。
- 不恢复已移除的推荐、词频统计或情感分析脚本，除非用户明确要求重新设计。
- 订单明细价格、商品编码/名称和收货地址是交易快照，不得按当前商品或地址反向覆盖。
- 创建、支付、取消订单时保持事务一致性、库存校验和重复操作保护。

## 数据库与迁移

- 当前数据库为 MySQL，ORM 模型是数据库结构的代码来源。
- 修改模型后必须创建新的迁移，并运行迁移一致性检查。
- 已应用迁移不得重写、删除或伪造；除非用户明确要求重建一个可丢弃的空数据库。
- 未经明确授权，不执行删库、删表、清空数据、迁移回退或 `--fake`。
- 金额使用 `Decimal`，不要用 `float` 参与交易金额计算。
- 优先使用外键、唯一约束、检查约束和事务维护核心不变量。
- 数据迁移必须考虑已有行；无法安全推导的值应请求确认，不得编造。

## 商品采集与入库

- `data/raw/` 是原始证据，默认只读；不要覆盖、重命名或删除已有批次。
- 爬虫输出固定核心字段和 `all_params`，不直接写数据库。
- Excel 默认从 `cleaning_result` 导入，且只接受 `status=approved` 的记录。
- JSON 原始快照只有在用户确认后才能使用 `--allow-unapproved` 导入。
- 正式入库前先运行 `--dry-run`；报告读取、跳过、新增和更新数量。
- 未经明确要求，不自动重新采集、联网抓取或批量导入数据。

常用入库命令：

```powershell
python database/import_products.py data/raw/<批次号>/products_raw.xlsx --dry-run
python database/import_products.py data/raw/<批次号>/products_raw.xlsx
python database/import_products.py data/raw/<批次号>/products_raw.json --allow-unapproved --dry-run
```

## Django/DRF 编码规则

- 保持应用边界，业务逻辑放在拥有该概念的应用中，避免把所有逻辑堆入根配置或总路由。
- API 字段由 Serializer 明确声明；新增或删除字段时同步检查调用方、Swagger、测试和小程序。
- 输入校验放在 Serializer、模型约束或服务边界，避免依赖数据库异常作为正常控制流。
- 查询列表时检查 N+1，按关系使用 `select_related`、`prefetch_related` 和必要索引。
- 批量操作应先完整验证输入，再在事务中修改数据，并返回可核对的结果。
- 沿用 `CONTEXT.md` 中的领域术语和现有英文标识；面向用户的提示保持中文一致性。
- 优先做小而聚焦的修改，不借任务之机升级框架、替换数据库或重写无关模块。

仓库当前没有 `requirements.txt` 或 `pyproject.toml`。不要声称依赖可由不存在的清单安装；新增生产依赖前先确认，并同步建立或更新依赖清单。

## 代码质量与简化规则

- 在满足当前需求、兼容性和数据安全的前提下选择最直接的实现；不要为了假设中的未来需求提前增加抽象层、配置项或第二套流程。
- 优先复用现有模型、接口、服务和工具函数。相同业务规则只保留一个事实来源，出现重复分支时提取有明确领域名称的共享逻辑。
- 函数和方法只承担一个清晰职责。主流程被多层嵌套遮挡时，优先使用提前返回或拆分短小辅助函数，但不要把简单逻辑切成大量单行封装。
- 命名应表达业务意图和数据单位，避免在较大作用域使用 `data`、`temp`、`handle` 等含义模糊的名称；重复业务值使用具名常量，避免散落的魔法数字和字符串。
- 注释和文档字符串用于说明“为什么这样做”、事务不变量、安全约束或不明显的兼容原因，不逐行复述代码。关键复杂逻辑应有必要且简短的注释；代码变化时同步更新或删除失效注释。
- 公共模块、公共类和不易从签名理解的公共函数应提供简短文档字符串；简单私有辅助函数无需为满足形式而增加无信息注释。
- 不静默吞掉异常。仅在系统边界需要转换、记录或补充上下文时捕获异常，并尽量捕获具体异常；返回给用户的错误应可理解，日志不得泄露敏感数据。
- 输入在 Serializer、表单或请求边界一次性校验，后续逻辑只使用已验证数据；涉及金额、库存、权限和状态流转时，服务端校验不得依赖前端结果。
- 查询代码避免循环内重复访问数据库；按实际关系使用 `select_related`、`prefetch_related`、聚合或批量操作，但没有证据时不做复杂的提前优化。
- 修复缺陷时增加能复现问题的回归测试；新增业务流程至少覆盖成功路径、关键边界和失败时不产生部分写入。测试名称直接描述可观察行为。
- 保持改动小而聚焦，删除本次修改产生的未使用导入、死代码和调试输出，不顺手格式化或重构无关文件。
- Python 代码遵循 PEP 8 和仓库既有风格；发生冲突时优先保证同一模块的一致性和可读性。参考：[PEP 20](https://peps.python.org/pep-0020/)、[PEP 8](https://peps.python.org/pep-0008/)、[Django 5.2 编码风格](https://docs.djangoproject.com/en/5.2/internals/contributing/writing-code/coding-style/) 和 [DRF Serializer 校验](https://www.django-rest-framework.org/api-guide/serializers/#validation)。

## 微信小程序

- `miniapp/` 使用微信原生小程序结构和 Vant Weapp。
- 不直接编辑 `miniapp/miniprogram_npm/`；应修改源配置/依赖后通过微信开发者工具重新构建 npm。
- 不新增散落的硬编码 API 地址；修改请求层时应集中管理 base URL、Token 和错误处理。
- 不在小程序代码中写入密码、Secret、固定 Token 或真实个人信息。
- 未在微信开发者工具中实际执行的页面和交互，必须标记 `NEEDS_MANUAL_VERIFICATION`，不能写成 PASS。

## 验证命令

根据改动范围运行最小充分验证：

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test Product
python manage.py test Orders
python manage.py test Users
python manage.py test
```

- 修改单个应用时先运行该应用测试；修改共享模型、认证、订单或路由时运行所有相关应用测试。
- 数据库约束和事务变化优先使用真实 ORM/API 测试，不只做语法检查。
- 文档或静态配置修改至少执行适用的格式/引用检查和 `git diff --check`。
- 若测试依赖不可用、MySQL 测试库无权限或 GUI 环境无法运行，如实记录错误并标记未验证。
- 不伪造通过率、性能数据、测试数量、Bug 或人工验收结果。

## 安全与变更边界

- 不提交或输出数据库密码、Cookie、Token、Secret、私钥和真实个人数据。
- 现有配置中的硬编码凭据视为待治理的遗留问题，不要复制到新文件。
- 未经用户明确要求，不安装依赖、不提交、不推送、不部署，也不修改外部服务状态。
- 不使用破坏性 Git 命令清理工作区，不删除无法确认归属的文件。
- 删除接口、模型或脚本前搜索所有引用，并同步检查路由、序列化器、测试和文档。

## 完成标准

交付前应：

1. 检查最终差异是否只覆盖请求范围。
2. 运行与风险匹配的检查和测试。
3. 明确列出修改文件、实际执行命令及结果。
4. 报告任何失败、跳过项、环境限制和需要人工验证的内容。
5. 不把计划、推断或未执行步骤描述为已完成事实。
