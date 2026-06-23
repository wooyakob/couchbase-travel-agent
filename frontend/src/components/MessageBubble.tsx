'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  role: 'user' | 'agent'
  content: string
}

export default function MessageBubble({ role, content }: Props) {
  if (role === 'user') {
    return (
      <div className="msg-user">
        <div className="msg-user-bubble">{content}</div>
      </div>
    )
  }

  return (
    <div className="msg-agent">
      <div className="msg-agent-bubble">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </div>
  )
}
