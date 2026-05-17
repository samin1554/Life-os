# 08 — Frontend

Next.js 15 App Router frontend for Life OS.

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout, auth provider, query client
│   ├── page.tsx                # Root redirect → /dashboard or /login
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── onboarding/
│   │   └── page.tsx            # Conversational onboarding UI
│   ├── dashboard/
│   │   └── page.tsx            # Main daily view
│   ├── chat/
│   │   └── page.tsx            # Direct agent chat
│   ├── tasks/
│   │   └── page.tsx            # Full task management
│   ├── goals/
│   │   └── page.tsx            # Goals tracker
│   └── settings/
│       └── page.tsx            # Memory view, preferences
├── components/
│   ├── ui/                     # shadcn/ui base components
│   ├── agent/
│   │   ├── AgentStream.tsx     # SSE streaming display
│   │   ├── AgentBadge.tsx      # Shows which agent is speaking
│   │   └── ThinkingDots.tsx    # Animated "agent is thinking"
│   ├── checkin/
│   │   ├── MorningCheckin.tsx
│   │   └── EveningCheckin.tsx
│   ├── tasks/
│   │   ├── TaskCard.tsx
│   │   ├── TaskQueue.tsx
│   │   └── ExecutionPanel.tsx  # Shows execution agent output for approval
│   ├── dashboard/
│   │   ├── DailyPlan.tsx
│   │   ├── EnergyIndicator.tsx
│   │   ├── PatternInsights.tsx
│   │   └── ChaosTrigger.tsx    # Big red button for overwhelm mode
│   └── layout/
│       ├── Sidebar.tsx
│       └── TopBar.tsx
├── lib/
│   ├── api.ts                  # All API call functions
│   ├── auth.ts                 # JWT management
│   ├── useSSE.ts               # SSE hook
│   └── store.ts                # Zustand store
└── types/
    └── index.ts                # All TypeScript types
```

---

## Key Components

### useSSE Hook (`lib/useSSE.ts`)
The most important piece of the frontend. Connects to the backend SSE stream and exposes tokens and agent state.

```typescript
import { useState, useCallback } from 'react';

interface SSEState {
  messages: { role: 'user' | 'assistant'; content: string; agent?: string }[];
  currentAgent: string | null;
  isStreaming: boolean;
  error: string | null;
}

export function useSSE() {
  const [state, setState] = useState<SSEState>({
    messages: [],
    currentAgent: null,
    isStreaming: false,
    error: null,
  });

  const sendMessage = useCallback(async (message: string) => {
    setState(prev => ({
      ...prev,
      isStreaming: true,
      messages: [...prev.messages, { role: 'user', content: message }],
    }));

    let assistantContent = '';

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ message }),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(line => line.startsWith('data: '));

      for (const line of lines) {
        const data = JSON.parse(line.replace('data: ', ''));

        if (data.type === 'agent_start') {
          setState(prev => ({ ...prev, currentAgent: data.agent }));
        }

        if (data.type === 'token') {
          assistantContent += data.content;
          setState(prev => ({
            ...prev,
            messages: [
              ...prev.messages.slice(0, -1),  // remove in-progress
              { role: 'assistant', content: assistantContent, agent: prev.currentAgent ?? undefined },
            ],
          }));
        }

        if (data.type === 'done') {
          setState(prev => ({ ...prev, isStreaming: false, currentAgent: null }));
        }
      }
    }
  }, []);

  return { ...state, sendMessage };
}
```

---

### AgentStream Component (`components/agent/AgentStream.tsx`)
Displays the live streaming response with agent attribution.

```typescript
interface Props {
  messages: { role: string; content: string; agent?: string }[];
  currentAgent: string | null;
  isStreaming: boolean;
}

const AGENT_LABELS: Record<string, string> = {
  supervisor: 'Routing',
  focus: 'Focus',
  health: 'Health',
  execution: 'Execution',
  chaos_triage: 'Triage',
  synthesis: 'Life OS',
  relationships: 'Relationships',
  goals: 'Goals',
  delegate: 'Research',
};

const AGENT_COLORS: Record<string, string> = {
  focus: 'bg-blue-100 text-blue-800',
  health: 'bg-green-100 text-green-800',
  execution: 'bg-purple-100 text-purple-800',
  chaos_triage: 'bg-red-100 text-red-800',
  synthesis: 'bg-gray-100 text-gray-800',
};

