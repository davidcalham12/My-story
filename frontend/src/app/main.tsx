import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { Boundary } from '@/shared/ui/Boundary'
import '@/shared/ui/styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* The floor. The keyed boundary inside App keeps a failure to one screen;
        this one catches anything outside it, so no arrangement of bad data can
        produce a blank document. */}
    <Boundary what="The panel">
      <App />
    </Boundary>
  </StrictMode>,
)
