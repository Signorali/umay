import React, { Suspense } from 'react'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { FeedbackButton } from './FeedbackButton'
import { OverdueModal } from './OverdueModal'

function PageSpinner() {
  return (
    <div className="loading-state">
      <div className="spinner" />
      <span>Loading...</span>
    </div>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <Topbar />
        <main className="app-content">
          <Suspense fallback={<PageSpinner />}>
            {children}
          </Suspense>
        </main>
      </div>
      <FeedbackButton />
      <OverdueModal />
    </div>
  )
}
