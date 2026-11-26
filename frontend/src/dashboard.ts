export const BANGKOK_TIME_ZONE = 'Asia/Bangkok'
export const DUE_SOON_DAYS = 14

export type DashboardTask = {
  id:number
  label:string
  completed:boolean
  due_date:string|null
}

export type DashboardItem = {
  id:number
  title:string|null
  provider:string|null
  deadline:string|null
  status:string
  archived_at:string|null
  checklist:DashboardTask[]
}

export type DeadlineGroup = { date:string; items:DashboardItem[] }
export type DueTask = { task:DashboardTask; scholarship:DashboardItem }

export function bangkokDateKey(now=new Date()):string {
  return new Intl.DateTimeFormat('en-CA',{
    timeZone:BANGKOK_TIME_ZONE,
    year:'numeric',
    month:'2-digit',
    day:'2-digit',
  }).format(now)
}

export function dateKeyPlusDays(dateKey:string,days:number):string {
  const date=new Date(`${dateKey}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate()+days)
  return date.toISOString().slice(0,10)
}

export function formatDate(dateKey:string):string {
  return new Intl.DateTimeFormat('en-GB',{
    timeZone:BANGKOK_TIME_ZONE,
    weekday:'short',
    day:'numeric',
    month:'short',
    year:'numeric',
  }).format(new Date(`${dateKey}T12:00:00Z`))
}

function groupDeadlines(items:DashboardItem[]):DeadlineGroup[] {
  const groups=new Map<string,DashboardItem[]>()
  for(const item of items){
    if(!item.deadline||item.archived_at)continue
    groups.set(item.deadline,[...(groups.get(item.deadline)||[]),item])
  }
  return [...groups].sort(([left],[right])=>left.localeCompare(right)).map(([date,rows])=>({date,items:rows}))
}

export function deadlineAttention(items:DashboardItem[],today=bangkokDateKey()) {
  const groups=groupDeadlines(items)
  return {
    overdue:groups.filter(group=>group.date<today),
    upcoming:groups.filter(group=>group.date>=today),
  }
}

export function dueSoonTasks(items:DashboardItem[],today=bangkokDateKey(),days=DUE_SOON_DAYS):DueTask[] {
  const lastDay=dateKeyPlusDays(today,days)
  return items.flatMap(scholarship=>scholarship.archived_at?[]:scholarship.checklist
    .filter(task=>!task.completed&&!!task.due_date&&task.due_date<=lastDay)
    .map(task=>({task,scholarship})))
    .sort((left,right)=>(left.task.due_date||'').localeCompare(right.task.due_date||'')||left.task.label.localeCompare(right.task.label))
}
