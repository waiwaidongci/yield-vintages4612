import {esc,fmt} from '../utils/format.js';import {table} from './common/table.js';import {status} from './common/status.js';
import {ACTIVE} from '../constants/enums.js';
function progress(run){
 if(run.status==='queued')return '<p class="progress-note">已入队，等待 worker 开始冻结…</p>';
 if(run.status==='freezing'||run.status==='frozen'){const pct=run.progress_total?Math.min(100,Math.round(run.progress_done/run.progress_total*100)):0;return `<div class="progress"><i style="width:${pct}%"></i></div><p class="progress-note">冻结底稿快照：已扫描 ${fmt(run.progress_done)} / ${fmt(run.progress_total)} 批，入册 ${fmt(run.lot_count)} 批（冻结期间可正常增改删底稿）</p>`}
 if(run.status==='calculating'||run.status==='running'){const pct=run.chunk_count?Math.min(100,Math.round(run.calc_index/run.chunk_count*100)):0;return `<div class="progress"><i style="width:${pct}%"></i></div><p class="progress-note">流式计算：已计算 ${fmt(run.calc_index)} / ${fmt(run.chunk_count)} 块</p>`}
 return '';
}
export function report(run){
 if(!run)return '<p class="empty">选择一个报告查看快照与结果。</p>';
 const snap=run.snapshot||{},legacy=Array.isArray(snap.sources);
 const origin=legacy?`来源 ${snap.sources.length} 行（旧版完整快照）`:`冻结边界 #${esc(snap.freeze_seq??'—')} · 入册 ${fmt(run.lot_count??snap.lot_count??0)} 批`;
 const snapView=legacy&&snap.sources.length>20?{...snap,sources:`共 ${snap.sources.length} 行，旧版完整快照从略展示`}:snap;
 return `<section class="report"><div class="report-top"><h2>${esc(run.name)}</h2>${status(run.status)}</div><p>口径：${esc(snap.policy?.version||'—')} · ${origin} · ${run.approved?'负责人已复核':'待复核'}</p>${ACTIVE.includes(run.status)?progress(run):''}${run.error?'<p class="error">失败原因：'+esc(run.error)+'</p>':''}${run.checksum?`<p class="checksum">SHA256 ${esc(run.checksum)}</p>`:'<p class="checksum">内容校验和将在冻结完成后生成</p>'}${run.result?`<div class="metrics">${Object.entries(run.result.summary).map(([k,v])=>`<div><small>${esc(k)}</small><strong>${fmt(v)}</strong></div>`).join('')}</div><p class="method">${esc(run.result.method)}</p>${run.result.warnings?.length?'<p class="warning">'+run.result.warnings.map(esc).join('；')+'</p>':''}${table(run.result.rows)}${run.result.trace?'<details><summary>逐笔分摊追溯</summary>'+table(run.result.trace)+'</details>':''}`:''}<details><summary>冻结口径与边界快照</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px">${esc(JSON.stringify(snapView,null,2))}</pre></details><p>${esc(run.review||'尚未填写复核说明')}</p></section>`;
}
