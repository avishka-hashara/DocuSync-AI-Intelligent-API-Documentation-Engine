'use client';

import { useState, useEffect, useCallback } from 'react';
import { Send, Terminal, Bot, FileCode2, FolderGit2, Plus, X, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Message {
  role: 'user' | 'ai';
  content: string;
  sources?: { name: string; file: string }[];
}

interface Project {
  id: number;
  name: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: 'Hello! I am DocuSync AI. Create or select a project to start chatting with your code.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectPath, setNewProjectPath] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Using useCallback to prevent linting dependency warnings
  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/projects');
      const data = await res.json();
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch projects", err);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newProjectName, path: newProjectPath }),
      });
      if (res.ok) {
        await fetchProjects();
        setIsModalOpen(false);
        setNewProjectName('');
        setNewProjectPath('');
        setMessages([{ role: 'ai', content: `Project "${newProjectName}" created! Ingestion is running.` }]);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to create project");
    } finally {
      setIsCreating(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !selectedProjectId) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage.content,
          project_id: selectedProjectId
        }),
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'ai', content: data.answer, sources: data.sources }]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { role: 'ai', content: 'Error connecting to API.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-[#0A0A0B] text-gray-200 font-sans relative">
      <header className="border-b border-gray-800 bg-[#0A0A0B] p-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Terminal className="text-blue-500" size={24} />
          <h1 className="text-xl font-semibold tracking-tight text-white">DocuSync AI</h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#141415] border border-gray-800 rounded-lg px-3 py-1.5">
            <FolderGit2 size={16} className="text-gray-400" />
            <select
              className="bg-transparent text-sm text-gray-200 focus:outline-none cursor-pointer"
              value={selectedProjectId || ''}
              onChange={(e) => setSelectedProjectId(Number(e.target.value))}
            >
              {projects.map(proj => (
                <option key={proj.id} value={proj.id}>{proj.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="p-2 bg-blue-600/10 hover:bg-blue-600/20 text-blue-500 rounded-lg border border-blue-600/20 transition-all"
          >
            <Plus size={20} />
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-6 max-w-4xl mx-auto w-full">
        {messages.map((msg, index) => (
          <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'ai' && (
              <div className="w-8 h-8 rounded-full bg-blue-900/50 border border-blue-800 flex items-center justify-center shrink-0 mt-1">
                <Bot size={18} className="text-blue-400" />
              </div>
            )}
            <div className={`max-w-[85%] rounded-2xl p-5 ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-sm' : 'bg-[#141415] border border-gray-800 text-gray-300 rounded-tl-sm shadow-sm'}`}>
              <div className={msg.role === 'ai' ? 'prose prose-invert max-w-none prose-sm' : 'whitespace-pre-wrap text-sm'}>
                {msg.role === 'ai' ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code(props) {
                        const { children, className, ...rest } = props;
                        const match = /language-(\w+)/.exec(className || '');
                        return match ? (
                          <SyntaxHighlighter
                            {...rest}
                            style={vscDarkPlus}
                            PreTag="div"
                            language={match[1]}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code {...rest} className="bg-gray-800 px-1.5 py-0.5 rounded-md text-blue-300">{children}</code>
                        );
                      }
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : msg.content}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 bg-[#0A0A0B] border-t border-gray-800">
        <form onSubmit={sendMessage} className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text" value={input} onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your code..."
            className="w-full bg-[#141415] border border-gray-700 text-white rounded-xl px-5 py-4 focus:outline-none focus:ring-1 focus:ring-blue-500"
            disabled={isLoading || !selectedProjectId}
          />
          <button type="submit" disabled={isLoading || !input.trim()} className="absolute right-2 p-2 bg-blue-600 text-white rounded-lg"><Send size={18} /></button>
        </form>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#141415] border border-gray-800 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-6">Ingest New Codebase</h2>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <input required value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} placeholder="Project Name" className="w-full bg-[#0A0A0B] border border-gray-800 rounded-lg px-4 py-2.5 text-white outline-none" />
              <input required value={newProjectPath} onChange={(e) => setNewProjectPath(e.target.value)} placeholder="E:\Projects\my-app" className="w-full bg-[#0A0A0B] border border-gray-800 rounded-lg px-4 py-2.5 text-white outline-none" />
              <button type="submit" disabled={isCreating} className="w-full bg-blue-600 py-3 rounded-lg flex items-center justify-center gap-2">
                {isCreating ? <Loader2 className="animate-spin" size={20} /> : 'Start Ingestion'}
              </button>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}