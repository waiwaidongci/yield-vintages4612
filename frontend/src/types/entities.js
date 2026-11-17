// API实体字段约定：来源{id,natural_key,data}、口径{id,version,data}、报告{id,status,snapshot(小快照{policy,period,freeze_seq}),checksum,result,approved,progress_total,progress_done,lot_count,calc_index,chunk_count}、计划{next_at,enabled}。底稿列表为{rows,total}分页结构。
export const ENTITY_KEYS=['sources','policies','runs','schedules','deliveries'];
