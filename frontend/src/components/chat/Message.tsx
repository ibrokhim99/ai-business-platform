'use client';

import { Sparkles } from 'lucide-react';
import { renderMarkdown } from '@/lib/chat/markdown';
import { BlockRenderer } from './Blocks';
import type { Message as Msg } from '@/lib/chat/types';

interface Props {
  msg: Msg;
  onSuggestionPick: (s: string) => void;
}

function TypingDots() {
  return (
    <div className="inline-flex items-center gap-1 py-2">
      <span className="dot inline-block w-1.5 h-1.5 bg-muted rounded-full" />
      <span className="dot inline-block w-1.5 h-1.5 bg-muted rounded-full" />
      <span className="dot inline-block w-1.5 h-1.5 bg-muted rounded-full" />
    </div>
  );
}

export function MessageBubble({ msg, onSuggestionPick }: Props) {
  if (msg.role === 'user') {
    return (
      <div className="w-full flex justify-end">
        <div className="max-w-[78%]">
          <div
            className="rounded-3xl px-4 py-2.5 text-fg text-[15px] leading-relaxed whitespace-pre-wrap break-words"
            style={{ background: 'rgb(var(--user-bubble))' }}
          >
            {msg.text}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex gap-3 md:gap-4">
      <div className="w-8 h-8 flex-shrink-0 rounded-full bg-gradient-to-br from-indigo-400 to-violet-600 grid place-items-center shadow-soft">
        <Sparkles className="w-4 h-4 text-white" />
      </div>
      <div className="flex-1 min-w-0 space-y-3 pt-1">
        {msg.pending ? (
          <TypingDots />
        ) : (
          <>
            {msg.text && (
              <div
                className="md text-fg text-[15px]"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
              />
            )}
            {msg.error && <div className="text-sm text-rose-500">{msg.error}</div>}
            {msg.blocks?.map((b, i) => (
              <BlockRenderer key={i} block={b} onSuggestionPick={onSuggestionPick} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
