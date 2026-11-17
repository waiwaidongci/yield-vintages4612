# 002 分块冻结与流式核算

为解决百万批底稿全量冻结耗尽内存的问题，核算改为"版本化底稿 + 一致性边界 + 分块冻结 + 流式计算"。已有数据库请先备份，再执行：

```sql
-- 底稿版本流水：只追加不改写；自增id即全局一致性序列；删除为tombstone
CREATE TABLE yield_lot_versions (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  lot_id INT NOT NULL,
  natural_key VARCHAR(120),
  data JSON NULL,
  deleted TINYINT(1) NOT NULL DEFAULT 0,
  created DOUBLE NOT NULL,
  KEY ix_yield_lot_versions_lot_id (lot_id)
);

-- 核算任务新增断点与进度列（既有报告行保持原值，默认0/NULL不影响展示）
ALTER TABLE yield_runs
  ADD COLUMN freeze_cursor INT DEFAULT 0,
  ADD COLUMN progress_total INT DEFAULT 0,
  ADD COLUMN progress_done INT DEFAULT 0,
  ADD COLUMN lot_count INT DEFAULT 0,
  ADD COLUMN chunks JSON NULL,
  ADD COLUMN calc_index INT DEFAULT 0,
  ADD COLUMN calc_state JSON NULL,
  ADD COLUMN updated DOUBLE DEFAULT 0;

UPDATE yield_runs SET updated = created WHERE updated = 0;

-- 历史底稿一次性补登记版本（幂等；此后增改删由应用同事务写版本行）
INSERT INTO yield_lot_versions (lot_id, natural_key, data, deleted, created)
SELECT l.id, l.natural_key, l.data, 0, UNIX_TIMESTAMP()
FROM yield_lots l LEFT JOIN yield_lot_versions v ON v.lot_id = l.id
WHERE v.id IS NULL;

-- 升级前卡在 running 的旧任务重置为排队，worker 将按旧版全量快照原算法收尾
UPDATE yield_runs SET status = 'queued' WHERE status = 'running';
```

说明：
- 新报告的 `snapshot` 只存 `{policy, period, freeze_seq}` 小对象，冻结完成后补 `lot_count/chunk_count`；`checksum` 在冻结完成时由块哈希链生成。既有报告的完整快照与结果不改动。
- 冻结块文件写入共享卷 `report-files`（`/app/artifacts/runs/<id>/lots-*.jsonl`），确定性命名、原子替换，重试安全。
- 底稿删除在版本流中记 tombstone，已删批次仍按发起时原值参与已发起的报告。
