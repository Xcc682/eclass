import { api } from "./request";

export interface CommunityAttachment {
  id: string;
  name: string;
  mime_type: string;
  size: number;
  url: string;
}
export interface CommunityReply {
  id: string;
  content: string;
  author: string;
  author_id: string;
  avatar_url: string;
  author_role: string;
  is_teacher: boolean;
  parent_reply_id?: string | null;
  accepted?: boolean;
  likes: number;
  liked: boolean;
  can_edit: boolean;
  created_at: string;
  updated_at: string;
}
export interface CommunityPost {
  id: string;
  title: string;
  content: string;
  excerpt: string;
  category: string;
  is_question: boolean;
  resolved: boolean;
  accepted_reply_id?: string | null;
  author_id: string;
  author: string;
  avatar_url: string;
  author_role: string;
  likes: number;
  replies: number;
  favorites: number;
  views: number;
  liked: boolean;
  favorited: boolean;
  can_edit: boolean;
  pinned: boolean;
  moderation_status: string;
  attachments: CommunityAttachment[];
  created_at: string;
  updated_at: string;
  reply_list?: CommunityReply[];
}
export interface PageInfo {
  page: number;
  page_size: number;
  total: number;
}
export interface CommunityFeed {
  items: CommunityPost[];
  pagination: PageInfo;
  topics: string[];
  followed_topics: string[];
  summary?: { unread_notifications: number; active_tasks: number };
}
export interface RubricCriterion {
  id: string;
  title: string;
  description: string;
  weight: number;
}
export interface RubricScore {
  criterion_id: string;
  score: number;
  comment: string;
}
export interface TaskSubmission {
  id: string;
  content: string;
  status: "draft" | "submitted" | "reviewed";
  score?: number | null;
  feedback: string;
  next_step: string;
  rubric_scores: RubricScore[];
  attachments: CommunityAttachment[];
  submitted_at?: string | null;
  updated_at?: string | null;
  user_id?: string;
  user_name?: string;
}
export interface TeacherTask {
  id: string;
  title: string;
  description: string;
  deadline: string;
  deadline_at?: string | null;
  status: "draft" | "published" | "expired" | "closed";
  creator_id?: string;
  can_manage: boolean;
  submission?: TaskSubmission | null;
  rubric: RubricCriterion[];
  attachments: CommunityAttachment[];
  created_at: string;
}
export interface CommunityNotification {
  id: string;
  type: string;
  title: string;
  content: string;
  resource_type: "post" | "task";
  resource_id: string;
  is_read: boolean;
  created_at: string;
}
export interface TopicState {
  name: string;
  followed: boolean;
  posts: number;
}
export interface ModerationReport {
  id: string;
  target_type: "post" | "reply";
  target_id: string;
  reason: string;
  detail: string;
  status: "pending" | "resolved" | "dismissed";
  created_at: string;
}

