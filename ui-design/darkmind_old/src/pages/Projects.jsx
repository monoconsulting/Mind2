import React from 'react'
import { FiSearch, FiPlus } from 'react-icons/fi'

export default function Projects() {
  return (
    <div className="dm-card p-6">
      <div className="flex items-center gap-3 mb-4">
        <FiSearch className="text-dm-subt" />
        <input type="search" placeholder="Search projects..." className="flex-1" />
        <button className="dm flex items-center gap-2"><FiPlus /> New Project</button>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-dm-subt">
            <tr>
              <th className="text-left py-2 pr-4">Name</th>
              <th className="text-left py-2 pr-4">Owner</th>
              <th className="text-left py-2 pr-4">Status</th>
              <th className="text-left py-2 pr-4">Due</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({length:12}).map((_,i)=>(
              <tr key={i} className="border-t border-dm-border/60">
                <td className="py-3 pr-4">Project {i+1}</td>
                <td className="py-3 pr-4">{['Alice','Bob','Carol','Dave'][i%4]}</td>
                <td className="py-3 pr-4">
                  <span className="badge">{['Planned','Active','Review','Done'][i%4]}</span>
                </td>
                <td className="py-3 pr-4">2025-09-{String((i%28)+1).padStart(2,'0')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
