'use client';

import { useState, useEffect, useCallback } from 'react';
import { Send, Terminal, Bot, FileCode2, FolderGit2, Plus, X, Loader2, Upload, CheckCircle2, AlertCircle } from 'lucide-react';
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
  status: 'pending' | 'cloning' | 'ingesting' | 'completed' | 'failed';
}

interface ProgressUpdate {
  status: 'extracting' | 'processing' | 'completed' | 'failed';
  message: string;
  total?: number;
  current?: number;
  file?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: 'Hello! Upload a ZIP file of your Python codebase to start chatting.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // WebSocket Progress State
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [showProgress, setShowProgress] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/projects');
      const data = await res.json();
      if (Array.isArray(data)) {
        setProjects(data);
        if (data.length > 0 && !selectedProjectId) setSelectedProjectId(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }, [selectedProjectId]);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  useEffect(() => {
    const interval = setInterval(() => {
      const hasProcessingProject = projects.some(p => !['completed', 'failed'].includes(p.status));
      if (hasProcessingProject) {
        fetchProjects();
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [projects, fetchProjects]);

  const connectWebSocket = (projectId: number) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/progress/${projectId}`);
    setShowProgress(true);

    ws.onmessage = (event) => {
      const data: ProgressUpdate = JSON.parse(event.data);
      setProgress(data);
      if (data.status === 'completed' || data.status === 'failed') {
        setTimeout(() => setShowProgress(false), 5000); // Hide after 5s
        ws.close();
      }
    };

    ws.onerror = () => {
      setProgress({ status: 'failed', message: 'WebSocket connection error.' });
      setTimeout(() => setShowProgress(false), 5000);
    };
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl || !newProjectName) return;

    setIsCreating(true);
    const formData = new FormData();
    formData.append('name', newProjectName);
    formData.append('repo_url', repoUrl);

    try {
      const res = await fetch('http://localhost:8000/api/v1/projects/sync', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        const projectId = data.project.id;
        
        await fetchProjects();
        setIsModalOpen(false);
        setNewProjectName('');
        setRepoUrl('');
        setSelectedProjectId(projectId);
        
        // Start listening for progress
        connectWebSocket(projectId);
        
        setMessages(prev => [...prev, { role: 'ai', content: `Project "${newProjectName}" sync started! Monitoring progress...` }]);
      }
    } catch (err) {
      alert("Sync failed.");
    } finally {
      setIsCreating(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !selectedProjectId) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMsg.content, project_id: selectedProjectId }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: 'Connection Error.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-[#0A0A0B] text-gray-200 font-sans relative">
      {/* Progress Overlay */}
      {showProgress && progress && (
        <div className="fixed top-20 right-6 z-50 animate-in fade-in slide-in-from-right-4 duration-300">
          <div className="bg-[#141415] border border-gray-800 rounded-xl p-4 shadow-2xl w-80">
            <div className="flex items-start gap-3">
              {progress.status === 'completed' ? (
                <CheckCircle2 className="text-green-500 shrink-0" size={20} />
              ) : progress.status === 'failed' ? (
                <AlertCircle className="text-red-500 shrink-0" size={20} />
              ) : (
                <Loader2 className="text-blue-500 animate-spin shrink-0" size={20} />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{progress.message}</p>
                {progress.total && progress.current !== undefined && (
                  <div className="mt-3">
                    <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                      <span>{progress.current} / {progress.total} files</span>
                      <span>{Math.round((progress.current / progress.total) * 100)}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-blue-600 transition-all duration-300 ease-out" 
                        style={{ width: `${(progress.current / progress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                {progress.file && <p className="mt-2 text-[10px] text-gray-500 truncate italic">Current: {progress.file}</p>}
              </div>
            </div>
          </div>
        </div>
      )}

      <header className="border-b border-gray-800 bg-[#0A0A0B] p-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Terminal className="text-blue-500" size={24} />
          <h1 className="text-xl font-semibold tracking-tight text-white">DocuSync AI</h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <div className="flex items-center gap-2 bg-[#141415] border border-gray-800 rounded-lg px-3 py-1.5">
              <FolderGit2 size={16} className="text-gray-400" />
              <select
                className="bg-transparent text-sm text-gray-200 focus:outline-none cursor-pointer"
                value={selectedProjectId || ''}
                onChange={(e) => setSelectedProjectId(Number(e.target.value))}
              >
                {projects.map(proj => <option key={proj.id} value={proj.id} className="bg-[#141415]">{proj.name}</option>)}
              </select>
            </div>
            {projects.find(p => p.id === selectedProjectId)?.status && !['completed', 'failed'].includes(projects.find(p => p.id === selectedProjectId)?.status || '') && (
              <span className="text-[10px] text-blue-500 animate-pulse mt-1 font-medium flex items-center gap-1">
                <Loader2 size={10} className="animate-spin" />
                {projects.find(p => p.id === selectedProjectId)?.status.toUpperCase()}
              </span>
            )}
          </div>
          <button onClick={() => setIsModalOpen(true)} className="p-2 bg-blue-600/10 hover:bg-blue-600/20 text-blue-500 rounded-lg border border-blue-600/20 transition-all">
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
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                    code(props) {
                      const { children, className, ...rest } = props;
                      const match = /language-(\w+)/.exec(className || '');
                      return match ? (
                        <SyntaxHighlighter {...rest} style={vscDarkPlus} PreTag="div" language={match[1]}>{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
                      ) : (
                        <code {...rest} className="bg-gray-800 px-1.5 py-0.5 rounded-md text-blue-300">{children}</code>
                      );
                    }
                  }}>{msg.content}</ReactMarkdown>
                ) : msg.content}
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-3 border-t border-gray-800 flex flex-wrap gap-2">
                  {msg.sources.map((s, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-md bg-gray-900 border border-gray-700 text-[10px] text-gray-500 flex items-center gap-1">
                      <FileCode2 size={10} /> {s.file}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && <div className="text-gray-500 animate-pulse flex items-center gap-2"><Bot size={18} /> Searching codebase...</div>}
        {selectedProjectId && projects.find(p => p.id === selectedProjectId)?.status !== 'completed' && (
          <div className="bg-blue-600/5 border border-blue-600/20 rounded-xl p-6 text-center animate-pulse">
            <Loader2 className="mx-auto text-blue-500 animate-spin mb-3" size={32} />
            <h3 className="text-white font-medium mb-1">
              {projects.find(p => p.id === selectedProjectId)?.status === 'failed' ? 'Ingestion Failed' : 'Project is being prepared'}
            </h3>
            <p className="text-sm text-gray-500">
              {projects.find(p => p.id === selectedProjectId)?.status === 'failed' 
                ? 'There was an error processing this repository.' 
                : 'Please wait while we clone and index the codebase. This may take a few minutes.'}
            </p>
          </div>
        )}
      </div>

      <div className="p-4 bg-[#0A0A0B] border-t border-gray-800">
        <form onSubmit={sendMessage} className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text" value={input} onChange={(e) => setInput(e.target.value)}
            placeholder={projects.find(p => p.id === selectedProjectId)?.status === 'completed' ? "Ask about your code..." : "Wait for ingestion to complete..."}
            className="w-full bg-[#141415] border border-gray-700 text-white rounded-xl px-5 py-4 outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading || !selectedProjectId || projects.find(p => p.id === selectedProjectId)?.status !== 'completed'}
          />
          <button type="submit" disabled={isLoading || !input.trim() || projects.find(p => p.id === selectedProjectId)?.status !== 'completed'} className="absolute right-2 p-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-800 disabled:text-gray-600"><Send size={18} /></button>
        </form>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#141415] border border-gray-800 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-white">Sync GitHub Repository</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-500 hover:text-white"><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateProject} className="space-y-6">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-2 uppercase">Project Name</label>
                <input required placeholder="e.g. My Awesome Project" value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} className="w-full bg-[#0A0A0B] border border-gray-800 rounded-lg px-4 py-2.5 text-white outline-none focus:border-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-2 uppercase">GitHub Repository URL</label>
                <input required type="url" placeholder="https://github.com/user/repo" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} className="w-full bg-[#0A0A0B] border border-gray-800 rounded-lg px-4 py-2.5 text-white outline-none focus:border-blue-500" />
              </div>
              <button type="submit" disabled={isCreating || !repoUrl || !newProjectName} className="w-full bg-blue-600 py-3 rounded-lg flex items-center justify-center gap-2 font-semibold">
                {isCreating ? <Loader2 className="animate-spin" size={20} /> : 'Sync Repository'}
              </button>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}