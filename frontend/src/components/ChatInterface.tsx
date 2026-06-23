'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import MessageBubble from './MessageBubble'
import ToolCallCard from './ToolCallCard'

type ChatItem =
  | { kind: 'user';      id: string; content: string }
  | { kind: 'agent';     id: string; content: string }
  | { kind: 'tool_call'; id: string; name: string; args: Record<string, unknown> }
  | { kind: 'thinking';  id: string }

export default function ChatInterface() {
  const [items, setItems] = useState<ChatItem[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 130)}px`
  }, [input])

  const send = useCallback(async () => {
    const text = input.trim()
    if (!text || busy) return

    setInput('')
    setBusy(true)

    const thinkingId = `thinking-${Date.now()}`
    setItems(prev => [
      ...prev,
      { kind: 'user', id: `u-${Date.now()}`, content: text },
      { kind: 'thinking', id: thinkingId },
    ])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, thread_id: 'traveler_1' }),
      })

      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let thinkingGone = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: Record<string, unknown>
          try { event = JSON.parse(raw) } catch { continue }

          if (!thinkingGone && event.type !== 'done') {
            setItems(prev => prev.filter(i => i.id !== thinkingId))
            thinkingGone = true
          }

          if (event.type === 'tool_call') {
            setItems(prev => [...prev, {
              kind: 'tool_call',
              id: `tc-${Date.now()}-${Math.random()}`,
              name: event.name as string,
              args: (event.args ?? {}) as Record<string, unknown>,
            }])
          } else if (event.type === 'message') {
            setItems(prev => [...prev, {
              kind: 'agent',
              id: `a-${Date.now()}`,
              content: event.content as string,
            }])
          } else if (event.type === 'error') {
            setItems(prev => [...prev, {
              kind: 'agent',
              id: `err-${Date.now()}`,
              content: `⚠ ${event.content}`,
            }])
          }
        }
      }
    } catch {
      setItems(prev => [
        ...prev.filter(i => i.id !== thinkingId),
        { kind: 'agent', id: `err-${Date.now()}`, content: '⚠ Could not reach the agent. Is the backend running?' },
      ])
    } finally {
      setBusy(false)
      textareaRef.current?.focus()
    }
  }, [input, busy])

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-wrapper">
      {/* Header */}
      <header className="header">
        <div className="header-dot" />
        <span className="header-title">Travel Agent</span>
        <span className="header-sub">Couchbase · AgentC</span>
      </header>

      {/* Messages */}
      <div className="messages">
        {items.length === 0 && (
          <div className="empty-state">Where would you like to go?</div>
        )}
        {items.map(item => {
          if (item.kind === 'user')
            return <MessageBubble key={item.id} role="user" content={item.content} />
          if (item.kind === 'agent')
            return <MessageBubble key={item.id} role="agent" content={item.content} />
          if (item.kind === 'tool_call')
            return <ToolCallCard key={item.id} name={item.name} args={item.args} />
          if (item.kind === 'thinking')
            return (
              <div key={item.id} className="thinking">
                <span /><span /><span />
              </div>
            )
          return null
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <div className="input-row">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder="Message your travel agent…"
            rows={1}
            disabled={busy}
          />
          <button
            className="send-btn"
            onClick={send}
            disabled={busy || !input.trim()}
            aria-label="Send"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  )
}
