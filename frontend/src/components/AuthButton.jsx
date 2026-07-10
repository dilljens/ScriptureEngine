import React, { useState } from 'react'

/**
 * AuthButton — optional Google sign-in for cross-device progress sync.
 *
 * Uses Google One Tap / Sign In With Google.
 * The user must set up a Google OAuth client ID in their Google Cloud Console
 * and add it to the app settings.
 *
 * For now, acts as a pass-through that shows sign-in flow
 * and stores the resulting user_id/name in localStorage.
 */
export default function AuthButton({ userId, userName, userAvatar, onLogin }) {
  const [open, setOpen] = useState(false)

  const handleSignIn = async () => {
    // Google Sign-In flow:
    // 1. Show Google One Tap or sign-in button
    // 2. On success, receive credential token
    // 3. Send to our backend: POST /api/v1/auth/google
    // 4. Backend verifies token, creates/returns user
    // 5. Store user info in localStorage
    // 6. Merge anonymous progress
    
    // For now, simulate with a prompt to set up Google Cloud
    setOpen(true)
  }

  const handleMerge = async () => {
    const anonId = localStorage.getItem('scripture_user_id')
    try {
      const r = await fetch('/api/v1/auth/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_token: localStorage.getItem('scripture_session_token') || '',
          anonymous_id: anonId,
        }),
      })
      const d = await r.json()
      if (d.ok) {
        alert(`Progress merged: ${d.data.total_merged} records`)
      }
    } catch {}
  }

  if (userName) {
    return (
      <div className="flex items-center gap-2 px-2 py-1 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
        {userAvatar ? (
          <img src={userAvatar} alt="" className="w-5 h-5 rounded-full" />
        ) : (
          <span className="w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-[10px] font-medium text-indigo-600 dark:text-indigo-400">
            {userName[0]?.toUpperCase() || '?'}
          </span>
        )}
        <span className="text-[10px] text-neutral-600 dark:text-neutral-400 font-medium">{userName}</span>
      </div>
    )
  }

  return (
    <>
      <button onClick={handleSignIn}
        className="px-2 py-1 rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-[10px] font-medium text-neutral-600 dark:text-neutral-400 cursor-pointer transition-colors flex items-center gap-1">
        <span className="text-xs">G</span>
        <span className="hidden sm:inline">Sign in</span>
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setOpen(false)}>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl border border-neutral-200 dark:border-neutral-700 p-6 max-w-sm mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Google Sign-In</h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-4">
              Sign in to sync your progress across devices. Your anonymous progress will be merged automatically.
            </p>
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mb-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
              To enable Google Sign-In, create a Google Cloud OAuth client ID and add it to the app configuration.
              <br /><br />
              Your current anonymous ID: <code className="text-indigo-600">{userId?.slice(0, 16)}…</code>
            </p>
            <div className="flex gap-2">
              <button onClick={() => setOpen(false)}
                className="flex-1 px-3 py-2 rounded-lg text-xs font-medium text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
                Close
              </button>
              <button onClick={() => { handleMerge(); setOpen(false) }}
                className="flex-1 px-3 py-2 rounded-lg text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 cursor-pointer transition-colors">
                Test Merge
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