export function AgentStream({ messages, currentAgent, isStreaming }: Props) {
  return (
    <div className="flex flex-col gap-4">
      {isStreaming && currentAgent && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <ThinkingDots />
          <AgentBadge agent={currentAgent} />
          <span>is thinking...</span>
        </div>
      )}
      {messages.map((msg, i) => (
        <div key={i} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
          <div className={`max-w-[80%] rounded-lg p-4 ${
            msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'
          }`}>
            {msg.agent && msg.role === 'assistant' && (
              <AgentBadge agent={msg.agent} className="mb-2" />
            )}
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

### ExecutionPanel (`components/tasks/ExecutionPanel.tsx`)
The "review and approve" UX for the Execution Agent. User sees the drafted email/doc, can edit, then approves.

```typescript
interface Props {
  taskTitle: string;
  executionOutput: string;
  onApprove: (finalContent: string) => void;
  onReject: () => void;
}

export function ExecutionPanel({ taskTitle, executionOutput, onApprove, onReject }: Props) {
  const [content, setContent] = useState(executionOutput);

  return (
    <div className="border rounded-lg p-4 bg-purple-50 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Ready for your review — {taskTitle}</p>
        <AgentBadge agent="execution" />
      </div>

      <textarea
        value={content}
        onChange={e => setContent(e.target.value)}
        className="w-full min-h-[200px] text-sm border rounded p-3 bg-white resize-y"
      />

      <p className="text-xs text-muted-foreground">Edit anything above, then approve.</p>

      <div className="flex gap-2">
        <button
          onClick={() => onApprove(content)}
          className="flex-1 bg-green-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-green-700"
        >
          Approve & Copy
        </button>
        <button
          onClick={onReject}
          className="px-4 py-2 text-sm border rounded hover:bg-muted"
        >
          Discard
        </button>
      </div>
    </div>
  );
}
```

---

### ChaosTrigger (`components/dashboard/ChaosTrigger.tsx`)
The overwhelm button. Visible on the dashboard at all times. One tap = chaos triage.

```typescript
export function ChaosTrigger() {
  const { sendMessage, isStreaming } = useSSE();

  return (
    <button
      onClick={() => sendMessage("I'm overwhelmed. Too much going on. Help me figure out what actually matters right now.")}
      disabled={isStreaming}
      className="w-full border-2 border-red-200 rounded-lg p-4 text-left hover:bg-red-50 transition-colors"
    >
      <p className="text-sm font-medium text-red-800">Everything feels like too much</p>
      <p className="text-xs text-red-600 mt-1">Tap to cut everything down to 3 things</p>
    </button>
  );
}
```

---

## Pages

### Dashboard (`app/dashboard/page.tsx`)
The main daily view. Loads on login. Contains:
- Morning check-in card (if not done today)
- Today's daily plan (from Focus Agent)
- Energy indicator (based on latest check-in)
- Task queue (today's tasks, ordered)
- Chaos trigger button
- Pattern insights (from Pattern Learning Agent)
- Relationship nudges (from Relationships Agent)

### Chat (`app/chat/page.tsx`)
Direct conversation with any agent. Includes:
- AgentStream component for the conversation
- Input box with send button
- Session context (which agent is active)

### Onboarding (`app/onboarding/page.tsx`)
Guided conversational onboarding. Blocks access to dashboard until complete.
- Chat-style interface, one question at a time
- Progress indicator (Step 3 of 10)
- Auto-redirects to dashboard when complete

---

## Zustand Store (`lib/store.ts`)

```typescript
interface LifeOSStore {
  // Auth
  token: string | null;
  userId: string | null;
  setAuth: (token: string, userId: string) => void;
  logout: () => void;

  // Current session
  currentAgent: string | null;
  chaosMode: boolean;
  setChaosMode: (v: boolean) => void;

  // Today
  todayPlan: Task[];
  todayCheckinDone: boolean;
  setTodayPlan: (tasks: Task[]) => void;
}

export const useStore = create<LifeOSStore>((set) => ({
  token: localStorage.getItem('token'),
  userId: localStorage.getItem('userId'),
  setAuth: (token, userId) => {
    localStorage.setItem('token', token);
    localStorage.setItem('userId', userId);
    set({ token, userId });
  },
  logout: () => {
    localStorage.clear();
    set({ token: null, userId: null });
  },
  currentAgent: null,
  chaosMode: false,
  setChaosMode: (v) => set({ chaosMode: v }),
  todayPlan: [],
  todayCheckinDone: false,
  setTodayPlan: (tasks) => set({ todayPlan: tasks }),
}));
```

---

## Environment Variables (Frontend)

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```
