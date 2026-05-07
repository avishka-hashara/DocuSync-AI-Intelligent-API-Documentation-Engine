'use client';

import { useState, useEffect } from 'react';
import { Send, Terminal, User, Bot, FileCode2, FolderGit2 } from 'lucide-react';
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
    { role: 'ai', content: 'Hello! I am DocuSync AI. Select a project above and ask me anything about its codebase.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // New State for Projects
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  // Fetch projects on initial load
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/projects');
        const data = await res.json();
        setProjects(data);
        if (data.length > 0) {
          setSelectedProjectId(data[0].id); // Auto-select the first project
        }
      } catch (error) {
        console.error("Failed to fetch projects", error);
      }
    };
    fetchProjects();
  }, []);

  // Clear chat when switching projects
  const handleProjectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedProjectId(Number(e.target.value));
    setMessages([
      { role: 'ai', content: `Switched context. Ask me anything about this project.` }
    ]);
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
          project_id: selectedProjectId // Passing the selected project ID securely
        }),
      });

      if (!response.ok) throw new Error('API Error');

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { role: 'ai', content: data.answer, sources: data.sources },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'ai', content: 'Sorry, I encountered an error connecting to the API.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-[#0A0A0B] text-gray-200 font-sans">
      {/* Header with Project Selector */}
      <header className="border-b border-gray-800 bg-[#0A0A0B] p-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Terminal className="text-blue-500" size={24} />
          <h1 className="text-xl font-semibold tracking-tight text-white">DocuSync AI</h1>
        </div>

        {/* Project Dropdown */}
        <div className="flex items-center gap-2 bg-[#141415] border border-gray-800 rounded-lg px-3 py-1.5">
          <FolderGit2 size={16} className="text-gray-400" />
          <select
            className="bg-transparent text-sm text-gray-200 focus:outline-none cursor-pointer"
            value={selectedProjectId || ''}
            onChange={handleProjectChange}
          >
            {projects.map(proj => (
              <option key={proj.id} value={proj.id} className="bg-[#141415]">
                {proj.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-8 space-y-6 max-w-4xl mx-auto w-full">
        {messages.map((msg, index) => (
          <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

            {msg.role === 'ai' && (
              <div className="w-8 h-8 rounded-full bg-blue-900/50 border border-blue-800 flex items-center justify-center shrink-0 mt-1">
                <Bot size={18} className="text-blue-400" />
              </div>
            )}

            <div className={`max-w-[85%] rounded-2xl p-5 ${msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-tr-sm'
                : 'bg-[#141415] border border-gray-800 text-gray-300 rounded-tl-sm shadow-sm'
              }`}>

              <div className={msg.role === 'ai' ? 'prose prose-invert max-w-none prose-sm' : 'whitespace-pre-wrap text-sm'}>
                {msg.role === 'ai' ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code(props) {
                        const { children, className, node, ...rest } = props;
                        const match = /language-(\w+)/.exec(className || '');
                        return match ? (
                          <SyntaxHighlighter
                            {...rest}
                            PreTag="div"
                            children={String(children).replace(/\n$/, '')}
                            language={match[1]}
                            style={vscDarkPlus}
                            className="rounded-md border border-gray-800 !mt-2 !mb-2"
                          />
                        ) : (
                          <code {...rest} className={`${className} bg-gray-800 px-1.5 py-0.5 rounded-md text-blue-300`}>
                            {children}
                          </code>
                        );
                      }
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>

              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-5 pt-4 border-t border-gray-800">
                  <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">Sources Consulted</p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((src, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gray-900 border border-gray-700 text-xs text-gray-400">
                        <FileCode2 size={12} className="text-blue-500" />
                        {src.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center shrink-0 mt-1">
                <User size={18} className="text-gray-300" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-4 items-center text-gray-500 text-sm mt-2">
            <Bot size={18} />
            <span className="animate-pulse">Thinking and scanning codebase...</span>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-[#0A0A0B] border-t border-gray-800">
        <form onSubmit={sendMessage} className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about endpoints, functions, or architecture..."
            className="w-full bg-[#141415] border border-gray-700 text-white placeholder-gray-500 rounded-xl px-5 py-4 pr-14 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all disabled:opacity-50"
            disabled={isLoading || projects.length === 0}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim() || projects.length === 0}
            className="absolute right-2 p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </main>
  );
}