import React from 'react';

interface TerminalProps {
  commands: string[];
}

const Terminal: React.FC<TerminalProps> = ({ commands }) => {
  return (
    <div className="bg-gray-900 rounded-lg p-6 my-6 font-mono text-sm shadow-xl overflow-x-auto">
      <div className="flex gap-2 mb-4 border-b border-gray-700 pb-2">
        <div className="w-3 h-3 rounded-full bg-red-500"></div>
        <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
        <div className="w-3 h-3 rounded-full bg-green-500"></div>
      </div>
      <div className="space-y-2">
        {commands.map((command, index) => (
          <div key={index} className="flex">
            <span className="text-green-400 mr-2">$</span>
            <code className="text-gray-100">{command}</code>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Terminal;
