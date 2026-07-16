import React, { useState, useEffect, useRef } from 'react';

const API_BASE = window.location.origin.includes('5173') ? 'http://127.0.0.1:8000' : '';

const CATEGORIES = [
  { id: 'everyday', label: 'Everyday Talk 💬', type: 'everyday' },
  { id: 'text_message', label: 'Text Message 📱', type: 'text_message' },
  { id: 'dating_app', label: 'Dating Text 💘', type: 'dating_app' },
  { id: 'workplace', label: 'Workplace 💼', type: 'workplace' },
  { id: 'family', label: 'Family Chat 🏠', type: 'family' },
  { id: 'headline', label: 'Headlines 📰', type: 'headline' },
  { id: 'awkward_situation', label: 'Awkward Talk 🎭', type: 'awkward_situation' },
  { id: 'random', label: 'Surprise Me ✨', type: 'random' }
];

const DIFFICULTY_LEVELS = [
  { id: 'simple', label: 'Simple 🌱', desc: 'Double meanings' },
  { id: 'intermediate', label: 'Intermediate 🌿', desc: 'Idioms & phrasing' },
  { id: 'expert', label: 'Expert 🔥', desc: 'Social context' }
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [difficulty, setDifficulty] = useState('simple');
  const [category, setCategory] = useState('everyday');
  const [setupStep, setSetupStep] = useState('difficulty'); // 'difficulty' | 'category' | 'ready'
  
  const [currentPrompt, setCurrentPrompt] = useState(null);
  const [inputVal, setInputVal] = useState('');
  const [historyIds, setHistoryIds] = useState([]);
  const [round, setRound] = useState(1);
  const [totalRounds, setTotalRounds] = useState(0);
  const [selectedStyles, setSelectedStyles] = useState({});

  // Hints toggles per message ID
  const [expandedHints, setExpandedHints] = useState({});

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Scroll on message list change or typing indicator toggle
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Initial welcome message
  useEffect(() => {
    setMessages([
      {
        id: 'welcome-1',
        sender: 'coach',
        type: 'text',
        content: "Hello! I'm Antigravity, your Wit & Misinterpretation Coach. 🧠\n\nI'll help you train your brain to notice double meanings and come up with funny, unexpected responses in real-life conversations.",
        timestamp: getTimestamp()
      },
      {
        id: 'welcome-2',
        sender: 'coach',
        type: 'text',
        content: "Before we begin, select your difficulty level to start:",
        timestamp: getTimestamp()
      }
    ]);
  }, []);

  const getTimestamp = () => {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const addMessage = (msg) => {
    setMessages((prev) => [...prev, { id: Math.random().toString(36).substr(2, 9), timestamp: getTimestamp(), ...msg }]);
  };

  // Handle Onboarding - Difficulty Selected
  const selectDifficulty = (diffId, diffLabel) => {
    setDifficulty(diffId);
    addMessage({
      sender: 'user',
      type: 'text',
      content: `I'll try: ${diffLabel}`
    });
    
    setSetupStep('loading');
    setIsTyping(true);
    
    setTimeout(() => {
      setIsTyping(false);
      addMessage({
        sender: 'coach',
        type: 'text',
        content: `Great choice! Now select a conversation category to practice with:`
      });
      setSetupStep('category');
    }, 1000);
  };

  // Handle Onboarding - Category Selected
  const selectCategory = (catId, catLabel) => {
    setCategory(catId);
    addMessage({
      sender: 'user',
      type: 'text',
      content: `Practice: ${catLabel}`
    });
    
    setSetupStep('ready');
    triggerNextPrompt(diffIdToText(difficulty), catId, []);
  };

  const diffIdToText = (id) => {
    if (id === 'simple') return 'simple';
    if (id === 'intermediate') return 'intermediate';
    return 'expert';
  };

  // Call API for Next Prompt
  const triggerNextPrompt = async (currDiff = difficulty, currCat = category, currHistory = historyIds) => {
    setIsTyping(true);
    try {
      const res = await fetch(`${API_BASE}/api/session/next`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          difficulty: currDiff,
          category: currCat,
          history: currHistory
        })
      });

      if (!res.ok) throw new Error("Could not fetch prompt");

      const promptData = await res.json();
      setCurrentPrompt(promptData);
      
      setIsTyping(false);
      addMessage({
        sender: 'coach',
        type: 'prompt',
        content: promptData
      });
    } catch (err) {
      console.error(err);
      setIsTyping(false);
      addMessage({
        sender: 'coach',
        type: 'text',
        content: "❌ Oh no! I'm having trouble connecting to the Wit Coach backend. Make sure the FastAPI server is running on port 8000."
      });
    }
  };

  // User submits misinterpretation
  const handleSendMessage = async () => {
    if (!inputVal.trim() || !currentPrompt) return;
    
    const text = inputVal;
    setInputVal('');
    
    addMessage({
      sender: 'user',
      type: 'text',
      content: text
    });

    // Clear current prompt so user cannot resubmit
    const activePrompt = currentPrompt;
    setCurrentPrompt(null);

    setIsTyping(true);

    try {
      const res = await fetch(`${API_BASE}/api/session/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt_text: activePrompt.prompt,
          context_hint: activePrompt.context_hint,
          user_response: text
        })
      });

      if (!res.ok) throw new Error("Evaluation failed");

      const evalData = await res.json();
      setIsTyping(false);

      // Add evaluation message block containing alternatives
      addMessage({
        sender: 'coach',
        type: 'evaluation',
        content: evalData,
        originalPrompt: activePrompt.prompt
      });

      setTotalRounds(prev => prev + 1);
      let nextDiff = difficulty;

      // Update history ids
      const nextHistory = [...historyIds, activePrompt.prompt];
      setHistoryIds(nextHistory);

      // Show actions bubble
      addMessage({
        sender: 'coach',
        type: 'actions',
        content: {
          nextDiff,
          nextHistory
        }
      });

    } catch (err) {
      console.error(err);
      setIsTyping(false);
      addMessage({
        sender: 'coach',
        type: 'text',
        content: "❌ Sorry, I hit an error while evaluating your response. Please try clicking the 'Next Prompt' button below."
      });
      // Show recovery actions bubble
      addMessage({
        sender: 'coach',
        type: 'actions',
        content: {
          nextDiff: difficulty,
          nextHistory: historyIds
        }
      });
    }
  };

  // Move to next round
  const handleNextRound = (nextDiff, nextHistory) => {
    setRound(prev => prev + 1);
    
    // Remove the action buttons for the current block to keep history clean
    setMessages(prev => prev.filter(m => m.type !== 'actions'));
    
    triggerNextPrompt(nextDiff, category, nextHistory);
  };

  // Change settings
  const handleResetSettings = () => {
    setMessages(prev => prev.filter(m => m.type !== 'actions'));
    addMessage({
      sender: 'coach',
      type: 'text',
      content: "Let's change our training mode. Choose your difficulty level:"
    });
    setSetupStep('difficulty');
  };

  // Toggle hints drawer
  const toggleHint = (msgId) => {
    setExpandedHints(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  // Style Color Selection
  const getStyleColor = (style) => {
    const s = style.toLowerCase();
    if (s.includes('dry')) return '#475569';
    if (s.includes('sarcastic')) return '#ea580c';
    if (s.includes('deadpan')) return '#64748b';
    if (s.includes('clever')) return '#0284c7';
    if (s.includes('absurd')) return '#db2777';
    if (s.includes('wordplay')) return '#ca8a04';
    if (s.includes('observational')) return '#0d9488';
    if (s.includes('self-deprecating') || s.includes('self')) return '#4f46e5';
    if (s.includes('tease') || s.includes('friendly')) return '#16a34a';
    if (s.includes('dark')) return '#b91c1c';
    return 'var(--accent-purple)';
  };

  // Alternative badge color codes
  const getStyleBadgeClass = (style) => {
    const s = style.toLowerCase();
    if (s.includes('dry')) return 'badge-dry';
    if (s.includes('sarcastic')) return 'badge-sarcastic';
    if (s.includes('deadpan')) return 'badge-deadpan';
    if (s.includes('clever')) return 'badge-clever';
    if (s.includes('absurd')) return 'badge-absurd';
    if (s.includes('wordplay')) return 'badge-wordplay';
    if (s.includes('observational')) return 'badge-observational';
    if (s.includes('self-deprecating') || s.includes('self')) return 'badge-self-deprecating';
    if (s.includes('tease') || s.includes('friendly')) return 'badge-friendly-tease';
    if (s.includes('dark')) return 'badge-dark';
    return 'badge-default-style';
  };

  // Render prompt visually based on context/theme
  const renderPromptBox = (promptObj) => {
    const type = promptObj.type.toLowerCase();
    
    switch (type) {
      case 'text_message':
        return (
          <div className="prompt-bubble-box theme-whatsapp">
            <div className="theme-header">New Message</div>
            <div className="theme-body">"{promptObj.prompt}"</div>
          </div>
        );
      case 'dating_app':
        return (
          <div className="prompt-bubble-box theme-tinder">
            <div className="theme-header">Dating Match</div>
            <div className="theme-body">"{promptObj.prompt}"</div>
          </div>
        );
      case 'workplace':
        return (
          <div className="prompt-bubble-box theme-slack">
            <div className="slack-avatar">💼</div>
            <div className="slack-body">
              <div className="slack-sender">Co-worker</div>
              <div className="slack-text">"{promptObj.prompt}"</div>
            </div>
          </div>
        );
      case 'headline':
        return (
          <div className="prompt-bubble-box theme-newspaper">
            <div className="news-header">DAILY NEWS CLIP</div>
            <div className="news-body">"{promptObj.prompt}"</div>
          </div>
        );
      default:
        return (
          <div className="prompt-bubble-box" style={{ borderLeft: '3px solid var(--accent-purple)', paddingLeft: '0.75rem', fontStyle: 'italic', color: '#fff', margin: '0.5rem 0' }}>
            "{promptObj.prompt}"
          </div>
        );
    }
  };

  return (
    <div className="app-container">

      {/* Chat Header */}
      <div className="chat-header">
        <div className="header-avatar">🧠</div>
        <div className="header-info">
          <div className="header-name">Coach Antigravity</div>
          <div className="header-status">Online</div>
        </div>
        
        <div className="header-round-badge" style={{ background: 'rgba(6, 182, 212, 0.15)', borderColor: 'rgba(6, 182, 212, 0.3)', color: '#22d3ee', marginLeft: '0.25rem' }}>
          R#{round}
        </div>
      </div>

      {/* Scrollable messages area */}
      <div className="chat-messages-container">
        {messages.map((msg) => {
          if (msg.sender === 'user') {
            return (
              <div key={msg.id} className="msg-row user">
                <div className="bubble user-msg">
                  <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                  <div className="bubble-meta" style={{ color: 'rgba(255,255,255,0.7)' }}>{msg.timestamp || getTimestamp()}</div>
                </div>
              </div>
            );
          } else if (msg.sender === 'system') {
            return (
              <div key={msg.id} className="msg-row system">
                <div className="bubble system-msg">
                  <p>{msg.content}</p>
                </div>
              </div>
            );
          } else {
            // Coach Sender
            return (
              <div key={msg.id} className="msg-row coach">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', width: '100%' }}>
                  
                  {/* Standard text bubble */}
                  {msg.type === 'text' && (
                    <div className="bubble coach-msg" style={{ width: '80%' }}>
                      <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                      <div className="bubble-meta">{msg.timestamp || getTimestamp()}</div>
                    </div>
                  )}

                  {/* Prompt delivery bubble */}
                  {msg.type === 'prompt' && (
                    <div className="bubble coach-msg" style={{ width: '85%' }}>
                      <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
                        📍 SCENARIO: {msg.content.context_hint}
                      </span>
                      {renderPromptBox(msg.content)}
                      
                      {/* Inline hints dropdown */}
                      <div>
                        <button 
                          className="hint-bubble-btn"
                          onClick={() => toggleHint(msg.id)}
                        >
                          <span>{expandedHints[msg.id] ? '🙈 Hide hints' : '💡 Show hints'}</span>
                        </button>
                        {expandedHints[msg.id] && (
                          <div style={{ marginTop: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '6px', fontSize: '0.8rem', borderLeft: '2px solid var(--accent-cyan)' }}>
                            <p style={{ fontWeight: 'bold', marginBottom: '0.2rem' }}>Literal vs Double Meaning:</p>
                            <ul style={{ paddingLeft: '0.75rem' }}>
                              {msg.content.possible_interpretations.map((hint, i) => (
                                <li key={i}>{hint}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                      <div className="bubble-meta">{msg.timestamp || getTimestamp()}</div>
                    </div>
                  )}

                  {/* Direct Flat List Alternative Selector */}
                  {msg.type === 'evaluation' && (
                    <div className="bubble coach-msg" style={{ width: '85%' }}>
                      <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
                        💡 Alternative Angles
                      </span>
                      
                      {msg.content.alternatives && msg.content.alternatives.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
                          {msg.content.alternatives.map((alt) => (
                            <div key={alt.style} style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', textAlign: 'left' }}>
                              <p style={{ fontWeight: '800', color: 'var(--text-primary)', fontSize: '0.9rem', textTransform: 'capitalize', borderLeft: `3px solid ${getStyleColor(alt.style)}`, paddingLeft: '0.5rem' }}>
                                {alt.style}
                              </p>
                              <ol style={{ paddingLeft: '1.2rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.88rem', color: '#fff' }}>
                                {alt.examples.map((ex, i) => (
                                  <li key={i} style={{ fontStyle: 'italic' }}>
                                    "{ex}"
                                  </li>
                                ))}
                              </ol>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      <div className="bubble-meta">{msg.timestamp || getTimestamp()}</div>
                    </div>
                  )}

                  {/* End of round actions bubble */}
                  {msg.type === 'actions' && (
                    <div className="bubble coach-msg action-btns-bubble" style={{ width: '70%' }}>
                      <p style={{ fontWeight: 'bold', marginBottom: '0.5rem', fontSize: '0.85rem' }}>Ready for the next scenario?</p>
                      <button 
                        className="action-btn"
                        onClick={() => handleNextRound(msg.content.nextDiff, msg.content.nextHistory)}
                      >
                        Next Prompt ⚡
                      </button>
                      <button 
                        className="action-btn-secondary"
                        onClick={handleResetSettings}
                      >
                        Change Settings ⚙️
                      </button>
                    </div>
                  )}

                </div>
              </div>
            );
          }
        })}

        {/* Typing indicator */}
        {isTyping && (
          <div className="msg-row coach">
            <div className="bubble coach-msg" style={{ width: '60px', padding: '0.4rem 0.8rem' }}>
              <div className="typing-indicator">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Onboarding Input Options - Floating Overlay */}
      {setupStep === 'difficulty' && (
        <div style={{ background: 'var(--bg-header)', borderTop: '1px solid var(--border-glass)', padding: '0.75rem 1rem' }}>
          <span className="section-label" style={{ fontSize: '0.7rem' }}>Select Practice Level:</span>
          <div className="setup-pills-wrap">
            <div className="pills-row">
              {DIFFICULTY_LEVELS.map((level) => (
                <button
                  key={level.id}
                  className="pill-btn"
                  onClick={() => selectDifficulty(level.id, level.label)}
                >
                  <strong>{level.label}</strong>
                  <span style={{ fontSize: '0.7rem', opacity: 0.7 }}>({level.desc})</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {setupStep === 'category' && (
        <div style={{ background: 'var(--bg-header)', borderTop: '1px solid var(--border-glass)', padding: '0.75rem 1rem' }}>
          <span className="section-label" style={{ fontSize: '0.7rem' }}>Select Scenario Context:</span>
          <div className="setup-pills-wrap">
            <div className="pills-row" style={{ maxHeight: '100px', overflowY: 'auto', paddingBottom: '0.25rem' }}>
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  className="pill-btn"
                  onClick={() => selectCategory(cat.id, cat.label)}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Standard Chat Input Box */}
      {setupStep === 'ready' && (
        <div className="chat-input-bar">
          <input 
            type="text" 
            className="chat-input"
            placeholder={currentPrompt ? "Type your witty comeback..." : "Waiting for prompt..."}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            disabled={!currentPrompt}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && inputVal.trim()) {
                handleSendMessage();
              }
            }}
          />
          <button 
            className="chat-send-btn"
            onClick={handleSendMessage}
            disabled={!inputVal.trim() || !currentPrompt}
          >
            ✈️
          </button>
        </div>
      )}
    </div>
  );
}
