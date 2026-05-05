import React from 'react';
import ChatBox from './ChatBox';

const RightPanel = ({ messages, input, setInput, onSubmit, chatLoading }) => {
  return (
    <div className="h-full flex flex-col gap-6 p-6 bg-surface-container-low rounded-2xl border border-outline-variant/50 shadow-soft overflow-y-auto">
      <div className="flex flex-col gap-4">
        <h2 className="font-headline text-2xl font-bold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">forum</span>
          Sentinel Assistant
        </h2>
        <ChatBox
          messages={messages}
          input={input}
          setInput={setInput}
          onSubmit={onSubmit}
          loading={chatLoading}
          className="shadow-none border border-outline-variant/30"
        />
      </div>
    </div>
  );
};

export default RightPanel;
