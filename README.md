# 砚泉试制良率口径簿

试制批次一次通过/返工/报废→冻结口径版本与加权透视→主管复核交付；历史快照不随口径改写

## 业务场景与工作流
模拟客户：砚泉研究协作组，12位业务与分析人员。每月研究明细先从`yield-vintages-202611.csv`录入底稿，经口径冻结、Python核算、负责人复核后向业务阅读者交付站内CSV。原有流程依靠人工表格抄算，痛点为口径版本难追溯、重复计算易错、复核与交付脱节。

模块：业务总览、业务底稿、新建口径版本、异步核算与复核、定时交付、站内收件箱、审计。底稿可新增/修改/删除；口径仅新增版本；报告提交时记录口径与一致性边界（底稿版本流水号），worker 分块冻结底稿快照并流式计算，完成后保存内容校验SHA256。定时交付引用已复核报告快照，worker到期写入数据库，业务阅读者下载。

## 百万批核算架构
底稿增改删在同一事务内向`yield_lot_versions`追加版本行（自增序列为全局一致性点，删除为tombstone），写入永不阻塞。提交核算只记录`{口径, 期间, freeze_seq}`小快照，进程内存O(1)。worker按`lot_id`键集分页解析发起时刻同版底稿，每2000批（`FREEZE_BATCH`可调）写一个原子替换的JSONL块文件至共享卷，游标与块清单同事务提交；计算逐块流式累加，透视累加器规模=期间×试制线×班次（有界），每块落检查点。排队/冻结/计算每进程额外内存实测<12MB（百万批，限128MB）。冻结期间底稿可并发增改删：发起后修改/删除不影响已发起报告，已删批次按发起时原值入册。worker重启或任务失败可从断点续跑，重试不漏批、不重复计入；页面展示分阶段进度与失败原因，失败任务可一键重试。完整核算（completed）后才允许复核与定时交付；既有报告的全量快照与结果保持原值。

## 算法口径
版本化良率分母规则、加权汇总与按线/班次差异归因。分母规则手算；大批小批汇总不能均值；更新规则旧run不变。

口径版本冻结 · 汇总按分母加权。输入：业务底稿与口径JSON；输出：summary、透视rows、method、warnings。算法实现在`backend/src/services/calculation.py`（`accumulate`/`build_result`为流式与原全量共用的同一口径），输入校验在`validation.py`，分块流水线在`pipeline.py`。固定seed=42，240条合成数据；未对接真实业务系统。修改源数据和新建因子/口径不会改变已提交报告。

## 一天的验收剧本
1. 09:00 admin查看240条seed底稿与具名业务期间。
2. 09:10 analyst添加`yield-vintages-202611.csv`的一条具名业务记录。
3. 09:20 admin在口径版本页登记新版本；旧版本保留。
4. 09:30 analyst命名"十一月核算"并选择期间/版本排队。
5. 09:31 Redis worker分块冻结底稿并流式计算，页面实时展示冻结/计算进度；期间analyst继续增改删底稿，报告不受影响。
6. 09:35 重启worker容器，中断任务自动从断点续跑；失败任务页面展示原因并可重试。
7. 09:40 admin核对数值后填写至少4字复核说明（仅completed报告可复核）。
8. 09:45 admin建立60秒周期计划，worker到期生成站内持久化交付。
9. 09:46 viewer在站内收件箱下载交付CSV；审计页查看操作者与时间。

## 快速启动
```sh
cp .env.example .env
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```
前端 http://localhost:18253 ，后端 http://localhost:19253/docs ，数据库宿主端口17753。中文父目录可用。恰好5服务frontend/backend/worker/db/redis；均有真实healthcheck。停止并清空演示数据：`docker compose down -v --remove-orphans`。

|角色|邮箱|密码|权限|
|---|---|---|---|
|admin|admin@demo.local|Demo2026!|全部底稿、口径版本、核算、复核、调度|
|analyst|analyst@demo.local|Demo2026!|底稿增改删、核算、导出；无复核/调度/口径写权限|
|viewer|viewer@demo.local|Demo2026!|只读；仅可下载已复核报告与站内交付|

## 工程结构与开发
Python3.11/FastAPI/SQLAlchemy/Redis，MySQL8；前端原生HTML/CSS/JS ES modules，Nginx代理`/api/`剥前缀至后端。`frontend/src`按api/stores/pages/components/hooks/utils/router/constants/types拆分；`backend/src`按models/schemas/services/controllers/routes/middlewares/config/utils/constants拆分；`backend/scripts/seed_demo.py`自然键幂等且不覆盖用户修改。SQLAlchemy启动创建初始结构，迁移说明在backend/migrations。

后端开发：在backend安装requirements，设置DATABASE_URL/REDIS_URL/JWT_SECRET，`uvicorn src.main:app --reload`；前端可用Nginx或带同等代理的静态开发服务器。前后端全部业务计算在Python。

环境变量：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、JWT_SECRET（部署替换）、DATABASE_URL、REDIS_URL、SEED_DEMO、ARTIFACT_DIR（冻结块文件目录，默认/app/artifacts）、FREEZE_BATCH（每块批数，默认2000）。`.env`不入Git。数据库/Redis/共享产物为命名卷。共享角色枚举admin/analyst/viewer与状态queued/freezing/frozen/calculating/completed/failed分别定义于backend/src/constants/enums.py和frontend/src/constants/enums.js。两个中间件：统一可恢复校验错误、每IP每分钟360请求限流。

## 已知边界
定时分发为站内收件箱；一名worker轮询执行，无外部邮件。调度发送已复核固定报告快照，不自动重算新数据。时间显示Asia/Shanghai。底稿列表分页返回（默认最新500条），期间取自期间字典表，均不再全量加载；报告结果透视行数=期间×试制线×班次，与批数无关。冻结块文件保留在共享卷供断点续算与审计，不随报告删除清理。底稿版本流只追加，长期增长需按需归档。Google Fonts不可用时回退serif。后端API以专属字段对象收发，页面通过业务输入控件编辑，不要求用户写JSON。新增来源期间自动可选；专属字段和算法严格校验。JWT演示有效期2小时。

MIT License。

## 实际实体映射
来源记录（Source，专属业务字段校验）、口径版本（Policy）、核算报告（Run）、交付计划（Schedule）、交付（Delivery）均经数据库→模型→请求schema→service→route/controller→frontend API→store→page。Period为已有来源期间字典，在任务期间选择器使用；不单独作为复杂度计数。底稿JSON为小型多字段单记录存储，不虚构未落库的子实体。

实际表：期间字典 yield_periods；专属来源 yield_lots；底稿版本流 yield_lot_versions；冻结口径 denominator_policies；异步报告 yield_runs。既有数据库升级见backend/migrations/002_freeze_pipeline.md。
