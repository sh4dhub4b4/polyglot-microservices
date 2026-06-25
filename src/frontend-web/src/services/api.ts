import { useAuthStore } from '../store/authStore';

const BASE = '/api/v1';

class ApiClient {
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const { getAuthHeaders } = useAuthStore.getState();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(options.headers as Record<string, string> || {}),
    };

    const res = await fetch(`${BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Request failed: ${res.status}`);
    }

    return res.json();
  }

  // ─── Student ───
  getStudentCourses() {
    return this.request<any[]>('/academic/student/courses');
  }

  getStudentAssignments(courseOfferingId: string) {
    return this.request<any[]>(`/academic/student/courses/${courseOfferingId}/assignments`);
  }

  submitAssignment(assignmentId: string, sourceCode: string, language: string) {
    return this.request<any>(`/academic/student/assignments/${assignmentId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ source_code: sourceCode, language }),
    });
  }

  getMySubmissions() {
    return this.request<any[]>('/academic/student/my-submissions');
  }

  // ─── Teacher ───
  getTeacherCourses() {
    return this.request<any[]>('/academic/teacher/courses');
  }

  createCourse(sectionNumber: string, maxCapacity: number) {
    return this.request<any>('/academic/teacher/courses', {
      method: 'POST',
      body: JSON.stringify({ section_number: sectionNumber, max_capacity: maxCapacity }),
    });
  }

  createAssignment(body: any) {
    return this.request<any>('/academic/teacher/assignments', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  getSubmissions(assignmentId: string) {
    return this.request<any[]>(`/academic/teacher/assignments/${assignmentId}/submissions`);
  }

  gradeSubmission(submissionId: string, marksAwarded: number, feedback: string) {
    return this.request<any>(`/academic/teacher/submissions/${submissionId}/grade`, {
      method: 'PATCH',
      body: JSON.stringify({ marks_awarded: marksAwarded, feedback }),
    });
  }

  // ─── Billing ───
  getBillingCredits() {
    return this.request<any>('/academic/billing/credits');
  }
}

export const api = new ApiClient();
