import React from 'react';
import { AgentDashboard } from './components/AgentDashboard';
import { Chat } from './components/Chat';

function App() {
  React.useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  return (
    <main className="h-full p-4 md:p-8 flex flex-col md:flex-row gap-6 md:gap-8 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-900 dark:to-gray-800">
      <div className="md:w-1/3 h-full">
        <AgentDashboard />
      </div>
      <div className="md:w-2/3 h-full">
        <Chat />
      </div>
    </main>
  );
}

export default App;
