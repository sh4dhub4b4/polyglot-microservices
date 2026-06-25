import { create } from 'zustand';
import { api } from '../services/api';
import { useAuthStore } from './authStore';

export interface Course {
  id: string;
  section_number: string;
  faculty_id: string;
  enrollment_id?: string;
}

export interface Assignment {
  id: string;
  title: string;
  description: string;
  allowed_pod_id: string;
  max_marks: number;
  due_date: string | null;
}

export interface Submission {
  submission_id: string;
  assignment_id: string;
  language: string;
  status: string;
  submitted_at: string;
  marks_awarded: number | null;
  tests_passed: number;
  tests_total: number;
}

interface CourseState {
  courses: Course[];
  assignments: Record<string, Assignment[]>;
  submissions: Submission[];
  credits: { remaining: number; tier: string } | null;
  loading: boolean;
  error: string | null;
  loadCourses: () => Promise<void>;
  loadAssignments: (courseId: string) => Promise<void>;
  loadSubmissions: () => Promise<void>;
  loadCredits: () => Promise<void>;
}

export const useCourseStore = create<CourseState>((set, _get) => ({
  courses: [],
  assignments: {},
  submissions: [],
  credits: null,
  loading: false,
  error: null,

  loadCourses: async () => {
    set({ loading: true, error: null });
    try {
      const role = useAuthStore.getState().user?.role;

      let courses: any[];
      if (role === 'faculty') {
        courses = await api.getTeacherCourses();
      } else {
        courses = await api.getStudentCourses();
      }
      set({ courses, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  loadAssignments: async (courseId: string) => {
    try {
      const assignments = await api.getStudentAssignments(courseId);
      set((state) => ({
        assignments: { ...state.assignments, [courseId]: assignments },
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  loadSubmissions: async () => {
    try {
      const submissions = await api.getMySubmissions();
      set({ submissions });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  loadCredits: async () => {
    try {
      const data = await api.getBillingCredits();
      set({
        credits: {
          remaining: data.compute_credits_remaining,
          tier: data.subscription_tier,
        },
      });
    } catch {
      // billing may fail silently
    }
  },
}));
