import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { TabProvider } from './tabContext.jsx'
import { SettingsProvider } from './settings.jsx'
import { ProgressProvider } from './progress.jsx'
import { ToggleProvider } from './components/ToggleProvider.jsx'
import './index.css'

// Include the compiled build ID in the SW script URL so every frontend
// release triggers the update lifecycle (and its in-app refresh notice).
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`/sw.js?build=${__BUILD_ID__}`, { updateViaCache: 'none' })
      .then((registration) => registration.update().catch(() => {}))
      .catch(() => {})
  })
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <SettingsProvider>
      <ProgressProvider>
        <TabProvider>
          <ToggleProvider>
            <App />
          </ToggleProvider>
        </TabProvider>
      </ProgressProvider>
    </SettingsProvider>
  </React.StrictMode>
)
