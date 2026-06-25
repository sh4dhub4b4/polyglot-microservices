import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useCourseStore, type Assignment } from '../store/courseStore';
import { api } from '../services/api';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { courses, assignments, submissions, credits, loading, error, loadCourses, loadAssignments, loadSubmissions, loadCredits } = useCourseStore();
  const [expandedCourse, setExpandedCourse] = useState<string | null>(null);
  const [showCreateCourse, setShowCreateCourse] = useState(false);
  const [newSection, setNewSection] = useState('');
  const [newCapacity, setNewCapacity] = useState('40');
  const [createError, setCreateError] = useState('');

  useEffect(() => {
    loadCourses();
    loadSubmissions();
    loadCredits();
  }, []);

  const handleToggleCourse = async (courseId: string) => {
    if (expandedCourse === courseId) {
      setExpandedCourse(null);
    } else {
      setExpandedCourse(courseId);
      if (!assignments[courseId]) {
        await loadAssignments(courseId);
      }
    }
  };

  const handleCreateCourse = async () => {
    if (!newSection.trim()) return;
    setCreateError('');
    try {
      await api.createCourse(newSection.trim(), parseInt(newCapacity) || 40);
      setNewSection('');
      setShowCreateCourse(false);
      await loadCourses();
    } catch (err: any) {
      setCreateError(err.message);
    }
  };

  const isFaculty = user?.role === 'faculty';
  const isStudent = user?.role === 'student';

  return (
    <div className="min-h-screen bg-[#121212] text-white">
      {/* Top nav */}
      <header className="flex items-center justify-between px-6 py-3 bg-[#1e1e1e] border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold text-[#aa3bff]">Ace 2.0 Dashboard</h1>
          <p className="text-gray-500 text-sm">
            {user?.displayName} · {user?.role} · Tenant: {user?.tenantId?.slice(0, 8)}...
          </p>
        </div>
        <div className="flex items-center gap-3">
          {credits && (
            <span className="text-xs text-gray-400">
              Credits: <span className="text-[#aa3bff] font-semibold">{credits.remaining.toFixed(1)}</span>
              <span className="text-gray-600"> ({credits.tier})</span>
            </span>
          )}
          <button
            onClick={() => navigate('/workspace')}
            className="bg-[#aa3bff] hover:bg-[#912ee6] px-4 py-1.5 rounded text-sm font-semibold transition-colors"
          >
            Open Workspace
          </button>
          <button onClick={() => { logout(); navigate('/login'); }} className="text-gray-500 hover:text-white text-sm">
            Logout
          </button>
        </div>
      </header>

      <div className="p-6 max-w-6xl mx-auto space-y-6">
        {/* Quick stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[#1e1e1e] border border-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold text-[#aa3bff]">{courses.length}</div>
            <div className="text-sm text-gray-400">Active Courses</div>
          </div>
          <div className="bg-[#1e1e1e] border border-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold text-[#aa3bff]">{submissions.length}</div>
            <div className="text-sm text-gray-400">Submissions</div>
          </div>
          <div className="bg-[#1e1e1e] border border-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold text-[#aa3bff]">
              {submissions.filter(s => s.status === 'graded' && s.marks_awarded != null).length}
            </div>
            <div className="text-sm text-gray-400">Graded</div>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-red-900/30 border border-red-700 text-red-300 px-4 py-2 rounded text-sm">
            {error}
          </div>
        )}

        {/* Courses section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">
              {isFaculty ? 'My Course Offerings' : 'My Enrolled Courses'}
            </h2>
            {isFaculty && (
              <button
                onClick={() => setShowCreateCourse(!showCreateCourse)}
                className="text-sm text-[#aa3bff] hover:underline"
              >
                + New Course
              </button>
            )}
          </div>

          {showCreateCourse && (
            <div className="bg-[#1e1e1e] border border-gray-800 rounded-lg p-4 mb-4">
              <h3 className="text-sm font-semibold mb-2">Create Course Offering</h3>
              {createError && <p className="text-red-400 text-xs mb-2">{createError}</p>}
              <div className="flex gap-2">
                <input
                  value={newSection}
                  onChange={(e) => setNewSection(e.target.value)}
                  placeholder="Section number (e.g. CS101-A)"
                  className="flex-1 bg-[#2d2d2d] border border-gray-700 rounded px-3 py-1.5 text-sm text-white outline-none"
                />
                <input
                  value={newCapacity}
                  onChange={(e) => setNewCapacity(e.target.value)}
                  placeholder="Capacity"
                  type="number"
                  className="w-24 bg-[#2d2d2d] border border-gray-700 rounded px-3 py-1.5 text-sm text-white outline-none"
                />
                <button onClick={handleCreateCourse} className="bg-[#aa3bff] px-4 rounded text-sm font-semibold">Create</button>
              </div>
            </div>
          )}

          {loading && <div className="text-gray-500 text-sm">Loading courses...</div>}

          {!loading && courses.length === 0 && (
            <div className="bg-[#1e1e1e] border border-gray-800 rounded-lg p-8 text-center">
              <p className="text-gray-500">
                {isFaculty
                  ? 'No course offerings yet. Create your first one!'
                  : 'No enrolled courses. Ask your faculty to enroll you.'}
              </p>
            </div>
          )}

          <div className="space-y-2">
            {courses.map((course) => (
              <div key={course.id} className="bg-[#1e1e1e] border border-gray-800 rounded-lg overflow-hidden">
                <button
                  onClick={() => handleToggleCourse(course.id)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-[#252525] transition-colors text-left"
                >
                  <div>
                    <span className="font-medium">{course.section_number}</span>
                    {isStudent && course.enrollment_id && (
                      <span className="ml-2 text-xs text-gray-500">Enrolled</span>
                    )}
                  </div>
                  <span className={`text-gray-500 transition-transform ${expandedCourse === course.id ? 'rotate-180' : ''}`}>
                    ▼
                  </span>
                </button>

                {expandedCourse === course.id && (
                  <div className="border-t border-gray-800 px-4 py-3">
                    <AssignmentsList
                      courseId={course.id}
                      assignments={assignments[course.id] || []}
                      submissions={submissions}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Recent submissions */}
        {submissions.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-3">Recent Submissions</h2>
            <div className="bg-[#1e1e1e] border border-gray-800 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-[#252525] text-gray-400">
                  <tr>
                    <th className="px-4 py-2 text-left">Assignment</th>
                    <th className="px-4 py-2 text-left">Language</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {submissions.slice(0, 10).map((s) => (
                    <tr key={s.submission_id} className="border-t border-gray-800 hover:bg-[#252525]">
                      <td className="px-4 py-2 text-gray-300">{s.assignment_id.slice(0, 8)}...</td>
                      <td className="px-4 py-2 text-gray-400">{s.language}</td>
                      <td className="px-4 py-2">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          s.status === 'graded' ? 'bg-green-900/40 text-green-300' :
                          s.status === 'submitted' ? 'bg-blue-900/40 text-blue-300' :
                          'bg-yellow-900/40 text-yellow-300'
                        }`}>
                          {s.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-300">
                        {s.marks_awarded != null ? `${s.tests_passed}/${s.tests_total}` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[#1e1e1e] p-4 rounded-lg border border-gray-800">
            <h3 className="font-semibold mb-2">Workspace</h3>
            <p className="text-sm text-gray-400 mb-3">Write and execute code in the interactive IDE.</p>
            <button onClick={() => navigate('/workspace')} className="w-full bg-[#aa3bff] hover:bg-[#912ee6] py-1.5 rounded text-sm font-semibold transition-colors">
              Open
            </button>
          </div>
          <div className="bg-[#1e1e1e] p-4 rounded-lg border border-gray-800">
            <h3 className="font-semibold mb-2">Events & CTF</h3>
            <p className="text-sm text-gray-400 mb-3">Live competitive programming events.</p>
            <button className="w-full border border-[#aa3bff] text-[#aa3bff] hover:bg-[#aa3bff] hover:text-white py-1.5 rounded text-sm font-semibold transition-colors">
              Coming Soon
            </button>
          </div>
          <div className="bg-[#1e1e1e] p-4 rounded-lg border border-gray-800">
            <h3 className="font-semibold mb-2">Admin Panel</h3>
            <p className="text-sm text-gray-400 mb-3">Manage resources, credits, and RBAC.</p>
            <button className="w-full bg-gray-700 hover:bg-gray-600 py-1.5 rounded text-sm font-semibold transition-colors">
              Manage
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

function AssignmentsList({ courseId: _courseId, assignments, submissions }: {
  courseId: string;
  assignments: Assignment[];
  submissions: any[];
}) {
  const navigate = useNavigate();

  if (assignments.length === 0) {
    return <p className="text-gray-500 text-sm">No assignments yet for this course.</p>;
  }

  return (
    <div className="space-y-1">
      {assignments.map((a) => {
        const sub = submissions.find(s => s.assignment_id === a.id);
        return (
          <div key={a.id} className="flex items-center justify-between py-1.5">
            <div>
              <span className="text-sm">{a.title}</span>
              {a.due_date && (
                <span className="ml-2 text-xs text-gray-500">
                  Due: {new Date(a.due_date).toLocaleDateString()}
                </span>
              )}
              <span className="ml-2 text-xs text-gray-600">
                {a.max_marks} pts
              </span>
            </div>
            <div className="flex items-center gap-2">
              {sub ? (
                <span className={`text-xs ${
                  sub.tests_passed === sub.tests_total && sub.tests_total > 0
                    ? 'text-green-400' : 'text-yellow-400'
                }`}>
                  {sub.marks_awarded != null ? `${sub.marks_awarded}/${a.max_marks}` : 'Submitted'}
                </span>
              ) : (
                <span className="text-xs text-gray-600">Not submitted</span>
              )}
              <button
                onClick={() => navigate('/workspace')}
                className="text-xs text-[#aa3bff] hover:underline"
              >
                {sub ? 'Resubmit' : 'Solve'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
