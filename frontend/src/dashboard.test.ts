import { describe, expect, it } from 'vitest'
import { bangkokDateKey, deadlineAttention, dueSoonTasks } from './dashboard'

const row=(id:number,deadline:string|null,tasks:{id:number;label:string;completed:boolean;due_date:string|null}[]=[])=>({
  id,title:`Scholarship ${id}`,provider:null,deadline,status:'saved',archived_at:null,checklist:tasks,
})

describe('Bangkok dashboard dates',()=>{
  it('changes the date at Bangkok midnight',()=>{
    expect(bangkokDateKey(new Date('2026-11-25T16:59:59Z'))).toBe('2026-11-25')
    expect(bangkokDateKey(new Date('2026-11-25T17:00:00Z'))).toBe('2026-11-26')
  })

  it('groups confirmed deadlines and ignores unknown dates',()=>{
    const attention=deadlineAttention([row(1,'2026-11-25'),row(2,'2026-11-26'),row(3,'2026-11-26'),row(4,null)],'2026-11-26')
    expect(attention.overdue.map(group=>group.date)).toEqual(['2026-11-25'])
    expect(attention.upcoming.map(group=>[group.date,group.items.length])).toEqual([['2026-11-26',2]])
  })

  it('includes incomplete overdue tasks through the fourteen-day boundary only',()=>{
    const tasks=[
      {id:1,label:'Overdue',completed:false,due_date:'2026-11-25'},
      {id:2,label:'Today',completed:false,due_date:'2026-11-26'},
      {id:3,label:'Boundary',completed:false,due_date:'2026-12-10'},
      {id:4,label:'Too late',completed:false,due_date:'2026-12-11'},
      {id:5,label:'Done',completed:true,due_date:'2026-11-26'},
      {id:6,label:'No date',completed:false,due_date:null},
    ]
    expect(dueSoonTasks([row(1,null,tasks)],'2026-11-26').map(entry=>entry.task.label)).toEqual(['Overdue','Today','Boundary'])
  })
})
