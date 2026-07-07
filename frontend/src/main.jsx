import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { TabProvider } from './tabContext.jsx'
import { SettingsProvider } from './settings.jsx'
import { ProgressProvider } from './progress.jsx'
import { ToggleProvider } from './components/ToggleProvider.jsx'
import './index.css'

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
