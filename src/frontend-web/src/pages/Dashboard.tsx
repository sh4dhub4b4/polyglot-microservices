import React from 'react';
import { useNavigate } from 'react-router-dom';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#121212] text-white p-8">
      <header className="mb-10">
        <h1 className="text-4xl font-bold text-[#aa3bff]">Ace 2.0 Dashboard</h1>
        <p className="text-gray-400 mt-2">Welcome to the Multi-Tenant Polyglot Platform.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[#1e1e1e] p-6 rounded-lg border border-gray-800 shadow-md">
          <h2 className="text-2xl font-semibold mb-4 text-white">Classroom</h2>
          <p className="text-gray-400 mb-6">Access assignments, hybrid grading, and WASM notebooks.</p>
          <button 
            className="w-full bg-[#aa3bff] hover:bg-[#912ee6] text-white py-2 rounded transition-colors"
            onClick={() => navigate('/workspace')}
          >
            Open Workspace
          </button>
        </div>

        <div className="bg-[#1e1e1e] p-6 rounded-lg border border-gray-800 shadow-md">
          <h2 className="text-2xl font-semibold mb-4 text-white">Events & CTF</h2>
          <p className="text-gray-400 mb-6">Live CP scoreboards and dynamically provisioned targets.</p>
          <button className="w-full border border-[#aa3bff] text-[#aa3bff] hover:bg-[#aa3bff] hover:text-white py-2 rounded transition-colors">
            View Events
          </button>
        </div>

        <div className="bg-[#1e1e1e] p-6 rounded-lg border border-gray-800 shadow-md">
          <h2 className="text-2xl font-semibold mb-4 text-white">Admin Panel</h2>
          <p className="text-gray-400 mb-6">Manage tenant resources, CPU/GPU hours, and RBAC.</p>
          <button className="w-full bg-gray-700 hover:bg-gray-600 text-white py-2 rounded transition-colors">
            Manage
          </button>
        </div>
      </div>
    </div>
  );
};