function query(params: Record<string, string | number | undefined>) {
  const value = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(
      ([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`,
    )
    .join("&");
  return value ? `?${value}` : "";
}
function uploadFile<T>(file: any, purpose: "post_image" | "task"): Promise<T> {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync("token");
    (uni as any).uploadFile({
      url: `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/community/attachments/upload`,
      filePath: typeof file === "string" ? file : undefined,
      file,
      name: "file",
      formData: { purpose },
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (response: any) => {
        let result: any;
        try {
          result =
            typeof response.data === "string"
              ? JSON.parse(response.data)
              : response.data;
        } catch {
          return reject(new Error("上传响应格式错误"));
        }
        if ((response.statusCode || 200) >= 400)
          return reject(
            new Error(
              typeof result.detail === "string"
                ? result.detail
                : result.detail?.message || "上传失败",
            ),
          );
        resolve(result.data);
      },
      fail: (error: any) => reject(new Error(error.errMsg || "上传失败")),
    });
  });
}

export const communityApi = {
  feed: (
    params: {
      section?: string;
      sort_by?: string;
      topic?: string;
      q?: string;
      page?: number;
      page_size?: number;
    } = {},
  ) => api.get<CommunityFeed>(`/community/feed${query(params)}`),
  getPosts: (kind = "all") =>
    api.get<CommunityPost[]>(`/community/posts?kind=${kind}`),
  getPost: (id: string) => api.get<CommunityPost>(`/community/posts/${id}`),
  createPost: (data: {
    title: string;
    content: string;
    category: string;
    is_question: boolean;
    attachment_ids?: string[];
    submission_id?: string;
  }) => api.post<CommunityPost>("/community/posts", data),
  updatePost: (
    id: string,
    data: {
      title: string;
      content: string;
      category: string;
      attachment_ids?: string[];
    },
  ) => api.put<CommunityPost>(`/community/posts/${id}`, data),
  deletePost: (id: string) => api.delete(`/community/posts/${id}`),
  reply: (
    id: string,
    data: { content: string; parent_reply_id?: string; submission_id?: string },
  ) => api.post<CommunityReply>(`/community/posts/${id}/replies`, data),
  deleteReply: (id: string) => api.delete(`/community/replies/${id}`),
  resolve: (postId: string, replyId: string) =>
    api.post(`/community/posts/${postId}/resolve/${replyId}`),
  like: (id: string) =>
    api.post<{ likes: number; liked: boolean }>(`/community/posts/${id}/like`),
  unlike: (id: string) =>
    api.delete<{ likes: number; liked: boolean }>(
      `/community/posts/${id}/like`,
    ),
  favorite: (id: string) =>
    api.post<{ favorites: number; favorited: boolean }>(
      `/community/posts/${id}/favorite`,
    ),
  unfavorite: (id: string) =>
    api.delete<{ favorites: number; favorited: boolean }>(
      `/community/posts/${id}/favorite`,
    ),
  likeReply: (id: string) =>
    api.post<{ likes: number; liked: boolean }>(
      `/community/replies/${id}/like`,
    ),
  unlikeReply: (id: string) =>
    api.delete<{ likes: number; liked: boolean }>(
      `/community/replies/${id}/like`,
    ),
  topics: () => api.get<TopicState[]>("/community/topics"),
  followTopic: (topic: string) =>
    api.post(`/community/topics/${encodeURIComponent(topic)}/follow`),
  unfollowTopic: (topic: string) =>
    api.delete(`/community/topics/${encodeURIComponent(topic)}/follow`),
  notifications: (page = 1) =>
    api.get<{
      items: CommunityNotification[];
      unread: number;
      pagination: PageInfo;
    }>(`/community/notifications?page=${page}`),
  readNotification: (id: string) =>
    api.post(`/community/notifications/${id}/read`),
  readAll: () => api.post("/community/notifications/read-all"),
  myCommunity: () =>
    api.get<{
      posts: CommunityPost[];
      favorites: CommunityPost[];
      replied: CommunityPost[];
      followed_topics: string[];
    }>("/community/me"),
  report: (data: {
    target_type: "post" | "reply";
    target_id: string;
    reason: string;
    detail?: string;
  }) => api.post("/community/reports", data),
  moderationReports: (status = "pending") =>
    api.get<ModerationReport[]>(
      `/community/moderation/reports${query({ status_filter: status })}`,
    ),
  moderate: (
    id: string,
    data: { action: "hide" | "restore" | "dismiss"; resolution: string },
  ) => api.put(`/community/moderation/reports/${id}`, data),
  upload: (file: any, purpose: "post_image" | "task") =>
    uploadFile<CommunityAttachment>(file, purpose),
  deleteAttachment: (id: string) => api.delete(`/community/attachments/${id}`),
  getTasks: () => api.get<TeacherTask[]>("/community/tasks"),
  getTask: (id: string) => api.get<TeacherTask>(`/community/tasks/${id}`),
  createTask: (data: any) => api.post<TeacherTask>("/community/tasks", data),
  updateTask: (id: string, data: any) =>
    api.put<TeacherTask>(`/community/tasks/${id}`, data),
  publishTask: (id: string) => api.post(`/community/tasks/${id}/publish`),
  closeTask: (id: string) => api.post(`/community/tasks/${id}/close`),
  saveTaskDraft: (
    id: string,
    data: { content: string; attachment_ids: string[] },
  ) => api.patch<TaskSubmission>(`/community/tasks/${id}/submission`, data),
  submitTask: (
    id: string,
    data: { content: string; attachment_ids: string[] },
  ) =>
    api.post<TaskSubmission>(`/community/tasks/${id}/submission/submit`, data),
  getSubmissions: (id: string, status = "") =>
    api.get<TaskSubmission[]>(
      `/community/tasks/${id}/submissions${query({ status_filter: status })}`,
    ),
  reviewSubmission: (
    id: string,
    data: { rubric_scores: RubricScore[]; feedback: string; next_step: string },
  ) =>
    api.put<TaskSubmission>(`/community/tasks/submissions/${id}/review`, data),
};
