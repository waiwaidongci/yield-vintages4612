import {request} from './client.js';
export const loadAll=async()=>{
 const [sources,periods,policies,runs,schedules,deliveries,audits]=await Promise.all(['/sources?limit=500','/periods','/policies','/runs','/schedules','/deliveries','/audits'].map(request));
 return{sources:sources.rows,sources_total:sources.total,periods,policies,runs,schedules,deliveries,audits};
};
export const saveSource=(data,id)=>request('/sources'+(id?'/'+id:''),id?'PUT':'POST',{data});
export const savePolicy=data=>request('/policies','POST',{data});
export const submitRun=data=>request('/runs','POST',data);
export const approveRun=(id,note)=>request('/runs/'+id+'/approve','POST',{note});
export const retryRun=id=>request('/runs/'+id+'/retry','POST',{});
