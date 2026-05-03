import React from 'react';

const ChatBox = ({
  messages,
  input,
  setInput,
  onSubmit,
  loading,
  className = ''
}) => {
  return (
    <div className={`flex flex-col bg-surface-container-low rounded-2xl border border-outline-variant/50 shadow-soft overflow-hidden ${className}`}>
      {/* Messages Area */}
      <div className="flex-grow p-6 overflow-y-auto space-y-4 flex flex-col min-h-[300px]">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-on-surface-variant font-body">
            <p>Start a conversation to analyze spatial data...</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`max-w-[80%] rounded-xl p-4 font-body text-sm ${
                msg.sender === 'user'
                  ? 'bg-primary text-on-primary self-end'
                  : 'bg-surface-container text-on-surface self-start border border-outline-variant/30'
              }`}
            >
              {msg.text}
            </div>
          ))
        )}
        {loading && (
          <div className="bg-surface-container text-on-surface self-start max-w-[80%] rounded-xl p-4 font-body text-sm border border-outline-variant/30 flex items-center gap-2">
            <span className="material-symbols-outlined animate-spin">refresh</span>
            Analyzing...
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-outline-variant/30 bg-surface">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
          className="flex items-center gap-2 relative"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="E.g., Find optimal locations for a new solar farm..."
            className="w-full bg-surface-container-highest border border-outline-variant/50 rounded-full py-3 px-6 text-on-surface font-body focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 h-10 w-10 bg-primary text-on-primary rounded-full flex items-center justify-center hover:bg-primary-container hover:text-on-primary-container transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-soft"
          >
            <span className="material-symbols-outlined text-lg">send</span>
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatBox;
